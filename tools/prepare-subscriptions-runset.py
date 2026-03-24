
from __future__ import annotations

import argparse
import codecs
import json
import re
import subprocess
import sys
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Lock, Thread
from typing import Any
from urllib.parse import parse_qs, urlparse

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from zenoytdl_config import resolve_settings

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = Path(__file__).resolve().parent
CONFIG_USER_DIR = PROJECT_ROOT / "config" / "user"
RUNTIME_BASE_DIR = PROJECT_ROOT / "config" / "runtime"
MODE = "prod"
DOWNLOADS_ROOT = "/downloads"
RUNTIME_DIR = RUNTIME_BASE_DIR / MODE
PROFILES_FILE = CONFIG_USER_DIR / "profiles-custom.yml"
SUBSCRIPTIONS_FILE = CONFIG_USER_DIR / "subscription-custom.yml"
SUBSCRIPTIONS_GENERATED_FILE = RUNTIME_DIR / "subscriptions.generated.yaml"
RUNSET_OUTPUT_FILE = RUNTIME_DIR / "subscriptions.runset.yaml"
STATE_FILE = RUNTIME_DIR / ".recent-items-state.json"
PENDING_STATE_FILE = RUNTIME_DIR / ".recent-items-state.pending.json"

YTDL_CONTAINER = resolve_settings("prod", project_root=PROJECT_ROOT, reference_file=__file__).ytdl_container

def build_media_rules(downloads_root: str) -> dict[str, dict[str, Any]]:
    return {
        "canales-youtube": {"dir": f"{downloads_root}/Canales-youtube/{{subscription_root}}", "exts": {".mp4", ".mkv", ".webm"}},
        "podcast": {"dir": f"{downloads_root}/Podcast/{{subscription_root}}/{{source_target}}", "exts": {".mp3"}},
        "tv-serie": {"dir": f"{downloads_root}/TV-Serie/{{subscription_root}}", "exts": {".mp4", ".mkv", ".webm"}},
        "music-playlist": {"dir": f"{downloads_root}/Music-Playlist/{{subscription_root}}", "exts": {".mp3"}},
        "ambience-video": {"dir": f"{downloads_root}/Ambience-Video/{{subscription_root}}", "exts": {".mp4", ".mkv", ".webm", ".mov", ".m4v", ".avi"}},
        "ambience-audio": {"dir": f"{downloads_root}/Ambience-Audio/{{subscription_root}}", "exts": {".mp3", ".m4a", ".aac", ".opus", ".ogg", ".wav", ".flac"}},
    }

MEDIA_RULES = build_media_rules(DOWNLOADS_ROOT)

def configure_runtime_context(project_root: Path | None, mode: str, downloads_root: str | None) -> None:
    global PROJECT_ROOT, TOOLS_DIR, CONFIG_USER_DIR, RUNTIME_BASE_DIR, MODE
    global DOWNLOADS_ROOT, RUNTIME_DIR, PROFILES_FILE, SUBSCRIPTIONS_FILE
    global SUBSCRIPTIONS_GENERATED_FILE, RUNSET_OUTPUT_FILE, STATE_FILE, PENDING_STATE_FILE, MEDIA_RULES, YTDL_CONTAINER
    settings = resolve_settings(mode, project_root=project_root, downloads_root_override=downloads_root, reference_file=__file__)
    PROJECT_ROOT = settings.project_root
    TOOLS_DIR = PROJECT_ROOT / "tools"
    CONFIG_USER_DIR = settings.config_user_dir
    RUNTIME_BASE_DIR = settings.runtime_base_dir
    MODE = settings.mode
    DOWNLOADS_ROOT = settings.downloads_root
    RUNTIME_DIR = settings.runtime_dir
    YTDL_CONTAINER = settings.ytdl_container
    PROFILES_FILE = CONFIG_USER_DIR / "profiles-custom.yml"
    SUBSCRIPTIONS_FILE = CONFIG_USER_DIR / "subscription-custom.yml"
    SUBSCRIPTIONS_GENERATED_FILE = RUNTIME_DIR / "subscriptions.generated.yaml"
    RUNSET_OUTPUT_FILE = RUNTIME_DIR / "subscriptions.runset.yaml"
    STATE_FILE = RUNTIME_DIR / ".recent-items-state.json"
    PENDING_STATE_FILE = RUNTIME_DIR / ".recent-items-state.pending.json"
    MEDIA_RULES = build_media_rules(DOWNLOADS_ROOT)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

