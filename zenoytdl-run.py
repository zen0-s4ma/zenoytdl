from __future__ import annotations

import argparse
import codecs
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Iterable

from zenoytdl_config import resolve_settings

PROJECT_ROOT = Path(__file__).resolve().parent
TOOLS_DIR = PROJECT_ROOT / "tools"
POSTPROCESS_SELFTEST_SCRIPT = TOOLS_DIR / "postprocess-selftest.py"
CONFIG = resolve_settings("prod", project_root=PROJECT_ROOT)
CONFIG_USER_DIR = CONFIG.config_user_dir
RUNTIME_BASE_DIR = CONFIG.runtime_base_dir
YTDL_CONTAINER = CONFIG.ytdl_container
BEETS_CONTAINER = CONFIG.beets_container
CONTAINER_PROJECT_ROOT = CONFIG.container_project_root

VALID_PROFILES = [
    "Canales-youtube",
    "Podcast",
    "TV-Serie",
    "Music-Playlist",
    "Ambience-Video",
    "Ambience-Audio",
]

PROFILE_TYPE_SLUG = {
    "Canales-youtube": "canales-youtube",
    "Podcast": "podcast",
    "TV-Serie": "tv-serie",
    "Music-Playlist": "music-playlist",
    "Ambience-Video": "ambience-video",
    "Ambience-Audio": "ambience-audio",
}


class ConsoleTheme:
    RESET = "\033[0m"
    COLORS = {
        "STEP": "\033[1;96m",
        "SUMMARY": "\033[1;95m",
        "INFO": "\033[94m",
        "PROC": "\033[90m",
        "OK": "\033[1;92m",
        "WARN": "\033[1;93m",
        "ERROR": "\033[1;91m",
        "FAIL": "\033[1;91m",
    }

    @classmethod
    def enable_windows_ansi(cls) -> None:
        if os.name != "nt":
            return
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)
            if handle == 0:
                return
            mode = ctypes.c_uint32()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)) == 0:
                return
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
        except Exception:
            pass

    @classmethod
    def color_for(cls, level: str | None) -> str:
        if not level:
            return cls.RESET
        return cls.COLORS.get(level, cls.RESET)


class RunnerError(RuntimeError):
    pass


@dataclass
class ProfileResult:
    profile_name: str
    ok: bool
    had_runset_entries: bool
    dry_run: bool
    mode: str
    message: str
    elapsed_seconds: float
    postprocess_seconds: float
    has_specific_postprocess: bool


@dataclass
class RuntimeContext:
    mode: str
    downloads_root: str
    runtime_dir: Path
    logs_root: Path
    state_file: Path
    pending_state_file: Path
    runset_file: Path
    generated_config_file: Path
    generated_subscriptions_file: Path
    beets_config_file: Path
    trim_script: Path
    remote_runtime_dir: str
    remote_generated_config_file: str
    remote_runset_file: str
    remote_beets_config_file: str
    remote_trim_script: str


ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
PREFIX_ONLY_RE = re.compile(r"^\[[^\[\]\r\n]+\]$")
PROC_PREFIX_RE = re.compile(r"^(\[[^\]]+\]\s)(\[[^\]]+\])(?:\s(.*))?$")
PROC_TAG_RE = re.compile(r"(\[[^\[\]\r\n]+\])")
URL_RE = re.compile(r"(https?://\S+)")


def build_runtime_context(mode: str, downloads_root: str | None = None) -> RuntimeContext:
    normalized_mode = str(mode).strip().lower()
    if normalized_mode not in {"prod", "test"}:
        raise RunnerError(f"Modo no soportado: {mode}")

    settings = resolve_settings(normalized_mode, project_root=PROJECT_ROOT, downloads_root_override=downloads_root)
    runtime_dir = settings.runtime_dir
    logs_root = runtime_dir / "logs"
    actual_downloads_root = settings.downloads_root
    remote_runtime_dir = settings.remote_runtime_dir

    return RuntimeContext(
        mode=normalized_mode,
        downloads_root=actual_downloads_root,
        runtime_dir=settings.runtime_dir,
        logs_root=logs_root,
        state_file=runtime_dir / ".recent-items-state.json",
        pending_state_file=runtime_dir / ".recent-items-state.pending.json",
        runset_file=runtime_dir / "subscriptions.runset.yaml",
        generated_config_file=runtime_dir / "config.generated.yaml",
        generated_subscriptions_file=runtime_dir / "subscriptions.generated.yaml",
        beets_config_file=runtime_dir / "beets.music-playlist.yaml",
        trim_script=TOOLS_DIR / "trim-ambience-video.py",
        remote_runtime_dir=remote_runtime_dir,
        remote_generated_config_file=f"{remote_runtime_dir}/config.generated.yaml",
        remote_runset_file=f"{remote_runtime_dir}/subscriptions.runset.yaml",
        remote_beets_config_file=f"{remote_runtime_dir}/beets.music-playlist.yaml",
        remote_trim_script=settings.remote_trim_script,
    )


