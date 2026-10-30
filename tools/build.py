#!/usr/bin/env python3
"""Собирает сайт Booknix в папку public/.

    python3 tools/build.py

Берёт data/books.json, data/settings.json, src/style.css, src/app.js
и генерирует: главную, страницу каждой книги (/knigi/<id>/), страницы жанров
(/zhanr/<slug>/), 404, sitemap.xml, robots.txt и картинки для превью (/og/<id>.jpg).
"""
import hashlib
import html
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PUB = ROOT / "public"
BASE = "https://booknix.net"
SITE_NAME = "Booknix"
HOME_TITLE = "Booknix — зарубежная фантастика и фэнтези: переводы на русский и рекомендации"
HOME_DESC = ("Фантастика и фэнтези из Европы, США и Азии, которые не выходили на русском: "
             "авторские переводы, рекомендации, аннотации, циклы и лист ожидания новых переводов.")
GENRE_MIN = 3  # жанр получает свою страницу, если в нём столько книг (как и строка на главной)

TYPES = {"translation": "Мой перевод", "wait": "Лист ожидания", "rec": "Рекомендация"}
SHELVES = {"translation": "Мои переводы", "wait": "Лист ожидания", "rec": "Рекомендации"}
MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа",
          "сентября", "октября", "ноября", "декабря"]
TRANSLIT = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
                    ["a", "b", "v", "g", "d", "e", "e", "zh", "z", "i", "y", "k", "l", "m", "n", "o", "p",
                     "r", "s", "t", "u", "f", "h", "c", "ch", "sh", "sch", "", "y", "", "e", "yu", "ya"]))
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
STYLE_URL = ""
THEME_JS = '<script>try{if(localStorage.getItem("bx-theme")==="light"){document.documentElement.setAttribute("data-theme","light");document.querySelector(\'meta[name="theme-color"]\').setAttribute("content","#f5f0e6");}}catch(x){}</script>'  # тема до отрисовки, без мигания
GA_HEAD = ""


def ga_head(gid):
    """Тег Google Analytics в режиме Consent Mode: по умолчанию без cookie."""
    if not gid:
        return ""
    gid = e(gid)
    return (f'<script async src="https://www.googletagmanager.com/gtag/js?id={gid}"></script>\n'
            "<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}"
            "gtag('consent','default',{ad_storage:'denied',ad_user_data:'denied',ad_personalization:'denied',"
            "analytics_storage:'denied'});"
            "try{if(localStorage.getItem('bx-cookies')==='yes')gtag('consent','update',{analytics_storage:'granted'});}catch(x){}"
            f"gtag('js',new Date());gtag('config','{gid}');</script>\n")


def slugify(t):
    s = "".join(TRANSLIT.get(c, c) for c in str(t).lower())
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-") or "x"


def fmt_date(v):
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", str(v or ""))
    return f"{int(m[3])} {MONTHS[int(m[2]) - 1]} {m[1]}" if m else str(v or "")


def short(text, n=160):
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(t) <= n:
        return t
    cut = t[:n].rsplit(" ", 1)[0]
    return cut.rstrip(",.;:—-«( ") + "…"


def clean(v):
    return str(v or "").strip()


# ---------- заголовки и описания ----------

def seo_title(b):
    """Заголовок вкладки и выдачи: под то, как книги реально ищут."""
    base = f"{b['title']} — {b['author']}"
    tail = {"translation": "читать на русском в переводе",
            "wait": "перевод на русский, дата выхода",
            "rec": "о чём книга, аннотация"}[b["type"]]
    for t in (f"{base}: {tail} | {SITE_NAME}", f"{base}: {tail}", f"{base} | {SITE_NAME}"):
        if len(t) <= 75:
            return t
    return base


def seo_desc(b):
    orig = ", ".join(x for x in [clean(b.get("origTitle")), clean(b.get("year"))] if x)
    head = f"«{b['title']}»" + (f" ({orig})" if orig else "") + f" — {b['author']}"
    genres = [g.lower() if g[:2] != "Yo" else g for g in (b.get("genres") or [])[:2]]
    if genres:
        head += ", " + ", ".join(genres)
    head += "."
    lead = {"translation": " Перевод на русский язык — книга не издавалась на русском официально.",
            "wait": (f" Перевод на русский выйдет примерно {fmt_date(b['eta'])}." if b.get("eta")
                     else " Перевод на русский готовится."),
            "rec": ""}[b["type"]]
    return short(head + lead + " " + (b.get("annotation") or ""), 165)