PREFIX_ONLY_RE = re.compile(r"^\[[^\[\]\r\n]+\]$")
PROC_PREFIX_RE = re.compile(r"^(\[[^\]]+\]\s)(\[[^\]]+\])(?:\s(.*))?$")
PROC_TAG_RE = re.compile(r"(\[[^\[\]\r\n]+\])")
URL_RE = re.compile(r"(https?://\S+)")


def _proc_tag_color(tag: str) -> str:
    token = tag.strip('[]').lower()
    if 'error' in token or 'fail' in token:
        return "\033[1;91m"
    if 'warn' in token or 'warning' in token:
        return "\033[1;93m"
    if 'download' in token:
        return "\033[1;96m"
    if token in {'info', 'beets'} or token.startswith('info:'):
        return "\033[94m"
    if 'youtube' in token or 'yt-dlp' in token or 'jsc:' in token:
        return "\033[1;95m"
    if token.startswith('ytdl-sub') or 'downloader' in token or 'preset' in token:
        return "\033[1;92m"
    if 'ffmpeg' in token or 'merger' in token or 'metadata' in token:
        return "\033[1;96m"
    return "\033[97m"


def _colorize_proc_text(text: str) -> str:
    if not text:
        return ''
    parts: list[str] = []
    last = 0
    for match in URL_RE.finditer(text):
        before = text[last:match.start()]
        if before:
            parts.append(before)
        parts.append(f"\033[96m{match.group(1)}{ConsoleTheme.RESET}")
        last = match.end()
    tail = text[last:]
    if tail:
        parts.append(tail)
    return ''.join(parts)


def _colorize_proc_message(message: str) -> str:
    if not message:
        return ''
    parts: list[str] = []
    last = 0
    for match in PROC_TAG_RE.finditer(message):
        before = message[last:match.start()]
        if before:
            parts.append(_colorize_proc_text(before))
        tag = match.group(1)
        parts.append(f"{_proc_tag_color(tag)}{tag}{ConsoleTheme.RESET}")
        last = match.end()
    tail = message[last:]
    if tail:
        parts.append(_colorize_proc_text(tail))
    return ''.join(parts)


def _format_console_line(level: str | None, line: str) -> str:
    if level != 'PROC':
        color = ConsoleTheme.color_for(level)
        reset = ConsoleTheme.RESET if color != ConsoleTheme.RESET else ''
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


@dataclass
class ProcResult:
    returncode: int
    stdout: str
    stderr: str


class ConsoleTheme:
    RESET = "\033[0m"
    COLORS = {
        "STEP": "\033[1;96m",
        "INFO": "\033[94m",
        "PROC": "\033[90m",
        "OK": "\033[1;92m",
        "WARN": "\033[1;93m",
        "ERROR": "\033[1;91m",
        "FAIL": "\033[1;91m",
        "RUN": "\033[1;92m",
        "SKIP": "\033[1;93m",
    }

    @classmethod
    def enable_windows_ansi(cls) -> None:
        import os
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

    @classmethod
    def print(cls, level: str, message: str, *, file=None) -> None:
        color = cls.color_for(level)
        reset = cls.RESET if color != cls.RESET else ""
        print(f"{color}{message}{reset}", file=file, flush=True)


class ConsoleLogger:
    def __init__(self) -> None:
        self._lock = Lock()
        self._progress_active = False

    def _terminal_width(self) -> int:
        try:
            import shutil
            return max(40, shutil.get_terminal_size((140, 20)).columns - 1)
        except Exception:
            return 140

    def _finish_progress_locked(self) -> None:
        if self._progress_active:
            sys.stdout.write("\n")
            sys.stdout.flush()
            self._progress_active = False

    def _emit_line_locked(self, level: str, text: str, *, file=None) -> None:
        target = file or sys.stdout
        print(_format_console_line(level, text), file=target, flush=True)

    def log(self, level: str, message: str, *, file=None) -> None:
        with self._lock:
            self._finish_progress_locked()
            self._emit_line_locked(level, message, file=file)

    def progress(self, level: str, message: str) -> None:
        with self._lock:
            width = self._terminal_width()
            padded = message[:width].ljust(width)
            sys.stdout.write(f"\r{_format_console_line(level, padded)}")
            sys.stdout.flush()
            self._progress_active = True

    def finish_progress(self) -> None:
        with self._lock:
            self._finish_progress_locked()


