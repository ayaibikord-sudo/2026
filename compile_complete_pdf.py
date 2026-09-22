import os
import re
import glob
import pymupdf
import markdown
import arabic_reshaper
from bidi.algorithm import get_display

from pdf_builder_core import (
    A5_WIDTH, A5_HEIGHT, MARGIN_LEFT, MARGIN_RIGHT, MARGIN_TOP, MARGIN_BOTTOM,
    CONTENT_RECT, CSS_STYLES, clean_arabic_markdown
)
from book_builder import (
    get_cover_html, get_copyright_html, get_disclaimer_dedication_html,
    get_toc_html, render_html_to_doc, wrap_html
)

FONT_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

def build_pdf_pipeline():
    os.makedirs('tmp_build', exist_ok=True)
    
    chapters = []
    
    # Intro part from 00
    with open('book/00_front_matter_and_start.md', 'r', encoding='utf-8') as f:
        c00 = f.read()
    idx_intro = c00.find('## مقدمة')
    intro_md = c00[idx_intro:]
    chapters.append(('المقدمة ودليل الاستعمال والتشخيص الذاتي', intro_md))
    
    # Chapters 01 to 23
    for fpath in sorted(glob.glob('book/[0-2]*.md')):
        if '00_front' in fpath:
            continue
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        h1 = re.findall(r'^#\s+(.+)$', content, re.MULTILINE)
        title = h1[0] if h1 else os.path.basename(fpath)
        title_clean = title.replace('القسم ', '').strip()
        chapters.append((title_clean, content))
    
    print(f'Total chapters prepared: {len(chapters)}')
    
    # Pass 1: Render with dummy TOC
    dummy_toc_items = [(t, 999) for t, _ in chapters]
    dummy_toc_html = get_toc_html(dummy_toc_items)
    
    doc = pymupdf.open()
    doc_cover = render_html_to_doc(get_cover_html(), 'tmp_build/cover.pdf')
    doc.insert_pdf(doc_cover)
    
    doc_cr = render_html_to_doc(get_copyright_html(), 'tmp_build/cr.pdf')
    doc.insert_pdf(doc_cr)
    
    doc_dd = render_html_to_doc(get_disclaimer_dedication_html(), 'tmp_build/dd.pdf')
    doc.insert_pdf(doc_dd)
    
    doc_toc = render_html_to_doc(dummy_toc_html, 'tmp_build/toc.pdf')
    doc.insert_pdf(doc_toc)
    toc_page_count = doc_toc.page_count
    
    toc_items = []
    for i, (title, md_content) in enumerate(chapters):
        start_page = doc.page_count + 1
        toc_items.append((title, start_page))
        
        html_body = markdown.markdown(
            clean_arabic_markdown(md_content),
            extensions=['tables', 'fenced_code', 'nl2br']
        )
        full_html = wrap_html(html_body)
        ch_pdf_path = f'tmp_build/ch_{i:02d}.pdf'
        ch_doc = render_html_to_doc(full_html, ch_pdf_path)
        doc.insert_pdf(ch_doc)
        print(f'Chapter {i+1} ({title[:25]}...): p.{start_page}, count {ch_doc.page_count}')
        
    print(f'Total pages pass 1: {doc.page_count}')
    
    # Pass 2: Re-render TOC with exact page numbers
    real_toc_html = get_toc_html(toc_items)
    real_doc_toc = render_html_to_doc(real_toc_html, 'tmp_build/real_toc.pdf')
    
    final_doc = pymupdf.open()
    final_doc.insert_pdf(doc_cover)
    final_doc.insert_pdf(doc_cr)
    final_doc.insert_pdf(doc_dd)
    final_doc.insert_pdf(real_doc_toc)
    
    for i in range(len(chapters)):
        ch_doc = pymupdf.open(f'tmp_build/ch_{i:02d}.pdf')
        final_doc.insert_pdf(ch_doc)
        
    print(f'Final reassembled pages: {final_doc.page_count}')
    
    header_raw = '«فلوسي فين كتمشي؟» — الدليل العملي للشاب المغربي'
    header_reshaped = get_display(arabic_reshaper.reshape(header_raw))
    
    for pindex in range(final_doc.page_count):
        page = final_doc[pindex]
        page_num = pindex + 1
        
        if page_num > 5:
            page.insert_font(fontname='dejavu', fontfile=FONT_PATH)
            p_line_start = pymupdf.Point(MARGIN_LEFT, 30)
            p_line_end = pymupdf.Point(A5_WIDTH - MARGIN_RIGHT, 30)
            page.draw_line(p_line_start, p_line_end, color=(0.77, 0.69, 0.35), width=0.5)
            
            page.insert_text(
                pymupdf.Point(A5_WIDTH - MARGIN_RIGHT - 210, 24),
                header_reshaped,
                fontname='dejavu',
                fontsize=7.5,
                color=(0.25, 0.32, 0.28)
            )
        
        if page_num >= 4:
            page.insert_font(fontname='dejavu', fontfile=FONT_PATH)
            footer_text = f'—  {page_num}  —'
            text_width = len(footer_text) * 4.5
            page.insert_text(
                pymupdf.Point(A5_WIDTH / 2 - text_width / 2, A5_HEIGHT - 20),
                footer_text,
                fontname='dejavu',
                fontsize=8.0,
                color=(0.35, 0.35, 0.35)
            )
            
    final_pdf_path = 'FLOUCI_FIN_KATMCHI_PRINT_READY_A5.pdf'
    # Use maximum compression and garbage collection to deduplicate fonts and resources
    final_doc.save(final_pdf_path, garbage=4, deflate=True, clean=True)
    size_mb = os.path.getsize(final_pdf_path) / (1024 * 1024)
    print(f'Saved final print-ready PDF: {final_pdf_path} (Pages: {final_doc.page_count}, Size: {size_mb:.2f} MB)')
    return final_doc.page_count

if __name__ == '__main__':
    build_pdf_pipeline()
