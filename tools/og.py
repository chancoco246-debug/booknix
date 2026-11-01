"""Картинки для превью ссылок (Telegram, WhatsApp, VK, соцсети), 1200×630.

* book_card()   — обложка книги целиком + название, автор, полка;
* home_collage() — галерея обложек для главной.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1200, 630
FONTS = Path(__file__).resolve().parent / "fonts"
INK = (11, 15, 21)
PAPER = (237, 230, 216)
MUTE = (154, 164, 179)
AMBER = (242, 165, 65)
BADGES = {"translation": ("МОЙ ПЕРЕВОД", (242, 165, 65), (26, 18, 6)),
          "rec": ("РЕКОМЕНДАЦИЯ", (76, 141, 255), (255, 255, 255)),
          "wait": ("ЛИСТ ОЖИДАНИЯ", (179, 155, 255), (26, 16, 51))}


def font(name, size, weight):
    f = ImageFont.truetype(str(FONTS / f"{name}.ttf"), size)
    f.set_variation_by_name(weight)
    return f


def fill(img, w, h):
    """Масштабировать и обрезать по центру, чтобы заполнить w×h."""
    s = max(w / img.width, h / img.height)
    img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    x, y = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))


def rounded(img, r):
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, img.width - 1, img.height - 1), r, fill=255)
    out = Image.new("RGBA", img.size)
    out.paste(img.convert("RGBA"), (0, 0), m)
    return out


def paste_with_shadow(canvas, img, xy, r=12, blur=22, alpha=170):
    sh = Image.new("RGBA", (img.width + blur * 4, img.height + blur * 4), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((blur * 2, blur * 2, blur * 2 + img.width, blur * 2 + img.height), r,
                                         fill=(0, 0, 0, alpha))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    canvas.alpha_composite(sh, (xy[0] - blur * 2, xy[1] - blur * 2 + 10))
    canvas.alpha_composite(rounded(img, r), xy)


def wrap(draw, text, f, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=f) <= width or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit_one_line(draw, text, f, width):
    if draw.textlength(text, font=f) <= width:
        return text
    while text and draw.textlength(text + "…", font=f) > width:
        text = text[:-1]
    return text.rstrip(" ,·") + "…"


def logo(draw, x, y, size):
    f = font("Unbounded", size, "ExtraBold")
    draw.text((x, y), "BOOK", font=f, fill=AMBER)
    draw.text((x + draw.textlength("BOOK", font=f), y), "NIX", font=f, fill=PAPER)
    return x + draw.textlength("BOOKNIX", font=f)


def book_card(b, cover_path, out):
    cover = Image.open(cover_path).convert("RGB")
    canvas = fill(cover, W, H).filter(ImageFilter.GaussianBlur(38)).convert("RGBA")
    canvas.alpha_composite(Image.new("RGBA", (W, H), INK + (200,)))
    ch = 550
    cw = round(cover.width * ch / cover.height)
    paste_with_shadow(canvas, cover.resize((cw, ch), Image.LANCZOS), (64, (H - ch) // 2))

    d = ImageDraw.Draw(canvas)
    x = 64 + cw + 56
    tw = W - x - 60
    y = 64
    label, bg, fg = BADGES.get(b["type"], BADGES["rec"])
    fb = font("GolosText", 22, "Bold")
    bw = d.textlength(label, font=fb) + 28
    d.rounded_rectangle((x, y, x + bw, y + 40), 6, fill=bg)
    d.text((x + 14, y + 7), label, font=fb, fill=fg)
    y += 70

    for size in (60, 54, 48, 42, 36):
        ft = font("Unbounded", size, "Bold")
        lines = wrap(d, b["title"], ft, tw)
        if len(lines) <= 3:
            break
    lines = lines[:3]
    for ln in lines:
        d.text((x, y), fit_one_line(d, ln, ft, tw), font=ft, fill=PAPER)
        y += round(size * 1.18)
    y += 14
    fa = font("GolosText", 32, "Medium")
    d.text((x, y), fit_one_line(d, b["author"], fa, tw), font=fa, fill=(220, 212, 198))
    y += 48
    orig = " · ".join(v for v in [str(b.get("origTitle") or "").strip(), str(b.get("year") or "").strip()] if v)
    if orig:
        fo = font("GolosText", 24, "Regular")
        d.text((x, y), fit_one_line(d, orig, fo, tw), font=fo, fill=MUTE)

    end = logo(d, x, H - 64 - 34, 34)
    fs = font("GolosText", 24, "Regular")
    d.text((end + 18, H - 64 - 27), "booknix.net", font=fs, fill=MUTE)
    canvas.convert("RGB").save(out, "JPEG", quality=86, optimize=True, progressive=True)


def home_collage(cover_paths, out, tagline):
    canvas = Image.new("RGBA", (W, H), INK + (255,))
    cw, chh, gap = 196, 294, 14
    rows = [(-70, -30), (cw // 2 - 70 + gap // 2, chh - 30 + gap)]
    covers = [Image.open(p).convert("RGB") for p in cover_paths]
    i = 0
    for x0, y in rows:
        x = x0
        while x < W:
            img = covers[i % len(covers)].resize((cw, chh), Image.LANCZOS)
            canvas.alpha_composite(rounded(img, 10), (x, y))
            x += cw + gap
            i += 1
    # затемнение снизу под логотип
    grad = Image.new("L", (1, H))
    for yy in range(H):
        t = max(0.0, (yy - 250) / (H - 250))
        grad.putpixel((0, yy), int(255 * min(1.0, t * 1.25)))
    shade = Image.new("RGBA", (W, H), INK + (255,))
    shade.putalpha(grad.resize((W, H)))
    canvas.alpha_composite(shade)
    canvas.alpha_composite(Image.new("RGBA", (W, H), INK + (40,)))

    d = ImageDraw.Draw(canvas)
    fl = font("Unbounded", 76, "ExtraBold")
    lw = d.textlength("BOOKNIX", font=fl)
    logo(d, (W - lw) / 2, 430, 76)
    ft = font("GolosText", 32, "Medium")
    d.text(((W - d.textlength(tagline, font=ft)) / 2, 538), tagline, font=ft, fill=PAPER)
    canvas.convert("RGB").save(out, "JPEG", quality=86, optimize=True, progressive=True)
