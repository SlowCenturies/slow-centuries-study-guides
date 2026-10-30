"""Build a branded, print-ready PDF for every guide in docs/*/index.md that has a `pdf:` block in its front matter.

    pip install -r requirements.txt && python -m playwright install chromium
    python scripts/build_pdf.py

The PDF is designed separately from the website: a charcoal cover with the glowing signature line and the
BCE → TODAY timeline, then warm paper pages with orange accents, a visual timeline, term cards, a worksheet
for the activity, and QR codes once the real links are filled in. Output: docs/pdf/<slug>.pdf
"""
import base64, html, io, pathlib, re, subprocess, sys
import markdown, yaml
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / 'docs'
SITE_URL = yaml.safe_load(re.sub(r'!!python/name:\S+', 'null', (ROOT / 'mkdocs.yml').read_text()))['site_url']

def qr_svg(url):
    """QR code as inline SVG, or a placeholder box while the URL still has a placeholder in it."""
    if not url or 'GITHUB_USER' in url or 'VIDEO_URL' in url:
        return '<div class="qr qr--todo">QR code<br>appears after<br>setup</div>'
    import qrcode, qrcode.image.svg
    img = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, border=1)
    buf = io.BytesIO(); img.save(buf)
    return '<div class="qr">' + buf.getvalue().decode().split('?>', 1)[-1] + '</div>'

def data_uri(path):
    return 'data:image/png;base64,' + base64.b64encode(path.read_bytes()).decode()

def font_face():
    f = (DOCS / 'assets' / 'fonts').as_uri()
    faces = [('Libre Caslon Display', 'libre-caslon-display', [('400', 'normal')]),
             ('Libre Caslon Text', 'libre-caslon-text', [('400', 'normal'), ('400', 'italic'), ('700', 'normal')]),
             ('Source Serif 4', 'source-serif-4', [('400', 'normal'), ('400', 'italic'), ('600', 'normal'), ('600', 'italic'), ('700', 'normal')]),
             ('Courier Prime', 'courier-prime', [('400', 'normal'), ('700', 'normal')])]
    out = []
    for fam, file, variants in faces:
        for ext in ('latin', 'latin-ext'):
            for w, st in variants:
                out.append(f"@font-face{{font-family:'{fam}';font-weight:{w};font-style:{st};src:url('{f}/{file}-{ext}-{w}-{st}.woff2') format('woff2')}}")
    return '\n'.join(out)

