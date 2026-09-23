#!/usr/bin/env python3
"""Build index.html + FLOUCI_FIN_KATMCHI_FULL_BOOK.html from the corrected markdown.

- Converts FLOUCI_FIN_KATMCHI_FULL_BOOK.md with python-markdown
- Builds a cover hero + auto table of contents (screen + print versions)
- Adds print-friendly section breaks, styled tracker chips, progress bar
- Respects markdown column alignment (fixes centered columns)
"""
import io
import re
import markdown

SRC = "FLOUCI_FIN_KATMCHI_FULL_BOOK.md"
OUT_FILES = ["index.html", "FLOUCI_FIN_KATMCHI_FULL_BOOK.html"]

CHAPTER_RE = re.compile(r"<h1>(.*?)</h1>", re.S)
SUB_RE = re.compile(r"<h2>(.*?)</h2>", re.S)


def slug(i: int) -> str:
    return f"sec-{i:02d}"


def build_body(md_text: str) -> tuple[str, list[tuple[str, str]]]:
    # Strip RTL wrapper divs (they are for Markdown viewers; HTML has its own dir="rtl")
    md_text = re.sub(r'^<div dir="rtl">\s*$|^</div>\s*$', '', md_text, flags=re.M)
    html = markdown.markdown(
        md_text, extensions=["tables", "fenced_code", "nl2br"]
    )
    # 1) Extract first h1/h2/h3 as hero content, drop duplicated title block
    m1 = CHAPTER_RE.search(html)
    title = m1.group(1).strip() if m1 else "فلوسي فين كتمشي؟"
    subs = SUB_RE.findall(html)
    subtitle = subs[0].strip() if subs else ""
    m3 = re.search(r"<h3>(.*?)</h3>", html, re.S)
    edition = m3.group(1).strip() if m3 else ""
    # Remove: first h1, first h2, first h3, first hr, second h1, second h2
    for pat in [r"<h1>.*?</h1>", r"<h2>.*?</h2>", r"<h3>.*?</h3>",
                r"<hr\s*/?>", r"<h1>.*?</h1>", r"<h2>.*?</h2>"]:
        html, n = re.subn(pat, "", html, count=1, flags=re.S)
    html = re.sub(r"^(<hr\s*/?>\s*)+", "", html).strip()

    # 2) Tag chapter headings + collect TOC (h1 = chapter, h2 right after = chapter subtitle)
    toc: list[tuple[str, str]] = []
    idx = 0

    def tag_h1(m: re.Match) -> str:
        nonlocal idx
        idx += 1
        text = m.group(1).strip()
        plain = re.sub(r"<[^>]+>", "", text)
        toc.append((slug(idx), plain))
        cls = "chapter-title" if plain.startswith("القسم") else "chapter-title front"
        return f'<h1 id="{slug(idx)}" class="{cls}">{text}</h1>'

    html = CHAPTER_RE.sub(tag_h1, html)
    return html, toc, title, subtitle, edition


