# -*- coding: utf-8 -*-
"""把懒笔记格式的六级汉译英 markdown 解析为逐句对齐 JSON"""
import re, json, os, glob

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "extracted")
OUT = os.path.join(BASE, "data.json")

PAGE_MARK = re.compile(r'^<!-- Page \d+ -->\s*$')
NUM_SENT = re.compile(r'^(\d{1,2})[.．、](?!\d)\s*(.+)$')
TAG_LINE = re.compile(r'^(?:#{1,4}\s*)?【([^】]{1,6})】\s*(.*)$')

CJK = r'\u4e00-\u9fff\u3000-\u303f\uff00-\uffef\u2018\u2019\u201c\u201d'
SPACE_IN_CJK = re.compile(rf'(?<=[{CJK}])\s+(?=[{CJK}])')
ARTIFACT = re.compile(r'\\+([、，。；：？！])')
# 子标题判定用标点
SUB_PUNCT = re.compile('[。；：？！，,、\\.（）()\u201c\u201d\u2018\u2019"\'…—]')


def clean_cn(t):
    t = ARTIFACT.sub(r'\1', t)
    t = SPACE_IN_CJK.sub('', t)
    return t.strip()


def is_sublike(s):
    """短、无句末标点、无英文 → 子标题/词条行"""
    return (len(s) <= 22 and not SUB_PUNCT.search(s)
            and not re.search(r'[A-Za-z]', s) and not s.startswith('【'))


def join_en(lines):
    out = ''
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        if out.endswith('-'):
            out += ln
        elif out:
            out += ' ' + ln
        else:
            out = ln
    return re.sub(r'\s+', ' ', out).strip()


def split_block_body(lines, first_sub=None):
    """行级拆分：短无标点行识别为子标题，其余行并入当前项正文（提取器每行间有空行，段落不可靠）"""
    items = []
    if first_sub is not None:
        items.append({'sub': clean_cn(first_sub), 'text': ''})
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        s = re.sub(r'^#{1,4}\s*', '', s).strip()  # 剥掉提取产物中的 ### 前缀
        if not s:
            continue
        if is_sublike(s) and not re.search(r'[。；，？！]', s):
            items.append({'sub': clean_cn(s), 'text': ''})
        elif items:
            if items[-1]['text'] == '' and items[-1]['sub']:
                items[-1]['text'] = s
            else:
                items[-1]['text'] = items[-1]['text'] + ' ' + s
        else:
            items.append({'sub': '', 'text': s})
    for it in items:
        it['text'] = clean_cn(it['text']) if not re.match(r'^[A-Z]', it['text']) else re.sub(r'\s+', ' ', it['text']).strip()
    return items


def parse_bridges(lines):
    """衔接区：短标题行开新条目，其余行并入当前条目正文；兼容【衔接】标记"""
    flat = []
    for ln in lines:
        s = ln.strip()
        if not s or s.startswith('懒笔记'):
            continue
        flat.append(re.sub(r'^【衔接】\s*', '', s))

    def is_title(s):
        if re.match(r'^第\d+句', s) and len(s) <= 30:
            return True
        return len(s) <= 20 and not re.search(r'[。；：，？！、]', s) and not re.search(r'[A-Za-z]', s)

    bridges = []
    for s in flat:
        if bridges and not is_title(s):
            last = bridges[-1]
            last['body'] = clean_cn(last['body'] + ' ' + s) if last['body'] else clean_cn(s)
        elif is_title(s) and (not bridges or bridges[-1]['body']):
            bridges.append({'title': clean_cn(s), 'body': ''})
        elif bridges:
            # 标题但上一条无正文（罕见）：并入上一条正文
            bridges[-1]['body'] = clean_cn(bridges[-1]['body'] + ' ' + s)
        else:
            bridges.append({'title': '', 'body': clean_cn(s)})
    return [b for b in bridges if b['title'] or b['body']]