CSS = r"""
@page { size: Letter; margin: 0.45in 0 0.55in 0; }
@page cover { margin: 0; }
.cover { page: cover; }
:root { --char:#0b0b0b; --ink:#1d1b18; --muted:#6d675f; --paper:#ffffff; --rule:#d9d3c8; --or:#e0793a; --or-hot:#ffb072; --or-dk:#a8521d; --hl: rgba(255,200,87,.7); }
* { box-sizing: border-box; }
html, body { margin:0; padding:0; background: var(--paper); color: var(--ink); font-family: 'Source Serif 4', Georgia, serif; font-size: 10pt; line-height: 1.5; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
a { color: var(--or-dk); text-decoration: none; }
em { font-style: italic; }

/* ---------- cover ---------- */
.cover { height: 11in; width: 8.5in; background: var(--char); color: #f3ede4; position: relative; overflow: hidden; page-break-after: always; }
.cover .kicker { position:absolute; left:0.75in; top:0.7in; font: 700 9pt 'Courier Prime'; letter-spacing:.04em; color: var(--or); }
.cover .brand { position:absolute; right:0.75in; top:0.66in; font: italic 400 14pt 'Libre Caslon Text'; color:#bdb6aa; }
.cover h1 { position:absolute; left:0.75in; right:0.75in; top:1.25in; margin:0; font: 400 52pt/0.95 'Libre Caslon Display'; letter-spacing:-.01em; }
.cover h1 span { color: var(--or); text-shadow: 0 0 22px rgba(224,121,58,.55); }
.cover .tagline { position:absolute; left:0.78in; right:2.4in; top:2.2in; font: italic 400 16pt/1.3 'Libre Caslon Text'; color:#d8d0c4; }
.cover svg.art { position:absolute; left:0; top:0; }
.cover .meta { position:absolute; left:0.75in; width:4.7in; bottom:1.5in; display:flex; gap:.3in; font: 400 8.5pt 'Source Serif 4'; color:#bdb6aa; }
.cover .meta b { display:block; font: 700 7.5pt 'Courier Prime'; letter-spacing:.04em; color: var(--or); margin-bottom: 2pt; }
.cover .qrs { position:absolute; right:0.75in; bottom:1.4in; display:flex; gap:12pt; text-align:center; font: 700 7pt 'Courier Prime'; letter-spacing:.04em; color:#bdb6aa; }
.cover .qr { width: 0.95in; height: 0.95in; background:#f3ede4; border-radius:6px; padding:4px; margin-bottom:4pt; }
.cover .qr svg { width:100%; height:100%; }
.cover .qr--todo { background:transparent; border:1px dashed #6d675f; color:#8c8984; font: 500 6.5pt/1.3 'Source Serif 4'; letter-spacing:0; display:flex; align-items:center; justify-content:center; }
.cover .tl { position:absolute; left:0.75in; right:0.75in; bottom:0.36in; }
.cover .tl .labels { display:flex; justify-content:space-between; font: 700 8pt 'Courier Prime'; letter-spacing:.04em; margin-top: 7pt; }
.cover .tl .labels span:last-child { color: var(--or); }

/* ---------- interior: quiet editorial layout, one accent colour, hairline rules, no boxes or glows ---------- */
main { padding: 0.2in 0.85in 0.2in; }
.sec { margin-top: 18pt; }
h2 { font: 400 20pt/1.1 'Libre Caslon Display'; margin: 0 0 8pt; padding-top: 7pt; border-top: 1px solid var(--ink); display: flex; gap: 10pt; align-items: baseline; break-after: avoid; break-inside: avoid; }
h2 .num { font: 400 10pt 'Courier Prime'; color: var(--or-dk); min-width: 16pt; }
h3 { font: 700 8.5pt 'Courier Prime'; letter-spacing:.04em; color: var(--ink); margin: 12pt 0 4pt; break-after: avoid; }
p { margin: 0 0 7pt; }
.lead p { font: 400 12pt/1.55 'Source Serif 4'; color: var(--ink); max-width: 5.6in; }

/* chapters: a plain two-column list */
.chapters { columns: 2; column-gap: 24pt; }
.chap { display: grid; grid-template-columns: 36pt 1fr; padding: 4pt 0; border-bottom: 0.5px solid var(--rule); break-inside: avoid; }
.chap .t { font: 400 9pt 'Courier Prime'; color: var(--or-dk); padding-top: 1pt; }
.chap .n { font: 600 9pt/1.3 'Source Serif 4'; }
.chap .w { grid-column: 2; font-size: 8.3pt; line-height: 1.35; color: var(--muted); }

/* timeline: the glowing orange line with a dot per event (brand motif) */
.timeline { position: relative; margin-left: 4pt; }
.timeline::before { content:''; position:absolute; left: 1.02in; top: 4pt; bottom: 4pt; width: 2px; background: linear-gradient(var(--or), var(--or-hot)); box-shadow: 0 0 6px rgba(224,121,58,.6); }
.ev { display:grid; grid-template-columns: 0.95in 1fr; column-gap: 0.22in; padding: 3.5pt 0; break-inside: avoid; position: relative; }
.ev::before { content:''; position:absolute; left: calc(1.02in - 3.5px); top: 7pt; width: 9px; height: 9px; border-radius: 50%; background: var(--paper); border: 2px solid var(--or); }
.ev .d { text-align:right; font: 700 8.5pt/1.25 'Courier Prime'; color: var(--or-dk); padding-top: 2pt; }
.ev .d small { display:block; font: 400 7.2pt 'Courier Prime'; color: var(--muted); margin-top: 1pt; }
.ev .x { font-size: 9pt; line-height: 1.4; padding-top: 1.5pt; }

/* key terms: a two-column glossary */
.terms { columns: 2; column-gap: 24pt; }
.term { padding: 0 0 6pt; break-inside: avoid; }
.term b { font: 600 9.5pt 'Source Serif 4'; display: inline; background: linear-gradient(rgba(255,200,87,0) 50%, var(--hl) 50%, var(--hl) 94%, rgba(255,200,87,0) 94%); padding: 0 1.5pt; -webkit-box-decoration-break: clone; box-decoration-break: clone; }
.term b::after { content: '. '; }
.term span { font-size: 9pt; line-height: 1.4; }

/* sources */
.sources ul { list-style: none; padding: 0; margin: 0; }
.sources li { padding: 3pt 0; border-bottom: 0.5px solid var(--rule); break-inside: avoid; font-size: 9pt; line-height: 1.4; }
.sources li a { color: var(--ink); text-decoration: underline; text-decoration-color: var(--or); text-decoration-thickness: 1px; text-underline-offset: 2px; }
.sources li strong { background: linear-gradient(rgba(255,200,87,0) 50%, var(--hl) 50%, var(--hl) 94%, rgba(255,200,87,0) 94%); padding: 0 1.5pt; -webkit-box-decoration-break: clone; box-decoration-break: clone; }
.sources li strong a { font-weight: 600; text-decoration: none; }
.sources .host { font: 400 7.5pt 'Courier Prime'; color: var(--muted); }
.sources .intro { font-size: 8.8pt; color: var(--muted); max-width: 5.6in; }

/* activity */
.worksheet { border-top: 1px solid var(--ink); border-bottom: 1px solid var(--ink); padding: 8pt 0 10pt; break-inside: avoid; }
.worksheet .bar { display: flex; flex-wrap: wrap; gap: 2pt 14pt; justify-content: space-between; align-items: baseline; margin-bottom: 6pt; }
.worksheet .bar b { font: 600 12pt 'Source Serif 4'; }
.worksheet .bar span { font: 400 8pt 'Courier Prime'; color: var(--muted); }
.worksheet .body { display: grid; grid-template-columns: 1.3fr 1fr; gap: 20pt; }
.worksheet ol { margin: 0; padding-left: 14pt; font-size: 9pt; }
.worksheet ol li { margin-bottom: 3pt; }
.grid-title { font: 700 7.5pt 'Courier Prime'; color: var(--muted); margin: 0 0 3pt; }
table.dbl { border-collapse: collapse; width: 100%; font: 400 9.5pt 'Courier Prime'; margin-bottom: 8pt; }
table.dbl td, table.dbl th { border-bottom: 0.5px solid #bdb5a8; padding: 2.5pt 6pt; text-align: center; height: 16pt; }
table.dbl th { font: 700 7pt 'Courier Prime'; color: var(--muted); border-bottom: 1px solid var(--ink); }
table.dbl td.ck { color: var(--or-dk); width: 20pt; font-weight: 700; }
table.dbl tr.tick td { font-weight: 700; }
.answer { font: 700 8.5pt 'Courier Prime'; color: var(--ink); }
.follow { margin-top: 8pt; font-size: 9pt; }
.follow ul { margin: 2pt 0 0; padding-left: 14pt; }
.follow p { margin: 6pt 0 0; }

/* discussion */
ol.disc { break-inside: avoid; list-style: none; counter-reset: q; padding: 0; margin: 0; }
ol.disc li { counter-increment: q; display: grid; grid-template-columns: 20pt 1fr; padding: 4pt 0; font-size: 9.5pt; }
ol.disc li::before { content: counter(q) '.'; font: 400 9pt 'Courier Prime'; color: var(--or-dk); padding-top: 1pt; }

/* debated + cultural note: highlighted as whole sections */
.callout { background: var(--char); color: #ece8e1; padding: 12pt 16pt 10pt; break-inside: avoid; }
.callout h2 { color: #f3ede4; border-top: 0; padding-top: 0; }
.callout h2 .num { color: var(--or-hot); }
.callout ul { margin: 0; padding-left: 14pt; font-size: 9.2pt; }
.callout li { margin-bottom: 5pt; }
.callout strong { color: var(--or-hot); font-weight: 600; }
.note { border: 1px solid var(--or); background: rgba(224,121,58,.07); padding: 10pt 16pt 6pt; break-inside: avoid; }
.note h2 { border-top: 0; padding-top: 0; }
.note p { font-style: italic; font-size: 9.2pt; }

.further ul { padding-left: 14pt; font-size: 9pt; margin: 0; }
.endcard { margin-top: 14pt; padding-top: 8pt; border-top: 1px solid var(--ink); display: flex; justify-content: space-between; gap: 20pt; font-size: 7.8pt; color: var(--muted); break-inside: avoid; }
.endcard .cc { font: 700 7.5pt 'Courier Prime'; color: var(--ink); white-space: nowrap; text-align: right; }
"""

