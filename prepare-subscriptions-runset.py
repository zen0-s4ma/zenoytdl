from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import yaml

BASE_DIR = Path(__file__).resolve().parent
PROFILES_FILE = BASE_DIR / "profiles-custom.yml"
SUBSCRIPTIONS_FILE = BASE_DIR / "subscription-custom.yml"
SUBSCRIPTIONS_GENERATED_FILE = BASE_DIR / "subscriptions.generated.yaml"
RUNSET_OUTPUT_FILE = BASE_DIR / "subscriptions.runset.yaml"
STATE_FILE = BASE_DIR / ".recent-items-state.json"
PENDING_STATE_FILE = BASE_DIR / ".recent-items-state.pending.json"

YTDL_CONTAINER = "ytdl-sub"

MEDIA_RULES = {
    "canales-youtube": {
        "dir": "/downloads/Canales-youtube/{subscription_root}",
        "exts": {".mp4", ".mkv", ".webm"},
    },
    "podcast": {
        "dir": "/downloads/Podcast/{subscription_root}/{source_target}",
        "exts": {".mp3"},
    },
    "tv-serie": {
        "dir": "/downloads/TV-Serie/{subscription_root}",
        "exts": {".mp4", ".mkv", ".webm"},
    },
    "music-playlist": {
        "dir": "/downloads/Music-Playlist/{subscription_root}",
        "exts": {".mp3"},
    },
    "ambience-video": {
        "dir": "/downloads/Ambience-Video/{subscription_root}",
        "exts": {".mp4", ".mkv", ".webm", ".mov", ".m4v", ".avi"},
    },
    "ambience-audio": {
        "dir": "/downloads/Ambience-Audio/{subscription_root}",
        "exts": {".mp3", ".m4a", ".aac", ".opus", ".ogg", ".wav", ".flac"},
    },
}


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(level: str, message: str) -> None:
    print(f"[{now_str()}] [{level}] {message}", flush=True)


def info(message: str) -> None:
    log("INFO", message)


def step(message: str) -> None:
    log("STEP", message)


def ok(message: str) -> None:
    log("OK", message)


def warn(message: str) -> None:
    log("WARN", message)


def fail(message: str) -> None:
    print(f"[{now_str()}] [ERROR] {message}", file=sys.stderr, flush=True)
    sys.exit(1)


def print_separator(title: str | None = None) -> None:
    print("", flush=True)
    print(f"[{now_str()}] ============================================================", flush=True)
    if title:
        print(f"[{now_str()}] {title}", flush=True)
        print(f"[{now_str()}] ============================================================", flush=True)
    print("", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preparar runset inteligente de suscripciones.")
    parser.add_argument(
        "--profile-name",
        dest="profile_names",
        action="append",
        default=[],
        help="Restringe la evaluación a uno o varios profile_name exactos. Puede repetirse.",
    )
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


def run_subprocess(cmd: list[str], *, description: str | None = None) -> subprocess.CompletedProcess[str]:
    shown = description or " ".join(cmd)
    step(f"Ejecutando subprocess: {shown}")
    started = time.time()
    cp = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    elapsed = time.time() - started
    info(f"Subprocess terminado en {elapsed:.2f}s con rc={cp.returncode}: {shown}")
    if cp.stderr and cp.stderr.strip():
        warn(f"stderr de subprocess ({shown}):\n{cp.stderr.strip()[:1500]}")
    return cp


def docker_exec_json(cmd: list[str]) -> Any:
    shown = "docker exec " + YTDL_CONTAINER + " " + " ".join(cmd)
    cp = run_subprocess(["docker", "exec", YTDL_CONTAINER, *cmd], description=shown)
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr.strip() or cp.stdout.strip() or f"docker exec failed: {' '.join(cmd)}")
    try:
        return json.loads(cp.stdout)
    except Exception as exc:
        raise RuntimeError(f"No se pudo parsear JSON de {' '.join(cmd)}: {exc}\nSalida: {cp.stdout[:1000]}") from exc


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
    data = docker_exec_json([
        "yt-dlp",
        "--dump-single-json",
        "--flat-playlist",
        "--ignore-errors",
        "--no-warnings",
        url,
    ])
    entries = data.get("entries") or []
    selected = select_entries(entries, max_items=None)
    ids = [item["id"] for item in selected]
    info(f"IDs resueltos (completo): {len(ids)}")
    return ids