def parse_file(path):
    raw = open(path, encoding='utf-8').read()
    lines = [l for l in raw.splitlines() if not PAGE_MARK.match(l)]

    # ---------- 标题（跳过前导空行） ----------
    i = 0
    while i < len(lines) and lines[i].strip() == '':
        i += 1
    title_parts = []
    while i < len(lines):
        s = lines[i].strip()
        if s == '':
            i += 1
            continue
        if re.match(r'^#{1,4}\s', s):
            title_parts.append(re.sub(r'^#{1,4}\s*', '', s).strip())
            i += 1
        else:
            break
    title_all = SPACE_IN_CJK.sub('', ' '.join(title_parts))
    m = re.search(r'（段落翻译）\s*·?\s*(.*?)\s*参考译文与解析', title_all)
    theme = clean_cn(m.group(1)) if m else title_all

    # ---------- 三段式扫描 ----------
    cn_lines, full_lines, bridge_region = [], [], []
    stage = 0  # 0=前言 1=中文 2=整篇译文 3=衔接 4=逐句解析
    idx_jj = next(k for k, l in enumerate(lines) if l.strip() == '逐句解析')
    for j in range(i, len(lines)):
        ln = lines[j]
        s = ln.strip()
        if j == idx_jj:
            stage = 4
            continue
        if stage == 0:
            if s.startswith('Directions:'):
                stage = 1
            continue
        if stage == 1:
            if s.startswith('参考译文'):
                stage = 2
            elif s:
                cn_lines.append(s)
            continue
        if stage == 2:
            if s.startswith('懒笔记'):
                continue
            if s.startswith('【衔接】'):
                stage = 3
                bridge_region.append(s)
                continue
            if s:
                full_lines.append(s)
            continue
        if stage == 3:
            if s.startswith('懒笔记'):
                continue
            bridge_region.append(ln.rstrip())
            continue
        break  # stage 4 单独处理

    chinese_para = clean_cn(' '.join(cn_lines))
    full_en_text = join_en(full_lines)
    bridges = parse_bridges(bridge_region)

    # ---------- 逐句解析区 ----------
    tail = lines[idx_jj + 1:]
    sentences, cur, cur_block, first_sub = [], None, None, None
    globals_blocks = []

    def flush_block():
        nonlocal cur_block, first_sub
        if cur_block is not None:
            items = split_block_body(cur_block['lines'], first_sub)
            blk = {'tag': cur_block['tag'], 'title': cur_block.get('title', ''), 'items': items}
            if cur is not None:
                cur['blocks'].append(blk)
            else:
                globals_blocks.append(blk)
        cur_block, first_sub = None, None

    for ln in tail:
        s = ln.strip()
        if s == '':
            if cur_block is not None:
                cur_block['lines'].append('')
            continue
        if s.startswith('懒笔记'):
            continue
        # 卷尾「全卷构成」导航区：到此为止，不再收集
        if '全卷构成' in s or re.match(r'^Part\s+[IVX]+\s', s):
            flush_block()
            break
        mnum = NUM_SENT.match(s)
        if mnum and int(mnum.group(1)) == len(sentences) + 1:
            flush_block()
            cur = {'cn': clean_cn(mnum.group(2)), 'blocks': [], 'en_raw': ''}
            sentences.append(cur)
            cur_block = None
            continue
        mtag = TAG_LINE.match(s)
        if mtag:
            flush_block()
            tag, rest = mtag.group(1), mtag.group(2)
            cur_block = {'tag': tag, 'title': '', 'lines': []}
            if tag == '译文':
                cur_block['lines'].append(rest)  # 英文首行
            elif rest:
                if is_sublike(rest):
                    first_sub = rest
                else:
                    cur_block['title'] = rest
            continue
        if cur_block is not None:
            cur_block['lines'].append(s)
        elif cur is not None:
            if not cur['cn'].endswith(('。', '！', '？', '.', '!', '?')):
                cur['cn'] = clean_cn(cur['cn'] + s)
        else:
            globals_blocks.append({'tag': 'TEXT', 'title': '', 'items': [{'sub': '', 'text': clean_cn(s)}]})
    flush_block()

    # 译文块 → sen['en_raw']；其余为解析块
    for sen in sentences:
        en_parts = [sen['en_raw']] if sen['en_raw'] else []
        for b in sen['blocks']:
            if b['tag'] == '译文':
                t = join_en([it['sub'] + ' ' + it['text'] if it['sub'] else it['text'] for it in b['items']])
                en_parts.append(t)
        sen['en_raw'] = re.sub(r'\s+', ' ', ' '.join(en_parts)).strip()
        sen['blocks'] = [b for b in sen['blocks'] if b['tag'] != '译文']

    # ---------- 用整篇译文交叉修复断行丢连字符 ----------
    en_sents = [x.strip() for x in re.split(r'(?<=[.!?])\s+(?=[A-Z\u201c"])', full_en_text) if x.strip()]
    norm = lambda t: re.sub(r'[\s\-]+', '', t).lower()
    for sen in sentences:
        raw = norm(sen['en_raw'])
        sen['en'] = sen['en_raw']
        if not raw:
            continue
        for es in en_sents:
            if norm(es) == raw:
                sen['en'] = es
                break

    # ---------- 全局块 ----------
    g = {'主旨': '', '时态': '', '译法': [], 'other': []}
    for b in globals_blocks:
        if b['tag'] == '主旨':
            g['主旨'] = clean_cn(' '.join(it['sub'] + ' ' + it['text'] if it['sub'] else it['text'] for it in b['items']))
        elif b['tag'] == '时态':
            g['时态'] = clean_cn(' '.join(it['sub'] + ' ' + it['text'] if it['sub'] else it['text'] for it in b['items']))
        elif b['tag'] == '译法':
            g['译法'] = [{'term': clean_cn(it['sub']) if it['sub'] else '', 'body': it['text']} for it in b['items']]
        elif b['tag'] != 'TEXT':
            g['other'].append(b)

    return {'theme': theme, 'chinese_para': chinese_para, 'full_en': full_en_text,
            'bridges': bridges, 'global': g, 'sentences': sentences}


