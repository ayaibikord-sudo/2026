import pymupdf
import re

# A5 standard dimensions in points (148 x 210 mm)
A5_WIDTH = 419.53
A5_HEIGHT = 595.28

MARGIN_LEFT = 36.0
MARGIN_RIGHT = 36.0
MARGIN_TOP = 42.0
MARGIN_BOTTOM = 45.0

CONTENT_RECT = pymupdf.Rect(
    MARGIN_LEFT,
    MARGIN_TOP,
    A5_WIDTH - MARGIN_RIGHT,
    A5_HEIGHT - MARGIN_BOTTOM
)

CSS_STYLES = """
@page {
    size: 148mm 210mm;
    margin: 15mm 13mm 16mm 13mm;
}
body {
    font-family: sans-serif;
    font-size: 8.5pt;
    line-height: 1.55;
    color: #222624;
    direction: rtl;
    text-align: right;
    margin: 0;
    padding: 0;
}
h1 {
    font-size: 14.5pt;
    font-weight: bold;
    color: #1A4331;
    margin-top: 0;
    margin-bottom: 7pt;
    border-bottom: 2pt solid #C5A059;
    padding-bottom: 4pt;
    line-height: 1.3;
}
h2 {
    font-size: 11pt;
    font-weight: bold;
    color: #2A5C45;
    margin-top: 10pt;
    margin-bottom: 5pt;
    border-right: 3.5pt solid #C5A059;
    padding-right: 6pt;
    line-height: 1.35;
}
h3 {
    font-size: 9.5pt;
    font-weight: bold;
    color: #1A4331;
    margin-top: 8pt;
    margin-bottom: 4pt;
}
h4 {
    font-size: 8.5pt;
    font-weight: bold;
    color: #333333;
    margin-top: 6pt;
    margin-bottom: 3pt;
}
p {
    margin-top: 0;
    margin-bottom: 6pt;
    text-align: justify;
}
blockquote {
    background-color: #F4EFE6;
    border-right: 3.5pt solid #1A4331;
    margin: 6pt 0;
    padding: 6pt 10pt;
    font-size: 8.2pt;
    color: #1A4331;
    line-height: 1.45;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin: 7pt 0;
    font-size: 7.8pt;
    line-height: 1.4;
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
    font-size: 8pt;
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
    font-size: 22pt;
    font-weight: bold;
    color: #1A4331;
    margin-bottom: 12pt;
}
.cover-subtitle {
    font-size: 11pt;
    color: #2A5C45;
    line-height: 1.5;
    margin-bottom: 25pt;
}
.cover-badge {
    display: inline-block;
    background-color: #F4EFE6;
    border: 1.5pt solid #C5A059;
    color: #1A4331;
    font-weight: bold;
    font-size: 9pt;
    padding: 6pt 12pt;
    margin-bottom: 40pt;
}
.cover-footer {
    margin-top: 80pt;
    font-size: 8.5pt;
    color: #555E59;
    border-top: 1pt solid #C5A059;
    padding-top: 10pt;
}
.copyright-page {
    font-size: 8pt;
    line-height: 1.6;
    padding-top: 80pt;
    color: #333333;
}
.disclaimer-box {
    background-color: #FBF9F4;
    border: 1pt solid #DCD5C5;
    padding: 8pt 10pt;
    margin-bottom: 16pt;
    font-size: 7.8pt;
    line-height: 1.5;
}
.dedication-box {
    background-color: #F4EFE6;
    border-right: 3.5pt solid #C5A059;
    padding: 10pt 14pt;
    font-size: 9pt;
    line-height: 1.6;
    color: #1A4331;
}
.toc-title {
    font-size: 13pt;
    font-weight: bold;
    color: #1A4331;
    border-bottom: 1.5pt solid #C5A059;
    padding-bottom: 4pt;
    margin-bottom: 8pt;
    text-align: center;
}
.toc-table {
    width: 100%;
    font-size: 8pt;
    border-collapse: collapse;
}
.toc-table td {
    border: none;
    border-bottom: 0.5pt dashed #DCD5C5;
    padding: 3.5pt 2pt;
}
"""

def clean_arabic_markdown(text):
    text = text.replace('الدليل العميل', 'الدليل العملي')
    text = text.replace('االدخار', 'الادخار')
    text = text.replace('ميثاق الرشف', 'ميثاق الشرف')
    text = text.replace('لحبص التدفقات', 'لحصر التدفقات')
    text = text.replace('لحفظ التدفقات', 'لحصر التدفقات')
    text = text.replace('لحفص التدفقات', 'لحصر التدفقات')
    text = text.replace('First Yourself Pay', 'Pay Yourself First')
    
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