def genre_title(g, n):
    return f"{g}: {n} {plural(n, 'книга', 'книги', 'книг')} — переводы и рекомендации | {SITE_NAME}"


def plural(n, one, few, many):
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


# ---------- файлы ----------

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


def write_dir_page(path, content):
    path.mkdir(parents=True, exist_ok=True)
    (path / "index.html").write_text(content, encoding="utf-8")


def prune(dirpath, keep):
    if not dirpath.exists():
        return
    for d in dirpath.iterdir():
        if d.name not in keep:
            for f in d.iterdir():
                f.unlink()
            d.rmdir()


def page(*, title, desc, canonical, og_img, og_type, jsonld, body, scripts, robots="index,follow",
         og_size=(360, 540), extra_head=""):
    lds = "".join('<script type="application/ld+json">' + json.dumps(j, ensure_ascii=False).replace("</", "<\\/")
                  + "</script>\n" for j in (jsonld if isinstance(jsonld, list) else [jsonld]))
    canon = f'<link rel="canonical" href="{e(canonical)}">\n<meta property="og:url" content="{e(canonical)}">\n' if canonical else ""
    return f"""<!doctype html>
<html lang="ru" prefix="og: https://ogp.me/ns#">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<meta name="robots" content="{robots},max-image-preview:large,max-snippet:-1">
{canon}<meta name="theme-color" content="#0b0f15">
{THEME_JS}
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:locale" content="ru_RU">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:image" content="{e(og_img)}">
<meta property="og:image:width" content="{og_size[0]}">
<meta property="og:image:height" content="{og_size[1]}">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(desc)}">
<meta name="twitter:image" content="{e(og_img)}">
{extra_head}{GA_HEAD}{FONTS}
<style>{RESET}</style>
<link rel="stylesheet" href="{STYLE_URL}" id="bx-style">
{lds}</head>
<body>
<div id="app">{body}</div>
{scripts}
</body>
</html>
"""


# ---------- статичный HTML (для поисковиков и без JS) ----------

def book_li(b):
    return f'<li><a href="/knigi/{e(b["id"])}/">{e(b["title"])}</a> — {e(b["author"])}</li>'


def similar(b, books, n=6):
    gs = set(b.get("genres") or [])
    scored = []
    for x in books:
        if x["id"] == b["id"] or x["type"] == "wait":
            continue
        common = len(gs & set(x.get("genres") or []))
        if common:
            same_series = b.get("series") and x.get("series") == b.get("series")
            if not same_series:
                scored.append((-common, -(x.get("added") or 0), x))
    scored.sort(key=lambda t: t[:2])
    return [t[2] for t in scored[:n]]


def gtag(g, gslug):
    return f'<a href="/zhanr/{gslug[g]}/">{e(g)}</a>' if g in gslug else e(g)