CSS = r"""
:root {
    --primary: #1A4331;
    --primary-light: #2A5C45;
    --primary-soft: #EAF1EC;
    --gold: #C5A059;
    --gold-dark: #9A7A3A;
    --gold-light: #E8D3A2;
    --gold-soft: #F4EFE6;
    --cream-bg: #FBF9F4;
    --text-dark: #222624;
    --text-muted: #555E59;
    --border: #DCD5C5;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body {
    font-family: 'Amiri', 'Traditional Arabic', 'Sakkal Majalla', serif;
    font-size: 18px;
    line-height: 1.9;
    color: var(--text-dark);
    background: #E9E4D8 radial-gradient(circle at 50% 0%, #F4F1E8 0%, #E9E4D8 70%);
    padding: 0 12px 60px;
    direction: rtl;
    text-align: right;
}
/* ---------- reading progress ---------- */
.progress-wrap { position: fixed; top: 0; right: 0; left: 0; height: 5px; z-index: 2000; background: transparent; }
#progressBar { height: 100%; width: 0; background: linear-gradient(to left, var(--primary), var(--gold)); }
/* ---------- toolbar ---------- */
.no-print-toolbar {
    max-width: 920px; margin: 14px auto 22px;
    background: linear-gradient(135deg, #143527 0%, var(--primary) 55%, var(--primary-light) 100%);
    color: #fff; padding: 14px 20px; border-radius: 12px;
    box-shadow: 0 6px 20px rgba(20,53,39,.35);
    font-family: 'Cairo', 'Segoe UI', Tahoma, sans-serif;
    border: 1px solid rgba(197,160,89,.45);
}
.toolbar-header { display: flex; flex-wrap: wrap; gap: 12px; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.toolbar-title { font-size: 16px; font-weight: 800; }
.toolbar-badge { display: inline-block; background: var(--gold); color: #1A3025; font-size: 11px; font-weight: 800;
    padding: 2px 10px; border-radius: 20px; margin-right: 8px; vertical-align: middle; }
.toolbar-actions { display: flex; flex-wrap: wrap; gap: 8px; }
.toolbar-tip { background: rgba(255,255,255,.10); border-radius: 8px; padding: 8px 14px; font-size: 13px;
    color: #F8F4EB; border-right: 3px solid var(--gold); line-height: 1.6; }
.btn { background: var(--gold); color: #1A3025; border: none; padding: 8px 14px; border-radius: 7px;
    font-weight: 800; cursor: pointer; text-decoration: none; display: inline-flex; align-items: center;
    gap: 6px; font-size: 13px; transition: all .2s; font-family: inherit; }
.btn:hover { background: #D4AF37; transform: translateY(-1px); }
.btn-secondary { background: #fff; color: var(--primary); }
.btn-secondary:hover { background: #F0EDE4; }
/* ---------- book shell ---------- */
.book-container {
    max-width: 920px; margin: 0 auto; background: var(--cream-bg);
    padding: 0 0 60px; border-radius: 14px;
    box-shadow: 0 14px 40px rgba(0,0,0,.14); border: 1px solid var(--border);
    overflow: hidden;
}
.book-body { padding: 10px 48px 20px; }
/* ---------- cover hero ---------- */
.cover-hero {
    background: linear-gradient(160deg, #10291E 0%, var(--primary) 60%, var(--primary-light) 100%);
    color: #fff; text-align: center; padding: 70px 30px 60px; position: relative; overflow: hidden;
}
.cover-hero::before, .cover-hero::after {
    content: ""; position: absolute; left: 8%; right: 8%; height: 1px;
    background: linear-gradient(to left, transparent, var(--gold) 30%, var(--gold) 70%, transparent);
}
.cover-hero::before { top: 22px; } .cover-hero::after { bottom: 22px; }
.cover-kicker { color: var(--gold-light); letter-spacing: 1px; font-size: 15px; font-weight: 700;
    font-family: 'Cairo', Tahoma, sans-serif; margin-bottom: 18px; }
.cover-title { font-family: 'Cairo', Tahoma, sans-serif; font-weight: 900; font-size: 3rem;
    line-height: 1.4; margin: 0 0 14px; color: #fff; }
.cover-title .q { color: var(--gold); }
.cover-subtitle { font-size: 1.25rem; line-height: 1.9; color: #F1EBDD; max-width: 640px; margin: 0 auto 26px; }
.cover-badges { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; margin-bottom: 30px;
    font-family: 'Cairo', Tahoma, sans-serif; }
.cover-badges span { border: 1.5px solid var(--gold); color: var(--gold-light); font-size: 13px;
    font-weight: 700; padding: 6px 16px; border-radius: 30px; background: rgba(197,160,89,.10); }
.cover-edition { display: inline-block; background: var(--gold); color: #1A3025; font-weight: 800;
    font-size: 14px; padding: 8px 26px; border-radius: 8px; font-family: 'Cairo', Tahoma, sans-serif; }
.cover-meta { margin-top: 22px; font-size: 13.5px; color: #CFC8B8; font-family: 'Cairo', Tahoma, sans-serif; }
/* ---------- TOC ---------- */
.toc { margin: 34px 0 10px; border: 1.5px solid var(--border); border-radius: 12px;
    background: #fff; overflow: hidden; font-family: 'Cairo', Tahoma, sans-serif; }
.toc-head { background: var(--primary); color: #fff; font-weight: 800; font-size: 17px;
    padding: 12px 20px; display: flex; align-items: center; gap: 10px; }
.toc-head .dot { width: 10px; height: 10px; border-radius: 50%; background: var(--gold); }
.toc ol { list-style: none; margin: 0; padding: 10px 0; columns: 1; }
.toc li a { display: flex; align-items: center; gap: 10px; padding: 9px 22px; color: var(--text-dark);
    text-decoration: none; font-size: 15px; font-weight: 600; border-bottom: 1px dashed #E7E0D2; transition: all .15s; }
.toc li:last-child a { border-bottom: none; }
.toc li a:hover { background: var(--gold-soft); color: var(--primary); padding-right: 28px; }
.toc li a .n { flex: 0 0 auto; width: 30px; height: 30px; border-radius: 50%; background: var(--primary-soft);
    color: var(--primary); font-size: 13px; font-weight: 800; display: inline-flex; align-items: center; justify-content: center; }
.toc li a:hover .n { background: var(--primary); color: #fff; }
/* ---------- typography ---------- */
h1, h2, h3, h4 { font-family: 'Cairo', 'Segoe UI', Tahoma, sans-serif; color: var(--primary);
    line-height: 1.6; font-weight: 800; }
h1.chapter-title { font-size: 1.9rem; text-align: center; padding: 18px 15px 14px; margin: 55px 0 8px;
    border: 2px solid var(--gold); border-radius: 12px; background: linear-gradient(180deg, #fff, var(--gold-soft));
    box-shadow: 0 4px 14px rgba(197,160,89,.18); scroll-margin-top: 20px; }
h1.chapter-title.front { font-size: 1.6rem; }
.book-body > h2:first-of-type { margin-top: 30px; }
h2 { font-size: 1.45rem; text-align: right; border-right: 5px solid var(--gold); background: linear-gradient(to left, var(--gold-soft), transparent 75%);
    padding: 8px 14px; border-radius: 6px 0 0 6px; margin: 2.2rem 0 1rem; }
h3 { font-size: 1.22rem; text-align: right; color: var(--primary-light); margin: 1.7rem 0 .8rem; padding-bottom: 6px;
    border-bottom: 1.5px dashed var(--border); }
h4 { font-size: 1.08rem; text-align: right; color: #33463D; margin: 1.3rem 0 .6rem; }
p { margin-bottom: 1rem; text-align: justify; }
strong { color: var(--primary); }
a { color: var(--primary-light); }
blockquote { background: var(--gold-soft); border-right: 5px solid var(--primary);
    padding: 16px 22px; margin: 22px 0; border-radius: 8px 0 0 8px; font-size: 1.04rem; color: var(--primary); }
blockquote strong { color: var(--primary); }
blockquote p:last-child { margin-bottom: 0; }
hr { border: none; height: 2px; margin: 42px auto; max-width: 420px;
    background: linear-gradient(to left, transparent, var(--gold) 25%, var(--gold) 75%, transparent); position: relative; }
hr::after { content: "◆"; position: absolute; top: 50%; right: 50%; transform: translate(50%,-58%);
    color: var(--gold); background: var(--cream-bg); padding: 0 12px; font-size: 13px; }
ul, ol { margin: 0 26px 1.2rem 0; padding-inline-start: 0; padding-left: 0; list-style-position: outside; }
li { margin-bottom: .55rem; }
li::marker { color: var(--gold-dark); font-weight: 800; }
/* tracker chips like [ 100 ] */
code { font-family: 'Cairo', Tahoma, sans-serif; background: #fff; border: 1.5px solid var(--gold);
    color: var(--primary); border-radius: 6px; padding: 1px 10px; font-size: .92em; font-weight: 700;
    white-space: nowrap; box-shadow: 0 1px 3px rgba(197,160,89,.25); }
/* ---------- tables ---------- */
.table-wrap { overflow-x: auto; margin: 24px 0; border-radius: 10px; border: 1px solid var(--border); }
.table-wrap table { margin: 0; border: none; border-radius: 0; }
table { width: 100%; border-collapse: collapse; margin: 24px 0; background: #fff;
    border-radius: 10px; overflow: hidden; border: 1px solid var(--border); direction: rtl; }
th, td { padding: 11px 14px; border: 1px solid #E4DCCB; vertical-align: top; line-height: 1.75; }
th { background: var(--primary); color: #fff; font-family: 'Cairo', Tahoma, sans-serif;
    font-weight: 700; font-size: 15.5px; text-align: right; }
td { font-size: 16.5px; text-align: right; }
td[align="center"], th[align="center"],
td[style*="text-align: center"], th[style*="text-align: center"] { text-align: center !important; }
td[align="left"], th[align="left"],
td[style*="text-align: left"], th[style*="text-align: left"] { text-align: right !important; }
td[style*="text-align: right"], th[style*="text-align: right"] { text-align: right !important; }
tr:nth-child(even) td { background: #FAF7F1; }
/* ---------- back to top ---------- */
#toTop { position: fixed; bottom: 24px; left: 24px; z-index: 1500; width: 48px; height: 48px; border-radius: 50%;
    border: 2px solid var(--gold); background: var(--primary); color: #fff; font-size: 20px; cursor: pointer;
    display: none; align-items: center; justify-content: center; box-shadow: 0 6px 16px rgba(0,0,0,.3); }
#toTop:hover { background: var(--primary-light); }
/* ---------- responsive ---------- */
@media (max-width: 640px) {
    body { font-size: 16.5px; padding: 0 6px 40px; }
    .book-body { padding: 10px 20px 16px; }
    .cover-title { font-size: 2.1rem; }
    .cover-subtitle { font-size: 1.05rem; }
    h1.chapter-title { font-size: 1.45rem; }
    h2 { font-size: 1.25rem; }
    table { display: block; overflow-x: auto; }
    td, th { font-size: 14.5px; padding: 8px 10px; }
}
/* ---------- print ---------- */
@media print {
    @page { margin: 0 !important; }
    html, body { background: #fff !important; margin: 0 !important; padding: 0 !important;
        font-size: 11.5pt; color: #000; }
    .no-print-toolbar, .progress-wrap, #toTop, .toc-screen { display: none !important; }
    .toc-print { display: block !important; }
    .book-container { max-width: 100% !important; border: none !important; box-shadow: none !important;
        margin: 0 !important; border-radius: 0; padding-bottom: 0; }
    .book-body { padding: 0 12mm 10mm !important; }
    .cover-hero { break-after: page; padding: 90px 20px; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    h1.chapter-title { break-before: page; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    h1, h2, h3, h4 { break-after: avoid; }
    table, blockquote, .toc { break-inside: avoid; }
    tr, li { break-inside: avoid; }
    a { text-decoration: none; color: inherit; }
    hr::after { background: #fff; }
}
.toc-print { display: none; }
"""

