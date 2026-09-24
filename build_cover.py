#!/usr/bin/env python3
"""Designed front cover for «فلوسي فين كتمشي؟» (A5, true-RTL, print-ready).

Draws a real book cover with PyMuPDF vector graphics (no HTML/Story limits):
deep-green gradient, gold double frame with corner ornaments, gold title in
Almarai Bold, cream subtitle, workbook badge, challenge coins and edition mark.

Outputs:
  FLOUCI_COVER_A5.pdf   standalone 1-page cover (for the print shop)
  FLOUCI_COVER_A5.png   150dpi preview (for sharing / stores)
Also exposes build_cover_doc() so the main pipeline can bind it as page 1.
"""
import os
import pymupdf
import arabic_reshaper
from bidi.algorithm import get_display

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, 'fonts')
# Cover-only face: Amiri carries full Arabic Presentation-Forms coverage, so
# pre-shaped (reshaper+bidi) direct insertion renders perfectly. Almarai
# lacks ~165/293 presentation forms (tofu boxes) and DejaVu is complete but
# plain. Body text keeps Almarai via Story/GSUB (see fonts/FONTS.md).
REGULAR = os.path.join(FONTS, 'Amiri-Regular.ttf')
BOLD = os.path.join(FONTS, 'Amiri-Bold.ttf')

A5_W, A5_H = 419.53, 595.28

# Palette
GREEN_TOP = (0x16 / 255, 0x38 / 255, 0x2B / 255)
GREEN_BOT = (0x0C / 255, 0x24 / 255, 0x1C / 255)
LATTICE = (0x1E / 255, 0x4C / 255, 0x39 / 255)
GOLD = (0xC5 / 255, 0xA0 / 255, 0x59 / 255)
GOLD_LT = (0xE9 / 255, 0xC7 / 255, 0x67 / 255)
CREAM = (0xFD / 255, 0xFA / 255, 0xF0 / 255)
INK_GREEN = (0x1A / 255, 0x43 / 255, 0x31 / 255)

_font_cache = {}


def _font(path):
    if path not in _font_cache:
        _font_cache[path] = pymupdf.Font(fontfile=path)
    return _font_cache[path]


def ar(text):
    """Shape + bidi-reorder Arabic for direct PDF text drawing."""
    return get_display(arabic_reshaper.reshape(text))


def center_x(page, text, fontpath, size, cx):
    w = _font(fontpath).text_length(ar(text), fontsize=size)
    return cx - w / 2


def put(page, text, x, y, fontpath, size, color):
    page.insert_font(fontname='cv' + ('B' if 'Bold' in fontpath else 'R'),
                     fontfile=fontpath)
    page.insert_text(pymupdf.Point(x, y), ar(text),
                     fontname='cv' + ('B' if 'Bold' in fontpath else 'R'),
                     fontsize=size, color=color)


def diamond(page, cx, cy, r, color, fill=None):
    pts = [pymupdf.Point(cx, cy - r), pymupdf.Point(cx + r, cy),
           pymupdf.Point(cx, cy + r), pymupdf.Point(cx - r, cy)]
    for i in range(4):
        page.draw_line(pts[i], pts[(i + 1) % 4], color=color, width=1.1)
    if fill is not None:
        shape = page.new_shape()
        shape.draw_polyline(pts + [pts[0]])
        shape.finish(color=color, fill=fill, width=0.6, closePath=True)
        shape.commit()


