#!/usr/bin/env python3
"""Забирает книги и обложки из HTML-файла сайта на claude.ai.

Использование:
    python3 tools/import_from_claude.py путь/к/index.html

Что делает:
  * вынимает данные книг из <script id="booknix-data">;
  * сохраняет обложки в public/covers/<id>.webp (360x540, сжатие WebP);
  * записывает data/books.json и data/settings.json;
  * удаляет обложки книг, которых больше нет.
"""
import base64
import io
import json
import re
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
COVERS = ROOT / "public" / "covers"
DATA = ROOT / "data"
COVER_W, COVER_H = 360, 540


def save_cover(book_id: str, data_uri: str) -> str:
    raw = base64.b64decode(data_uri.split(",", 1)[1])
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    # обрезка под 2:3 и уменьшение
    w, h = img.size
    target = COVER_W / COVER_H
    if w / h > target:
        nw = int(h * target)
        img = img.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    elif w / h < target:
        nh = int(w / target)
        img = img.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    img = img.resize((COVER_W, COVER_H), Image.LANCZOS)
    out = COVERS / f"{book_id}.webp"
    img.save(out, "WEBP", quality=78, method=6)
    return f"/covers/{book_id}.webp"


def main(path: str) -> None:
    html = Path(path).read_text(encoding="utf-8")
    m = re.search(r'<script type="application/json" id="booknix-data">(.*?)</script>', html, re.S)
    if not m:
        sys.exit("В файле не найдены данные книг (booknix-data).")
    state = json.loads(m.group(1))
    COVERS.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)

    keep = set()
    books = []
    for b in state["books"]:
        cover = b.get("cover") or ""
        if cover.startswith("data:image/"):
            b["cover"] = save_cover(b["id"], cover)
        elif cover and not cover.startswith("/covers/"):
            b["cover"] = ""
        if b.get("cover"):
            keep.add(Path(b["cover"]).name)
        if b.get("type") == "progress":
            b["type"] = "wait"
        books.append(b)

    for f in COVERS.glob("*.webp"):
        if f.name not in keep:
            f.unlink()

    books.sort(key=lambda b: -(b.get("added") or 0))
    (DATA / "books.json").write_text(json.dumps(books, ensure_ascii=False, indent=1), encoding="utf-8")
    # настройки, которых нет в версии на claude.ai (например, gaId), сохраняем
    sf = DATA / "settings.json"
    settings = json.loads(sf.read_text(encoding="utf-8")) if sf.exists() else {}
    settings.update(state["settings"])
    sf.write_text(json.dumps(settings, ensure_ascii=False, indent=1), encoding="utf-8")
    size = sum(f.stat().st_size for f in COVERS.glob("*.webp"))
    print(f"Книг: {len(books)}, обложек: {len(keep)}, вес обложек: {size/1024/1024:.1f} МБ")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