HTML_TMPL = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="فلوسي فين كتمشي؟ — الدليل العملي للشاب المغربي لتنظيم الراتب والتحكم في المصاريف والادخار. طبعة منقحة لغوياً 2026.">
    <title>فلوسي فين كتمشي؟ — الطبعة المنقحة الكاملة (2026)</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Amiri:ital,wght@0,400;0,700;1,400&family=Cairo:wght@400;600;700;800;900&display=swap" rel="stylesheet">
    <style id="page-size-style">
        @page { size: A5; margin: 0; }
    </style>
    <style>__CSS__</style>
</head>
<body>
    <div class="progress-wrap"><div id="progressBar"></div></div>

    <div class="no-print-toolbar">
        <div class="toolbar-header">
            <div class="toolbar-title">
                📖 <strong>«فلوسي فين كتمشي؟»</strong><span class="toolbar-badge">طبعة منقحة لغوياً ✓</span>
            </div>
            <div class="toolbar-actions">
                <a class="btn" href="./FLOUCI_FIN_KATMCHI_PRINT_READY_A5.pdf" download="FLOUCI_FIN_KATMCHI_PRINT_READY_A5.pdf">📕 تحميل النسخة الطباعية A5 (PDF)</a>
                <a class="btn" href="./flouci_fin_katmchi_book_complete.zip" download="flouci_fin_katmchi_book_complete.zip" style="background:#2A5C45;color:#fff;">📦 الحزمة الكاملة (ZIP)</a>
                <button class="btn btn-secondary" onclick="printClean('A5')">🖨️ طباعة (A5)</button>
                <button class="btn btn-secondary" onclick="printClean('B5')">🖨️ طباعة (B5)</button>
                <a class="btn btn-secondary" href="./FLOUCI_FIN_KATMCHI_FULL_BOOK.md" download="فلوسي_فين_كتمشي.md">📄 Markdown</a>
            </div>
        </div>
        <div class="toolbar-tip">
            💡 <strong>للطباعة الصافية:</strong> في نافذة الطباعة ألغِ تفعيل خيار <strong>«Headers and footers» / «الرؤوس والتذييلات»</strong> حتى لا يطبع المتصفح التاريخ أو الرابط. كل قسم يبدأ في صفحة جديدة تلقائياً.
        </div>
    </div>

    <div class="book-container">
        <header class="cover-hero">
            <div class="cover-kicker">سلسلة التمكين المالي الشخصي بالمغرب</div>
            <div class="cover-title"><span class="q">«</span>__TITLE__<span class="q">»</span></div>
            <p class="cover-subtitle">__SUBTITLE__</p>
            <div class="cover-badges">
                <span>كتاب تدريبي تطبيقي (Workbook)</span>
                <span>تحديات 1,000 / 5,000 / 10,000 درهم</span>
                <span>نظام الأظرفة + خطة 90 يوماً</span>
            </div>
            <div><span class="cover-edition">__EDITION__</span></div>
            <div class="cover-meta">منشورات الثقافة المالية والتمكين الاقتصادي — 2026</div>
        </header>

        <div class="book-body">
            <nav class="toc toc-screen" aria-label="الفهرس">
                <div class="toc-head"><span class="dot"></span> الفهرس العام للكتاب</div>
                <ol>__TOC__</ol>
            </nav>
            <div class="toc toc-print" aria-label="الفهرس">
                <div class="toc-head"><span class="dot"></span> الفهرس العام للكتاب</div>
                <ol>__TOC__</ol>
            </div>
            __BODY__
        </div>
    </div>

    <button id="toTop" title="العودة للأعلى" onclick="window.scrollTo({top:0,behavior:'smooth'})">↑</button>

    <script>
        function printClean(size) {
            const tag = document.getElementById('page-size-style');
            tag.innerHTML = size === 'B5'
                ? '@page { size: B5; margin: 0; }'
                : '@page { size: A5; margin: 0; }';
            setTimeout(() => window.print(), 120);
        }
        (function () {
            const bar = document.getElementById('progressBar');
            const top = document.getElementById('toTop');
            function onScroll() {
                const h = document.documentElement;
                const max = h.scrollHeight - h.clientHeight;
                bar.style.width = (max > 0 ? (h.scrollTop / max) * 100 : 0) + '%';
                top.style.display = h.scrollTop > 600 ? 'inline-flex' : 'none';
            }
            document.addEventListener('scroll', onScroll, { passive: true });
            onScroll();
        })();
    </script>
</body>
</html>
"""


def main() -> None:
    with io.open(SRC, encoding="utf-8") as f:
        md_text = f.read()
    body, toc, title, subtitle, edition = build_body(md_text)
    toc_html = "\n".join(
        f'<li><a href="#{a}"><span class="n">{i+1}</span><span>{t}</span></a></li>'
        for i, (a, t) in enumerate(toc)
    )
    page = (
        HTML_TMPL.replace("__CSS__", CSS)
        .replace("__TITLE__", title)
        .replace("__SUBTITLE__", subtitle)
        .replace("__EDITION__", edition)
        .replace("__TOC__", toc_html)
        .replace("__BODY__", body)
    )
    for out in OUT_FILES:
        with io.open(out, "w", encoding="utf-8") as f:
            f.write(page)
        print(f"wrote {out} ({len(page)} chars, {len(toc)} chapters)")


if __name__ == "__main__":
    main()