CONSOLE = ConsoleLogger()


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(level: str, message: str) -> None:
    CONSOLE.log(level, f"[{now_str()}] [{level}] {message}")


def info(message: str) -> None:
    log("INFO", message)


def step(message: str) -> None:
    log("STEP", message)


def ok(message: str) -> None:
    log("OK", message)


def warn(message: str) -> None:
    log("WARN", message)


def fail(message: str) -> None:
    CONSOLE.log("ERROR", f"[{now_str()}] [ERROR] {message}", file=sys.stderr)
    sys.exit(1)


def progress_log(level: str, message: str) -> None:
    CONSOLE.progress(level, f"[{now_str()}] [{level}] {message}")


def runset_progress(*, phase: str, current: int, total: int, run_count: int, skip_count: int, preset_name: str | None = None, detail: str | None = None, level_tag: str = "[info]") -> None:
    safe_total = max(total, 1)
    percent = int((current / safe_total) * 100)
    chunks = [
        f"{level_tag} [RUNSET] progreso={percent:3d}% ({current}/{total})",
        f"fase={phase}",
        f"RUN={run_count}",
        f"SKIP={skip_count}",
    ]
    if preset_name:
        chunks.append(preset_name)
    if detail:
        chunks.append(detail)
    progress_log("PROC", " | ".join(chunks))


def _relay_stream(stream, sink: list[bytes], sink_level: str) -> None:
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
                progress_log(sink_level, f"{pending_prefix} {stripped}")
                pending_prefix = None
                return
            log(sink_level, pending_prefix)
            pending_prefix = None

        if _looks_like_prefix_only_text(stripped) and not from_carriage_return:
            pending_prefix = stripped
            return

        if from_carriage_return or _looks_like_progress_text(stripped):
            progress_log(sink_level, stripped)
            return

        log(sink_level, stripped)

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
            log(sink_level, pending_prefix)
    finally:
        stream.close()


def print_separator(title: str | None = None) -> None:
    CONSOLE.finish_progress()
    print("", flush=True)
    ConsoleTheme.print("STEP", f"[{now_str()}] [STEP] ============================================================")
    if title:
        ConsoleTheme.print("STEP", f"[{now_str()}] [STEP] {title}")
        ConsoleTheme.print("STEP", f"[{now_str()}] [STEP] ============================================================")
    print("", flush=True)



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preparar runset inteligente de suscripciones.")
    parser.add_argument("--profile-name", dest="profile_names", action="append", default=[], help="Restringe la evaluación a uno o varios profile_name exactos. Puede repetirse.")
    parser.add_argument("--mode", choices=["prod", "test"], default="prod", help="Selecciona el runtime objetivo: prod o test.")
    parser.add_argument("--project-root", default="", help="Ruta raíz del proyecto zenoytdl. Si no se indica, se autodetecta desde el propio script.")
    parser.add_argument("--downloads-root", default="", help="Raíz de descargas dentro del contenedor. Si no se indica, se toma de config/zenoytdl.yml según el modo.")
    return parser.parse_args()


def load_yaml(path: Path) -> Any:
    if not path.exists():
        fail(f"No existe el fichero requerido: {path}")
    info(f"Cargando YAML: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data if data is not None else {}


def dump_yaml(path: Path, data: Any) -> None:
    info(f"Escribiendo YAML: {path}")
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        yaml.safe_dump(
            data,
            fh,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            width=1000,
        )


def dump_json(path: Path, data: Any) -> None:
    info(f"Escribiendo JSON: {path}")
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        warn(f"No existe estado previo: {path} (se usará vacío)")
        return {}
    try:
        info(f"Cargando JSON: {path}")
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        warn(f"No se pudo leer correctamente {path}; se usará estado vacío")
        return {}


def slugify(value: str) -> str:
    raw = str(value).strip().lower()
    raw = unicodedata.normalize("NFKD", raw)
    raw = raw.encode("ascii", "ignore").decode("ascii")
    raw = raw.replace("_", "-")
    raw = re.sub(r"[^a-z0-9\-]+", "-", raw)
    raw = re.sub(r"-{2,}", "-", raw)
    raw = raw.strip("-")
    return raw or "item"


def parse_max_items(value: Any, default: int = 3) -> int:
    if value is None or value == "":
        return default
    parsed = int(value)
    if parsed < 0:
        raise ValueError(f"max_items no puede ser negativo: {value}")
    return parsed


def extract_source_target_from_url(url: str) -> str:
    url = url.strip()
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)

    if "v" in qs and qs["v"]:
        return slugify(qs["v"][0])
    if "list" in qs and qs["list"]:
        return slugify(qs["list"][0])

    at_match = re.search(r"youtube\.com/@([^/?#]+)", url, re.IGNORECASE)
    if at_match:
        return slugify(at_match.group(1))

    path_parts = [p for p in parsed.path.split("/") if p]
    if path_parts:
        return slugify(path_parts[-1])

    return "source"