def host(url):
    m = re.match(r'https?://(?:www\.)?([^/]+)', url)
    return m.group(1) if m else ''

def cover_art(meta, img_path):
    """SVG: hero image, glowing signature line entering left, tracing the image, leaving right, plus the BCE→TODAY rule."""
    W, H = 816, 1056                     # 8.5x11in at 96 dpi
    size, cx, cy = 430, W * 0.60, 560    # hero image box
    x0, y0 = cx - size / 2, cy - size / 2
    pts = [(x0 + u / 530 * size, y0 + v / 530 * size) for u, v in (meta.get('cover_trace') or [])]
    if pts:
        path = [(-10, pts[0][1])] + pts + [(W + 10, pts[-1][1])]
    else:
        path = [(-10, cy), (W + 10, cy)]
    d = 'M' + ' L'.join(f'{x:.1f},{y:.1f}' for x, y in path)
    img = f'<image href="{data_uri(img_path)}" x="{x0}" y="{y0}" width="{size}" height="{size}" filter="url(#shadow)"/>' if img_path and img_path.exists() else ''
    ty = H - 0.62 * 96
    ticks = ''.join(f'<line x1="{72 + (W-144)*t:.0f}" x2="{72 + (W-144)*t:.0f}" y1="{ty-7}" y2="{ty+7}" stroke="#8a5a3a" stroke-width="2"/>' for t in (.2, .42, .6, .76, .9))
    return f'''<svg class="art" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs>
    <filter id="glow" filterUnits="userSpaceOnUse" x="-50" y="-50" width="{W+100}" height="{H+100}"><feGaussianBlur stdDeviation="5" result="a"/><feGaussianBlur stdDeviation="14" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="a"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy="26" stdDeviation="22" flood-color="#000" flood-opacity=".85"/></filter>
    <radialGradient id="spot"><stop offset="0" stop-color="#e0793a" stop-opacity=".30"/><stop offset="1" stop-color="#e0793a" stop-opacity="0"/></radialGradient>
  </defs>
  {img}
  <path d="{d}" fill="none" stroke="#e0793a" stroke-width="5" stroke-linejoin="round" filter="url(#glow)"/>
  <path d="{d}" fill="none" stroke="#ffb072" stroke-width="1.8" stroke-linejoin="round"/>
  <line x1="72" x2="{W-72}" y1="{ty}" y2="{ty}" stroke="#e0793a" stroke-width="3" filter="url(#glow)"/>
  <line x1="72" x2="{W-72}" y1="{ty}" y2="{ty}" stroke="#ffb072" stroke-width="1.2"/>
  {ticks}
  <line x1="72" x2="72" y1="{ty-9}" y2="{ty+9}" stroke="#e0793a" stroke-width="3"/>
  <circle cx="{W-72}" cy="{ty}" r="7" fill="#fff1e0" filter="url(#glow)"/>
</svg>'''

