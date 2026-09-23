import pymupdf
import re

# A5 standard dimensions in points (148 x 210 mm)
A5_WIDTH = 419.53
A5_HEIGHT = 595.28

# RTL binding: the book is bound on the RIGHT side, so the inner (right)
# margin is larger and the outer (left) margin is smaller.
MARGIN_LEFT = 30.0
MARGIN_RIGHT = 44.0
MARGIN_TOP = 42.0
MARGIN_BOTTOM = 45.0

CONTENT_RECT = pymupdf.Rect(
    MARGIN_LEFT,
    MARGIN_TOP,
    A5_WIDTH - MARGIN_RIGHT,
    A5_HEIGHT - MARGIN_BOTTOM
)

CSS_STYLES = """
@font-face {
    font-family: 'Almarai';
    src: url('Almarai-Regular.ttf');
    font-weight: normal;
    font-style: normal;
}
@font-face {
    font-family: 'Almarai';
    src: url('Almarai-Bold.ttf');
    font-weight: bold;
    font-style: normal;
}
@font-face {
    font-family: 'Almarai';
    src: url('Almarai-Regular.ttf');
    font-weight: normal;
    font-style: italic;
}
@font-face {
    font-family: 'DejaVu Sans';
    src: url('DejaVuSans.ttf');
    font-weight: normal;
    font-style: normal;
}
@font-face {
    font-family: 'DejaVu Sans';
    src: url('DejaVuSans-Bold.ttf');
    font-weight: bold;
    font-style: normal;
}
@page {
    size: 148mm 210mm;
    margin: 15mm 15.5mm 16mm 10.6mm;
}
body {
    font-family: 'Almarai', 'DejaVu Sans', serif;
    font-size: 9.5pt;
    line-height: 1.7;
    color: #222624;
    direction: rtl;
    text-align: right;
    margin: 0;
    padding: 0;
}
h1 {
    font-size: 15pt;
    font-weight: bold;
    color: #1A4331;
    text-align: center;
    margin-top: 0;
    margin-bottom: 7pt;
    border-bottom: 2pt solid #C5A059;
    padding-bottom: 4pt;
    line-height: 1.4;
}
h2 {
    font-size: 11.5pt;
    font-weight: bold;
    color: #2A5C45;
    text-align: right;
    margin-top: 10pt;
    margin-bottom: 5pt;
    border-right: 3.5pt solid #C5A059;
    padding-right: 6pt;
    line-height: 1.4;
}
h3 {
    font-size: 10pt;
    font-weight: bold;
    color: #1A4331;
    text-align: right;
    margin-top: 8pt;
    margin-bottom: 4pt;
}
h4 {
    font-size: 9.5pt;
    font-weight: bold;
    color: #333333;
    text-align: right;
    margin-top: 6pt;
    margin-bottom: 3pt;
}
p {
    margin-top: 0;
    margin-bottom: 6pt;
    text-align: right;
}
p.rtl-li {
    margin-top: 0;
    margin-bottom: 3pt;
    text-align: right;
}
p.li-d1 { margin-right: 16pt; }
p.li-d2 { margin-right: 30pt; }
p.li-d3 { margin-right: 42pt; }
.li-mk {
    font-weight: bold;
    color: #1A4331;
}
blockquote {
    background-color: #F4EFE6;
    border-right: 3.5pt solid #1A4331;
    margin: 6pt 0;
    padding: 6pt 10pt;
    font-size: 9pt;
    color: #1A4331;
    line-height: 1.6;
    text-align: right;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin: 7pt 0;
    font-size: 8.5pt;
    line-height: 1.5;
}
th, td {
    border: 0.5pt solid #DCD5C5;
    padding: 3.5pt 5pt;
    text-align: right;
}
th {
    background-color: #1A4331;
    color: #FFFFFF;
    font-weight: bold;
    font-size: 9pt;
}
code {
    font-family: 'Almarai', 'DejaVu Sans', monospace;
    font-size: 8.5pt;
}
ul, ol {
    margin-top: 0;
    margin-bottom: 6pt;
    padding-right: 14pt;
}
li {
    margin-bottom: 2.5pt;
}
hr {
    border: none;
    border-top: 1pt solid #C5A059;
    margin: 8pt 0;
}
.cover-page {
    text-align: center;
    padding-top: 60pt;
}
.cover-title {
    font-size: 24pt;
    font-weight: bold;
    color: #1A4331;
    margin-bottom: 12pt;
}
.cover-subtitle {
    font-size: 12pt;
    color: #2A5C45;
    line-height: 1.6;
    margin-bottom: 25pt;
}
.cover-badge {
    display: inline-block;
    background-color: #F4EFE6;
    border: 1.5pt solid #C5A059;
    color: #1A4331;
    font-weight: bold;
    font-size: 10pt;
    padding: 6pt 12pt;
    margin-bottom: 40pt;
}
.cover-footer {
    margin-top: 80pt;
    font-size: 9pt;
    color: #555E59;
    border-top: 1pt solid #C5A059;
    padding-top: 10pt;
}
.copyright-page {
    font-size: 8.5pt;
    line-height: 1.7;
    padding-top: 80pt;
    color: #333333;
}
.disclaimer-box {
    background-color: #FBF9F4;
    border: 1pt solid #DCD5C5;
    padding: 8pt 10pt;
    margin-bottom: 16pt;
    font-size: 8.5pt;
    line-height: 1.6;
}
.dedication-box {
    background-color: #F4EFE6;
    border-right: 3.5pt solid #C5A059;
    padding: 10pt 14pt;
    font-size: 9.5pt;
    line-height: 1.7;
    color: #1A4331;
}
.toc-title {
    font-size: 14pt;
    font-weight: bold;
    color: #1A4331;
    border-bottom: 1.5pt solid #C5A059;
    padding-bottom: 4pt;
    margin-bottom: 8pt;
    text-align: center;
}
.toc-table {
    width: 100%;
    font-size: 9pt;
    border-collapse: collapse;
}
.toc-table td {
    border: none;
    border-bottom: 0.5pt dashed #DCD5C5;
    padding: 3.5pt 2pt;
}
"""