def detect_download_strategy(url: str) -> str:
    url_l = url.lower()
    if "watch?v=" in url_l or "youtu.be/" in url_l:
        return "single_video"
    if "playlist?list=" in url_l or "list=" in url_l:
        return "playlist"
    return "channel"


def normalize_profiles(raw: Any) -> dict[str, dict[str, Any]]:
    profiles_list = raw.get("profiles")
    if not isinstance(profiles_list, list):
        raise ValueError("En profiles-custom.yml la clave 'profiles' debe ser una lista.")
    result: dict[str, dict[str, Any]] = {}
    for item in profiles_list:
        if not isinstance(item, dict):
            continue
        name = str(item.get("profile_name", "")).strip()
        if not name:
            continue
        defaults = item.get("defaults") or {}
        result[name] = {
            "profile_name": name,
            "profile_type": str(item.get("profile_type") or name).strip(),
            "defaults": defaults,
        }
    return result


def normalize_subscriptions(raw: Any) -> list[dict[str, Any]]:
    items = raw.get("subscriptions")
    if not isinstance(items, list):
        raise ValueError("En subscription-custom.yml la clave 'subscriptions' debe ser una lista.")
    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        sources = item.get("sources") or []
        if not isinstance(sources, list) or not sources:
            continue
        normalized.append({
            "profile_name": str(item.get("profile_name", "")).strip(),
            "custom_name": str(item.get("custom_name", "")).strip(),
            "sources": sources,
        })
    return normalized


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def run_subprocess(cmd: list[str], *, description: str | None = None) -> ProcResult:
    shown = description or " ".join(cmd)
    step("Ejecutando subprocess...")
    started = time.time()

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
    )

    stdout_chunks: list[bytes] = []
    stderr_chunks: list[bytes] = []

    stdout_thread = Thread(target=_relay_stream, args=(process.stdout, stdout_chunks, "PROC"), daemon=True)
    stderr_thread = Thread(target=_relay_stream, args=(process.stderr, stderr_chunks, "PROC"), daemon=True)

    stdout_thread.start()
    stderr_thread.start()

    process.wait()
    stdout_thread.join()
    stderr_thread.join()

    elapsed = time.time() - started
    info(f"Subprocess terminado en {elapsed:.2f}s con rc={process.returncode}")
    return ProcResult(process.returncode, b"".join(stdout_chunks).decode("utf-8", "replace"), b"".join(stderr_chunks).decode("utf-8", "replace"))


def docker_exec_json(cmd: list[str]) -> Any:
    shown = "docker exec " + YTDL_CONTAINER + " " + " ".join(cmd)
    cp = run_subprocess(["docker", "exec", YTDL_CONTAINER, *cmd], description=shown)
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr.strip() or cp.stdout.strip() or f"docker exec failed: {' '.join(cmd)}")
    try:
        return json.loads(cp.stdout)
    except Exception as exc:
        raise RuntimeError(f"No se pudo parsear JSON de {' '.join(cmd)}: {exc}\nSalida: {cp.stdout[:1000]}") from exc