def section(label_no, label, title, inner, cls=''):
    return f'<section class="sec {cls}"><h2><span class="num">{label_no}</span>{title}</h2>{inner}</section>'

def build(md_path):
    raw = md_path.read_text(encoding='utf-8')
    fm, body = raw.split('---', 2)[1:]
    meta = yaml.safe_load(fm) or {}
    pdf = meta.get('pdf')
    if not pdf: return None
    folder = md_path.parent.name
    html_body = markdown.markdown(body, extensions=['attr_list', 'def_list', 'tables'])
    soup = BeautifulSoup(html_body, 'html.parser')

    # split into {h2 text: [nodes]} plus the header paragraph(s)
    sections, cur, head = {}, None, []
    for node in list(soup.children):
        if getattr(node, 'name', None) == 'h1': continue
        if getattr(node, 'name', None) == 'h2':
            cur = node.get_text(strip=True); sections[cur] = []; continue
        (sections[cur] if cur else head).append(node)
    get = lambda key: next((v for k, v in sections.items() if k.lower().startswith(key)), [])
    inner = lambda nodes: ''.join(str(n) for n in nodes)

    # cover facts from the "**Episode length:** ..." line
    facts = []
    for p in BeautifulSoup(inner(head), 'html.parser').find_all('p'):
        for b in p.find_all('strong'):
            val = b.next_sibling
            val = (val if isinstance(val, str) else '').strip(' ·')
            if val: facts.append((b.get_text().rstrip(':'), val))
    title = meta.get('title', '')
    t_words = title.split(' ', 2)
    title_html = (' '.join(t_words[:-1]) + f' <span>{t_words[-1]}</span>') if len(t_words) > 1 else title
    guide_url = SITE_URL.rstrip('/') + f'/{folder}/'
    video = re.search(r'\[[^\]]*Watch the episode\]\(([^)]+)\)', body)
    cover = f'''<div class="cover">{cover_art(pdf, DOCS / pdf.get('cover_image', ''))}
  <div class="kicker">SLOW CENTURIES · STUDY GUIDE</div><div class="brand">Watch the world's systems take shape.</div>
  <h1>{title_html}</h1><div class="tagline">{html.escape(pdf.get('tagline', ''))}</div>
  <div class="meta">{''.join(f'<div><b>{html.escape(k.upper())}</b>{html.escape(v)}</div>' for k, v in facts)}</div>
  <div class="qrs"><div>{qr_svg(video.group(1) if video else '')}WATCH</div><div>{qr_svg(guide_url)}ALL LINKS</div></div>
  <div class="tl"><div class="labels"><span>{html.escape(str(pdf.get('timeline_start', '')))}</span><span>TODAY</span></div></div>
</div>'''

    out, n = [], 0
    def add(label, title, content, cls=''):
        nonlocal n; n += 1; out.append(section(n, label, title, content, cls))

    # 1 summary
    add('Summary', 'In one paragraph', f'<div class="lead">{inner(get("in one paragraph"))}</div>')
    # 2 chapters as cards
    tb = BeautifulSoup(inner(get('watch with chapters')), 'html.parser').find('table')
    if tb:
        cards = ''.join(f'<div class="chap"><div class="t">{c[0].get_text()}</div><div class="n">{c[1].decode_contents()}</div><div class="w">{c[2].decode_contents()}</div></div>'
                        for c in (r.find_all('td') for r in tb.find_all('tr')[1:]) if len(c) >= 3)
        add('Watch', 'Watch with chapters', f'<div class="chapters">{cards}</div>')
    # 3 visual timeline
    tb = BeautifulSoup(inner(get('timeline')), 'html.parser').find('table')
    if tb:
        evs = ''.join(f'<div class="ev"><div class="d">{c[0].get_text()}<small>{c[1].get_text()}</small></div><div class="x">{c[2].decode_contents()}</div></div>'
                      for c in (r.find_all('td') for r in tb.find_all('tr')[1:]) if len(c) >= 3)
        add('Timeline', 'The timeline', f'<div class="timeline">{evs}</div>')
    # 4 key terms as cards
    dl = BeautifulSoup(inner(get('key terms')), 'html.parser').find('dl')
    if dl:
        cards = ''.join(f'<div class="term"><b>{dt.get_text()}</b><span>{dt.find_next_sibling("dd").decode_contents()}</span></div>' for dt in dl.find_all('dt'))
        add('Vocabulary', 'Key terms', f'<div class="terms">{cards}</div>')
    # 5 activity worksheet
    act_key = next((k for k in sections if k.lower().startswith('hands-on activity')), None)
    if act_key:
        a = BeautifulSoup(inner(sections[act_key]), 'html.parser')
        name = act_key.split(':', 1)[-1].strip(); name = name[:1].upper() + name[1:]
        timep = a.find('p'); steps = a.find('ol'); rest = steps.find_all_next() if steps else []
        follow_html = ''.join(str(x) for x in a.find_all(['ul']) ) if a.find('ul') else ''
        ext = next((p for p in a.find_all('p') if p.get_text().lower().startswith('extension')), None)
        worked = ''
        if 'egyptian' in act_key.lower():   # worked example + blank practice grid for the doubling method
            rows = [(1, 12, True), (2, 24, False), (4, 48, True), (8, 96, True)]
            worked = ('<div class="grid-title">WORKED EXAMPLE · 12 × 13</div><table class="dbl"><tr><th></th><th>COUNT</th><th>DOUBLE</th></tr>'
                      + ''.join(f'<tr class="{"tick" if t else ""}"><td class="ck">{"✓" if t else ""}</td><td>{a_}</td><td>{b_}</td></tr>' for a_, b_, t in rows)
                      + '</table><div class="answer">1 + 4 + 8 = 13 → 12 + 48 + 96 = 156</div>'
                      + '<div class="grid-title" style="margin-top:10pt">YOUR TURN · ____ × ____</div><table class="dbl"><tr><th></th><th>COUNT</th><th>DOUBLE</th></tr>'
                      + ''.join(f'<tr><td class="ck"></td><td>{v}</td><td></td></tr>' for v in (1, 2, 4, 8, 16)) + '</table>')
        content = (f'<div class="worksheet"><div class="bar"><b>{name}</b><span>{timep.get_text().upper() if timep else ""}</span></div>'
                   f'<div class="body"><div>{str(steps) if steps else ""}</div><div>{worked}</div></div>'
                   f'<div class="follow"><b>Follow-up questions</b>{follow_html}{str(ext) if ext else ""}</div></div>')
        add('Try it', 'Hands-on activity', content)
    # 6 discussion
    ol = BeautifulSoup(inner(get('discussion questions')), 'html.parser').find('ol')
    if ol:
        ol['class'] = 'disc'
        add('Talk about it', 'Discussion questions', str(ol))
    # 7 debated (dark callout)
    deb = get("what's still debated")
    if deb:
        n += 1; out.append(f'<section class="sec"><div class="callout"><h2><span class="num">{n}</span>What\'s still debated</h2>{inner(deb)}</div></section>')
    # 8 sources
    src = BeautifulSoup(inner(get('primary sources')), 'html.parser')
    for a_ in src.find_all('a'):   # site name as a separate grey label, outside the highlight
        tag = src.new_tag('span', attrs={'class': 'host'}); tag.string = '· ' + host(a_.get('href', ''))
        anchor = a_.parent if a_.parent.name == 'strong' else a_
        anchor.insert_after(tag); anchor.insert_after(' ')
    first_p = src.find('p')
    if first_p: first_p['class'] = 'intro'
    add('Go to the source', 'Primary sources and places to visit online', f'<div class="sources">{str(src)}</div>')
    # 9 cultural note
    note = get('a note on cultural respect')
    if note:
        n += 1; out.append(f'<section class="sec"><div class="note"><h2><span class="num">{n}</span>A note on cultural respect</h2>{inner(note)}</div></section>')
    # further reading + end card
    fr = get('further reading')
    if fr:
        add('Read more', 'Further reading', f'<div class="further">{inner(fr)}</div>')
    credits = BeautifulSoup(inner(get('credits and reuse')), 'html.parser').find('p')
    out.append(f'<div class="endcard"><div>{credits.decode_contents() if credits else ""}</div><div class="cc">CC BY 4.0<br>Slow Centuries</div></div>')

    wrap = lambda b: f'<!doctype html><html><head><meta charset="utf-8"><style>{font_face()}{CSS}</style></head><body>{b}</body></html>'
    return pdf['slug'], title, wrap(cover), wrap(f'<main>{"".join(out)}</main>')

