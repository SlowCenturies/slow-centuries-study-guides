"""Check every external link in docs/ and (optionally) ask the Wayback Machine to save a copy.

    python scripts/check_links.py            # report broken links
    python scripts/check_links.py --archive  # also save each working link to web.archive.org
Run it before publishing a new guide and once a term.
"""
import pathlib, re, sys, time, urllib.request
ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = {'User-Agent': 'Mozilla/5.0 (SlowCenturies link check)'}
links = set()
for md in (ROOT / 'docs').rglob('*.md'):
    for url in re.findall(r'\]\((https?://[^)\s]+)\)', md.read_text(encoding='utf-8')):
        if 'GITHUB_USER' not in url: links.add((url, md.relative_to(ROOT)))
bad = 0
for url, src in sorted(links):
    try:
        req = urllib.request.Request(url, headers=UA, method='GET')
        code = urllib.request.urlopen(req, timeout=25).status
    except Exception as e:
        code = getattr(e, 'code', str(e)[:60])
    ok = code == 200
    bad += not ok
    print(('OK  ' if ok else 'FAIL'), code, url, f'({src})')
    if ok and '--archive' in sys.argv:
        try: urllib.request.urlopen(urllib.request.Request('https://web.archive.org/save/' + url, headers=UA), timeout=60); time.sleep(5)
        except Exception as e: print('     archive failed:', e)
print(f'\n{len(links)} links, {bad} need attention')
sys.exit(1 if bad else 0)