def book_static(b, settings, by_series, books, gslug):
    orig = " · ".join(x for x in [clean(b.get("origTitle")), clean(b.get("origAuthor")), clean(b.get("year"))] if x)
    paras = [p.strip() for p in re.split(r"\n\s*\n", b.get("annotation") or "") if p.strip()]
    meta = e(b.get("origin"))
    genres = " · ".join(gtag(g, gslug) for g in b.get("genres") or [])
    series = ""
    if b.get("series"):
        series = f" — цикл «{e(b['series'])}»" + (f", книга {e(b['seriesNo'])}" if b.get("seriesNo") else "")
    others = by_series.get(b.get("series", "").lower(), [])
    olist = ""
    if len(others) > 1:
        olist = "<h2>Книги цикла «" + e(b["series"]) + "» по порядку</h2><ol>" + "".join(
            (f'<li>{e(x["title"])}</li>' if x["id"] == b["id"] else
             f'<li><a href="/knigi/{e(x["id"])}/">{e(x["title"])}</a></li>') for x in others) + "</ol>"
    sim = similar(b, books)
    slist = ("<h2>Похожие книги</h2><ul>" + "".join(book_li(x) for x in sim) + "</ul>") if sim else ""
    link = b.get("post") or settings["channelUrl"]
    img = (f'<img src="{e(b["cover"])}" alt="Обложка книги «{e(b["title"])}» — {e(b["author"])}" width="240" height="360">'
           if b.get("cover") else "")
    eta = f"<p>Выход перевода на русский — примерно <b>{fmt_date(b['eta'])}</b></p>" if b.get("eta") and b["type"] == "wait" else ""
    note = ""
    if b.get("note"):
        note = f"<p><b>{'Рекомендация' if b['type'] == 'rec' else 'От переводчика'}:</b> {e(b['note'])}</p>"
    cta = {"translation": "Читать перевод в Telegram", "wait": "Следить за переводом в Telegram",
           "rec": "Обсуждение книги в Telegram"}[b["type"]]
    return (f'<main class="seo"><nav><a href="/">Booknix</a> › {e(SHELVES[b["type"]])}</nav>{img}'
            f'<h1>{e(b["title"])}</h1><p>{e(b["author"])}{series}</p>'
            + (f"<p>Оригинал: {e(orig)}</p>" if orig else "")
            + (f"<p>{meta}</p>" if meta else "") + (f"<p>Жанры: {genres}</p>" if genres else "")
            + eta + "<h2>Аннотация</h2>" + "".join(f"<p>{e(p)}</p>" for p in paras) + note
            + f'<p><a href="{e(link)}">{cta}</a></p>{olist}{slist}</main>')


def genre_links(gslug, counts):
    return "<ul>" + "".join(f'<li><a href="/zhanr/{gslug[g]}/">{e(g)}</a> ({counts[g]})</li>'
                            for g in sorted(gslug, key=lambda g: (-counts[g], g))) + "</ul>"


def home_static(books, settings, gslug, counts):
    out = [f'<main class="seo"><h1>Зарубежная фантастика и фэнтези: переводы на русский и рекомендации</h1>'
           f'<p>{e(settings["about"])}</p>']
    for t in ("translation", "wait", "rec"):
        items = [b for b in books if b["type"] == t]
        if items:
            out.append(f"<h2>{SHELVES[t]}</h2><ul>" + "".join(book_li(b) for b in items) + "</ul>")
    out.append("<h2>Жанры</h2>" + genre_links(gslug, counts))
    out.append(f'<p><a href="{e(settings["channelUrl"])}">Telegram-канал {e(settings["channelName"])}</a></p></main>')
    return "".join(out)


def genre_static(g, items, gslug, counts):
    out = [f'<main class="seo"><nav><a href="/">Booknix</a> › Жанры</nav><h1>{e(g)}: книги</h1>'
           f'<p>{len(items)} {plural(len(items), "книга", "книги", "книг")} в жанре «{e(g)}» — '
           f'переводы на русский и рекомендации зарубежной фантастики и фэнтези.</p>']
    for b in items:
        out.append(f'<h2><a href="/knigi/{e(b["id"])}/">{e(b["title"])}</a> — {e(b["author"])}</h2>'
                   f'<p>{e(short(b.get("annotation"), 260))}</p>')
    out.append("<h2>Другие жанры</h2>" + genre_links({k: v for k, v in gslug.items() if k != g}, counts) + "</main>")
    return "".join(out)


# ---------- разметка schema.org ----------

def crumbs(*items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": u}
                                for i, (n, u) in enumerate(items)]}


def book_jsonld(b, url, img, settings):
    d = {"@context": "https://schema.org", "@type": "Book", "name": b["title"], "url": url,
         "image": img, "inLanguage": "ru",
         "author": {"@type": "Person", "name": b["author"]},
         "description": short(b.get("annotation"), 500)}
    if b.get("genres"):
        d["genre"] = b["genres"]
    if b.get("year"):
        d["datePublished"] = str(b["year"])
    if b.get("origTitle"):
        d["alternateName"] = b["origTitle"]
    if b.get("series"):
        d["isPartOf"] = {"@type": "BookSeries", "name": b["series"]}
        if b.get("seriesOrig"):
            d["isPartOf"]["alternateName"] = b["seriesOrig"]
        if b.get("seriesNo"):
            d["position"] = b["seriesNo"]
    if b.get("origTitle") or b.get("origAuthor"):
        w = {"@type": "Book"}
        if b.get("origTitle"):
            w["name"] = b["origTitle"]
        if b.get("origAuthor"):
            w["author"] = {"@type": "Person", "name": b["origAuthor"]}
        if b.get("year"):
            w["datePublished"] = str(b["year"])
        d["translationOfWork"] = w
    if b["type"] == "translation":
        d["translator"] = {"@type": "Organization", "name": settings["channelName"], "url": settings["channelUrl"]}
    if b.get("post"):
        d["sameAs"] = b["post"]
    return d


