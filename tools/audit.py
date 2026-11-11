#!/usr/bin/env python3
"""SEO-проверка собранного сайта (docs/) и данных книг.  python3 tools/audit.py"""
import collections
import html
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "docs"
BASE = "https://booknix.net"


def g(rx, s):
    m = re.search(rx, s, re.S)
    return html.unescape(m.group(1)) if m else None


def main():
    pages = list(P.rglob("index.html"))
    issues = collections.defaultdict(list)
    titles, descs, links = collections.defaultdict(list), collections.defaultdict(list), set()
    for p in pages:
        s = p.read_text(encoding="utf-8")
        url = "/" if p.parent == P else "/" + str(p.parent.relative_to(P)) + "/"
        t = g(r"<title>(.*?)</title>", s)
        d = g(r'<meta name="description" content="([^"]*)"', s)
        c = g(r'<link rel="canonical" href="([^"]*)"', s)
        oi = g(r'<meta property="og:image" content="([^"]*)"', s)
        if not t:
            issues["нет title"].append(url)
        elif len(t) > 78:
            issues["title длиннее 78"].append(f"{url} ({len(t)})")
        if not d:
            issues["нет description"].append(url)
        elif len(d) < 70:
            issues["description короче 70"].append(f"{url}: {d}")
        elif len(d) > 170:
            issues["description длиннее 170"].append(url)
        titles[t].append(url)
        descs[d].append(url)
        if c != BASE + url:
            issues["canonical не совпадает"].append(f"{url} -> {c}")
        if not oi or not (P / oi.replace(BASE + "/", "")).exists():
            issues["og:image нет файла"].append(f"{url} {oi}")
        body = g(r'<div id="app">(.*?)</div>\n<script', s) or ""
        if len(re.findall(r"<h1[ >]", body)) != 1:
            issues["h1 не один"].append(url)
        for j in re.findall(r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
            try:
                json.loads(j.replace("<\\/", "</"))
            except Exception:
                issues["JSON-LD битый"].append(url)
        for img in re.findall(r"<img [^>]*>", body):
            if 'alt="' not in img or 'alt=""' in img:
                issues["img без alt"].append(url)
        for h in re.findall(r'href="(/(?:knigi|zhanr)/[^"]*)"', s):
            links.add((url, h))
    for u, h in links:
        if not (P / h.strip("/") / "index.html").exists():
            issues["битая внутренняя ссылка"].append(f"{u} -> {h}")
    for t, u in titles.items():
        if len(u) > 1:
            issues["одинаковый title"].append(f"{t}: {u}")
    for d, u in descs.items():
        if len(u) > 1:
            issues["одинаковый description"].append(str(u))
    sm = {x.replace(BASE, "") for x in re.findall(r"<loc>([^<]*)</loc>", (P / "sitemap.xml").read_text())
          if not x.endswith((".jpg", ".webp"))}
    allu = {"/" if p.parent == P else "/" + str(p.parent.relative_to(P)) + "/" for p in pages}
    for u in allu - sm:
        issues["страница не в sitemap"].append(u)
    for u in sm - allu:
        issues["в sitemap нет страницы"].append(u)

    books = json.loads((ROOT / "data/books.json").read_text(encoding="utf-8"))
    today = date.today().isoformat()
    for b in books:
        n = b["title"]
        if len((b.get("annotation") or "").strip()) < 250:
            issues["короткая аннотация (<250 знаков)"].append(n)
        if not b.get("cover"):
            issues["нет обложки"].append(n)
        if not b.get("genres"):
            issues["нет жанров"].append(n)
        if not b.get("post"):
            issues["нет ссылки на пост"].append(n)
        o = b.get("origin") or ""
        if "?" in o or "предполож" in o.lower():
            issues["сомнительная страна"].append(f"{n}: «{o}»")
        if b["type"] == "wait" and b.get("eta") and b["eta"] < today:
            issues["дата перевода уже прошла"].append(f"{n}: {b['eta']}")
    ser = collections.defaultdict(set)
    for b in books:
        if b.get("seriesOrig"):
            ser[b["seriesOrig"].strip().lower()].add(b.get("series"))
    for k, v in ser.items():
        if len(v) > 1:
            issues["один цикл под разными названиями"].append(f"{k}: {v}")
    for k, c in collections.Counter((b["title"].lower(), b["author"]) for b in books).items():
        if c > 1:
            issues["дубль книги"].append(str(k))

    print(f"Страниц: {len(pages)}, книг: {len(books)}, ссылок: {len(links)}")
    for k, v in issues.items():
        print(f"## {k}: {len(v)}")
        for x in v[:40]:
            print("   ", x)


if __name__ == "__main__":
    main()
