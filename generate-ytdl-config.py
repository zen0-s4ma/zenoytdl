from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import yaml


BASE_DIR = Path(__file__).resolve().parent

PROFILES_FILE = BASE_DIR / "profiles-custom.yml"
SUBSCRIPTIONS_FILE = BASE_DIR / "subscription-custom.yml"

CONFIG_OUTPUT_FILE = BASE_DIR / "config.generated.yaml"
SUBSCRIPTIONS_OUTPUT_FILE = BASE_DIR / "subscriptions.generated.yaml"
BEETS_OUTPUT_FILE = BASE_DIR / "beets.music-playlist.yaml"


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def load_yaml_file(path: Path) -> Any:
    if not path.exists():
        fail(f"No existe el fichero requerido: {path}")
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        return data if data is not None else {}
    except Exception as exc:
        fail(f"No se pudo leer YAML en {path}: {exc}")


def dump_yaml_file(path: Path, data: Any) -> None:
    try:
        with path.open("w", encoding="utf-8", newline="\n") as fh:
            yaml.safe_dump(
                data,
                fh,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
                width=1000,
            )
    except Exception as exc:
        fail(f"No se pudo escribir YAML en {path}: {exc}")


def slugify(value: str) -> str:
    raw = str(value).strip().lower()
    raw = unicodedata.normalize("NFKD", raw)
    raw = raw.encode("ascii", "ignore").decode("ascii")
    raw = raw.replace("_", "-")
    raw = re.sub(r"[^a-z0-9\-]+", "-", raw)
    raw = re.sub(r"-{2,}", "-", raw)
    raw = raw.strip("-")
    return raw or "item"


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

    channel_match = re.search(r"youtube\.com/channel/([^/?#]+)", url, re.IGNORECASE)
    if channel_match:
        return slugify(channel_match.group(1))

    user_match = re.search(r"youtube\.com/user/([^/?#]+)", url, re.IGNORECASE)
    if user_match:
        return slugify(user_match.group(1))

    c_match = re.search(r"youtube\.com/c/([^/?#]+)", url, re.IGNORECASE)
    if c_match:
        return slugify(c_match.group(1))

    short_match = re.search(r"youtu\.be/([^/?#]+)", url, re.IGNORECASE)
    if short_match:
        return slugify(short_match.group(1))

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