def profile_download_dirs(ctx: RuntimeContext, profiles: Iterable[str]) -> list[str]:
    base = ctx.downloads_root
    mapping = {
        "Canales-youtube": [f"{base}/Canales-youtube"],
        "Podcast": [f"{base}/Podcast"],
        "TV-Serie": [f"{base}/TV-Serie"],
        "Music-Playlist": [f"{base}/Music-Playlist"],
        "Ambience-Video": [f"{base}/Ambience-Video"],
        "Ambience-Audio": [f"{base}/Ambience-Audio"],
    }
    dirs: list[str] = []
    for profile_name in profiles:
        dirs.extend(mapping[profile_name])
    return dirs


def _proc_tag_color(tag: str) -> str:
    token = tag.strip("[]").lower()
    if "error" in token or "fail" in token:
        return "\033[1;91m"
    if "warn" in token or "warning" in token:
        return "\033[1;93m"
    if "download" in token:
        return "\033[1;96m"
    if token in {"info", "beets"} or token.startswith("info:"):
        return "\033[94m"
    if "youtube" in token or "yt-dlp" in token or "jsc:" in token:
        return "\033[1;95m"
    if token.startswith("ytdl-sub") or "downloader" in token or "preset" in token:
        return "\033[1;92m"
    if "ffmpeg" in token or "merger" in token or "metadata" in token:
        return "\033[1;96m"
    return "\033[97m"


def _colorize_proc_text(text: str) -> str:
    if not text:
        return ""
    parts: list[str] = []
    last = 0
    for match in URL_RE.finditer(text):
        before = text[last : match.start()]
        if before:
            parts.append(before)
        parts.append(f"\033[96m{match.group(1)}{ConsoleTheme.RESET}")
        last = match.end()
    tail = text[last:]
    if tail:
        parts.append(tail)
    return "".join(parts)


def _colorize_proc_message(message: str) -> str:
    if not message:
        return ""
    parts: list[str] = []
    last = 0
    for match in PROC_TAG_RE.finditer(message):
        before = message[last : match.start()]
        if before:
            parts.append(_colorize_proc_text(before))
        tag = match.group(1)
        parts.append(f"{_proc_tag_color(tag)}{tag}{ConsoleTheme.RESET}")
        last = match.end()
    tail = message[last:]
    if tail:
        parts.append(_colorize_proc_text(tail))
    return "".join(parts)


def _format_console_line(level: str | None, line: str) -> str:
    if level != "PROC":
        color = ConsoleTheme.color_for(level)
        reset = ConsoleTheme.RESET if color != ConsoleTheme.RESET else ""
        return f"{color}{line}{reset}"

    match = PROC_PREFIX_RE.match(line)
    if not match:
        return f"\033[90m{line}{ConsoleTheme.RESET}"

    ts_part, level_part, message = match.groups()
    colored_prefix = f"\033[90m{ts_part}\033[1;90m{level_part}{ConsoleTheme.RESET}"
    if not message:
        return colored_prefix
    return f"{colored_prefix} {_colorize_proc_message(message)}"


