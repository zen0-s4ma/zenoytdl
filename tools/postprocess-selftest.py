from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import textwrap
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from zenoytdl_config import resolve_settings

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG = resolve_settings("prod", project_root=PROJECT_ROOT, reference_file=__file__)
YTDL_CONTAINER = CONFIG.ytdl_container
BEETS_CONTAINER = CONFIG.beets_container
REMOTE_RUNTIME_BASE_DIR = CONFIG.remote_runtime_base_dir


class SelfTestError(RuntimeError):
    pass


def ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(level: str, message: str) -> None:
    print(f"[{ts()}] [{level}] {message}", flush=True)


class Runner:
    def __init__(self) -> None:
        self.created_local_paths: list[Path] = []
        self.cleanup_tasks: list[tuple[str, list[str]]] = []

    def run(self, cmd: list[str], *, allow_failure: bool = False) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout:
            for line in result.stdout.splitlines():
                if line.strip():
                    log("PROC", line)
        if result.stderr:
            for line in result.stderr.splitlines():
                if line.strip():
                    log("PROC", line)
        if result.returncode != 0 and not allow_failure:
            raise SelfTestError(f"Comando falló ({result.returncode}): {' '.join(cmd)}")
        return result

    def add_cleanup(self, label: str, cmd: list[str]) -> None:
        self.cleanup_tasks.append((label, cmd))

    def cleanup(self) -> None:
        for path in reversed(self.created_local_paths):
            try:
                if path.is_file():
                    path.unlink(missing_ok=True)
                elif path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
            except Exception:
                pass
        for label, cmd in reversed(self.cleanup_tasks):
            try:
                self.run(cmd, allow_failure=True)
            except Exception:
                pass


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Autotest de postprocesados de ZenoYTDL")
    parser.add_argument("--mode", choices=["prod", "test"], default="prod", help="Modo a usar para resolver rutas y runtime.")
    parser.add_argument("--project-root", default="", help="Ruta raíz del proyecto zenoytdl. Si no se indica, se autodetecta desde el propio script.")
    parser.add_argument("--downloads-root", default="", help="Raíz de descargas dentro del contenedor. Si no se indica, se toma de config/zenoytdl.yml según el modo.")
    return parser


def _ffprobe_tags(runner: Runner, remote_file: str) -> dict[str, str]:
    result = runner.run(
        [
            "docker", "exec", YTDL_CONTAINER,
            "ffprobe", "-v", "error",
            "-show_entries", "format_tags=artist,title,album,genre",
            "-of", "json",
            remote_file,
        ]
    )
    data = json.loads(result.stdout or "{}")
    tags = ((data.get("format") or {}).get("tags") or {})
    return {str(k).lower(): str(v) for k, v in tags.items()}


def _ffprobe_duration(runner: Runner, remote_file: str) -> float:
    result = runner.run(
        [
            "docker", "exec", YTDL_CONTAINER,
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            remote_file,
        ]
    )
    data = json.loads(result.stdout or "{}")
    return float(((data.get("format") or {}).get("duration")) or 0.0)


def run_music_metadata_selftest(runner: Runner, project_root: Path, mode: str, downloads_root: str) -> None:
    log("STEP", "============================================================")
    log("STEP", "POSTPROCESS SELFTEST: BEETS METADATA")
    log("STEP", "============================================================")

    remote_root = f"{downloads_root}/__postprocess-selftest__/music"
    remote_file = f"{remote_root}/metallica nothing else matters.mp3"
    runtime_tmp_dir = project_root / "config" / "runtime" / mode / "__postprocess_selftest__"
    runtime_tmp_dir.mkdir(parents=True, exist_ok=True)
    runner.created_local_paths.append(runtime_tmp_dir)

    beets_config_local = runtime_tmp_dir / "beets-postprocess-selftest.yaml"
    remote_runtime_dir = f"{REMOTE_RUNTIME_BASE_DIR.rstrip('/')}/{mode}"
    beets_library_remote = f"{remote_runtime_dir}/__postprocess_selftest__/beets-selftest.db"
    beets_log_remote = f"{remote_runtime_dir}/__postprocess_selftest__/beets-selftest.log"
    beets_config_remote = "/tmp/beets-postprocess-selftest.yaml"
    beets_config_local.write_text(
        textwrap.dedent(
            f"""
            directory: {remote_root}
            library: {beets_library_remote}
            logfile: {beets_log_remote}
            import:
              move: no
              copy: no
              write: yes
              quiet_fallback: skip
              timid: no
              none_rec_action: asis
            match:
              strong_rec_thresh: 0.10
            """
        ).strip() + "\n",
        encoding="utf-8",
    )
    runner.created_local_paths.append(beets_config_local)

    runner.add_cleanup(
        "cleanup-selftest-downloads",
        ["docker", "exec", YTDL_CONTAINER, "sh", "-lc", f"rm -rf '{downloads_root}/__postprocess-selftest__'"],
    )
    runner.add_cleanup(
        "cleanup-selftest-beets-config",
        ["docker", "exec", BEETS_CONTAINER, "rm", "-f", beets_config_remote],
    )

    log("INFO", "Creando MP3 sintético sin metadata...")
    runner.run(
        [
            "docker", "exec", YTDL_CONTAINER, "sh", "-lc",
            "mkdir -p '{root}' && ffmpeg -hide_banner -loglevel error -y "
            "-f lavfi -i sine=frequency=440:duration=4 "
            "-map_metadata -1 -metadata title= -metadata artist= -metadata album= -metadata genre= "
            "-c:a libmp3lame '{file}'".format(root=remote_root, file=remote_file),
        ]
    )

    before_tags = _ffprobe_tags(runner, remote_file)
    if before_tags.get("artist") or before_tags.get("title"):
        raise SelfTestError("El MP3 sintético ya contiene metadata antes de pasar por beets")
    log("OK", "MP3 de prueba creado sin artist/title embebidos.")

    log("INFO", "Copiando configuración temporal de beets...")
    runner.run(["docker", "cp", str(beets_config_local), f"{BEETS_CONTAINER}:{beets_config_remote}"])

    log("INFO", "Importando el archivo en beets...")
    runner.run(["docker", "exec", BEETS_CONTAINER, "beet", "-c", beets_config_remote, "import", "-q", "-s", remote_root])

    log("INFO", "Aplicando metadata con beets...")
    runner.run(
        [
            "docker", "exec", BEETS_CONTAINER,
            "beet", "-c", beets_config_remote,
            "modify", "-y", "-w",
            f"path:{remote_root}",
            "artist=Metallica",
            "title=Nothing Else Matters",
            "album=Metallica",
            "genre=Metal",
        ]
    )

    after_tags = _ffprobe_tags(runner, remote_file)
    if after_tags.get("artist") != "Metallica":
        raise SelfTestError(f"Beets no escribió artist correctamente: {after_tags}")
    if after_tags.get("title") != "Nothing Else Matters":
        raise SelfTestError(f"Beets no escribió title correctamente: {after_tags}")
    log("OK", "Beets ha escrito metadata correctamente en el MP3 sintético.")