def clean_arabic_markdown(text):
    # Strip RTL wrapper divs (for Markdown viewers; PDF has its own RTL handling)
    text = re.sub(r'^<div dir="rtl">\s*$|^</div>\s*$', '', text, flags=re.M)
    text = text.replace('الدليل العميل', 'الدليل العملي')
    text = text.replace('االدخار', 'الادخار')
    text = text.replace('ميثاق الرشف', 'ميثاق الشرف')
    text = text.replace('لحبص التدفقات', 'لحصر التدفقات')
    text = text.replace('لحفظ التدفقات', 'لحصر التدفقات')
    text = text.replace('لحفص التدفقات', 'لحصر التدفقات')
    text = text.replace('First Yourself Pay', 'Pay Yourself First')

    # Emoji have no glyphs in print fonts -> map to classic print symbols
    # (DejaVu Sans fallback covers these in the PDF).
    text = text.replace('\u2705', '\u2713')
    text = text.replace('\u274c', '\u2717')
    text = text.replace('\U0001f31f', '\u2605')
    text = text.replace('\U0001f539', '\u25c6')
    
    # Mathematical correction in savings challenge 10,000 DH:
    text = text.replace("300، 400 درهم", "250، 300 درهم")
    
    # Dates
    text = re.sub(r'\.\.\.\.\s*/\s*\.\.\.\.\s*/\s*6\b', '...... / ...... / 2026 م', text)
    text = re.sub(r'\.\.\.\.\s*/\s*\.\.\.\.\s*/\s*202\.\.\.\s*م', '...... / ...... / 2026 م', text)
    text = re.sub(r'\.\.\.\.\s*/\s*\.\.\.\.\s*/\s*202\.\s*م', '...... / ...... / 2026 م', text)

    # Phrasing
    text = text.replace('المعيار الصحي: يجب ألا يتجاوز 30% إلى 33% كحد أقصى.', 
                        'كقاعدة إرشادية مرنة: يُستحسن ألا يتجاوز عبء السكن 30% إلى 33% كنقطة بداية قابلة للتعديل حسب المدينة والظروف.')
    text = text.replace('المعيار الصحي: أقل من 15%.', 
                        'كقاعدة إرشادية: يُفضل أن تكون نسبة أقساط الديون أقل من 15% من الدخل الصافي.')
    text = text.replace('الحد الأدنى للبدء: 5% إلى 10%.', 
                        'كنقطة انطلاق إرشادية: البدء بادخار 5% إلى 10% ثم التدرج بحسب الإمكانات.')

    return text