def get_latest_top_ids(url: str, max_items: int) -> list[str]:
    info(f"Resolviendo TOP {max_items} IDs recientes de la fuente: {url}")
    data = docker_exec_json([
        "yt-dlp",
        "--dump-single-json",
        "--flat-playlist",
        "--ignore-errors",
        "--no-warnings",
        url,
    ])
    entries = data.get("entries") or []
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
    args = parse_args()
    requested_profiles = [p.strip() for p in args.profile_names if str(p).strip()]
    requested_profiles_set = set(requested_profiles)

    print_separator("PREPARAR RUNSET INTELIGENTE DE SUSCRIPCIONES")

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
            print(f"[{now_str()}] ------------------------------------------------------------", flush=True)
            print(f"[{now_str()}] [SOURCE {source_counter}/{total_sources}] {preset_name}", flush=True)
            print(f"[{now_str()}]   profile_name      : {profile_name}", flush=True)
            print(f"[{now_str()}]   profile_key       : {profile_key}", flush=True)
            print(f"[{now_str()}]   custom_name       : {custom_name}", flush=True)
            print(f"[{now_str()}]   subscription_root : {subscription_root}", flush=True)
            print(f"[{now_str()}]   source_target     : {source_target}", flush=True)
            print(f"[{now_str()}]   max_items         : {max_items}", flush=True)
            print(f"[{now_str()}]   url               : {url}", flush=True)

            download_strategy = detect_download_strategy(url)
            include = True
            reason = "fuente no evaluable; se fuerza ejecución"
            selected_ids: list[str] = []

            previous_ids = list((current_state.get("sources") or {}).get(source_key, {}).get("selected_ids") or [])

            output_dir = build_output_dir(profile_key, subscription_root, source_target)
            current_count = (
                docker_count_files(output_dir, MEDIA_RULES[profile_key]["exts"])
                if output_dir and profile_key in MEDIA_RULES
                else 0
            )

            info(f"Estrategia detectada: {download_strategy}")
            info(f"Output dir: {output_dir}")
            info(f"Ficheros locales detectados: {current_count}")
            info(f"IDs previos guardados: {len(previous_ids)}")

            if profile_key in MEDIA_RULES and download_strategy in {"channel", "playlist"}:
                if max_items > 0:
                    selected_ids = get_latest_top_ids(url, max_items)
                    expected_count = min(max_items, len(selected_ids)) if selected_ids else max_items

                    info(f"IDs seleccionados ahora: {len(selected_ids)}")
                    info(f"Ficheros esperados según top: {expected_count}")

                    if not selected_ids:
                        include = True
                        reason = "no se pudieron resolver ids recientes; se fuerza ejecución"
                    elif current_count < expected_count:
                        include = True
                        reason = f"faltan ficheros locales ({current_count}/{expected_count})"
                    elif previous_ids == selected_ids:
                        include = False
                        reason = f"top {max_items} intacto; no toca descargar"
                    else:
                        include = True
                        reason = "el top reciente cambió; toca descargar y purgar"
                else:
                    selected_ids = get_all_ids(url)

                    info(f"IDs seleccionados ahora (fuente completa): {len(selected_ids)}")

                    if not selected_ids:
                        include = True
                        reason = "no se pudieron resolver ids de la fuente completa; se fuerza ejecución"
                    elif current_count == 0:
                        include = True
                        reason = "no hay ficheros locales; toca descarga inicial completa"
                    elif not previous_ids:
                        include = False
                        reason = "ya existe contenido local; se consolida estado sin reejecutar"
                    elif previous_ids == selected_ids:
                        include = False
                        reason = "fuente completa intacta; no toca descargar"
                    else:
                        include = True
                        reason = "la fuente completa cambió; toca descargar"
            elif profile_key in MEDIA_RULES and download_strategy == "single_video":
                selected_ids = [source_target]

                info(f"Single video target: {source_target}")

                if current_count == 0:
                    include = True
                    reason = "no existe fichero local; toca descarga inicial"
                elif not previous_ids:
                    include = False
                    reason = "single video ya presente; se consolida estado sin reejecutar"
                elif previous_ids == selected_ids:
                    include = False
                    reason = "single video intacto; no toca descargar"
                else:
                    include = True
                    reason = "cambió el estado del single video; toca ejecutar"
            else:
                selected_ids = [source_target] if download_strategy == "single_video" else []

            pending_state["sources"][source_key] = {
                "profile_name": profile_name,
                "profile_type": profile["profile_type"],
                "custom_name": custom_name,
                "url": url,
                "max_items": max_items,
                "selected_ids": selected_ids,
                "download_strategy": download_strategy,
            }

            status = "RUN" if include else "SKIP"
            print(f"[{now_str()}] [{status}] {preset_name} -> {reason}", flush=True)

            if include:
                run_count += 1
                runset[preset_name] = generated_entry
            else:
                skip_count += 1

            info(f"Acumulado: RUN={run_count} | SKIP={skip_count}")
            step(f"Fuente {source_counter}/{total_sources} terminada")

    print_separator("ESCRIBIENDO RESULTADOS")

    dump_yaml(RUNSET_OUTPUT_FILE, runset)
    dump_json(PENDING_STATE_FILE, pending_state)

    print("", flush=True)
    ok(f"Runset generado: {RUNSET_OUTPUT_FILE}")
    ok(f"Estado pendiente: {PENDING_STATE_FILE}")
    ok(f"Suscripciones a ejecutar: {len(runset)}")
    ok(f"Resumen final: RUN={run_count} | SKIP={skip_count}")
    print("", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        fail(str(exc))
