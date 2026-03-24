from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path


VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".webm", ".mov", ".m4v", ".avi",
}

AUDIO_EXTENSIONS = {
    ".mp3", ".m4a", ".aac", ".opus", ".ogg", ".wav", ".flac",
}

FASTSTART_EXTENSIONS = {
    ".mp4", ".m4v", ".mov",
}

ALREADY_TRIMMED_TOLERANCE_SECONDS = 2.0


class ConsoleTheme:
    RESET = "\033[0m"
    COLORS = {
        "INFO": "\033[94m",
        "PROC": "\033[90m",
        "OK": "\033[1;92m",
        "WARN": "\033[1;93m",
        "ERROR": "\033[1;91m",
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


class ConsoleLogger:
    def __init__(self) -> None:
        self._progress_active = False

    def _terminal_width(self) -> int:
        try:
            return max(40, shutil.get_terminal_size((140, 20)).columns - 1)
        except Exception:
            return 140

    def _finish_progress(self) -> None:
        if self._progress_active:
            sys.stdout.write("\n")
            sys.stdout.flush()
            self._progress_active = False

    def log(self, level: str, message: str, *, file=None) -> None:
        self._finish_progress()
        color = ConsoleTheme.color_for(level)
        reset = ConsoleTheme.RESET if color != ConsoleTheme.RESET else ""
        target = file or sys.stdout
        print(f"{color}{message}{reset}", file=target, flush=True)

    def progress(self, level: str, message: str, *, final: bool = False) -> None:
        width = self._terminal_width()
        padded = message[:width].ljust(width)
        color = ConsoleTheme.color_for(level)
        reset = ConsoleTheme.RESET if color != ConsoleTheme.RESET else ""
        end = "\n" if final else ""
        sys.stdout.write(f"\r{color}{padded}{reset}{end}")
        sys.stdout.flush()
        self._progress_active = not final


CONSOLE = ConsoleLogger()


def fail(message: str) -> None:
    CONSOLE.log("ERROR", f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def info(message: str) -> None:
    CONSOLE.log("INFO", f"[INFO] {message}")


def ok(message: str) -> None:
    CONSOLE.log("OK", f"[OK]   {message}")


def warn(message: str) -> None:
    CONSOLE.log("WARN", f"[WARN] {message}")


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        check=False,
    )


def parse_duration_to_seconds(value: str) -> int:
    raw = value.strip().lower()

    if ":" in raw:
        parts = raw.split(":")
        if len(parts) != 3:
            fail(f"Duración inválida: {value}")
        h, m, s = [int(x) for x in parts]
        return h * 3600 + m * 60 + s

    match = re.fullmatch(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", raw)
    if match and any(group is not None for group in match.groups()):
        h = int(match.group(1) or 0)
        m = int(match.group(2) or 0)
        s = int(match.group(3) or 0)
        return h * 3600 + m * 60 + s

    fail(f"Duración inválida: {value}")
    return 0


def format_seconds(seconds: float) -> str:
    total = int(round(seconds))
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def ffprobe_duration_seconds(path: Path) -> float:
    result = run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            str(path),
        ]
    )
    if result.returncode != 0:
        fail(f"ffprobe falló:\n{result.stderr}")

    try:
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    except Exception as exc:
        fail(f"No se pudo leer duración con ffprobe: {exc}")
        return 0.0


def ffprobe_stream_summary(path: Path) -> str:
    result = run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "stream=index,codec_type,codec_name",
            "-of", "json",
            str(path),
        ]
    )
    if result.returncode != 0:
        return "desconocido"

    try:
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        parts: list[str] = []
        for stream in streams:
            codec_type = stream.get("codec_type", "?")
            codec_name = stream.get("codec_name", "?")
            parts.append(f"{codec_type}:{codec_name}")
        return ", ".join(parts) if parts else "sin streams"
    except Exception:
        return "desconocido"


def file_size_mb(path: Path) -> float:
    return path.stat().st_size / (1024 * 1024)


