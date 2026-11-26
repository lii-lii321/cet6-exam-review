# -*- coding: utf-8 -*-
"""解析懒笔记写作真题 md → writing.json"""
import re, json, os, glob

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "extracted_writing")
OUT = os.path.join(BASE, "writing.json")

PAGE_MARK = re.compile(r'^<!-- Page \d+ -->\s*$')
CJK = r'\u4e00-\u9fff\u3000-\u303f\uff00-\uffef\u2018\u2019\u201c\u201d'
SPACE_IN_CJK = re.compile(rf'(?<=[{CJK}])\s+(?=[{CJK}])')
DECOR = re.compile(r'^[A-Z](?:\s+[A-Z])+\s*·')  # A N A L Y S I S · 装饰行


def clean_cn(t):
    t = re.sub(r'\\+([、，。；：？！])', r'\1', t)
    t = SPACE_IN_CJK.sub('', t)
    return t.strip()


def join_text(lines):
    out = ''
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        if out.endswith('-'):
            out += ln
        else:
            out = (out + ' ' + ln) if out else ln
    return re.sub(r'\s+', ' ', out).strip()


def is_title_line(s):
    """条目标题行：短、无句末标点、无英文；或 第N段/数字编号/维度名 开头"""
    if re.match(r'^第\s*\d+\s*段', s):
        return len(s) <= 30
    if re.match(r'^\d{1}[.、]\s*', s) and len(s) <= 25:
        return True
    if s.startswith(('核心任务', '读者', '中心立意', '要展开的要点', '典型低分写法', '反面示例')):
        return len(s) <= 25
    if ' · ' in s:
        head = s.split(' · ')[0]
        if len(head) <= 12 and not re.search(r'[。；，？！]', head):
            return 'FRAME'  # 句架条目（含英文名句）
    if len(s) <= 20 and not re.search(r'[。；，？！.!?]', s) and not re.search(r'[A-Za-z]', s):
        return True
    return False


def bracket_open(s):
    """未闭合括号数：>0 表示条目正文还没写完"""
    return s.count('（') + s.count('(') - s.count('）') - s.count(')')


def split_items(lines):
    """通用节解析：标题行开新条目，正文并入；括号未闭合的续行强制并入上一条"""
    items = []
    cur = None
    for ln in lines:
        s = ln.strip()
        if not s or s.startswith('懒笔记'):
            continue
        s = re.sub(r'^#{1,4}\s*', '', s).strip()
        if not s:
            continue
        # 以（开头的说明行 → 并入上一条（句架填空说明）
        if cur is not None and s.startswith('（'):
            cur['body'] = (cur['body'] + ' ' + s).strip()
            continue
        # 上一条正文括号未闭合 → 强制并入（修复句架说明/续行被误判为标题）
        if cur is not None and cur['body'] and bracket_open(cur['body']) > 0:
            cur['body'] = (cur['body'] + ' ' + s).strip()
            continue
        t = is_title_line(s)
        if t == 'FRAME':
            head, rest = s.split(' · ', 1)
            cur = {'title': clean_cn(head), 'body': rest, 'frame': True}
            items.append(cur)
            continue
        if t:
            cur = {'title': clean_cn(s), 'body': '', 'frame': False}
            items.append(cur)
            continue
        if cur is not None:
            cur['body'] = (cur['body'] + ' ' + s).strip()
        else:
            cur = {'title': '', 'body': s, 'frame': False}
            items.append(cur)
    for it in items:
        it['body'] = clean_cn(it['body']) if not re.match(r'^[A-Za-z]', it['body']) else re.sub(r'\s+', ' ', it['body'])
    return items


def parse_para_note(s):
    """【第 N 段】标题句。开头一字不差…… → 拆 title 与 body"""
    m = re.match(r'^【(第\s*\d+\s*段)】\s*(.*)$', s)
    seg, rest = m.group(1), m.group(2)
    mm = re.match(r'([^。！？]+。)\s*(.*)$', rest)
    if mm:
        return {'title': clean_cn(seg + ' ' + mm.group(1)).rstrip('。'), 'body': clean_cn(mm.group(2))}
    return {'title': clean_cn(seg + ' ' + rest), 'body': ''}


def split_en_sents(text):
    parts = [x.strip() for x in re.split(r'(?<=[.!?])\s+(?=[A-Z\u201c"])', text) if x.strip()]
    return parts


def split_cn_sents(text):
    parts = re.split(r'(?<=[。！？])', text)
    return [p.strip() for p in parts if p.strip()]