def run_trim_selftest(runner: Runner, project_root: Path, downloads_root: str) -> None:
    log("STEP", "============================================================")
    log("STEP", "POSTPROCESS SELFTEST: TRIM AMBIENCE")
    log("STEP", "============================================================")

    remote_root = f"{downloads_root}/__postprocess-selftest__/ambience-video"
    remote_file = f"{remote_root}/selftest-trim.mkv"
    trim_remote = "/tmp/trim-ambience-video-selftest.py"
    trim_local = project_root / "tools" / "trim-ambience-video.py"
    if not trim_local.exists():
        raise SelfTestError(f"No existe trim-ambience-video.py en {trim_local}")

    runner.add_cleanup(
        "cleanup-selftest-trim-script",
        ["docker", "exec", YTDL_CONTAINER, "rm", "-f", trim_remote],
    )

    log("INFO", "Creando MKV sintético de 12 segundos...")
    runner.run(
        [
            "docker", "exec", YTDL_CONTAINER, "sh", "-lc",
            "mkdir -p '{root}' && ffmpeg -hide_banner -loglevel error -y "
            "-f lavfi -i color=c=black:s=640x360:r=25:d=12 "
            "-f lavfi -i sine=frequency=880:duration=12 "
            "-shortest -c:v libx264 -preset ultrafast -pix_fmt yuv420p -c:a aac '{file}'".format(root=remote_root, file=remote_file),
        ]
    )

    duration_before = _ffprobe_duration(runner, remote_file)
    if duration_before < 10.0:
        raise SelfTestError(f"Duración inicial inesperada para el MKV sintético: {duration_before:.2f}s")
    log("OK", f"MKV sintético creado correctamente ({duration_before:.2f}s).")

    log("INFO", "Copiando trim-ambience-video.py al contenedor...")
    runner.run(["docker", "cp", str(trim_local), f"{YTDL_CONTAINER}:{trim_remote}"])

    log("INFO", "Ejecutando trim sobre el MKV sintético...")
    runner.run(
        [
            "docker", "exec", YTDL_CONTAINER,
            "python", trim_remote,
            "--input", remote_file,
            "--max-duration", "00:00:05",
            "--replace",
            "--skip-output-probe",
        ]
    )

    duration_after = _ffprobe_duration(runner, remote_file)
    if duration_after > 6.0:
        raise SelfTestError(f"El trim no ha reducido el vídeo lo suficiente: {duration_after:.2f}s")
    log("OK", f"Trim correcto. Duración final: {duration_after:.2f}s")



def main() -> int:
    args = build_arg_parser().parse_args()
    settings = resolve_settings(args.mode, project_root=Path(args.project_root).expanduser() if args.project_root else None, downloads_root_override=args.downloads_root or None, reference_file=__file__)
    global YTDL_CONTAINER, BEETS_CONTAINER, REMOTE_RUNTIME_BASE_DIR
    YTDL_CONTAINER = settings.ytdl_container
    BEETS_CONTAINER = settings.beets_container
    REMOTE_RUNTIME_BASE_DIR = settings.remote_runtime_base_dir
    runner = Runner()
    project_root = settings.project_root
    started = time.time()
    try:
        log("STEP", "============================================================")
        log("STEP", "INICIO AUTOTEST DE POSTPROCESADOS")
        log("STEP", "============================================================")
        log("INFO", f"Project root: {project_root}")
        log("INFO", f"Config YAML: {settings.config_file}")
        log("INFO", f"Mode: {settings.mode}")
        log("INFO", f"Downloads root: {settings.downloads_root}")

        run_music_metadata_selftest(runner, project_root, settings.mode, settings.downloads_root)
        run_trim_selftest(runner, project_root, settings.downloads_root)

        elapsed = time.time() - started
        log("OK", f"Autotest de postprocesados completado correctamente en {elapsed:.2f}s")
        return 0
    except Exception as exc:
        log("ERROR", f"Autotest de postprocesados falló: {exc}")
        return 1
    finally:
        runner.cleanup()
        log("INFO", "Limpieza del autotest de postprocesados completada.")


if __name__ == "__main__":
    raise SystemExit(main())