def main():
    papers = []
    pat = re.compile(r'英语六级(\d{4})年(\d{1,2})月第(\d)套')
    for fn in sorted(glob.glob(os.path.join(SRC, '*.md'))):
        m = pat.search(os.path.basename(fn))
        year, month, setn = int(m.group(1)), int(m.group(2)), int(m.group(3))
        p = parse_file(fn)
        p.update({'year': year, 'month': month, 'set': setn, 'id': f'{year}-{month:02d}-{setn}'})
        papers.append(p)
    papers.sort(key=lambda x: (x['year'], x['month'], x['set']))

    bad = []
    CJK_RE = re.compile(r'[\u4e00-\u9fff]')
    for p in papers:
        for n, s in enumerate(p['sentences']):
            if not s['en'] or not s['cn']:
                bad.append((p['id'], n + 1, 'cn' if not s['cn'] else '', 'en' if not s['en'] else ''))
                continue
            if CJK_RE.search(s['en']):
                bad.append((p['id'], n + 1, 'en含中文', s['en'][:50]))
            if not s['cn'].rstrip('"』」”').endswith(('。', '！', '？', '；', ';', '.', '!', '?')):
                bad.append((p['id'], n + 1, 'cn未以句号结尾', s['cn'][-20:]))
            if len(s['cn']) < 6:
                bad.append((p['id'], n + 1, 'cn过短', s['cn']))
        if not p['theme']:
            bad.append((p['id'], 'theme'))
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(papers, f, ensure_ascii=False, indent=1)
    total = sum(len(p['sentences']) for p in papers)
    print(f'共 {len(papers)} 套, 总句数 {total}')
    print('异常:', bad if bad else '无，全部句对齐 ✓')
    nofix = sum(1 for p in papers for s in p['sentences'] if s['en'] == s['en_raw'] and '-' in s['en_raw'])
    for p in papers:
        print(p['id'], p['theme'][:18], '|', len(p['sentences']), '句 | 译法',
              len(p['global']['译法']), '| 衔接', len(p['bridges']), '| 主旨', 'Y' if p['global']['主旨'] else 'N')


if __name__ == '__main__':
    main()
