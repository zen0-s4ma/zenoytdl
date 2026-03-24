from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any

try:
    from mutagen.id3 import ID3, APIC, ID3NoHeaderError
    from mutagen.easyid3 import EasyID3
except ImportError:
    print("ERROR: falta la dependencia 'mutagen'. Instala con: pip install mutagen", file=sys.stderr)
    sys.exit(1)


def safe_join(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return " | ".join(str(x) for x in value if x is not None)
    return str(value)


def read_easy_tags(mp3_path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    try:
        tags = EasyID3(str(mp3_path))
    except Exception:
        return data

    wanted_keys = [
        "artist",
        "title",
        "album",
        "albumartist",
        "genre",
        "date",
        "tracknumber",
        "discnumber",
        "musicbrainz_trackid",
        "musicbrainz_albumid",
        "musicbrainz_artistid",
    ]

    for key in wanted_keys:
        try:
            if key in tags:
                data[key] = safe_join(tags.get(key, []))
            else:
                data[key] = ""
        except Exception:
            data[key] = ""

    return data


def read_id3_extra(mp3_path: Path) -> dict[str, Any]:
    result = {
        "embedded_art": False,
        "apic_count": 0,
    }

    try:
        id3 = ID3(str(mp3_path))
    except ID3NoHeaderError:
        return result
    except Exception:
        return result

    apic_frames = id3.getall("APIC")
    result["apic_count"] = len(apic_frames)
    result["embedded_art"] = len(apic_frames) > 0
    return result


def is_metadata_ok(row: dict[str, Any]) -> tuple[bool, list[str]]:
    missing: list[str] = []

    required = [
        "artist",
        "title",
    ]

    recommended = [
        "album",
        "genre",
    ]

    for key in required:
        if not str(row.get(key, "")).strip():
            missing.append(key)

    # estas no son obligatorias al 100%, pero ayudan a detectar metadata pobre
    missing_recommended = [k for k in recommended if not str(row.get(k, "")).strip()]

    ok = len(missing) == 0
    if missing_recommended:
        missing.extend([f"{k} (recommended)" for k in missing_recommended])

    return ok, missing


def collect_mp3s(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.mp3") if p.is_file())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verifica metadata real de todos los MP3 de un perfil."
    )
    parser.add_argument(
        "--music-dir",
        required=True,
        help="Ruta raíz del perfil musical, por ejemplo /downloads/Music-Playlist o E:\\...\\Music-Playlist",
    )
    parser.add_argument(
        "--output-csv",
        required=True,
        help="Ruta del CSV de salida",
    )
    args = parser.parse_args()

    music_dir = Path(args.music_dir).expanduser().resolve()
    output_csv = Path(args.output_csv).expanduser().resolve()

    if not music_dir.exists() or not music_dir.is_dir():
        print(f"ERROR: no existe la carpeta: {music_dir}", file=sys.stderr)
        return 1

    mp3_files = collect_mp3s(music_dir)
    if not mp3_files:
        print(f"ERROR: no se han encontrado MP3 en: {music_dir}", file=sys.stderr)
        return 1

    output_csv.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []

    total = 0
    ok_count = 0
    incomplete_count = 0
    art_count = 0

    for mp3_path in mp3_files:
        total += 1

        easy = read_easy_tags(mp3_path)
        extra = read_id3_extra(mp3_path)

        row: dict[str, Any] = {
            "file": str(mp3_path),
            "artist": easy.get("artist", ""),
            "title": easy.get("title", ""),
            "album": easy.get("album", ""),
            "albumartist": easy.get("albumartist", ""),
            "genre": easy.get("genre", ""),
            "date": easy.get("date", ""),
            "tracknumber": easy.get("tracknumber", ""),
            "discnumber": easy.get("discnumber", ""),
            "mb_trackid": easy.get("musicbrainz_trackid", ""),
            "mb_albumid": easy.get("musicbrainz_albumid", ""),
            "mb_artistid": easy.get("musicbrainz_artistid", ""),
            "embedded_art": "yes" if extra.get("embedded_art") else "no",
            "apic_count": extra.get("apic_count", 0),
        }

        ok, missing = is_metadata_ok(row)
        row["metadata_ok"] = "yes" if ok else "no"
        row["missing_fields"] = " | ".join(missing)

        if ok:
            ok_count += 1
        else:
            incomplete_count += 1

        if extra.get("embedded_art"):
            art_count += 1

        rows.append(row)

    fieldnames = [
        "file",
        "artist",
        "title",
        "album",
        "albumartist",
        "genre",
        "date",
        "tracknumber",
        "discnumber",
        "mb_trackid",
        "mb_albumid",
        "mb_artistid",
        "embedded_art",
        "apic_count",
        "metadata_ok",
        "missing_fields",
    ]

    with output_csv.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("=" * 80)
    print("VERIFICACION DE METADATA")
    print("=" * 80)
    print(f"Carpeta analizada : {music_dir}")
    print(f"CSV generado      : {output_csv}")
    print(f"Total MP3         : {total}")
    print(f"Metadata OK       : {ok_count}")
    print(f"Incompletos       : {incomplete_count}")
    print(f"Con caratula      : {art_count}")
    print("=" * 80)

    if incomplete_count > 0:
        print("Primeros archivos con metadata incompleta:")
        shown = 0
        for row in rows:
            if row["metadata_ok"] == "no":
                print(f"- {row['file']}")
                print(f"  missing: {row['missing_fields']}")
                shown += 1
                if shown >= 20:
                    break

    return 0


if __name__ == "__main__":
    raise SystemExit(main())