def parse_duration_to_seconds(value: str | int | None) -> int | None:
    if value is None or value == "":
        return None

    if isinstance(value, int):
        return value

    raw = str(value).strip().lower()

    simple_match = re.fullmatch(r"(\d+)(s|m|h)?", raw)
    if simple_match:
        amount = int(simple_match.group(1))
        unit = simple_match.group(2) or "s"
        if unit == "s":
            return amount
        if unit == "m":
            return amount * 60
        if unit == "h":
            return amount * 3600

    hms_match = re.fullmatch(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", raw)
    if hms_match and any(group is not None for group in hms_match.groups()):
        hours = int(hms_match.group(1) or 0)
        minutes = int(hms_match.group(2) or 0)
        seconds = int(hms_match.group(3) or 0)
        return hours * 3600 + minutes * 60 + seconds

    colon_match = re.fullmatch(r"(\d+):(\d{1,2}):(\d{1,2})", raw)
    if colon_match:
        hours = int(colon_match.group(1))
        minutes = int(colon_match.group(2))
        seconds = int(colon_match.group(3))
        return hours * 3600 + minutes * 60 + seconds

    raise ValueError(f"Duración no válida: {value}")


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def normalize_profiles(raw: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, dict):
        raise ValueError("profiles-custom.yml debe ser un mapa YAML.")

    profiles_list = raw.get("profiles")
    if not isinstance(profiles_list, list):
        raise ValueError("En profiles-custom.yml la clave 'profiles' debe ser una lista.")

    result: dict[str, dict[str, Any]] = {}

    for idx, item in enumerate(profiles_list, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"El perfil #{idx} no es un objeto válido.")

        profile_name = item.get("profile_name")
        if not profile_name:
            raise ValueError(f"El perfil #{idx} no tiene 'profile_name'.")

        defaults = item.get("defaults", {})
        if defaults is None:
            defaults = {}
        if not isinstance(defaults, dict):
            raise ValueError(f"El perfil '{profile_name}' tiene 'defaults' inválido.")

        result[str(profile_name).strip()] = {
            "profile_name": str(profile_name).strip(),
            "profile_type": str(item.get("profile_type") or profile_name).strip(),
            "defaults": defaults,
        }

    return result


def normalize_subscriptions(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, dict):
        raise ValueError("subscription-custom.yml debe ser un mapa YAML.")

    subscriptions_list = raw.get("subscriptions")
    if not isinstance(subscriptions_list, list):
        raise ValueError("En subscription-custom.yml la clave 'subscriptions' debe ser una lista.")

    result: list[dict[str, Any]] = []

    for idx, item in enumerate(subscriptions_list, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"La suscripción #{idx} no es un objeto válido.")

        profile_name = str(item.get("profile_name", "")).strip()
        custom_name = str(item.get("custom_name", "")).strip()
        sources = item.get("sources")

        if not profile_name:
            raise ValueError(f"La suscripción #{idx} no tiene 'profile_name'.")
        if not custom_name:
            raise ValueError(f"La suscripción #{idx} no tiene 'custom_name'.")
        if not isinstance(sources, list) or not sources:
            raise ValueError(f"La suscripción '{custom_name}' no tiene 'sources' válidos.")

        normalized_sources: list[dict[str, Any]] = []
        for source_idx, source in enumerate(sources, start=1):
            if not isinstance(source, dict):
                raise ValueError(
                    f"La fuente #{source_idx} de la suscripción '{custom_name}' no es válida."
                )
            if not str(source.get("url", "")).strip():
                raise ValueError(
                    f"La fuente #{source_idx} de la suscripción '{custom_name}' no tiene URL."
                )
            normalized_sources.append(source)

        result.append(
            {
                "profile_name": profile_name,
                "custom_name": custom_name,
                "sources": normalized_sources,
            }
        )

    return result


def quality_to_preset(quality: str) -> str | None:
    quality_key = str(quality).strip().lower()
    if quality_key == "720p":
        return "Max 720p"
    if quality_key == "1080p":
        return "Max 1080p"
    if quality_key == "best":
        return None
    raise ValueError(f"Calidad no soportada: {quality}")


def parse_max_items(value: Any, default: int = 3) -> int:
    if value is None or value == "":
        return default

    try:
        parsed = int(value)
    except Exception as exc:
        raise ValueError(f"max_items no válido: {value}") from exc

    if parsed < 0:
        raise ValueError(f"max_items no puede ser negativo: {value}")

    return parsed


def build_profile_preset(profile_type: str, merged_values: dict[str, Any]) -> dict[str, Any]:
    profile_key = slugify(profile_type)
    throttle_enabled = bool(merged_values.get("enable_throttle_protection", False))
    embed_thumbnail = bool(merged_values.get("embed_thumbnail", True))
    output_format = str(merged_values.get("format", "")).strip().lower()
    quality_value = str(merged_values.get("quality", "best")).strip().lower()
    max_items = parse_max_items(merged_values.get("max_items"), default=3)
    use_only_recent = max_items > 0

    if profile_key == "canales-youtube":
        preset_list = ["Jellyfin TV Show by Date"]
        preset_quality = quality_to_preset(quality_value)
        if preset_quality:
            preset_list.append(preset_quality)
        if use_only_recent:
            preset_list.append("Only Recent")

        tv_show_directory = merged_values.get(
            "tv_show_directory",
            "/downloads/Canales-youtube",
        )

        return {
            "preset": preset_list,
            "overrides": {
                "enable_throttle_protection": throttle_enabled,
                "tv_show_directory": tv_show_directory,
            },
            "embed_thumbnail": embed_thumbnail,
        }

    if profile_key == "podcast":
        output_directory = merged_values.get(
            "output_directory",
            "/downloads/Podcast/{subscription_root_sanitized}/{source_target_sanitized}",
        )

        preset_list = ["Filter Duration", "Max MP3 Quality"]
        if use_only_recent:
            preset_list.insert(0, "Only Recent")

        return {
            "preset": preset_list,
            "overrides": {
                "enable_throttle_protection": throttle_enabled,
            },
            "embed_thumbnail": True,
            "output_options": {
                "output_directory": output_directory,
                "file_name": "{title_sanitized}.{ext}",
                "maintain_download_archive": True,
            },
            "download": "{url}",
            "audio_extract": {
                "enable": True,
                "codec": "mp3",
                "quality": 0,
            },
        }

    if profile_key == "tv-serie":
        preset_list = ["Jellyfin TV Show by Date"]
        preset_quality = quality_to_preset(quality_value)
        if preset_quality:
            preset_list.append(preset_quality)
        if use_only_recent:
            preset_list.append("Only Recent")
        preset_list.append("Filter Duration")

        tv_show_directory = merged_values.get(
            "tv_show_directory",
            "/downloads/TV-Serie",
        )

        return {
            "preset": preset_list,
            "overrides": {
                "enable_throttle_protection": throttle_enabled,
                "tv_show_directory": tv_show_directory,
            },
            "embed_thumbnail": embed_thumbnail,
            "ytdl_options": {
                "merge_output_format": output_format,
            },
        }

    if profile_key == "music-playlist":
        output_directory = merged_values.get(
            "output_directory",
            "/downloads/Music-Playlist/{subscription_root_sanitized}",
        )

        preset_list = ["Max MP3 Quality"]
        if use_only_recent:
            preset_list.insert(0, "Only Recent")

        return {
            "preset": preset_list,
            "overrides": {
                "enable_throttle_protection": throttle_enabled,
            },
            "embed_thumbnail": True,
            "output_options": {
                "output_directory": output_directory,
                "file_name": "{title_sanitized}.{ext}",
                "maintain_download_archive": True,
            },
            "download": "{url}",
            "audio_extract": {
                "enable": True,
                "codec": "mp3",
                "quality": 0,
            },
        }

    if profile_key == "ambience-video":
        output_directory = merged_values.get(
            "output_directory",
            "/downloads/Ambience-Video/{subscription_root_sanitized}",
        )

        preset_list: list[str] = []
        preset_quality = quality_to_preset(quality_value)
        if preset_quality:
            preset_list.append(preset_quality)

        return {
            "preset": preset_list,
            "overrides": {
                "enable_throttle_protection": throttle_enabled,
            },
            "embed_thumbnail": embed_thumbnail,
            "output_options": {
                "output_directory": output_directory,
                "file_name": "{title_sanitized}.{ext}",
                "maintain_download_archive": True,
            },
            "download": "{url}",
            "ytdl_options": {
                "merge_output_format": output_format,
            },
        }

    if profile_key == "ambience-audio":
        output_directory = merged_values.get(
            "output_directory",
            "/downloads/Ambience-Audio/{subscription_root_sanitized}",
        )

        return {
            "preset": [],
            "overrides": {
                "enable_throttle_protection": throttle_enabled,
            },
            "embed_thumbnail": embed_thumbnail,
            "output_options": {
                "output_directory": output_directory,
                "file_name": "{title_sanitized}.{ext}",
                "maintain_download_archive": True,
            },
            "download": "{url}",
            "audio_extract": {
                "enable": True,
                "codec": "mp3",
                "quality": 0,
            },
        }

    raise ValueError(f"Perfil no soportado: {profile_type}")


def build_subscription_entry(
    profile_type: str,
    custom_name: str,
    merged_values: dict[str, Any],
    source_item: dict[str, Any],
) -> tuple[str, str, dict[str, Any]]:
    profile_key = slugify(profile_type)

    url = str(source_item["url"]).strip()
    source_target = slugify(extract_source_target_from_url(url))
    subscription_root = slugify(custom_name)

    max_files = parse_max_items(merged_values.get("max_items"), default=3)
    min_duration_s = parse_duration_to_seconds(merged_values.get("min_duration"))
    max_duration_s = parse_duration_to_seconds(merged_values.get("max_duration"))
    download_strategy = detect_download_strategy(url)

    preset_name = f"{slugify(profile_type)}-{subscription_root}-{source_target}"
    subscription_name = f"{subscription_root}-{source_target}"

    entry: dict[str, Any] = {
        "url": url,
        "enable_resolution_assert": False,
        "subscription_root_sanitized": subscription_root,
        "source_target_sanitized": source_target,
        "download_strategy": download_strategy,
    }

    if profile_key not in ("ambience-video", "ambience-audio") and max_files > 0:
        entry["only_recent_max_files"] = max_files
        entry["only_recent_date_range"] = str(merged_values.get("date_range", "100years"))

    if min_duration_s is not None:
        entry["filter_duration_min_s"] = min_duration_s

    if profile_key in ("ambience-video", "ambience-audio"):
        if max_duration_s is not None:
            entry["postprocess_trim_max_s"] = max_duration_s
    else:
        if max_duration_s is not None:
            entry["filter_duration_max_s"] = max_duration_s

    if profile_key == "canales-youtube":
        entry["tv_show_name"] = source_target

    if profile_key == "tv-serie":
        entry["tv_show_name"] = subscription_root

    return preset_name, subscription_name, entry


def build_beets_config() -> dict[str, Any]:
    return {
        "directory": "/downloads/Music-Playlist",
        "library": "/config/musiclibrary.db",
        "plugins": [
            "fromfilename",
            "chroma",
            "discogs",
            "lastgenre",
            "scrub",
            "fetchart",
            "embedart",
        ],
        "import": {
            "write": True,
            "move": False,
            "copy": False,
            "delete": False,
            "resume": False,
            "incremental": False,
            "quiet": False,
            "timid": False,
            "singletons": True,
            "group_albums": False,
            "log": "/config/logs/beets-import.log",
            "default_action": "apply",
            "none_rec_action": "skip",
        },
        "match": {
            "strong_rec_thresh": 0.10,
            "medium_rec_thresh": 0.25,
        },
        "fromfilename": {
            "fallback": "asis",
        },
        "embedart": {
            "auto": True,
            "ifempty": False,
            "remove_art_file": False,
        },
        "fetchart": {
            "auto": False,
        },
        "lastgenre": {
            "auto": True,
            "source": "track",
            "force": False,
        },
        "discogs": {
            "user_token": "SYBUdMECyTYqcXLCSqsHdUmjgmbVyiaWqytguVLn"
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generador de config y subscriptions para ytdl-sub"
    )
    parser.add_argument(
        "--only-profile",
        dest="only_profile",
        default="",
        help="Genera solo un profile_type, por ejemplo: music-playlist",
    )
    args = parser.parse_args()

    try:
        profiles_raw = load_yaml_file(PROFILES_FILE)
        subscriptions_raw = load_yaml_file(SUBSCRIPTIONS_FILE)

        profiles = normalize_profiles(profiles_raw)
        subscriptions = normalize_subscriptions(subscriptions_raw)

        only_profile = slugify(args.only_profile) if args.only_profile else ""

        config_generated: dict[str, Any] = {
            "configuration": {
                "working_directory": "/tmp/ytdl-sub-working-directory",
                "file_name_max_bytes": 255,
                "persist_logs": {
                    "keep_successful_logs": True,
                    "logs_directory": "/config/logs",
                },
                "lock_directory": "/tmp",
            },
            "presets": {},
        }

        subscriptions_generated: dict[str, Any] = {}
        preset_names_seen: set[str] = set()
        includes_music_playlist = False

        for subscription in subscriptions:
            profile_name = subscription["profile_name"]
            custom_name = subscription["custom_name"]

            if profile_name not in profiles:
                raise ValueError(
                    f"La suscripción usa un perfil no definido: {profile_name}"
                )

            profile_data = profiles[profile_name]
            profile_type = profile_data["profile_type"]

            if only_profile and slugify(profile_type) != only_profile:
                continue

            if slugify(profile_type) == "music-playlist":
                includes_music_playlist = True

            profile_defaults = profile_data.get("defaults", {})

            for source in subscription["sources"]:
                merged_values = deep_merge(profile_defaults, source)

                preset_name, subscription_name, entry = build_subscription_entry(
                    profile_type=profile_type,
                    custom_name=custom_name,
                    merged_values=merged_values,
                    source_item=source,
                )

                if preset_name in preset_names_seen:
                    raise ValueError(f"Nombre de preset duplicado: {preset_name}")
                preset_names_seen.add(preset_name)

                config_generated["presets"][preset_name] = build_profile_preset(
                    profile_type=profile_type,
                    merged_values=merged_values,
                )

                subscriptions_generated[preset_name] = {
                    f"~{subscription_name}": entry
                }

        if not config_generated["presets"]:
            raise ValueError("No se generó ningún preset. Revisa el filtro --only-profile.")

        dump_yaml_file(CONFIG_OUTPUT_FILE, config_generated)
        dump_yaml_file(SUBSCRIPTIONS_OUTPUT_FILE, subscriptions_generated)

        if includes_music_playlist:
            dump_yaml_file(BEETS_OUTPUT_FILE, build_beets_config())

        print("Generación completada correctamente.")
        print(f"Directorio base: {BASE_DIR}")
        print(f"Generado: {CONFIG_OUTPUT_FILE}")
        print(f"Generado: {SUBSCRIPTIONS_OUTPUT_FILE}")
        if includes_music_playlist:
            print(f"Generado: {BEETS_OUTPUT_FILE}")

    except Exception as exc:
        fail(str(exc))


if __name__ == "__main__":
    main()