#!/usr/bin/env python3
"""Собирает сайт Booknix в папку public/.

    python3 tools/build.py

Берёт data/books.json, data/settings.json, src/style.css, src/app.js
и генерирует: главную, страницу каждой книги (/knigi/<id>/), 404,
sitemap.xml, robots.txt и картинки для превью в соцсетях (/og/<id>.jpg).
"""
import hashlib
import html
import json
import re
from datetime import date
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PUB = ROOT / "public"
BASE = "https://booknix.net"
SITE_NAME = "Booknix"
HOME_TITLE = "Booknix — фантастика и фэнтези в переводах"

TYPES = {"translation": "Мой перевод", "wait": "Лист ожидания", "rec": "Рекомендация"}
MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа",
          "сентября", "октября", "ноября", "декабря"]
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Unbounded:wght@500;700;800'
         '&amp;family=Golos+Text:wght@400;500;600&amp;family=Literata:ital,opsz,wght@0,7..72,500;'
         '0,7..72,700;1,7..72,400&amp;display=swap">')
RESET = (":root{box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);"
         "padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0;padding:0}img{max-width:100%}"
         "[hidden]:not([hidden=until-found i]){display:none!important}"
         ".seo{max-width:900px;margin:0 auto;padding:32px 20px}.seo img{border-radius:8px}"
         ".seo a{text-decoration:underline}.seo ul{padding-left:20px}")

e = lambda s: html.escape(str(s or ""), quote=True)


def fmt_date(v):
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", str(v or ""))
    return f"{int(m[3])} {MONTHS[int(m[2]) - 1]} {m[1]}" if m else str(v or "")


def short(text, n=160):
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(t) <= n:
        return t
    cut = t[:n].rsplit(" ", 1)[0]
    return cut.rstrip(",.;:—-") + "…"


def asset(name, content):
    """Пишет файл в public/assets и возвращает URL с меткой версии."""
    (PUB / "assets").mkdir(parents=True, exist_ok=True)
    (PUB / "assets" / name).write_text(content, encoding="utf-8")
    v = hashlib.sha1(content.encode()).hexdigest()[:10]
    return f"/assets/{name}?v={v}"


def og_image(b):
    """JPEG-превью для соцсетей (не все мессенджеры понимают WebP)."""
    if not b.get("cover"):
        return f"{BASE}/og-default.jpg"
    src = PUB / b["cover"].lstrip("/")
    out = PUB / "og" / f"{b['id']}.jpg"
    out.parent.mkdir(exist_ok=True)
    if src.exists() and (not out.exists() or out.stat().st_mtime < src.stat().st_mtime):
        Image.open(src).convert("RGB").save(out, "JPEG", quality=80, optimize=True)
    return f"{BASE}/og/{b['id']}.jpg"


