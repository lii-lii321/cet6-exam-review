# -*- coding: utf-8 -*-
"""解析懒笔记词表 md → vocab.json（三份词表 + 合并打字题库）"""
import re, json, os

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "vocab")
OUT = os.path.join(BASE, "vocab.json")

CJK = r'\u4e00-\u9fff\u3000-\u303f\uff00-\uffef\u2018\u2019\u201c\u201d'
SPACE_IN_CJK = re.compile(rf'(?<=[{CJK}])\s+(?=[{CJK}])')

ENTRY = re.compile(
    r'(\d{1,4})\s+([A-Za-z][A-Za-z\-]*)\s+(A1|A2|B1|B2|C1|C2)\s+(.*?)\s*(?=\d{1,4}\s+[A-Za-z][A-Za-z\-]*\s+(?:A1|A2|B1|B2|C1|C2)\s|$)')


def parse(fn):
    text = open(os.path.join(SRC, fn), encoding='utf-8').read()
    items = []
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith('#') or s.startswith('<!--') or not s:
            continue
        for m in ENTRY.finditer(s):
            rank, word, cefr, gloss = int(m.group(1)), m.group(2), m.group(3), m.group(4)
            gloss = SPACE_IN_CJK.sub('', gloss).strip()
            fq = None
            mfq = re.search(r'\s+(\d{1,4})$', gloss)
            if mfq:
                fq = int(mfq.group(1))
                gloss = gloss[:mfq.start()].strip()
            items.append({'rank': rank, 'word': word, 'cefr': cefr, 'gloss': gloss, 'freq': fq})
    items.sort(key=lambda x: x['rank'])
    return items


def check(items, expect, name):
    ok = [it['rank'] for it in items] == list(range(1, expect + 1))
    print(f'{name}: {len(items)} 条, 序号连续: {ok}')
    if not ok:
        ranks = [it['rank'] for it in items]
        print('  缺:', sorted(set(range(1, expect + 1)) - set(ranks))[:10],
              '重:', sorted({r for r in ranks if ranks.count(r) > 1})[:10])
    return ok


CEFR_RANK = {'C2': 6, 'C1': 5, 'B2': 4, 'B1': 3, 'A2': 2, 'A1': 1}


def merge(lists):
    """lists: [(tag, items)] → 按小写词去重合并"""
    pool = {}
    for tag, items in lists:
        for w in items:
            k = w['word'].lower()
            e = pool.setdefault(k, {'word': w['word'], 'cefr': '', 'gloss': '', 'freq': 0, 'tags': []})
            if tag not in e['tags']:
                e['tags'].append(tag)
            if CEFR_RANK.get(w['cefr'], 0) > CEFR_RANK.get(e['cefr'], 0):
                e['cefr'] = w['cefr']
            if len(w['gloss']) > len(e['gloss']):
                e['gloss'] = w['gloss']
            e['freq'] = max(e['freq'], w['freq'] or 0)
    out = sorted(pool.values(), key=lambda x: -x['freq'])
    return out


def main():
    over = parse('超纲词.md')
    c12 = parse('高频词.md')
    kg = parse('考纲高频词.md')
    check(over, 263, '超纲词')
    check(c12, 204, 'C1-C2高频词')
    check(kg, 1834, '考纲高频词')
    merged = merge([('超纲', over), ('C1C2', c12), ('考纲', kg)])
    print('合并去重后:', len(merged), '词')
    multi = sum(1 for w in merged if len(w['tags']) > 1)
    print('多表重合词:', multi)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump({'over': over, 'c12': c12, 'kg': kg, 'merged': merged}, f, ensure_ascii=False, indent=1)
    print('样例 merged[0]:', merged[0])


if __name__ == '__main__':
    main()
