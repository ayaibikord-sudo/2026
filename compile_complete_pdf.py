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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Running header/footer use DejaVu Sans: Almarai's alef presentation forms
# lose their mapping (U+0000) in insert_text subsets, DejaVu stays clean.
FONT_PATH = os.path.join(BASE_DIR, 'fonts', 'DejaVuSans.ttf')
HEADER_FONT_SIZE = 8.0
FOOTER_FONT_SIZE = 8.5

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
        full_html = wrap_html(html_body, _label=f'ch{i:02d}')
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
    # True right alignment: measure the reshaped header, anchor its right
    # edge to the inner (right) margin.
    _hf_font = pymupdf.Font(fontfile=FONT_PATH)
    header_width = _hf_font.text_length(header_reshaped, fontsize=HEADER_FONT_SIZE)

    for pindex in range(final_doc.page_count):
        page = final_doc[pindex]
        page_num = pindex + 1

        if page_num > 5:
            page.insert_font(fontname='runfont', fontfile=FONT_PATH)
            p_line_start = pymupdf.Point(MARGIN_LEFT, 30)
            p_line_end = pymupdf.Point(A5_WIDTH - MARGIN_RIGHT, 30)
            page.draw_line(p_line_start, p_line_end, color=(0.77, 0.69, 0.35), width=0.5)

            page.insert_text(
                pymupdf.Point(A5_WIDTH - MARGIN_RIGHT - header_width, 24),
                header_reshaped,
                fontname='runfont',
                fontsize=HEADER_FONT_SIZE,
                color=(0.25, 0.32, 0.28)
            )

        if page_num >= 4:
            page.insert_font(fontname='runfont', fontfile=FONT_PATH)
            footer_text = f'—  {page_num}  —'
            footer_width = _hf_font.text_length(footer_text, fontsize=FOOTER_FONT_SIZE)
            page.insert_text(
                pymupdf.Point(A5_WIDTH / 2 - footer_width / 2, A5_HEIGHT - 20),
                footer_text,
                fontname='runfont',
                fontsize=FOOTER_FONT_SIZE,
                color=(0.35, 0.35, 0.35)
            )
            
    # Ghost-strip cover-up: Story duplicates table header rows as empty
    # green strips on later pages (pre-existing engine quirk, also in the
    # old DejaVu build). Every genuine header cell in this book contains
    # text (audited), so any textless green strip is certainly a ghost:
    # paint it paper-white. Pagination and real content are untouched.
    GHOST_GREEN = (0.102, 0.263, 0.192)  # #1A4331
    ghosts_covered, ghosts_skipped = 0, 0
    for pindex in range(final_doc.page_count):
        page = final_doc[pindex]
        lines = [ln['bbox'] for b in page.get_text('dict')['blocks']
                 for ln in b.get('lines', [])]
        for dr in page.get_drawings():
            r = dr['rect']
            c = dr.get('fill')
            if not (r.width > 8 and 3 <= r.height <= 12 and c and len(c) == 3
                    and abs(c[0] - GHOST_GREEN[0]) < 0.02
                    and abs(c[1] - GHOST_GREEN[1]) < 0.02
                    and abs(c[2] - GHOST_GREEN[2]) < 0.02):
                continue
            near = any(not (r.x1 < t[0] - 1.5 or r.x0 > t[2] + 1.5
                            or r.y1 < t[1] - 1.5 or r.y0 > t[3] + 1.5)
                       for t in lines)
            if near:
                ghosts_skipped += 1
                continue
            cover = pymupdf.Rect(r.x0 - 1, r.y0 - 1, r.x1 + 1, r.y1 + 1)
            page.draw_rect(cover, color=None, fill=(1, 1, 1), width=0, overlay=True)
            ghosts_covered += 1
    print(f'Ghost strips covered: {ghosts_covered}, skipped (near text): {ghosts_skipped}')

    final_pdf_path = 'FLOUCI_FIN_KATMCHI_PRINT_READY_A5.pdf'
    # Use maximum compression and garbage collection to deduplicate fonts and resources
    final_doc.save(final_pdf_path, garbage=4, deflate=True, clean=True)
    size_mb = os.path.getsize(final_pdf_path) / (1024 * 1024)
    print(f'Saved final print-ready PDF: {final_pdf_path} (Pages: {final_doc.page_count}, Size: {size_mb:.2f} MB)')
    return final_doc.page_count

if __name__ == '__main__':
    build_pdf_pipeline()
