# Print fonts (for `compile_complete_pdf.py`)

The A5 print PDF embeds these fonts (subset). They live here so the build
is hermetic — no system-font dependency.

| File | Family / use | Source | License |
|---|---|---|---|
| `Almarai-Regular.ttf` | Almarai — body text, tables, headings | [google/fonts `ofl/almarai`](https://github.com/google/fonts/tree/main/ofl/almarai) | SIL Open Font License 1.1 |
| `Almarai-Bold.ttf` | Almarai Bold — headings, emphasis | same | same |
| `DejaVuSans.ttf` | Running header/footer + symbol fallback (`✓ ★ ◆ ← …`) | DejaVu Fonts (system copy) | Bitstream Vera + Arev free licenses |
| `DejaVuSans-Bold.ttf` | Bold symbol fallback | same | same |

Why Almarai: it is a professional Arabic book face **and** it round-trips
cleanly through the PDF text layer (copy/search works). Fonts whose Arabic
glyphs live only behind GSUB rules without cmap entries (tested: Amiri,
Scheherazade New) render fine but extract as garbage codepoints, so they
were rejected for this print pipeline.