def build_trim_command(
    input_path: Path,
    temp_output: Path,
    max_seconds: int,
    faststart: bool,
) -> list[str]:
    suffix = input_path.suffix.lower()

    common_prefix = [
        "ffmpeg",
        "-hide_banner",
        "-nostdin",
        "-y",
        "-progress", "pipe:1",
        "-nostats",
        "-loglevel", "error",
        "-fflags", "+genpts",
        "-i", str(input_path),
        "-t", str(max_seconds),
    ]

    if suffix in VIDEO_EXTENSIONS:
        cmd = common_prefix + [
            "-map", "0",
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
        ]
        if faststart and suffix in FASTSTART_EXTENSIONS:
            cmd += ["-movflags", "+faststart"]
        cmd += [str(temp_output)]
        return cmd

    if suffix in AUDIO_EXTENSIONS:
        return common_prefix + [
            "-map", "0:a:0",
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            str(temp_output),
        ]

    fail(f"Extensión no soportada para recorte: {input_path.suffix}")
    return []


def print_progress_line(message: str, *, final: bool = False) -> None:
    CONSOLE.progress("PROC", message, final=final)


def run_ffmpeg_with_progress(cmd: list[str], target_seconds: int) -> None:
    info("Lanzando ffmpeg...")
    info("Comando:")
    CONSOLE.log("PROC", " ".join(f'"{x}"' if " " in x else x for x in cmd))

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )

    if process.stdout is None:
        fail("No se pudo abrir la salida de ffmpeg.")

    last_out_time_ms: int | None = None
    last_speed: str | None = None
    last_fps: str | None = None
    last_size: str | None = None
    last_percent_text = ""
    saw_progress = False

    for raw_line in process.stdout:
        line = raw_line.strip()
        if not line:
            continue

        if "=" in line:
            key, value = line.split("=", 1)

            if key == "out_time_ms":
                try:
                    last_out_time_ms = int(value)
                except ValueError:
                    pass

            elif key == "speed":
                last_speed = value

            elif key == "fps":
                last_fps = value

            elif key == "total_size":
                last_size = value

            elif key == "progress":
                saw_progress = True

                if last_out_time_ms is not None:
                    out_seconds = last_out_time_ms / 1_000_000
                    pct = min(100.0, (out_seconds / target_seconds) * 100.0) if target_seconds > 0 else 0.0
                    speed_txt = last_speed or "?"
                    fps_txt = last_fps or "?"
                    size_txt = last_size or "?"
                    last_percent_text = (
                        f"[FFMPEG] progreso={pct:6.2f}% "
                        f"out_time={format_seconds(out_seconds)} "
                        f"objetivo={format_seconds(target_seconds)} "
                        f"speed={speed_txt} "
                        f"fps={fps_txt} "
                        f"bytes={size_txt}"
                    )
                    print_progress_line(last_percent_text)
                else:
                    last_percent_text = "[FFMPEG] trabajando..."
                    print_progress_line(last_percent_text)

                continue

        if "Enter command:" in line:
            continue

        if not saw_progress:
            CONSOLE.log("PROC", f"[FFMPEG-RAW] {line}")

    returncode = process.wait()

    if last_percent_text:
        print_progress_line(last_percent_text, final=True)

    if returncode != 0:
        fail(f"ffmpeg falló con exit code {returncode}")