def _looks_like_progress_text(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if "progreso=" in stripped and "%" in stripped:
        return True
    if stripped.startswith("[download]"):
        return True
    if "] [download]" in stripped:
        return True
    return False


def _looks_like_prefix_only_text(text: str) -> bool:
    return bool(PREFIX_ONLY_RE.fullmatch(text.strip()))


class TeeLogger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("w", encoding="utf-8", newline="\n")
        self._lock = Lock()
        self._progress_active = False

    def close(self) -> None:
        with self._lock:
            self._finish_progress_locked()
            self._fh.close()

    def _terminal_width(self) -> int:
        try:
            return max(40, shutil.get_terminal_size((140, 20)).columns - 1)
        except Exception:
            return 140

    def _finish_progress_locked(self) -> None:
        if self._progress_active:
            sys.stdout.write("\n")
            sys.stdout.flush()
            self._progress_active = False

    def _write_console_locked(self, level: str | None, line: str, *, end: str = "\n", carriage: bool = False) -> None:
        prefix = "\r" if carriage else ""
        sys.stdout.write(f"{prefix}{_format_console_line(level, line)}{end}")
        sys.stdout.flush()

    def _write_file_line_locked(self, line: str) -> None:
        clean_line = ANSI_RE.sub("", line)
        self._fh.write(clean_line + "\n")
        self._fh.flush()
        os.fsync(self._fh.fileno())

    def _write(self, level: str, line: str) -> None:
        with self._lock:
            self._finish_progress_locked()
            self._write_console_locked(level, line)
            self._write_file_line_locked(line)

    def log(self, level: str, message: str) -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._write(level, f"[{now}] [{level}] {message}")

    def progress(self, level: str, message: str) -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{now}] [{level}] {message}"
        with self._lock:
            padded = line[: self._terminal_width()].ljust(self._terminal_width())
            self._write_console_locked(level, padded, end="", carriage=True)
            self._progress_active = True

    def section(self, title: str) -> None:
        bar = "=" * 78
        self.log("STEP", bar)
        self.log("STEP", title)
        self.log("STEP", bar)

    def plain(self, text: str = "", *, level: str = "SUMMARY") -> None:
        with self._lock:
            self._finish_progress_locked()
            self._write_console_locked(level, text)
            self._write_file_line_locked(text)


def _relay_subprocess_stream(stream, logger: TeeLogger, sink: list[bytes], level: str) -> None:
    if stream is None:
        return

    decoder = codecs.getincrementaldecoder("utf-8")("replace")
    current_chars: list[str] = []
    pending_prefix: str | None = None

    def emit_buffer(*, from_carriage_return: bool) -> None:
        nonlocal pending_prefix
        current_text = "".join(current_chars)
        current_chars.clear()
        stripped = current_text.strip()
        if not stripped:
            return

        if pending_prefix:
            if _looks_like_progress_text(stripped):
                logger.progress(level, f"{pending_prefix} {stripped}")
                pending_prefix = None
                return
            logger.log(level, pending_prefix)
            pending_prefix = None

        if _looks_like_prefix_only_text(stripped) and not from_carriage_return:
            pending_prefix = stripped
            return

        if from_carriage_return or _looks_like_progress_text(stripped):
            logger.progress(level, stripped)
            return

        logger.log(level, stripped)

    def handle_text(text: str) -> None:
        for ch in text:
            if ch == "\r":
                emit_buffer(from_carriage_return=True)
                continue
            if ch == "\n":
                emit_buffer(from_carriage_return=False)
                continue
            current_chars.append(ch)

    try:
        while True:
            chunk = stream.read(1)
            if chunk == b"":
                break
            sink.append(chunk)
            handle_text(decoder.decode(chunk))

        tail_text = decoder.decode(b"", final=True)
        if tail_text:
            handle_text(tail_text)

        emit_buffer(from_carriage_return=False)
        if pending_prefix:
            logger.log(level, pending_prefix)
    finally:
        stream.close()


