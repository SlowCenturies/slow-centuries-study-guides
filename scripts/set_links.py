"""Fill in the real links once the repo and videos exist, then rebuild the PDFs (QR codes appear automatically).

    python scripts/set_links.py --user your-github-name \
        --algorithms https://youtu.be/XXXX --money https://youtu.be/YYYY --encryption https://youtu.be/ZZZZ

Any episode you leave out keeps its VIDEO_URL placeholder, so you can run it again as each video goes live.
"""
import argparse, pathlib, re, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument('--user', required=True)
for ep in ('algorithms', 'money', 'encryption'): ap.add_argument(f'--{ep}')
a = ap.parse_args()
files = [ROOT / 'mkdocs.yml', ROOT / 'README.md', ROOT / 'CONTRIBUTING.md'] + list((ROOT / 'docs').rglob('*.md')) + list((ROOT / 'templates').rglob('*.md'))
for f in files:
    if not f.exists(): continue
    t = f.read_text(encoding='utf-8'); t0 = t
    t = t.replace('GITHUB_USER', a.user)
    ep = f.parent.name
    url = getattr(a, ep, None) if ep in ('algorithms', 'money', 'encryption') else None
    if url: t = t.replace('VIDEO_URL', url)
    if t != t0: f.write_text(t, encoding='utf-8'); print('updated', f.relative_to(ROOT))
subprocess.run([sys.executable, str(ROOT / 'scripts' / 'build_pdf.py')], check=True)
print('done: commit and push, and GitHub Pages republishes the site')