def trim_from_start_fast(
    input_path: Path,
    max_seconds: int,
    replace: bool,
    faststart: bool,
    skip_output_probe: bool,
) -> Path:
    if not input_path.exists():
        fail(f"No existe el fichero de entrada: {input_path}")

    suffix = input_path.suffix.lower()
    if suffix not in VIDEO_EXTENSIONS and suffix not in AUDIO_EXTENSIONS:
        fail(f"Extensión no soportada: {input_path.suffix}")

    info(f"Entrada: {input_path}")
    info(f"Tamaño entrada: {file_size_mb(input_path):.2f} MiB")
    info(f"Streams entrada: {ffprobe_stream_summary(input_path)}")

    duration = ffprobe_duration_seconds(input_path)
    info(f"Duración entrada: {duration:.3f}s ({format_seconds(duration)})")
    info(f"Límite pedido   : {max_seconds}s ({format_seconds(max_seconds)})")
    info(f"Tolerancia      : {ALREADY_TRIMMED_TOLERANCE_SECONDS:.3f}s")

    if duration <= (max_seconds + ALREADY_TRIMMED_TOLERANCE_SECONDS):
        ok("El fichero ya está recortado o dentro de tolerancia. No se recorta.")
        return input_path

    suffix = input_path.suffix or ".bin"
    temp_output = input_path.with_name(f"{input_path.stem}.trimmed{suffix}")
    backup_path = input_path.with_name(f"{input_path.name}.bak")

    if temp_output.exists():
        warn(f"Eliminando temporal previo: {temp_output}")
        temp_output.unlink()

    if backup_path.exists():
        warn(f"Eliminando backup previo: {backup_path}")
        backup_path.unlink()

    cmd = build_trim_command(
        input_path=input_path,
        temp_output=temp_output,
        max_seconds=max_seconds,
        faststart=faststart,
    )

    start_ts = time.time()
    run_ffmpeg_with_progress(cmd, max_seconds)
    elapsed = time.time() - start_ts

    if not temp_output.exists():
        fail("ffmpeg terminó sin error pero no generó el fichero recortado.")

    info(f"Temporal generado: {temp_output}")
    info(f"Tamaño temporal  : {file_size_mb(temp_output):.2f} MiB")
    ok(f"Recorte terminado en {elapsed:.2f}s")

    if not skip_output_probe:
        trimmed_duration = ffprobe_duration_seconds(temp_output)
        info(f"Duración salida  : {trimmed_duration:.3f}s ({format_seconds(trimmed_duration)})")
        if trimmed_duration > (max_seconds + 5):
            fail(
                f"El fichero recortado no respetó la duración esperada. "
                f"Esperado <= {max_seconds + 5}s, obtenido={trimmed_duration:.3f}s"
            )
    else:
        warn("Se omite ffprobe final de validación por velocidad (--skip-output-probe).")

    if replace:
        info("Sustituyendo original por fichero recortado...")
        os.replace(input_path, backup_path)
        try:
            os.replace(temp_output, input_path)
        except Exception as exc:
            if backup_path.exists() and not input_path.exists():
                os.replace(backup_path, input_path)
            fail(f"No se pudo sustituir el fichero original: {exc}")

        if backup_path.exists():
            backup_path.unlink()

        ok(f"Original sustituido correctamente: {input_path}")
        return input_path

    ok(f"Salida recortada disponible en: {temp_output}")
    return temp_output


def main() -> None:
    ConsoleTheme.enable_windows_ansi()
    parser = argparse.ArgumentParser(description="Recorta media ambience desde el inicio, rápido y con progreso visible")
    parser.add_argument("--input", required=True, help="Ruta al fichero descargado")
    parser.add_argument("--max-duration", required=True, help="Ej. 3h3m3s o 03:03:03")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Sustituye el fichero original por la versión recortada",
    )
    parser.add_argument(
        "--faststart",
        action="store_true",
        help="Añade +faststart para mp4/m4v/mov. Más compatible para streaming, pero más lento.",
    )
    parser.add_argument(
        "--skip-output-probe",
        action="store_true",
        help="No hace ffprobe final al fichero recortado. Más rápido, pero con menos validación.",
    )
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    max_seconds = parse_duration_to_seconds(args.max_duration)

    result_path = trim_from_start_fast(
        input_path=input_path,
        max_seconds=max_seconds,
        replace=args.replace,
        faststart=args.faststart,
        skip_output_probe=args.skip_output_probe,
    )
    print(result_path, flush=True)


if __name__ == "__main__":
    main()