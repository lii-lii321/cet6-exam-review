# -*- coding: utf-8 -*-
"""注入 data.json + vocab.json + writing.json 到 template.html，生成最终网页"""
import json, os

BASE = os.path.dirname(os.path.abspath(__file__))
tpl = open(os.path.join(BASE, 'template.html'), encoding='utf-8').read()
data = json.load(open(os.path.join(BASE, 'data.json'), encoding='utf-8'))
vocab = json.load(open(os.path.join(BASE, 'vocab.json'), encoding='utf-8'))
writing = json.load(open(os.path.join(BASE, 'writing.json'), encoding='utf-8'))
assert all(x in tpl for x in ('__DATA_JSON__', '__VOCAB_JSON__', '__WRITING_JSON__'))

def inj(js):
    return json.dumps(js, ensure_ascii=False).replace('</', '<\\/')

out = (tpl.replace('__DATA_JSON__', inj(data))
          .replace('__VOCAB_JSON__', inj(vocab))
          .replace('__WRITING_JSON__', inj(writing)))
dst = os.path.join(BASE, '..', '..', '六级翻译逐句对照.html')
open(dst, 'w', encoding='utf-8').write(out)
print('OK', os.path.getsize(dst), 'bytes')
