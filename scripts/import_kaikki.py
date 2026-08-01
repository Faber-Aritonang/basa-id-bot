"""Impor data kosakata dari Kaikki.org (machine-readable Wiktionary).

Skrip ini mengunduh JSONL kamus bahasa (Jawa/Sunda/Indonesia) dari
https://kaikki.org, memfilter entri yang tidak berguna (romanization,
entri tanpa gloss), dan menulisnya ke folder data/ dalam format proyek.

Penggunaan:
    python scripts/import_kaikki.py --lang javanese
    python scripts/import_kaikki.py --lang sundanese --limit 500   # uji coba
    python scripts/import_kaikki.py --lang indonesian --out data/
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from datetime import date
from pathlib import Path

from basa.data.kaikki import dedupe_words, parse_line, to_project_word

# (nama, code ISO, nama folder, nama tampilan, URL JSONL di kaikki.org)
LANGUAGES: dict[str, dict] = {
    "javanese": {
        "code": "jv",
        "name": "Javanese",
        "folder": "jawa",
        "url": "https://kaikki.org/dictionary/Javanese/kaikki.org-dictionary-Javanese.jsonl",
    },
    "sundanese": {
        "code": "su",
        "name": "Sundanese",
        "folder": "sunda",
        "url": "https://kaikki.org/dictionary/Sundanese/kaikki.org-dictionary-Sundanese.jsonl",
    },
    "indonesian": {
        "code": "id",
        "name": "Indonesian",
        "folder": "indonesia",
        "url": "https://kaikki.org/dictionary/Indonesian/kaikki.org-dictionary-Indonesian.jsonl",
    },
}


def download(url: str, dest: Path) -> None:
    """Unduh file JSONL dari Kaikki.org ke dest (streaming, progres sederhana)."""
    print(f"  Mengunduh {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Basa.id/0.1 (portfolio project)"})
    with urllib.request.urlopen(req) as resp, dest.open("wb") as out:
        total = int(resp.headers.get("Content-Length") or 0)
        written = 0
        while chunk := resp.read(1024 * 256):
            out.write(chunk)
            written += len(chunk)
            if total:
                pct = written * 100 // total
                print(f"\r  {pct:3d}% ({written / 1e6:.1f}/{total / 1e6:.1f} MB)", end="", flush=True)
    print()


def import_language(lang_key: str, limit: int | None = None, out_root: Path = Path("data")) -> Path:
    """Proses utama: unduh → parse → filter → tulis JSON proyek.

    Mengembalikan path file JSON yang dihasilkan.
    """
    info = LANGUAGES[lang_key]
    out_dir = out_root / info["folder"]
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_file = out_dir / f"kaikki-{info['code']}.jsonl"
    out_file = out_dir / f"{info['folder']}.json"

    print(f"[1/3] Mengunduh kamus {info['name']}...")
    try:
        download(info["url"], raw_file)

        print("[2/3] Memparse JSONL & memfilter...")
        words: list[dict] = []
        with raw_file.open("r", encoding="utf-8") as f:
            for line in f:
                entry = parse_line(line)
                if entry is None:
                    continue
                words.append(to_project_word(entry))
                if limit is not None and len(words) >= limit:
                    break

        words = dedupe_words(words)

        print(f"[3/3] Menulis {len(words)} kata → {out_file}")
        payload = {
            "language": {"code": info["code"], "name": info["name"]},
            "source": "kaikki.org (Wiktionary, wiktextract)",
            "license": "CC BY-SA 3.0",
            "imported_at": date.today().isoformat(),
            "words": words,
        }
        with out_file.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return out_file
    finally:
        # File JSONL mentah tidak perlu disimpan di git (bisa diunduh ulang) —
        # bersihkan juga jika proses gagal di tengah jalan.
        raw_file.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Impor data kosakata dari Kaikki.org")
    parser.add_argument(
        "--lang",
        required=True,
        choices=sorted(LANGUAGES),
        help="Bahasa yang diimpor",
    )
    parser.add_argument("--limit", type=int, default=None, help="Batas jumlah kata (uji coba)")
    parser.add_argument("--out", type=Path, default=Path("data"), help="Folder output (default: data/)")
    args = parser.parse_args()

    result = import_language(args.lang, limit=args.limit, out_root=args.out)
    print(f"\nSelesai! File: {result}")


if __name__ == "__main__":
    main()