def parse_file(path):
    raw = open(path, encoding='utf-8').read()
    lines = [l for l in raw.splitlines() if not PAGE_MARK.match(l)]

    i = 0
    while i < len(lines) and lines[i].strip() == '':
        i += 1
    title_parts = []
    while i < len(lines):
        s = lines[i].strip()
        if s == '':
            i += 1; continue
        if re.match(r'^#{1,4}\s', s):
            title_parts.append(re.sub(r'^#{1,4}\s*', '', s).strip()); i += 1
        else:
            break

    directions, essay, trans, para_notes = [], [], [], []
    sec_analysis, sec_structure, sec_review = [], [], []
    word_count = None
    stage = 0  # 0=前言 1=范文 2=译文 3=逐段解析 4=analysis 5=structure 6=review 7=done

    for j in range(i, len(lines)):
        s = lines[j].strip()
        if s == '':
            continue
        if s.startswith('懒笔记'):
            continue
        if '全卷构成' in s or re.match(r'^Part\s+[IVX]+\s', s):
            break
        if s.startswith('# ') and ('写作题和范文' in s or '真题、范文' in s):
            continue
        if stage == 0:
            if s.startswith('Directions:'):
                directions.append(s[11:].strip())
                stage = 0.5
            elif DECOR.match(s):
                # 装饰行出现在前言——不可能，范文在 Directions 后
                continue
            elif s.startswith('【参考范文'):
                m = re.search(r'(\d+)\s*词', s)
                word_count = int(m.group(1)) if m else None
                stage = 1
            continue
        if stage == 0.5:
            if s.startswith('【参考范文'):
                m = re.search(r'(\d+)\s*词', s)
                word_count = int(m.group(1)) if m else None
                stage = 1
            else:
                directions.append(s)
            continue
        if stage == 1:
            if s.startswith('【参考译文】') or s.startswith('【参考译文'):
                stage = 2
            else:
                essay.append(s)
            continue
        if stage == 2:
            if re.match(r'^【第\s*\d+\s*段】', s):
                para_notes.append(parse_para_note(s))
                stage = 3
            elif DECOR.match(s) or s.startswith('# '):
                stage = 3  # 逐段解析缺失时直接进下一节
                continue
            else:
                trans.append(s)
            continue
        if stage == 3:
            if re.match(r'^【第\s*\d+\s*段】', s):
                para_notes.append(parse_para_note(s))
            elif s.startswith('# ') or DECOR.match(s):
                # 进入 REVIEW 前的大节标题行
                if '审' in s and '立' in s or 'ANALYSIS' in s.replace(' ', ''):
                    stage = 4
                elif '谋' in s and '逐' in s or 'STRUCTURE' in s.replace(' ', ''):
                    stage = 5
                elif '避' in s or 'REVIEW' in s.replace(' ', ''):
                    stage = 6
                continue
            else:
                if para_notes and not para_notes[-1]['body']:
                    para_notes[-1]['body'] = clean_cn(para_notes[-1]['body'] + ' ' + s) if para_notes[-1]['body'] else clean_cn(s)
                elif para_notes:
                    para_notes[-1]['body'] = clean_cn(para_notes[-1]['body'] + ' ' + s)
                else:
                    # 逐段解析缺失：忽略
                    pass
            continue
        if stage in (4, 5, 6):
            if s.startswith('# ') or DECOR.match(s):
                head = s.lstrip('# ').strip()
                # 大节切换：按关键词
                if ('谋' in head and '段' in head) or 'STRUCTURE' in head.replace(' ', ''):
                    stage = 5; continue
                if ('避' in head) or 'REVIEW' in head.replace(' ', ''):
                    stage = 6; continue
                if ('审' in head or '立意' in head) or 'ANALYSIS' in head.replace(' ', ''):
                    stage = 4; continue
                continue
            target = {4: sec_analysis, 5: sec_structure, 6: sec_review}[stage]
            target.append(s)
            continue

    directions_text = join_text(directions)
    essay_text = join_text(essay)
    trans_text = clean_cn(' '.join(trans))
    en_sents = split_en_sents(essay_text)
    cn_sents = split_cn_sents(trans_text)

    # 主题：优先取 begin with the sentence 的给定首句，否则取 Directions 前 60 字符
    mtheme = re.search(r'begins with the sentence\s*[“"]([^”"]{10,})[”"]', directions_text)
    if mtheme:
        theme = mtheme.group(1).strip()
    else:
        m2 = re.search(r'(?:essay|letter|proposal|speech)[^\.]{0,120}\.', directions_text)
        theme = (m2.group(0)[:80] if m2 else directions_text[:80]).strip()

    return {
        'theme': theme,
        'directions': directions_text,
        'word_count': word_count,
        'en_sents': en_sents,
        'cn_sents': cn_sents,
        'para_notes': para_notes,
        'analysis': split_items(sec_analysis),
        'structure': split_items(sec_structure),
        'review': split_items(sec_review),
    }


def main():
    papers = []
    pat = re.compile(r'英语六级(\d{4})年(\d{1,2})月第(\d)套写作')
    mis = []
    for fn in sorted(glob.glob(os.path.join(SRC, '*.md'))):
        m = pat.search(os.path.basename(fn))
        year, month, setn = int(m.group(1)), int(m.group(2)), int(m.group(3))
        p = parse_file(fn)
        p.update({'year': year, 'month': month, 'set': setn, 'id': f'{year}-{month:02d}-{setn}'})
        papers.append(p)
    papers.sort(key=lambda x: (x['year'], x['month'], x['set']))

    eq = 0
    for p in papers:
        ne, nc = len(p['en_sents']), len(p['cn_sents'])
        if ne == nc:
            eq += 1
        else:
            mis.append((p['id'], ne, nc))
        if not p['en_sents'] or not p['cn_sents'] or not p['directions']:
            mis.append((p['id'], 'EMPTY', ne, nc))
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(papers, f, ensure_ascii=False, indent=1)
    print(f'共 {len(papers)} 套 | 英中句数完全相等: {eq}/{len(papers)}')
    print('不等/异常:', mis)
    print('样例 2023-12-1:', len(papers[9]['en_sents']) if len(papers) > 9 else '?', '句 |',
          papers[9]['word_count'] if len(papers) > 9 else '?', '词 | 逐段', len(papers[9]['para_notes']),
          '| analysis', len(papers[9]['analysis']), '| structure', len(papers[9]['structure']),
          '| review', len(papers[9]['review']))


if __name__ == '__main__':
    main()