def docker_exec_json_lines(cmd: list[str]) -> list[dict[str, Any]]:
    shown = "docker exec " + YTDL_CONTAINER + " " + " ".join(cmd)
    cp = run_subprocess(["docker", "exec", YTDL_CONTAINER, *cmd], description=shown)
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr.strip() or cp.stdout.strip() or f"docker exec failed: {' '.join(cmd)}")

    items: list[dict[str, Any]] = []
    for raw_line in cp.stdout.splitlines():
        line = raw_line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            parsed = json.loads(line)
        except Exception:
            continue
        if isinstance(parsed, dict):
            items.append(parsed)
    return items


def docker_count_files(path: str, extensions: set[str]) -> int:
    find_parts = " -o ".join([f"-iname '*{ext}'" for ext in sorted(extensions)])
    script = (
        'if [ -d "{path}" ]; then '
        'find "{path}" -type f \\( {find_parts} \\) | wc -l; '
        'else echo 0; fi'
    ).format(path=path, find_parts=find_parts)
    cp = run_subprocess(
        ["docker", "exec", YTDL_CONTAINER, "sh", "-lc", script],
        description=f"docker_count_files path={path}",
    )
    if cp.returncode != 0:
        warn(f"No se pudo contar ficheros en {path}; se usará 0")
        return 0
    try:
        count = int((cp.stdout or "0").strip())
        info(f"Conteo de ficheros en {path}: {count}")
        return count
    except Exception:
        warn(f"No se pudo parsear el conteo de {path}; se usará 0")
        return 0


def select_entries(entries: list[dict[str, Any]], max_items: int | None = None) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        video_id = str(entry.get("id") or "").strip()
        if not video_id:
            continue
        filtered.append({
            "id": video_id,
            "title": str(entry.get("title") or "").strip(),
            "timestamp": entry.get("timestamp") or entry.get("release_timestamp") or 0,
            "upload_date": str(entry.get("upload_date") or ""),
            "playlist_index": entry.get("playlist_index") if entry.get("playlist_index") is not None else index,
        })

    def sort_key(item: dict[str, Any]) -> tuple[Any, Any, Any]:
        return (
            int(item.get("timestamp") or 0),
            item.get("upload_date") or "",
            -int(item.get("playlist_index") or 0),
        )

    has_dates = any(int(item.get("timestamp") or 0) > 0 or item.get("upload_date") for item in filtered)
    if has_dates:
        filtered.sort(key=sort_key, reverse=True)

    if max_items is None or max_items <= 0:
        return filtered
    return filtered[:max_items]


def get_all_ids(url: str) -> list[str]:
    info(f"Resolviendo TODOS los IDs de la fuente: {url}")
    entries = docker_exec_json_lines([
        "yt-dlp",
        "--dump-json",
        "--flat-playlist",
        "--lazy-playlist",
        "--ignore-errors",
        url,
    ])
    selected = select_entries(entries, max_items=None)
    ids = [item["id"] for item in selected]
    info(f"IDs resueltos (completo): {len(ids)}")
    return ids


def get_latest_top_ids(url: str, max_items: int) -> list[str]:
    info(f"Resolviendo TOP {max_items} IDs recientes de la fuente: {url}")
    entries = docker_exec_json_lines([
        "yt-dlp",
        "--dump-json",
        "--flat-playlist",
        "--lazy-playlist",
        "--playlist-end",
        str(max_items),
        "--ignore-errors",
        url,
    ])
    selected = select_entries(entries, max_items=max_items)
    ids = [item["id"] for item in selected]
    info(f"IDs resueltos (top {max_items}): {len(ids)}")
    return ids


def build_output_dir(profile_key: str, subscription_root: str, source_target: str) -> str | None:
    rule = MEDIA_RULES.get(profile_key)
    if not rule:
        return None
    return rule["dir"].format(subscription_root=subscription_root, source_target=source_target)




