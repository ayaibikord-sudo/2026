#!/usr/bin/env python3
"""True-RTL post-processing for the print PDF pipeline.

PyMuPDF's Story engine shapes Arabic text correctly but lays out blocks
(LTR): list markers on the left, table columns left-to-right, headings
left-aligned. This module rewrites generated HTML so the *layout* itself
becomes RTL, like a real printed Arabic book:

- ``<ol>/<ul>/<li>``  -> right-aligned ``<p class="rtl-li">`` with an
  inline marker (``1.`` / ``•``) that bidi places on the RIGHT.
  Nested levels indent from the RIGHT (margin-right).
- ``<table>`` rows    -> cells emitted in reverse order so the first
  logical column renders on the RIGHT. Applies to EVERY table
  (contents page, metadata and chapter tables alike): in an Arabic
  book the first logical column always belongs on the right.
- inter-tag whitespace inside ``<table>`` (outside cells) is dropped:
  Story renders it as empty ghost rows on later pages.

All other markup passes through byte-identical.
"""
import re
from html.parser import HTMLParser


class _RTLTransformer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.out: list[str] = []
        self.lists: list[dict] = []       # {'type': ol/ul, 'n': counter}
        self.li_stack: list[dict] = []    # {'marker': str, 'depth': int, 'buf': [], 'used': bool}
        self.in_table = False
        self.in_row = False
        self.in_cell: dict | None = None   # {'tag': str, 'open': str, 'buf': []}
        self.row_cells: list[str] = []
        self.stats = {'li': 0, 'markers': 0, 'rows': 0, 'cells': 0}


    # ---------- helpers ----------
    def _emit(self, s: str) -> None:
        if self.in_cell is not None:
            self.in_cell['buf'].append(s)
        elif self.li_stack:
            self.li_stack[-1]['buf'].append(s)
        else:
            self.out.append(s)

    def _flush_li(self, li: dict) -> None:
        html = ''.join(li['buf']).strip()
        li['buf'] = []
        if not html:
            return
        # Unwrap loose-list <p> wrappers inside the item (avoid nested <p>).
        html = re.sub(r'<p(\s[^>]*)?>', '', html)
        html = html.replace('</p>', '')
        html = html.strip()
        if not html:
            return
        mk = ''
        if not li['used']:
            mk = f'<span class="li-mk">{li["marker"]}</span> '
            li['used'] = True
            self.stats['markers'] += 1
        d = min(li['depth'], 3)
        self.out.append(f'<p class="rtl-li li-d{d}">{mk}{html}</p>')

    # ---------- parser events ----------
    def handle_starttag(self, tag: str, attrs: list) -> None:
        raw = self.get_starttag_text()
        if tag in ('ol', 'ul') and not self.in_cell:
            if self.li_stack:
                self._flush_li(self.li_stack[-1])
            self.lists.append({'type': tag, 'n': 0})
            return
        if tag == 'li' and not self.in_cell:
            self.stats['li'] += 1
            depth = max(len(self.lists) - 1, 0)
            if self.lists and self.lists[-1]['type'] == 'ol':
                self.lists[-1]['n'] += 1
                marker = f"{self.lists[-1]['n']}."
            else:
                marker = '\u2022'
            self.li_stack.append({'marker': marker, 'depth': depth, 'buf': [], 'used': False})
            return
        if tag == 'table':
            self.in_table = True
            self._emit(raw)
            return
        if tag == 'tr' and self.in_table:
            self.in_row = True
            self.row_cells = []
            self._row_open = raw
            return
        if tag in ('td', 'th') and self.in_row:
            self.in_cell = {'tag': tag, 'open': raw, 'buf': []}
            return
        self._emit(raw)

    def handle_endtag(self, tag: str) -> None:
        if tag in ('ol', 'ul') and not self.in_cell:
            if self.lists:
                self.lists.pop()
            return
        if tag == 'li' and not self.in_cell:
            if self.li_stack:
                li = self.li_stack.pop()
                self._flush_li(li)
            return
        if tag == 'table':
            self.in_table = False
            self._emit(f'</{tag}>')
            return
        if tag == 'tr' and self.in_table:
            self.in_row = False
            self.stats['rows'] += 1
            # Mirror: emit cells in reverse order -> first column on the RIGHT.
            cells = ''.join(reversed(self.row_cells))
            self._emit(self._row_open + cells + '</tr>')
            self.row_cells = []
            return
        if tag in ('td', 'th') and self.in_cell:
            inner = ''.join(self.in_cell['buf'])
            self.row_cells.append(f"{self.in_cell['open']}{inner}</{tag}>")
            self.stats['cells'] += 1
            self.in_cell = None
            return
        self._emit(f'</{tag}>')

    def handle_startendtag(self, tag: str, attrs: list) -> None:
        self._emit(self.get_starttag_text())

    def handle_data(self, data: str) -> None:
        # Drop pure-whitespace nodes between table structure tags: Story
        # turns them into empty ghost rows (header-styled strips that
        # paginate to later pages). HTML collapses them anyway, so this
        # is rendering-neutral for correct engines.
        if not data.strip() and self.in_table and self.in_cell is None:
            return
        self._emit(data)

    def handle_entityref(self, name: str) -> None:
        self._emit(f'&{name};')

    def handle_charref(self, name: str) -> None:
        self._emit(f'&#{name};')

    def handle_comment(self, data: str) -> None:
        self._emit(f'<!--{data}-->')

    def handle_decl(self, decl: str) -> None:
        self._emit(f'<!{decl}>')




def rtl_transform(html: str) -> tuple[str, dict]:
    """Rewrite lists + tables for true RTL layout. Returns (html, stats)."""
    t = _RTLTransformer()
    t.feed(html)
    t.close()
    return ''.join(t.out), t.stats