def main():
    (DOCS / 'pdf').mkdir(exist_ok=True)
    tmp = ROOT / '_pdfbuild'; tmp.mkdir(exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page()
        for md in sorted(DOCS.glob('*/index.md')):
            res = build(md)
            if not res: continue
            slug, title, cover_doc, body_doc = res
            out = DOCS / 'pdf' / f'{slug}.pdf'
            parts = []
            for part, doc in (('cover', cover_doc), ('body', body_doc)):
                hp = tmp / f'{slug}-{part}.html'; hp.write_text(doc, encoding='utf-8')
                pg.goto(hp.as_uri(), wait_until='networkidle'); pg.evaluate('document.fonts.ready')
                pp = tmp / f'{slug}-{part}.pdf'; parts.append(str(pp))
                if part == 'cover':
                    pg.pdf(path=str(pp), format='Letter', print_background=True, prefer_css_page_size=True)
                else:
                    footer = (f'<div style="width:100%;font:700 7px Courier Prime,Courier,monospace;letter-spacing:.04em;color:#8c8984;padding:0 0.75in;display:flex;justify-content:space-between">'
                              f'<span>{html.escape(title.upper())} · STUDY GUIDE</span><span style="color:#e0793a">SLOW CENTURIES · <span class="pageNumber"></span></span></div>')
                    pg.pdf(path=str(pp), format='Letter', print_background=True, display_header_footer=True,
                           header_template='<span></span>', footer_template=footer, prefer_css_page_size=True)
            subprocess.run(['pdfunite', *parts, str(out)], check=True)   # poppler-utils
            print('wrote', out.relative_to(ROOT))
        b.close()
    if '--keep-html' not in sys.argv:
        import shutil; shutil.rmtree(tmp)

if __name__ == '__main__':
    main()