def draw_cover(page):
    W, H, cx = A5_W, A5_H, A5_W / 2

    # --- gradient background (120 bands) ---
    for i in range(120):
        f = i / 119
        c = tuple(GREEN_TOP[k] + (GREEN_BOT[k] - GREEN_TOP[k]) * f
                  for k in range(3))
        page.draw_rect(pymupdf.Rect(0, H * i / 120, W, H * (i + 1) / 120 + 0.5),
                       color=None, fill=c, width=0)

    # --- subtle diagonal lattice ---
    step = 46
    x = -H
    while x < W + H:
        page.draw_line(pymupdf.Point(x, 0), pymupdf.Point(x + H, H),
                       color=LATTICE, width=0.5)
        x += step
    x = -H
    while x < W + H:
        page.draw_line(pymupdf.Point(x + H, 0), pymupdf.Point(x, H),
                       color=LATTICE, width=0.5)
        x += step

    # --- double gold frame ---
    page.draw_rect(pymupdf.Rect(14, 14, W - 14, H - 14), color=GOLD, width=2)
    page.draw_rect(pymupdf.Rect(21, 21, W - 21, H - 21), color=GOLD, width=0.75)
    for px, py in [(21, 21), (W - 21, 21), (21, H - 21), (W - 21, H - 21)]:
        diamond(page, px, py, 4.5, GOLD, fill=GOLD)

    # --- kicker ---
    kicker = 'سلسلة التمكين المالي الشخصي بالمغرب'
    put(page, kicker, center_x(page, kicker, BOLD, 10.5, cx), 78, BOLD, 10.5,
        GOLD_LT)
    page.draw_line(pymupdf.Point(cx - 110, 92), pymupdf.Point(cx + 110, 92),
                   color=GOLD, width=0.75)
    diamond(page, cx, 92, 3.5, GOLD, fill=GOLD)

    # --- main title (auto-fit one line) ---
    title = '«فلوسي فين كتمشي؟»'
    size = 33
    while _font(BOLD).text_length(ar(title), fontsize=size) > W - 110 and size > 18:
        size -= 1
    put(page, title, center_x(page, title, BOLD, size, cx), 168, BOLD, size,
        GOLD_LT)

    # --- divider with medallion ---
    page.draw_line(pymupdf.Point(cx - 95, 196), pymupdf.Point(cx - 12, 196),
                   color=GOLD, width=1)
    page.draw_line(pymupdf.Point(cx + 12, 196), pymupdf.Point(cx + 95, 196),
                   color=GOLD, width=1)
    diamond(page, cx, 196, 6, GOLD, fill=None)
    diamond(page, cx, 196, 2.6, GOLD, fill=GOLD)

    # --- subtitle ---
    sub1 = 'الدليل العملي للشاب المغربي لتنظيم الراتب،'
    sub2 = 'التحكم في المصاريف، الادخار وبناء أول خطة مالية'
    put(page, sub1, center_x(page, sub1, REGULAR, 11.5, cx), 224, REGULAR, 11.5,
        CREAM)
    put(page, sub2, center_x(page, sub2, REGULAR, 11.5, cx), 243, REGULAR, 11.5,
        CREAM)

    # --- workbook badge ---
    badge = 'كتاب تدريبي تطبيقي وتفاعلي (Workbook)'
    bw = _font(BOLD).text_length(ar(badge), fontsize=10.5)
    bx0, by0 = cx - bw / 2 - 16, 264
    page.draw_rect(pymupdf.Rect(bx0, by0, cx + bw / 2 + 16, by0 + 30),
                   color=GOLD, fill=CREAM, width=1)
    put(page, badge, cx - bw / 2, by0 + 20.5, BOLD, 10.5, INK_GREEN)

    # --- challenges caption + coins (RTL: 1,000 at right) ---
    cap = 'تحديات الادخار الكبرى (درهم)'
    put(page, cap, center_x(page, cap, BOLD, 10, cx), 336, BOLD, 10, GOLD_LT)
    coins = [('1,000', cx + 108), ('5,000', cx), ('10,000', cx - 108)]
    for amount, px in coins:
        page.draw_circle(pymupdf.Point(px, 372), 27, color=GOLD, fill=GOLD,
                         width=1)
        page.draw_circle(pymupdf.Point(px, 372), 22.5, color=INK_GREEN,
                         width=0.9)
        aw = _font(BOLD).text_length(amount, fontsize=10.5)
        page.insert_font(fontname='cvB', fontfile=BOLD)
        page.insert_text(pymupdf.Point(px - aw / 2, 376), amount,
                         fontname='cvB', fontsize=10.5, color=INK_GREEN)

    # --- extras line ---
    extra = 'نظام الأظرفة • جداول التتبع الأسبوعية • خطة الـ 90 يوماً'
    put(page, extra, center_x(page, extra, REGULAR, 9.5, cx), 428, REGULAR, 9.5,
        CREAM)

    # --- bottom ornament + edition + publisher ---
    page.draw_line(pymupdf.Point(cx - 70, 470), pymupdf.Point(cx + 70, 470),
                   color=GOLD, width=0.75)
    for dx in (-14, 0, 14):
        diamond(page, cx + dx, 470, 3.2, GOLD, fill=GOLD if dx == 0 else None)
    ed = 'الطبعة الأولى الرسمية الكاملة (2026)'
    put(page, ed, center_x(page, ed, BOLD, 10.5, cx), 498, BOLD, 10.5, CREAM)
    pub = 'منشورات الثقافة المالية والتمكين الاقتصادي'
    put(page, pub, center_x(page, pub, REGULAR, 9.5, cx), 518, REGULAR, 9.5,
        GOLD_LT)


def build_cover_doc():
    doc = pymupdf.open()
    page = doc.new_page(width=A5_W, height=A5_H)
    draw_cover(page)
    return doc


if __name__ == '__main__':
    os.chdir(HERE)
    doc = build_cover_doc()
    doc.save('FLOUCI_COVER_A5.pdf', garbage=4, deflate=True)
    print('saved FLOUCI_COVER_A5.pdf')
    doc[0].get_pixmap(dpi=150).save('FLOUCI_COVER_A5.png')
    print('saved FLOUCI_COVER_A5.png')
