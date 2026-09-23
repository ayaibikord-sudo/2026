import os
import re
import glob
import pymupdf
import markdown
from pdf_builder_core import (
    A5_WIDTH, A5_HEIGHT, CONTENT_RECT, CSS_STYLES, clean_arabic_markdown
)
from pdf_rtl import rtl_transform

FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
ARCHIVE = pymupdf.Archive(FONTS_DIR)

def render_html_to_doc(html_content, temp_path):
    story = pymupdf.Story(html=html_content, archive=ARCHIVE)
    writer = pymupdf.DocumentWriter(temp_path)
    mediabox = pymupdf.Rect(0, 0, A5_WIDTH, A5_HEIGHT)
    more = 1
    while more:
        dev = writer.begin_page(mediabox)
        more, _ = story.place(CONTENT_RECT)
        story.draw(dev)
        writer.end_page()
    writer.close()
    return pymupdf.open(temp_path)

def wrap_html(body_content, _label='?'):
    # True-RTL layout: right-side list markers, mirrored tables (TOC and
    # metadata tables carry no-mirror classes and pass through verbatim).
    body_content, rtl_stats = rtl_transform(body_content)
    if rtl_stats['li'] or rtl_stats['rows']:
        print(f'  [rtl:{_label}] li={rtl_stats["li"]} markers={rtl_stats["markers"]} rows={rtl_stats["rows"]} cells={rtl_stats["cells"]}')
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<style>
{CSS_STYLES}
</style>
</head>
<body>
{body_content}
</body>
</html>"""

def get_cover_html():
    return wrap_html("""
    <div class="cover-page">
        <div style="font-size: 12pt; letter-spacing: 2pt; color: #C5A059; margin-bottom: 20pt; font-weight: bold;">
            سلسلة التمكين المالي الشخصي بالمغرب
        </div>
        
        <div class="cover-title">
            «فلوسي فين كتمشي؟»
        </div>
        
        <div class="cover-subtitle">
            الدليل العملي للشاب المغربي لتنظيم الراتب،<br>
            التحكم في المصاريف، الادخار وبناء أول خطة مالية
        </div>
        
        <div class="cover-badge">
            كتاب تدريبي تطبيقي وتفاعلي (Workbook)
        </div>
        
        <div style="margin: 25pt auto; width: 60px; height: 2px; background: #C5A059;"></div>

        <div style="font-size: 10.5pt; color: #2A5C45; font-weight: bold; line-height: 1.8;">
            يتضمن تحديات الادخار الكبرى (1,000 / 5,000 / 10,000 درهم)<br>
            ونظام الأظرفة، وجداول التتبع الأسبوعية، وخطة الـ 90 يوماً
        </div>
        
        <div class="cover-footer">
            <strong>الطبعة الأولى الرسمية الكاملة (2026)</strong><br>
            منشورات الثقافة المالية والتمكين الاقتصادي
        </div>
    </div>
    """)

def get_copyright_html():
    return wrap_html("""
    <div class="copyright-page">
        <h2 style="text-align: center; border: none; font-size: 11pt; color: #1A4331; margin-bottom: 15pt;">بيانات الإصدار وحقوق النشر</h2>
        <table style="width: 100%; border: none; font-size: 8.5pt; margin-bottom: 20pt;">
            <tr><td style="border: none; width: 35%; font-weight: bold;">عنوان العمل:</td><td style="border: none;">فلوسي فين كتمشي؟</td></tr>
            <tr><td style="border: none; font-weight: bold;">العنوان الفرعي:</td><td style="border: none;">الدليل العملي للشاب المغربي لتنظيم الراتب، التحكم في المصاريف، الادخار وبناء أول خطة مالية</td></tr>
            <tr><td style="border: none; font-weight: bold;">الإعداد والتحرير:</td><td style="border: none;">فريق إعداد الثقافة المالية وتبسيط الاقتصاد الشخصي</td></tr>
            <tr><td style="border: none; font-weight: bold;">سنة الإصدار:</td><td style="border: none;">الطبعة الأولى المعتمدة — 2026 م</td></tr>
            <tr><td style="border: none; font-weight: bold;">المقاس الطباعي:</td><td style="border: none;">A5 القياسي (148 × 210 مم)</td></tr>
            <tr><td style="border: none; font-weight: bold;">حقوق النشر:</td><td style="border: none;">جميع الحقوق محفوظة للمؤلفين ودار النشر © 2026</td></tr>
        </table>
        <div style="font-size: 7.5pt; color: #555E59; line-height: 1.5; border-top: 0.5pt solid #DCD5C5; padding-top: 10pt;">
            لا يُسمح بإعادة إنتاج هذا الكتاب أو أي جزء منه بأي شكل من الأشكال أو نقله بأي وسيلة إلكترونية أو ميكانيكية دون إذن كتابي مسبق، باستثناء الجداول وصفحات التطبيق والتمارين والتحديات المخصصة للاستخدام الشخصي للقارئ.
        </div>
    </div>
    """)

def get_disclaimer_dedication_html():
    return wrap_html("""
    <div style="padding-top: 30pt;">
        <div class="disclaimer-box">
            <strong style="color: #1A4331; font-size: 8.5pt; display: block; margin-bottom: 4pt;">إخلاء مسؤولية قانونية وتعليمية:</strong>
            هذا الكتاب ذو طبيعة تعليمية وإرشادية وتثقيفية عامة تهدف إلى تعزيز الوعي المالي الفردي وتبسيط مهارات إدارة الميزانية الشخصية. المعلومات والنسب الواردة فيه تُقدَّم كقواعد إرشادية مرنة ونقاط انطلاق استرشادية، ولا تشكل استشارة مالية أو استثمارية أو قانونية أو ضريبية شخصية ملزمة. ينبغي لكل قارئ تكييف هذه القواعد وفقاً لظروفه الخاصة ودخله والتزاماته الأسرية والقوانين الجاري بها العمل بالمملكة المغربية.
        </div>
        
        <div style="height: 25pt;"></div>

        <div class="dedication-box">
            <strong style="font-size: 11pt; display: block; margin-bottom: 8pt; color: #1A4331;">إهـــــداء</strong>
            إلى كل شاب وشابة في المغرب يستيقظون باكراً ليقاتلوا بشرف في سبيل لقمة العيش..<br><br>
            إلى العامل، والموظف، والمستقل، وكل من يتعب طوال الشهر، ثم يقف متحيراً في اليوم العاشر ويقول في سره:<br>
            <span style="font-size: 11pt; color: #1A4331; font-weight: bold;">«ما عرفت فين مشاو الفلوس!»</span><br><br>
            هذا الكتاب ليس ليعاتبك على ما مضى، بل ليعطيك المفتاح حتى تصبح أنت السيد على دراهمك، لا العبد لقلق نهاية الشهر.<br><br>
            <strong>إلى كرامتك المالية، وراحة بالك.. نهدي هذا العمل.</strong>
        </div>
    </div>
    """)

def get_toc_html(toc_items):
    half = len(toc_items) // 2 + 1
    p1_items = toc_items[:half]
    p2_items = toc_items[half:]
    
    def render_table(items):
        rows = []
        for title, pnum in items:
            rows.append(f"""<tr>
                <td style="border: none; border-bottom: 0.5pt dashed #DCD5C5; padding: 3.5pt 2pt;">{title}</td>
                <td style="border: none; border-bottom: 0.5pt dashed #DCD5C5; text-align: left; font-weight: bold; color: #1A4331; width: 35pt;">{pnum}</td>
            </tr>""")
        return f"""<table class="toc-table">{''.join(rows)}</table>"""
    
    html = f"""
    <div class="toc-title">الفهرس العام للكتاب</div>
    {render_table(p1_items)}
    <div style="break-before: always; page-break-before: always;"></div>
    <div class="toc-title">تابع: الفهرس العام للكتاب</div>
    {render_table(p2_items)}
    """
    return wrap_html(html)