def item_list(name, items):
    return {"@context": "https://schema.org", "@type": "ItemList", "name": name,
            "numberOfItems": len(items),
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f"{BASE}/knigi/{b['id']}/",
                                 "name": b["title"]} for i, b in enumerate(items)]}


# ---------- сборка ----------

def main():
    global STYLE_URL, GA_HEAD
    books = json.loads((ROOT / "data/books.json").read_text(encoding="utf-8"))
    settings = json.loads((ROOT / "data/settings.json").read_text(encoding="utf-8"))
    books.sort(key=lambda b: -(b.get("added") or 0))
    pages = {}  # url -> (html, image) — для sitemap

    counts = Counter(g for b in books if b["type"] != "wait" for g in b.get("genres") or [])
    gslug = {g: slugify(g) for g, n in counts.items() if n >= GENRE_MIN}
    gtitles = {g: genre_title(g, counts[g]) for g in gslug}

    GA_HEAD = ga_head(settings.get("gaId"))
    STYLE_URL = asset("style.css", (ROOT / "src/style.css").read_text(encoding="utf-8"))
    payload = {"settings": settings, "books": books, "homeTitle": HOME_TITLE,
               "seo": {b["id"]: seo_title(b) for b in books},
               "genres": {g: {"slug": gslug[g], "title": gtitles[g]} for g in gslug}}
    data_js = "window.BOOKNIX=" + json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + ";"
    data_url = asset("books.js", data_js)
    app_url = asset("app.js", (ROOT / "src/app.js").read_text(encoding="utf-8"))
    consent_url = asset("consent.js", (ROOT / "src/consent.js").read_text(encoding="utf-8"))
    scripts = (f'<script src="{data_url}" defer></script>\n<script src="{app_url}" defer></script>\n'
               f'<script src="{consent_url}" defer></script>')

    by_series = {}
    for b in books:
        if b.get("series"):
            by_series.setdefault(b["series"].lower(), []).append(b)
    num = lambda x: float(x["seriesNo"]) if re.match(r"^\d+(\.\d+)?$", str(x.get("seriesNo") or "")) else 999
    for lst in by_series.values():
        lst.sort(key=num)

    # главная
    first_cover = next((b for b in books if b.get("featured") and b.get("cover")), books[0])
    home_ld = [{"@context": "https://schema.org", "@type": "WebSite", "name": SITE_NAME, "url": BASE + "/",
                "inLanguage": "ru", "description": HOME_DESC,
                "potentialAction": {"@type": "SearchAction", "target": BASE + "/?q={search_term_string}",
                                    "query-input": "required name=search_term_string"}},
               {"@context": "https://schema.org", "@type": "Organization", "name": SITE_NAME, "url": BASE + "/",
                "logo": BASE + "/favicon.svg", "sameAs": [settings["channelUrl"]]},
               item_list("Мои переводы", [b for b in books if b["type"] == "translation"])]
    pages["/"] = page(title=HOME_TITLE, desc=HOME_DESC, canonical=BASE + "/", og_img=og_image(first_cover),
                      og_type="website", jsonld=home_ld, body=home_static(books, settings, gslug, counts),
                      scripts=scripts)
    (PUB / "index.html").write_text(pages["/"], encoding="utf-8")

    # книги
    ids = {b["id"] for b in books}
    prune(PUB / "knigi", ids)
    images = {}
    for b in books:
        path = f"/knigi/{b['id']}/"
        url = BASE + path
        img = og_image(b)
        images[path] = (img, f"Обложка книги «{b['title']}» — {b['author']}")
        ld = [book_jsonld(b, url, img, settings),
              crumbs((SITE_NAME, BASE + "/"), (SHELVES[b["type"]], BASE + "/#" + {"translation": "translations",
                                                                                   "wait": "wait", "rec": "rec"}[b["type"]]),
                     (b["title"], url))]
        extra = f'<meta property="book:author" content="{e(b["author"])}">\n' + "".join(
            f'<meta property="book:tag" content="{e(g)}">\n' for g in b.get("genres") or [])
        pages[path] = page(title=seo_title(b), desc=seo_desc(b), canonical=url, og_img=img, og_type="book",
                           jsonld=ld, body=book_static(b, settings, by_series, books, gslug), scripts=scripts,
                           extra_head=extra)
        write_dir_page(PUB / "knigi" / b["id"], pages[path])
    for f in (PUB / "og").glob("*.jpg"):
        if f.stem not in ids:
            f.unlink()

    # жанры
    prune(PUB / "zhanr", set(gslug.values()))
    for g, sl in gslug.items():
        path = f"/zhanr/{sl}/"
        items = [b for b in books if b["type"] != "wait" and g in (b.get("genres") or [])]
        names = ", ".join(f"«{b['title']}»" for b in items[:3])
        desc = short(f"Книги в жанре «{g}»: {names} и ещё {len(items) - 3 if len(items) > 3 else 0}. "
                     f"Аннотации, переводы на русский и рекомендации зарубежных книг.", 165) \
            if len(items) > 3 else short(f"Книги в жанре «{g}»: {names}. Аннотации, переводы на русский и рекомендации.", 165)
        cover_book = next((b for b in items if b.get("cover")), first_cover)
        ld = [{"@context": "https://schema.org", "@type": "CollectionPage", "name": f"{g}: книги",
               "url": BASE + path, "inLanguage": "ru", "description": desc},
              item_list(g, items), crumbs((SITE_NAME, BASE + "/"), (g, BASE + path))]
        pages[path] = page(title=gtitles[g], desc=desc, canonical=BASE + path, og_img=og_image(cover_book),
                           og_type="website", jsonld=ld, body=genre_static(g, items, gslug, counts), scripts=scripts)
        write_dir_page(PUB / "zhanr" / sl, pages[path])

    # 404
    nf = ('<main class="seo" style="text-align:center;padding-top:15vh"><h1>Такой страницы нет</h1>'
          '<p>Возможно, книга переехала или ссылка набрана с ошибкой.</p>'
          '<p><a href="/">Вернуться на главную Booknix</a></p></main>')
    (PUB / "404.html").write_text(page(title="Страница не найдена | Booknix", desc="Страница не найдена",
                                       canonical="", og_img=og_image(first_cover), og_type="website",
                                       jsonld={"@context": "https://schema.org", "@type": "WebPage"},
                                       body=nf, scripts="", robots="noindex"), encoding="utf-8")

    # sitemap: дата меняется только у страниц, которые реально изменились
    lm_file = ROOT / "data" / "lastmod.json"
    lastmod = json.loads(lm_file.read_text()) if lm_file.exists() else {}
    today = date.today().isoformat()
    new_lm = {}
    for path, content in pages.items():
        h = hashlib.sha1(re.sub(r"\?v=[0-9a-f]+", "", content).encode()).hexdigest()[:12]
        old = lastmod.get(path)
        new_lm[path] = old if old and old["hash"] == h else {"hash": h, "date": today}
    lm_file.write_text(json.dumps(new_lm, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")

    def url_xml(path):
        img = ""
        if path in images:
            loc, cap = images[path]
            img = f"<image:image><image:loc>{e(loc)}</image:loc><image:title>{e(cap)}</image:title></image:image>"
        return f"<url><loc>{BASE}{path}</loc><lastmod>{new_lm[path]['date']}</lastmod>{img}</url>"

    (PUB / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
        + "\n".join(url_xml(p) for p in pages) + "\n</urlset>\n", encoding="utf-8")
    (PUB / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\n"
                                    f"Sitemap: {BASE}/sitemap.xml\n", encoding="utf-8")
    print(f"Готово: {len(books)} книг, {len(gslug)} жанров → public/")


if __name__ == "__main__":
    main()