def main() -> None:
    ConsoleTheme.enable_windows_ansi()
    args = parse_args()
    requested_profiles = [p.strip() for p in args.profile_names if str(p).strip()]
    requested_profiles_set = set(requested_profiles)
    configure_runtime_context(Path(args.project_root).expanduser() if args.project_root else None, args.mode, args.downloads_root or None)
    print_separator("PREPARAR RUNSET INTELIGENTE DE SUSCRIPCIONES")
    info(f"Project root: {PROJECT_ROOT}")
    info(f"Modo       : {MODE}")
    info(f"Downloads  : {DOWNLOADS_ROOT}")
    info(f"Runtime dir: {RUNTIME_DIR}")
    profiles = normalize_profiles(load_yaml(PROFILES_FILE))
    subscriptions = normalize_subscriptions(load_yaml(SUBSCRIPTIONS_FILE))
    generated = load_yaml(SUBSCRIPTIONS_GENERATED_FILE)
    current_state = load_json(STATE_FILE)
    if requested_profiles:
        info(f"Scope de perfiles solicitado: {', '.join(requested_profiles)}")
        unknown = [p for p in requested_profiles if p not in profiles]
        if unknown:
            raise ValueError(f"Perfiles no definidos: {', '.join(unknown)}")
        subscriptions = [s for s in subscriptions if s["profile_name"] in requested_profiles_set]
    runset: dict[str, Any] = {}
    pending_state: dict[str, Any] = {"sources": {}}
    info(f"Perfiles cargados: {len(profiles)}")
    info(f"Suscripciones cargadas tras filtro: {len(subscriptions)}")
    info(f"Entradas generadas disponibles: {len(generated) if isinstance(generated, dict) else 0}")
    total_sources = sum(len(subscription["sources"]) for subscription in subscriptions)
    info(f"Fuentes totales a evaluar: {total_sources}")
    source_counter = 0
    run_count = 0
    skip_count = 0
    runset_progress(phase="inicio", current=0, total=total_sources, run_count=run_count, skip_count=skip_count, detail="preparando evaluación", level_tag="[info]")
    for subscription_index, subscription in enumerate(subscriptions, start=1):
        profile_name = subscription["profile_name"]
        custom_name = subscription["custom_name"]
        step(f"Suscripción {subscription_index}/{len(subscriptions)}: profile={profile_name} custom_name={custom_name}")
        if profile_name not in profiles:
            raise ValueError(f"Perfil no definido: {profile_name}")
        profile = profiles[profile_name]
        defaults = profile.get("defaults") or {}
        profile_key = slugify(profile["profile_type"])
        subscription_root = slugify(custom_name)
        for source in subscription["sources"]:
            source_counter += 1
            step(f"Evaluando fuente {source_counter}/{total_sources}")
            merged = deep_merge(defaults, source)
            max_items = parse_max_items(merged.get("max_items"), default=3)
            url = str(source.get("url") or "").strip()
            source_target = extract_source_target_from_url(url)
            preset_name = f"{profile_key}-{subscription_root}-{source_target}"
            source_key = preset_name
            generated_entry = generated.get(preset_name)
            if not generated_entry:
                raise ValueError(f"No existe entrada generada para preset {preset_name}")
            print("", flush=True)
            print(f"[{now_str()}] [STEP] ------------------------------------------------------------", flush=True)
            print(f"[{now_str()}] [STEP] [SOURCE {source_counter}/{total_sources}] {preset_name}", flush=True)
            print(f"[{now_str()}] [INFO] profile_name      : {profile_name}", flush=True)
            print(f"[{now_str()}] [INFO] profile_key       : {profile_key}", flush=True)
            print(f"[{now_str()}] [INFO] custom_name       : {custom_name}", flush=True)
            print(f"[{now_str()}] [INFO] subscription_root : {subscription_root}", flush=True)
            print(f"[{now_str()}] [INFO] source_target     : {source_target}", flush=True)
            print(f"[{now_str()}] [INFO] max_items         : {max_items}", flush=True)
            print(f"[{now_str()}] [INFO] url               : {url}", flush=True)
            runset_progress(phase="analizando", current=source_counter, total=total_sources, run_count=run_count, skip_count=skip_count, preset_name=preset_name, detail="calculando estrategia y estado local", level_tag="[info]")
            download_strategy = detect_download_strategy(url)
            include = True
            reason = "fuente no evaluable; se fuerza ejecución"
            selected_ids: list[str] = []
            previous_ids = list((current_state.get("sources") or {}).get(source_key, {}).get("selected_ids") or [])
            output_dir = build_output_dir(profile_key, subscription_root, source_target)
            current_count = docker_count_files(output_dir, MEDIA_RULES[profile_key]["exts"]) if output_dir and profile_key in MEDIA_RULES else 0
            info(f"Estrategia detectada: {download_strategy}")
            info(f"Output dir: {output_dir}")
            info(f"Ficheros locales detectados: {current_count}")
            info(f"IDs previos guardados: {len(previous_ids)}")
            if profile_key in MEDIA_RULES and download_strategy in {"channel", "playlist"}:
                if max_items > 0:
                    runset_progress(phase="resolviendo-ids", current=source_counter, total=total_sources, run_count=run_count, skip_count=skip_count, preset_name=preset_name, detail=f"top recientes max_items={max_items}", level_tag="[download]")
                    selected_ids = get_latest_top_ids(url, max_items)
                    expected_count = min(max_items, len(selected_ids)) if selected_ids else max_items
                    info(f"IDs seleccionados ahora: {len(selected_ids)}")
                    info(f"Ficheros esperados según top: {expected_count}")
                    if not selected_ids:
                        include = True; reason = "no se pudieron resolver ids recientes; se fuerza ejecución"
                    elif current_count < expected_count:
                        include = True; reason = f"faltan ficheros locales ({current_count}/{expected_count})"
                    elif previous_ids == selected_ids:
                        include = False; reason = f"top {max_items} intacto; no toca descargar"
                    else:
                        include = True; reason = "el top reciente cambió; toca descargar y purgar"
                else:
                    runset_progress(phase="resolviendo-ids", current=source_counter, total=total_sources, run_count=run_count, skip_count=skip_count, preset_name=preset_name, detail="fuente completa", level_tag="[download]")
                    selected_ids = get_all_ids(url)
                    info(f"IDs seleccionados ahora (fuente completa): {len(selected_ids)}")
                    if not selected_ids:
                        include = True; reason = "no se pudieron resolver ids de la fuente completa; se fuerza ejecución"
                    elif current_count == 0:
                        include = True; reason = "no hay ficheros locales; toca descarga inicial completa"
                    elif not previous_ids:
                        include = False; reason = "ya existe contenido local; se consolida estado sin reejecutar"
                    elif previous_ids == selected_ids:
                        include = False; reason = "fuente completa intacta; no toca descargar"
                    else:
                        include = True; reason = "la fuente completa cambió; toca descargar"
            elif profile_key in MEDIA_RULES and download_strategy == "single_video":
                selected_ids = [source_target]
                info(f"Single video target: {source_target}")
                if current_count == 0:
                    include = True; reason = "no existe fichero local; toca descarga inicial"
                elif not previous_ids:
                    include = False; reason = "single video ya presente; se consolida estado sin reejecutar"
                elif previous_ids == selected_ids:
                    include = False; reason = "single video intacto; no toca descargar"
                else:
                    include = True; reason = "cambió el estado del single video; toca ejecutar"
            else:
                selected_ids = [source_target] if download_strategy == "single_video" else []
            pending_state["sources"][source_key] = {
                "profile_name": profile_name,
                "profile_type": profile["profile_type"],
                "custom_name": custom_name,
                "url": url,
                "max_items": max_items,
                "download_strategy": download_strategy,
                "selected_ids": selected_ids,
                "output_dir": output_dir,
                "mode": MODE,
                "downloads_root": DOWNLOADS_ROOT,
                "updated_at": now_str(),
            }
            if include:
                run_count += 1
                runset[preset_name] = generated_entry
                runset_progress(phase="decisión", current=source_counter, total=total_sources, run_count=run_count, skip_count=skip_count, preset_name=preset_name, detail=reason, level_tag="[download]")
                ConsoleTheme.print("RUN", f"[{now_str()}] [RUN] {preset_name} -> {reason}")
            else:
                skip_count += 1
                runset_progress(phase="decisión", current=source_counter, total=total_sources, run_count=run_count, skip_count=skip_count, preset_name=preset_name, detail=reason, level_tag="[warning]")
                ConsoleTheme.print("SKIP", f"[{now_str()}] [SKIP] {preset_name} -> {reason}")
    CONSOLE.finish_progress()
    dump_yaml(RUNSET_OUTPUT_FILE, runset)
    dump_json(PENDING_STATE_FILE, pending_state)
    ok(f"[RUNSET] Runset generado: {RUNSET_OUTPUT_FILE}")
    ok(f"[RUNSET] Estado pendiente: {PENDING_STATE_FILE}")
    ok(f"[RUNSET] Resumen final: RUN={run_count} | SKIP={skip_count}")


if __name__ == "__main__":
    main()