def page(*, title, desc, canonical, og_img, og_type, jsonld, body, scripts, robots="index,follow"):
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<meta name="robots" content="{robots}">
<link rel="canonical" href="{e(canonical)}">
<meta name="theme-color" content="#0b0f15">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:locale" content="ru_RU">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(canonical)}">
<meta property="og:image" content="{e(og_img)}">
<meta name="twitter:card" content="summary_large_image">
{FONTS}
<style>{RESET}</style>
<link rel="stylesheet" href="{STYLE_URL}" id="bx-style">
<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False).replace("</", "<\\/")}</script>
</head>
<body>
<div id="app">{body}</div>
{scripts}
</body>
</html>
"""


def book_static(b, settings, by_series):
    """Статичная версия карточки книги — для поисковиков и людей без JS."""
    orig = " · ".join(x for x in [b.get("origTitle"), b.get("origAuthor"), b.get("year")] if x)
    paras = [p.strip() for p in re.split(r"\n\s*\n", b.get("annotation") or "") if p.strip()]
    meta = " · ".join([x for x in [b.get("origin")] + (b.get("genres") or []) if x])
    series = ""
    if b.get("series"):
        series = f" — {e(b['series'])}" + (f", книга {e(b['seriesNo'])}" if b.get("seriesNo") else "")
    others = by_series.get(b.get("series", "").lower(), [])
    olist = ""
    if len(others) > 1:
        olist = "<h2>Книги цикла «" + e(b["series"]) + "»</h2><ul>" + "".join(
            f'<li><a href="/knigi/{e(x["id"])}/">{e(x["title"])}</a></li>' for x in others) + "</ul>"
    link = b.get("post") or settings["channelUrl"]
    img = (f'<img src="{e(b["cover"])}" alt="Обложка: {e(b["title"])}" width="240" height="360">'
           if b.get("cover") else "")
    eta = f"<p>Выход перевода — примерно <b>{fmt_date(b['eta'])}</b></p>" if b.get("eta") and b["type"] == "wait" else ""
    note = ""
    if b.get("note"):
        note = f"<p><b>{'Рекомендация' if b['type'] == 'rec' else 'От переводчика'}:</b> {e(b['note'])}</p>"
    return (f'<main class="seo"><p><a href="/">Booknix</a> › {e(TYPES.get(b["type"], ""))}</p>{img}'
            f'<h1>{e(b["title"])}</h1><p>{e(b["author"])}{series}</p>'
            + (f"<p>Оригинал: {e(orig)}</p>" if orig else "") + (f"<p>{e(meta)}</p>" if meta else "")
            + eta + "".join(f"<p>{e(p)}</p>" for p in paras) + note
            + f'<p><a href="{e(link)}">Открыть в Telegram</a></p>{olist}</main>')


def home_static(books, settings):
    groups = [("Мои переводы", "translation"), ("Лист ожидания", "wait"), ("Рекомендации", "rec")]
    out = [f'<main class="seo"><h1>{SITE_NAME} — фантастика и фэнтези в переводах</h1><p>{e(settings["about"])}</p>']
    for title, t in groups:
        items = [b for b in books if b["type"] == t]
        if items:
            out.append(f"<h2>{title}</h2><ul>" + "".join(
                f'<li><a href="/knigi/{e(b["id"])}/">{e(b["title"])}</a> — {e(b["author"])}</li>' for b in items) + "</ul>")
    out.append(f'<p><a href="{e(settings["channelUrl"])}">Telegram-канал {e(settings["channelName"])}</a></p></main>')
    return "".join(out)


def book_jsonld(b, url, img):
    d = {"@context": "https://schema.org", "@type": "Book", "name": b["title"], "url": url,
         "image": img, "inLanguage": "ru",
         "author": {"@type": "Person", "name": b["author"]},
         "description": short(b.get("annotation"), 300)}
    if b.get("genres"):
        d["genre"] = b["genres"]
    if b.get("year"):
        d["datePublished"] = str(b["year"])
    if b.get("series"):
        d["isPartOf"] = {"@type": "BookSeries", "name": b["series"]}
    if b.get("origTitle") or b.get("origAuthor"):
        w = {"@type": "Book"}
        if b.get("origTitle"):
            w["name"] = b["origTitle"]
        if b.get("origAuthor"):
            w["author"] = {"@type": "Person", "name": b["origAuthor"]}
        d["translationOfWork"] = w
    if b["type"] == "translation":
        d["translator"] = {"@type": "Organization", "name": "Booknix", "url": BASE}
    return d


def main():
    global STYLE_URL
    books = json.loads((ROOT / "data/books.json").read_text(encoding="utf-8"))
    settings = json.loads((ROOT / "data/settings.json").read_text(encoding="utf-8"))
    books.sort(key=lambda b: -(b.get("added") or 0))

    STYLE_URL = asset("style.css", (ROOT / "src/style.css").read_text(encoding="utf-8"))
    data_js = "window.BOOKNIX=" + json.dumps({"settings": settings, "books": books},
                                               ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + ";"
    data_url = asset("books.js", data_js)
    app_url = asset("app.js", (ROOT / "src/app.js").read_text(encoding="utf-8"))
    scripts = f'<script src="{data_url}" defer></script>\n<script src="{app_url}" defer></script>'

    by_series = {}
    for b in books:
        if b.get("series"):
            by_series.setdefault(b["series"].lower(), []).append(b)
    for lst in by_series.values():
        lst.sort(key=lambda x: (float(x["seriesNo"]) if re.match(r"^\d+(\.\d+)?$", str(x.get("seriesNo") or "")) else 999))

    # главная
    first_cover = next((b for b in books if b.get("featured") and b.get("cover")), books[0])
    home = page(title=HOME_TITLE, desc=short(settings["about"], 200), canonical=BASE + "/",
                og_img=og_image(first_cover), og_type="website",
                jsonld={"@context": "https://schema.org", "@type": "WebSite", "name": SITE_NAME, "url": BASE + "/",
                        "inLanguage": "ru", "description": settings["about"],
                        "sameAs": [settings["channelUrl"]]},
                body=home_static(books, settings), scripts=scripts)
    (PUB / "index.html").write_text(home, encoding="utf-8")

    # книги
    kn = PUB / "knigi"
    ids = {b["id"] for b in books}
    if kn.exists():
        for d in kn.iterdir():
            if d.name not in ids:
                for f in d.iterdir():
                    f.unlink()
                d.rmdir()
    for b in books:
        url = f"{BASE}/knigi/{b['id']}/"
        img = og_image(b)
        kind = {"translation": "перевод", "wait": "скоро в переводе", "rec": "рекомендация"}[b["type"]]
        title = f"{b['title']} — {b['author']} | {SITE_NAME}"
        desc = short(f"{b['author']}, «{b['title']}» ({kind}). {b.get('annotation') or ''}", 200)
        out = kn / b["id"]
        out.mkdir(parents=True, exist_ok=True)
        (out / "index.html").write_text(page(title=title, desc=desc, canonical=url, og_img=img, og_type="book",
                                             jsonld=book_jsonld(b, url, img),
                                             body=book_static(b, settings, by_series), scripts=scripts),
                                        encoding="utf-8")
    for f in (PUB / "og").glob("*.jpg"):
        if f.stem not in ids:
            f.unlink()

    # 404
    nf = ('<main class="seo" style="text-align:center;padding-top:15vh"><h1>Такой страницы нет</h1>'
          '<p>Возможно, книга переехала или ссылка набрана с ошибкой.</p>'
          '<p><a href="/">Вернуться на главную Booknix</a></p></main>')
    (PUB / "404.html").write_text(page(title="Страница не найдена | Booknix", desc="Страница не найдена",
                                       canonical=BASE + "/", og_img=og_image(first_cover), og_type="website",
                                       jsonld={"@context": "https://schema.org", "@type": "WebPage"},
                                       body=nf, scripts="", robots="noindex"), encoding="utf-8")

    # sitemap / robots
    today = date.today().isoformat()
    urls = [f"<url><loc>{BASE}/</loc><lastmod>{today}</lastmod><priority>1.0</priority></url>"]
    urls += [f"<url><loc>{BASE}/knigi/{b['id']}/</loc><lastmod>{today}</lastmod></url>" for b in books]
    (PUB / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
                                     '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                     + "\n".join(urls) + "\n</urlset>\n", encoding="utf-8")
    (PUB / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n", encoding="utf-8")
    print(f"Готово: {len(books)} книг → public/")


if __name__ == "__main__":
    main()
