# -*- coding: utf-8 -*-
"""Edge headless 批量截图各视图 → docs/screenshots/"""
import os, subprocess, urllib.parse

BASE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(BASE, '..', '..'))
HTML = os.path.join(WS, '六级翻译逐句对照.html')
OUT = os.path.join(WS, 'docs', 'screenshots')
os.makedirs(OUT, exist_ok=True)
EDGE = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'

shots = [
    ('pair.png',     'sec=t&mode=pair&expand=all'),
    ('full.png',     'sec=t&mode=full'),
    ('writing.png',  'sec=w&mode=pair'),
    ('vocab.png',    'mode=vocab'),
    ('type.png',     'mode=type'),
]
for name, qs in shots:
    url = 'file:///' + urllib.parse.quote(HTML.replace('\\', '/')) + '?' + qs
    out = os.path.join(OUT, name)
    r = subprocess.run([EDGE, '--headless=new', '--disable-gpu', '--hide-scrollbars',
                        '--window-size=1440,1000', '--virtual-time-budget=6000',
                        '--screenshot=' + out, url], capture_output=True, timeout=60)
    size = os.path.getsize(out) if os.path.exists(out) else 0
    print(f'{name}: {size//1024} KB (exit {r.returncode})')