class ZenoYTDLRunner:
    def __init__(self, logger: TeeLogger, ctx: RuntimeContext) -> None:
        self.logger = logger
        self.ctx = ctx

    def run_subprocess(
        self,
        cmd: list[str],
        *,
        label: str,
        cwd: Path | None = None,
        allow_failure: bool = False,
    ) -> int:
        self.logger.log("INFO", f"Ejecutando [{label}]...")
        started = time.time()
        env = dict(os.environ)
        env.setdefault("PYTHONUNBUFFERED", "1")

        process = subprocess.Popen(
            cmd,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
            env=env,
        )

        assert process.stdout is not None
        stdout_chunks: list[bytes] = []
        _relay_subprocess_stream(process.stdout, self.logger, stdout_chunks, "PROC")

        return_code = process.wait()
        elapsed = time.time() - started
        self.logger.log("INFO", f"Fin [{label}] rc={return_code} en {elapsed:.2f}s")
        if return_code != 0 and not allow_failure:
            raise RunnerError(f"Fallo [{label}] con exit code {return_code}")
        return return_code

    def ensure_supported_profile(self, profile_name: str) -> None:
        if profile_name not in VALID_PROFILES:
            raise RunnerError(f"Perfil no válido: {profile_name}. Válidos: {', '.join(VALID_PROFILES)}")

    def clean_environment(self, profiles: list[str], *, restart_ytdl_sub: bool) -> None:
        self.logger.section(f"Limpieza previa del entorno ({self.ctx.mode})")
        self.logger.log("INFO", f"Perfiles en alcance de limpieza: {', '.join(profiles)}")
        self.ctx.runtime_dir.mkdir(parents=True, exist_ok=True)

        for path in [
            self.ctx.runset_file,
            self.ctx.runtime_dir / "subscriptions.runset.filtered.yaml",
            self.ctx.pending_state_file,
            self.ctx.runtime_dir / ".recent-items-state.pending.filtered.json",
            self.ctx.generated_config_file,
            self.ctx.generated_subscriptions_file,
            self.ctx.beets_config_file,
        ]:
            if path.exists():
                path.unlink()
                self.logger.log("OK", f"Eliminado temporal local: {path}")

        empty_state = {"sources": {}}
        self.ctx.state_file.write_text(json.dumps(empty_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.logger.log("OK", f"Estado local reiniciado: {self.ctx.state_file}")

        download_dirs = profile_download_dirs(self.ctx, profiles)
        quoted_dirs = " ".join(f'"{item}"' for item in download_dirs)
        remote_runtime = self.ctx.remote_runtime_dir
        ytdl_script = f"""#!/bin/sh
set -eu
for target in {quoted_dirs}
do
  if [ -d \"$target\" ]; then
    echo \"[INFO] Vaciando contenido de $target\"
    find \"$target\" -mindepth 1 -delete
  fi
done
rm -rf /tmp/ytdl-sub-working-directory/* 2>/dev/null || true
rm -rf /config/.ytdl-sub-working-directory/* 2>/dev/null || true
rm -rf /config/.ytdl-sub-lock 2>/dev/null || true
rm -f {remote_runtime}/subscriptions.runset.yaml 2>/dev/null || true
rm -f {remote_runtime}/subscriptions.runset.filtered.yaml 2>/dev/null || true
rm -f {remote_runtime}/.recent-items-state.pending.json 2>/dev/null || true
rm -f {remote_runtime}/.recent-items-state.pending.filtered.json 2>/dev/null || true
rm -f {self.ctx.remote_trim_script} 2>/dev/null || true
"""
        self._run_docker_script(YTDL_CONTAINER, ytdl_script, label="clean-ytdl-sub")

        settings = resolve_settings(self.ctx.mode, project_root=PROJECT_ROOT, downloads_root_override=self.ctx.downloads_root)
        beets_library = settings.beets_library_path
        beets_log = settings.beets_log_path
        beets_script = f"""#!/bin/sh
set -eu
for target in {quoted_dirs}
do
  if [ -d \"$target\" ]; then
    echo \"[INFO] Vaciando contenido de $target\"
    find \"$target\" -mindepth 1 -delete
  fi
done
rm -rf /tmp/ytdl-sub-working-directory/* 2>/dev/null || true
rm -rf /config/.ytdl-sub-working-directory/* 2>/dev/null || true
rm -rf /config/.ytdl-sub-lock 2>/dev/null || true
rm -f {beets_log} 2>/dev/null || true
rm -f {beets_library} 2>/dev/null || true
"""
        self._run_docker_script(BEETS_CONTAINER, beets_script, label="clean-beets")

        if restart_ytdl_sub:
            self.run_subprocess(["docker", "restart", YTDL_CONTAINER], label="restart-ytdl-sub")
        else:
            self.logger.log("INFO", "No se reinicia ytdl-sub (flag no especificado).")

    def _run_docker_script(self, container: str, script: str, *, label: str) -> None:
        tmp_local = self.ctx.runtime_dir / f".__{label}.sh"
        tmp_local.write_text(script.replace("\r\n", "\n"), encoding="utf-8", newline="\n")
        try:
            tmp_remote = f"/tmp/{tmp_local.name}"
            self.run_subprocess(["docker", "cp", str(tmp_local), f"{container}:{tmp_remote}"], label=f"{label}-cp")
            self.run_subprocess(["docker", "exec", container, "sh", tmp_remote], label=f"{label}-exec")
            self.run_subprocess(["docker", "exec", container, "rm", "-f", tmp_remote], label=f"{label}-rm", allow_failure=True)
        finally:
            tmp_local.unlink(missing_ok=True)

    def _has_runset_entries(self) -> bool:
        if not self.ctx.runset_file.exists():
            return False
        raw = self.ctx.runset_file.read_text(encoding="utf-8").strip()
        return bool(raw and raw not in {"{}", "---", "null"})

    def _promote_pending_state(self) -> None:
        if not self.ctx.pending_state_file.exists():
            self.logger.log("WARN", f"No existe estado pendiente para promover: {self.ctx.pending_state_file}")
            return
        shutil.copyfile(self.ctx.pending_state_file, self.ctx.state_file)
        self.logger.log("OK", f"Estado promovido: {self.ctx.pending_state_file} -> {self.ctx.state_file}")

    def _copy_trim_script(self) -> None:
        self.run_subprocess(["docker", "cp", str(self.ctx.trim_script), f"{YTDL_CONTAINER}:{self.ctx.remote_trim_script}"], label="copy-trim-script")

    def _run_music_postprocess(self) -> None:
        music_root = f"{self.ctx.downloads_root}/Music-Playlist"
        script = f"""#!/bin/sh
set -eu
if [ -d \"{music_root}\" ]; then
  find \"{music_root}\" -mindepth 1 -maxdepth 1 -type d | while read -r d; do
    echo \"[BEETS] $d\"
    beet -v -c \"{self.ctx.remote_beets_config_file}\" import -s -q \"$d\" || true
  done
else
  echo '[WARN] No existe {music_root}'
fi
"""
        self._run_docker_script(BEETS_CONTAINER, script, label="beets-music")

    def _run_ambience_postprocess(self, profile_name: str) -> None:
        if profile_name == "Ambience-Video":
            base_dir = f"{self.ctx.downloads_root}/Ambience-Video"
            find_expr = "\\( -iname '*.mp4' -o -iname '*.mkv' -o -iname '*.webm' -o -iname '*.mov' -o -iname '*.m4v' -o -iname '*.avi' \\)"
        else:
            base_dir = f"{self.ctx.downloads_root}/Ambience-Audio"
            find_expr = "\\( -iname '*.mp3' -o -iname '*.m4a' -o -iname '*.aac' -o -iname '*.opus' -o -iname '*.ogg' -o -iname '*.wav' -o -iname '*.flac' \\)"

        script = f"""#!/bin/sh
set -eu
if [ -d \"{base_dir}\" ]; then
  find \"{base_dir}\" -type f {find_expr} | while IFS= read -r f; do
    echo \"[TRIM] $f\"
    python {self.ctx.remote_trim_script} --input \"$f\" --max-duration 03:03:03 --replace --skip-output-probe
  done
else
  echo '[WARN] No existe {base_dir}'
fi
"""
        self._run_docker_script(YTDL_CONTAINER, script, label=f"trim-{PROFILE_TYPE_SLUG[profile_name]}")

    def run_profile(self, profile_name: str, *, dry_run: bool) -> ProfileResult:
        self.ensure_supported_profile(profile_name)
        started = time.time()
        postprocess_seconds = 0.0
        has_specific_postprocess = profile_name in {"Music-Playlist", "Ambience-Video", "Ambience-Audio"}
        self.logger.section(f"Inicio ejecución perfil: {profile_name}")
        self.logger.log("INFO", f"Project root: {PROJECT_ROOT}")
        self.logger.log("INFO", f"Mode: {self.ctx.mode}")
        self.logger.log("INFO", f"DryRun: {dry_run}")

        try:
            self.run_subprocess(
                [
                    sys.executable,
                    str(TOOLS_DIR / "generate-ytdl-config.py"),
                    "--mode",
                    self.ctx.mode,
                    "--project-root",
                    str(PROJECT_ROOT),
                    "--downloads-root",
                    self.ctx.downloads_root,
                    "--only-profile",
                    PROFILE_TYPE_SLUG[profile_name],
                ],
                label="generate-ytdl-config",
                cwd=PROJECT_ROOT,
            )
            self.run_subprocess(
                [
                    sys.executable,
                    str(TOOLS_DIR / "prepare-subscriptions-runset.py"),
                    "--mode",
                    self.ctx.mode,
                    "--project-root",
                    str(PROJECT_ROOT),
                    "--downloads-root",
                    self.ctx.downloads_root,
                    "--profile-name",
                    profile_name,
                ],
                label="prepare-subscriptions-runset",
                cwd=PROJECT_ROOT,
            )

            has_entries = self._has_runset_entries()
            self.logger.log("INFO", f"Runset con entradas: {has_entries}")

            if profile_name in {"Ambience-Video", "Ambience-Audio"}:
                self._copy_trim_script()

            if dry_run:
                self.logger.log("OK", "Dry-run activo: se omite la descarga real y cualquier postproceso.")
            elif not has_entries:
                self.logger.log("WARN", "El runset está vacío para este perfil; no se ejecuta ytdl-sub.")
            else:
                self.run_subprocess(
                    [
                        "docker",
                        "exec",
                        YTDL_CONTAINER,
                        "ytdl-sub",
                        "--config",
                        self.ctx.remote_generated_config_file,
                        "sub",
                        self.ctx.remote_runset_file,
                    ],
                    label="ytdl-sub-sub",
                )
                self._promote_pending_state()

                if profile_name == "Music-Playlist":
                    post_started = time.time()
                    self._run_music_postprocess()
                    postprocess_seconds += time.time() - post_started
                elif profile_name in {"Ambience-Video", "Ambience-Audio"}:
                    post_started = time.time()
                    self._run_ambience_postprocess(profile_name)
                    postprocess_seconds += time.time() - post_started
                else:
                    self.logger.log("INFO", "Este perfil no requiere postproceso específico.")

            elapsed = time.time() - started
            message = "Perfil completado correctamente."
            self.logger.log("OK", message)
            return ProfileResult(profile_name, True, has_entries, dry_run, self.ctx.mode, message, elapsed, postprocess_seconds, has_specific_postprocess)
        except Exception as exc:
            elapsed = time.time() - started
            message = str(exc)
            self.logger.log("ERROR", message)
            return ProfileResult(profile_name, False, False, dry_run, self.ctx.mode, message, elapsed, postprocess_seconds, has_specific_postprocess)



def _format_duration_compact(seconds: float) -> str:
    total_seconds = max(0, int(round(seconds)))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    if minutes > 0:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


def _build_duration_bar(seconds: float, max_seconds: float, width: int = 16) -> str:
    if max_seconds <= 0:
        return "-"
    filled = max(1, round((seconds / max_seconds) * width)) if seconds > 0 else 0
    return "▓" * filled


def _emit_executive_summary(logger: TeeLogger, results: list[ProfileResult], total_suite_seconds: float) -> None:
    if not results:
        return

    total_postprocess_seconds = sum(result.postprocess_seconds for result in results)
    slowest = max(results, key=lambda item: item.elapsed_seconds)
    fastest = min(results, key=lambda item: item.elapsed_seconds)
    postprocess_candidates = [item for item in results if item.has_specific_postprocess]
    max_postprocess = max(postprocess_candidates, key=lambda item: item.postprocess_seconds, default=None)
    no_postprocess_profiles = [item.profile_name for item in results if not item.has_specific_postprocess]
    max_elapsed = max((item.elapsed_seconds for item in results), default=0.0)
    name_width = max(len(item.profile_name) for item in results) + 2
    bar_width = 16
    separator = "━" * 34

    logger.plain("")
    logger.plain(separator)
    logger.plain("        RESUMEN EJECUTIVO")
    logger.plain(separator)
    logger.plain("")
    logger.plain("⏱️ Duración por perfil")
    logger.plain("")
    for item in results:
        bar = _build_duration_bar(item.elapsed_seconds, max_elapsed, width=bar_width)
        logger.plain(f"{item.profile_name:<{name_width}}{bar:<{bar_width}}  {_format_duration_compact(item.elapsed_seconds)}")

    logger.plain("")
    logger.plain(f"🔧 Postprocesado total:        {_format_duration_compact(total_postprocess_seconds)}")
    logger.plain(f"🕒 Tiempo total de la suite:   {_format_duration_compact(total_suite_seconds)}")
    logger.plain("")
    logger.plain(separator)
    logger.plain("          LECTURA RÁPIDA")
    logger.plain(separator)
    logger.plain("")
    logger.plain("• Perfil más lento:")
    logger.plain(f"  {slowest.profile_name} → {_format_duration_compact(slowest.elapsed_seconds)}")
    logger.plain("")
    logger.plain("• Perfil más rápido:")
    logger.plain(f"  {fastest.profile_name} → {_format_duration_compact(fastest.elapsed_seconds)}")
    logger.plain("")
    logger.plain("• Mayor tiempo de postprocesado:")
    if max_postprocess and max_postprocess.postprocess_seconds > 0:
        logger.plain(f"  {max_postprocess.profile_name} → {_format_duration_compact(max_postprocess.postprocess_seconds)}")
    elif max_postprocess:
        logger.plain(f"  {max_postprocess.profile_name} → 0s")
    else:
        logger.plain("  Ninguno")
    logger.plain("")
    logger.plain("• Sin postproceso específico:")
    if no_postprocess_profiles:
        logger.plain("  " + ", ".join(no_postprocess_profiles))
    else:
        logger.plain("  Ninguno")
    logger.plain("")
    percentage = (total_postprocess_seconds / total_suite_seconds * 100.0) if total_suite_seconds > 0 else 0.0
    logger.plain("• Peso del postprocesado sobre el total:")
    logger.plain(f"  ~{percentage:.1f}%")
    logger.plain("")

def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lanzador oficial de ZenoYTDL.")
    scope = parser.add_mutually_exclusive_group(required=False)
    scope.add_argument("--profile", dest="profiles", action="append", help="Nombre exacto del perfil a ejecutar. Puede repetirse.")
    scope.add_argument("--all-profiles", action="store_true", help="Ejecuta todos los perfiles soportados.")

    clean_scope = parser.add_mutually_exclusive_group(required=False)
    clean_scope.add_argument("--clean", action="store_true", help="Limpia todo el entorno del modo seleccionado antes de empezar.")
    clean_scope.add_argument(
        "--clean-profile",
        "--cleanprofile",
        dest="clean_profile",
        action="store_true",
        help="Limpia solo el ámbito de los perfiles seleccionados antes de empezar.",
    )

    log_scope = parser.add_mutually_exclusive_group(required=False)
    log_scope.add_argument(
        "--clean-logs",
        action="store_true",
        help="Borra los logs antiguos del modo seleccionado antes de arrancar. El log activo nuevo se conserva.",
    )
    log_scope.add_argument("--keep-logs", action="store_true", help="Conserva los logs antiguos. Es el comportamiento por defecto.")

    parser.add_argument("--mode", choices=["prod", "test"], default="prod", help="Selecciona el runtime objetivo: prod o test.")
    parser.add_argument("--downloads-root", default="", help="Raíz de descargas dentro del contenedor. Si no se indica, se toma de config/zenoytdl.yml según el modo.")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", default=True, help="Modo seguro por defecto: genera config y runset, pero no lanza descargas reales ni postprocesos.")
    parser.add_argument("--real-run", dest="dry_run", action="store_false", help="Ejecuta descargas y postprocesos reales.")
    parser.add_argument("--restart-ytdl-sub", action="store_true", help="Reinicia el contenedor ytdl-sub después de la limpieza previa.")
    parser.add_argument(
        "--include-postprocess-tests",
        nargs="?",
        const="continue",
        choices=["continue", "fail"],
        help="Ejecuta primero el autotest de postprocesados. Sin valor usa continue. Valores: continue o fail.",
    )
    return parser


def prepare_log_file(ctx: RuntimeContext, clean_logs: bool) -> Path:
    if clean_logs and ctx.logs_root.exists():
        shutil.rmtree(ctx.logs_root)
    ctx.logs_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return ctx.logs_root / f"zenoytdl-run-{ctx.mode}-{timestamp}.log"


def main() -> int:
    ConsoleTheme.enable_windows_ansi()
    args = build_arg_parser().parse_args()

    profiles = VALID_PROFILES[:] if args.all_profiles or not args.profiles else list(dict.fromkeys(args.profiles or []))
    for profile_name in profiles:
        if profile_name not in VALID_PROFILES:
            print(f"Perfil no válido: {profile_name}. Válidos: {', '.join(VALID_PROFILES)}", file=sys.stderr, flush=True)
            return 2

    ctx = build_runtime_context(mode=args.mode, downloads_root=args.downloads_root or None)
    clean_logs = bool(args.clean_logs)
    log_path = prepare_log_file(ctx, clean_logs=clean_logs)
    logger = TeeLogger(log_path)
    runner = ZenoYTDLRunner(logger, ctx)

    suite_started = time.time()
    try:
        logger.section("Inicio ejecución ZenoYTDL")
        logger.log("INFO", f"Proyecto: {PROJECT_ROOT}")
        logger.log("INFO", f"Config YAML: {CONFIG.config_file}")
        logger.log("INFO", f"Config user: {CONFIG_USER_DIR}")
        logger.log("INFO", f"Runtime dir: {ctx.runtime_dir}")
        logger.log("INFO", f"Perfiles objetivo: {', '.join(profiles)}")
        logger.log("INFO", f"Mode: {ctx.mode}")
        logger.log("INFO", f"DownloadsRoot: {ctx.downloads_root}")
        logger.log("INFO", f"DryRun: {args.dry_run}")
        logger.log("INFO", f"Clean: {args.clean}")
        logger.log("INFO", f"CleanProfile: {args.clean_profile}")
        logger.log("INFO", f"CleanLogs: {args.clean_logs}")
        logger.log("INFO", f"KeepLogs: {args.keep_logs or not args.clean_logs}")
        logger.log("INFO", f"RestartYtdlSub: {args.restart_ytdl_sub}")
        logger.log("INFO", f"IncludePostprocessTests: {args.include_postprocess_tests or 'disabled'}")
        logger.log("INFO", f"Log principal: {log_path}")

        if args.include_postprocess_tests:
            logger.section("Autotest inicial de postprocesados")
            try:
                runner.run_subprocess(
                    [
                        sys.executable,
                        str(POSTPROCESS_SELFTEST_SCRIPT),
                        "--mode",
                        ctx.mode,
                        "--project-root",
                        str(PROJECT_ROOT),
                        "--downloads-root",
                        ctx.downloads_root,
                    ],
                    label="postprocess-selftest",
                    cwd=PROJECT_ROOT,
                )
                logger.log("OK", "Autotest de postprocesados completado correctamente.")
            except Exception as exc:
                if args.include_postprocess_tests == "fail":
                    logger.log("ERROR", f"Autotest de postprocesados fallido en modo estricto: {exc}")
                    return 1
                logger.log("WARN", f"Autotest de postprocesados fallido, pero se continúa: {exc}")

        if args.clean:
            runner.clean_environment(VALID_PROFILES[:], restart_ytdl_sub=args.restart_ytdl_sub)
        elif args.clean_profile:
            runner.clean_environment(profiles, restart_ytdl_sub=args.restart_ytdl_sub)
        else:
            logger.log("INFO", "No se ejecuta limpieza previa.")

        results: list[ProfileResult] = []
        for profile_name in profiles:
            results.append(runner.run_profile(profile_name, dry_run=args.dry_run))

        logger.section("Resumen final de la ejecución")
        ok_count = 0
        for result in results:
            status = "OK" if result.ok else "FAIL"
            logger.log(
                status,
                (
                    f"{result.profile_name} | ok={result.ok} | mode={result.mode} | dry_run={result.dry_run} | "
                    f"runset_con_entradas={result.had_runset_entries} | elapsed={result.elapsed_seconds:.2f}s | {result.message}"
                ),
            )
            if result.ok:
                ok_count += 1

        logger.log("INFO", f"Total perfiles: {len(results)}")
        logger.log("INFO", f"Perfiles OK: {ok_count}")
        logger.log("INFO", f"Perfiles FAIL: {len(results) - ok_count}")
        logger.log("INFO", f"Log único generado: {log_path}")
        _emit_executive_summary(logger, results, time.time() - suite_started)
        return 0 if ok_count == len(results) else 1
    finally:
        logger.close()


if __name__ == "__main__":
    raise SystemExit(main())
