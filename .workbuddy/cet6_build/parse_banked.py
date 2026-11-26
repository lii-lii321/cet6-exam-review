# -*- coding: utf-8 -*-
"""解析懒笔记选词填空 md → banked.json"""
import re, json, os, glob

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "extracted_banked")
OUT = os.path.join(BASE, "banked.json")
VOCAB = json.load(open(os.path.join(BASE, "vocab.json"), encoding="utf-8"))

PAGE_MARK = re.compile(r'^<!-- Page \d+ -->\s*$')
DECOR = re.compile(r'^[A-Z](?:\s+[A-Z-])+\s*·')  # W O R D B A N K · 装饰行
CJK_START = re.compile(r'^[^A-Za-z0-9]')  # 非 ASCII 开头即视为中文行（含全角引号）
TAIL_CN = re.compile(r'(?<![A-Za-z0-9])[\u4e00-\u9fff][\u4e00-\u9fff。；：，、？！\u201c\u201d（）\s]{7,}\s*$')
BLANK_MARK = re.compile(r'\\*_{2,4}\\*\((\d{2})\)\\*_{2,4}')
WBLANK = re.compile(r'^([A-O])\s*\)\s*([A-Za-z-]+)\s+(形容词|名词|动词|副词.*)$')
WB_ITEM = re.compile(r'([A-O])\s*\)\s*([A-Za-z-]+)\s+((?:形容词|名词|动词|副词)(?:\s+(?:形容词|名词|动词|副词))*)')
NUM_Q = re.compile(r'^(\d{2})\.\s*(.*)$')
RIVAL = re.compile(r'^([A-O])\s*\)\s*(\S+)\s*(.*)$')
HFW_HEAD = re.compile(r'^([A-Za-z-]+)\s+(A1|A2|B1|B2|C1|C2)\s*$')
HFW_CNT = re.compile(r'本篇\s*(\d+)\s*次\s*·\s*真题\s*(\d+)\s*句')
FOOTER = ('懒笔记资料站', '懒笔记刷题站')


def clean(t):
    t = re.sub(r'\\+([、，。；：？！])', r'\1', t)
    t = re.sub(r'\s+([\u4e00-\u9fff])', r'\1', t)
    t = re.sub(r'([\u4e00-\u9fff。；：，、（）『』\u201c\u201d])\s+(?=[\u4e00-\u9fff。；：，、（）『』\u201c\u201d])', r'\1', t)
    return t.strip()


def norm_blank(s):
    s = s.replace('\\', '')
    s = re.sub(r'_{2,}\((\d{2})\)', r'‹\1›', s)
    s = re.sub(r'_{3,}', '＿＿', s)
    return s


TAG_SPLIT = re.compile(r'(【(?:答案|词性槽|依据|竞争词|易错)】)')
BANK_ROW = re.compile(r'^[A-O]\s*\)\s*[A-Za-z-]+')


def parse_file(path):
    raw = open(path, encoding='utf-8').read()
    lines = [l for l in raw.splitlines() if not PAGE_MARK.match(l)]

    i = 0
    while i < len(lines) and lines[i].strip() == '':
        i += 1

    directions, passage, analysis, wordbank = [], [], [], []
    gist_lines, distractors, hfw = [], [], []
    stage = 'head'  # head→dir→passage→analysis→wordbank→gist→distractor→sight→hfw→done

    cur_q = None          # 逐空解析当前
    cur_rival = None      # 当前竞争词
    cur_sub = None        # 当前子块标签: slot/basis/trap
    cur_wb = None         # 当前词库条目
    cur_dis = None        # 当前干扰词条目
    cur_en, cur_cn = [], []
    cur_hfw = None

    def flush_seg():
        nonlocal cur_en, cur_cn
        if cur_en:
            passage.append({'lang': 'en', 'text': norm_blank(' '.join(x.strip() for x in cur_en if x.strip()))})
            cur_en = []
        if cur_cn:
            passage.append({'lang': 'cn', 'text': clean(' '.join(cur_cn))})
            cur_cn = []

    def close_q():
        nonlocal cur_q, cur_rival, cur_sub
        if cur_q:
            analysis.append(cur_q)
        cur_q, cur_rival, cur_sub = None, None, None

    for j in range(i, len(lines)):
        s = lines[j].strip()
        if not s or s.startswith(FOOTER):
            continue
        if '全卷构成' in s or re.match(r'^Part\s+[IVX]+\s', s):
            flush_seg(); close_q(); break
        # 各节装饰/标题行（hfw 区的 ### 行是词条，不切节）
        if (DECOR.match(s) or re.match(r'^#{1,4}\s', s)) and stage != 'hfw':
            head = s.lstrip('# ').strip()
            head_clean = re.sub(r'\s+', '', head)
            flush_seg(); close_q()
            cur_wb = cur_dis = cur_hfw = None
            if '词库分类' in head or 'WORDBANK' in head_clean:
                stage = 'wordbank'
            elif head_clean.startswith('全文主旨'):
                stage = 'gist'
            elif '干扰词' in head or 'DISTRACTORS' in head_clean:
                stage = 'distractor'
            elif '句子精讲' in head or 'SENTENCE' in head_clean:
                stage = 'sight'
            elif '高频词' in head or 'HIGH' in head_clean:
                stage = 'hfw'
            elif '选词填空题和解析' in head_clean or 'BLANKS' in head_clean:
                stage = 'head'
            continue
        if s.startswith('Directions:'):
            flush_seg(); close_q()
            stage = 'dir'
            directions.append(s[11:].strip())
            continue
        if stage == 'dir':
            # Directions 固定以 "...more than once." 结尾，之后的行全部是正文
            if 'more than once' in s:
                flush_seg(); stage = 'passage'
                cut = s.find('more than once')
                head_part = s[:cut + 14].strip()
                if head_part: directions.append(head_part)
                rest = s[cut + 14:].strip().lstrip('.。').strip()
                if rest:
                    mt = TAIL_CN.search(rest)
                    if mt:
                        en_part = rest[:mt.start()].strip(); cn_part = rest[mt.start():].strip()
                        if en_part: cur_en.append(en_part)
                        if cn_part: cur_cn.append(cn_part)
                    else:
                        cur_en.append(rest)
                continue
            directions.append(s)
            continue
        if stage == 'passage':
            if re.match(r'^\d{2}(\s+\d{2})*$', s):
                continue  # 页脚残留的空位标号行（26 27 28）
            # 词库速览行（每行一个词条，或一行多词条）→ 丢弃
            if re.match(r'^[A-O]\s*\)\s*[A-Za-z-]{2,}(\s+\d{1,2})?\s*$', s):
                continue
            if re.match(r'^[A-O]\s*\)\s*[A-Za-z-]+', s) and len(re.findall(r'[A-O]\s*\)\s*[A-Za-z-]+', s)) >= 2:
                continue
            if NUM_Q.match(s) and not CJK_START.match(s):
                flush_seg(); stage = 'analysis'
                mq = NUM_Q.match(s)
                cur_q = {'num': int(mq.group(1)), 'sentence': norm_blank(mq.group(2)),
                         'answer': None, 'slot': '', 'basis': '', 'rivals': [], 'trap': ''}
                cur_rival = None; cur_sub = None
                continue
            if CJK_START.match(s):
                if cur_en:
                    flush_seg()
                cur_cn.append(s)
            else:
                # 英文行行尾可能粘着中文翻译 → 切出
                mt = TAIL_CN.search(s)
                if mt:
                    en_part = s[:mt.start()].strip()
                    cn_part = s[mt.start():].strip()
                    if en_part:
                        cur_en.append(en_part)
                    flush_seg()
                    cur_cn.append(cn_part)
                    continue
                if cur_cn:
                    flush_seg()
                cur_en.append(s)
            continue
        if stage == 'analysis':
            # 一行内可能混排多个【标签】（如句子第二行 + 【答案】），先切分
            chunks = TAG_SPLIT.split(s)
            pieces = [(None, chunks[0])] + [(chunks[i], chunks[i+1]) for i in range(1, len(chunks)-1, 2)]
            if len(chunks) % 2 == 0 and chunks[-1] == '' and len(pieces) > 1:
                pieces = pieces[:-1] if pieces[-1][1] == '' else pieces
            if len(chunks) >= 3 and chunks[-1] == '':
                pieces = [(None, chunks[0])] + [(chunks[i], chunks[i+1]) for i in range(1, len(chunks)-1, 2)]
                if pieces and pieces[-1][1] == '' and len(chunks) > 2 and chunks[-1] == '':
                    pieces = pieces[:-1] if not pieces[-1][1] else pieces
            for tag, text in pieces:
                text = text.strip()
                if tag is None and text:
                    mq = NUM_Q.match(text)
                    if mq:  # 任何位置的题目编号行都开新题（含被英文行尾拼进来的情况）
                        flush_seg(); close_q()
                        cur_q = {'num': int(mq.group(1)), 'sentence': norm_blank(mq.group(2)),
                                 'answer': None, 'slot': '', 'basis': '', 'rivals': [], 'trap': ''}
                        cur_rival = None; cur_sub = None
                        continue
                    mr = RIVAL.match(text)
                    if mr and cur_sub == 'rival' and cur_q is not None:
                        cur_rival = {'word': mr.group(2), 'reason': norm_blank(mr.group(3))}
                        cur_q['rivals'].append(cur_rival)
                        continue
                    if cur_q is None:
                        continue
                    if cur_sub == 'slot':
                        cur_q['slot'] = norm_blank(cur_q['slot'] + ' ' + text)
                    elif cur_sub == 'basis':
                        cur_q['basis'] = norm_blank(cur_q['basis'] + ' ' + text)
                    elif cur_sub == 'trap':
                        cur_q['trap'] = norm_blank(cur_q['trap'] + ' ' + text)
                    elif cur_sub == 'rival' and cur_rival is not None:
                        cur_rival['reason'] = norm_blank(cur_rival['reason'] + ' ' + text)
                    else:
                        cur_q['sentence'] = norm_blank(cur_q['sentence'] + ' ' + text)
                    continue
                # 有标签的部分
                if tag == '【答案】':
                    cur_rival = None; cur_sub = 'answer'
                    m = re.match(r'([A-O])\s*\)\s*(\S+)\s*(.+)$', text.strip())
                    if m and cur_q is not None:
                        cur_q['answer'] = {'letter': m.group(1), 'word': m.group(2), 'pos': clean(m.group(3))}
                    continue
                if tag == '【词性槽】':
                    cur_sub = 'slot'; cur_rival = None
                    if cur_q is not None: cur_q['slot'] = norm_blank(text)
                    continue
                if tag == '【依据】':
                    cur_sub = 'basis'; cur_rival = None
                    if cur_q is not None: cur_q['basis'] = norm_blank(text)
                    continue
                if tag == '【竞争词】':
                    cur_sub = 'rival'
                    mr = RIVAL.match(text.strip())
                    if mr and cur_q is not None:
                        cur_rival = {'word': mr.group(2), 'reason': norm_blank(mr.group(3))}
                        cur_q['rivals'].append(cur_rival)
                    continue
                if tag == '【易错】':
                    cur_sub = 'trap'; cur_rival = None
                    if cur_q is not None: cur_q['trap'] = norm_blank(text)
                    continue
            continue
        if stage == 'wordbank':
            if s.startswith('全文主旨'):
                flush_seg(); close_q(); cur_wb = None
                stage = 'gist'; continue
            # 双栏合并行处理：一行里可能同时含「状态标记」与「新词条」甚至多个标记
            pos_ = 0
            while pos_ < len(s):
                m_used = re.search(r'用于第\s*(\d+)\s*空', s[pos_:])
                m_no = re.search(r'干扰词\s*·?\s*未选用', s[pos_:])
                m_it = WB_ITEM.search(s, pos_)
                # 计算三个标记的位置（相对 pos_）
                cands = []
                if m_used: cands.append(('used', m_used.start(), m_used))
                if m_no: cands.append(('no', m_no.start(), m_no))
                if m_it: cands.append(('item', m_it.start(), m_it))
                if not cands:
                    # 剩余全是释义文本
                    txt = clean(s[pos_:])
                    if txt and cur_wb is not None:
                        cur_wb['gloss'] = (cur_wb['gloss'] + '；' + txt) if cur_wb['gloss'] else txt
                    break
                cands.sort(key=lambda x: x[1])
                kind, off, mm = cands[0]
                between = clean(s[pos_:pos_ + off])
                if between and cur_wb is not None and not cur_wb['gloss']:
                    cur_wb['gloss'] = between
                elif between and cur_wb is not None:
                    cur_wb['gloss'] = (cur_wb['gloss'] + '；' + between) if between not in cur_wb['gloss'] else cur_wb['gloss']
                if kind == 'used':
                    if cur_wb: cur_wb['used'] = int(mm.group(1))
                    pos_ = pos_ + mm.end()
                elif kind == 'no':
                    if cur_wb: cur_wb['used'] = None
                    pos_ = pos_ + mm.end()
                else:
                    cur_wb = {'letter': mm.group(1), 'word': mm.group(2),
                              'pos': mm.group(3).split(), 'gloss': '', 'used': None}
                    wordbank.append(cur_wb)
                    pos_ = pos_ + mm.end()
            continue
        if stage == 'gist':
            gist_lines.append(s)
            continue
        if stage == 'distractor':
            md = RIVAL.match(s)
            if md and len(md.group(2)) <= 20:
                cur_dis = {'word': md.group(2), 'title': clean(md.group(3)), 'body': ''}
                distractors.append(cur_dis)
            elif cur_dis is not None:
                cur_dis['body'] = clean(cur_dis['body'] + ' ' + s)
            continue
        if stage == 'sight':
            continue  # 句子精讲内容较薄，跳过
        if stage == 'hfw':
            s2 = re.sub(r'^#{1,4}\s*', '', s)
            mh = HFW_HEAD.match(s2)
            if mh:
                if cur_hfw:
                    hfw.append(cur_hfw)
                cur_hfw = {'word': mh.group(1), 'cefr': mh.group(2), 'pos': '', 'gloss': '', 'here': None, 'freq': None}
                continue
            if cur_hfw is None:
                continue
            mh2 = re.match(r'^((?:名词|动词|形容词|副词|det|adv|adj|n|v)\.?)\s*(.*)$', s2)
            if mh2 and not cur_hfw['pos']:
                cur_hfw['pos'] = mh2.group(1); cur_hfw['gloss'] = clean(mh2.group(2))
                continue
            mc = HFW_CNT.search(s2)
            if mc:
                cur_hfw['here'] = int(mc.group(1)); cur_hfw['freq'] = int(mc.group(2))
                hfw.append(cur_hfw); cur_hfw = None
                continue
            if not cur_hfw['gloss']:
                cur_hfw['gloss'] = clean(s2)
            continue

    flush_seg(); close_q()
    directions_text = clean(' '.join(directions))

    # 段落配对清理：英中逐对配对（丢弃提取残留的多余段）
    en_list = [x['text'] for x in passage if x['lang'] == 'en']
    cn_list = [x['text'] for x in passage if x['lang'] == 'cn']
    n_pairs = min(len(en_list), len(cn_list))
    passage = [{'lang': 'en', 'text': en_list[i]} for i in range(n_pairs)] + \
              [{'lang': 'cn', 'text': cn_list[i]} for i in range(n_pairs)]

    # 词库 gloss 截断跨栏污染（"；X ) xxx" 起）
    for w in wordbank:
        if w['gloss']:
            w['gloss'] = re.split(r'；\s*[A-O]\s*\)', w['gloss'])[0].strip('；; ')

    return {'directions': directions_text, 'passage': passage, 'analysis': analysis,
            'wordbank': wordbank, 'gist': clean(' '.join(gist_lines)),
            'distractors': distractors, 'hfw': hfw}


def main():
    papers = []
    pat = re.compile(r'英语六级(\d{4})年(\d{1,2})月第(\d)套完形填空')
    for fn in sorted(glob.glob(os.path.join(SRC, '*.md'))):
        m = pat.search(os.path.basename(fn))
        year, month, setn = int(m.group(1)), int(m.group(2)), int(m.group(3))
        p = parse_file(fn)
        p.update({'year': year, 'month': month, 'set': setn, 'id': f'{year}-{month:02d}-{setn}'})
        papers.append(p)
    papers.sort(key=lambda x: (x['year'], x['month'], x['set']))

    # 词池：33 套 15 词去重，从 vocab.json 补 cefr
    pool = {}
    for p in papers:
        for w in p['wordbank']:
            k = w['word'].lower()
            e = pool.setdefault(k, {'word': w['word'], 'pos': [], 'gloss': w['gloss'], 'sets': 0})
            e['sets'] += 1
            for ps in w['pos']:
                if ps not in e['pos']:
                    e['pos'].append(ps)
    vmap = {}
    for lst in (VOCAB['merged'], VOCAB['over'], VOCAB['c12'], VOCAB['kg']):
        for w in lst:
            vmap[w['word'].lower()] = w
    pool_list = []
    for k, e in pool.items():
        v = vmap.get(k)
        gloss = v['gloss'] if v and v.get('gloss') else e['gloss']
        pool_list.append({'word': e['word'], 'pos': e['pos'], 'gloss': gloss,
                          'cefr': v['cefr'] if v else '', 'sets': e['sets']})
    pool_list.sort(key=lambda x: -x['sets'])
    # 词池只存顶层一份（每套不重复复制，避免 json 膨胀）

    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump({'papers': papers, 'wordPool': pool_list}, f, ensure_ascii=False, indent=1)

    print(f'共 {len(papers)} 套')
    bad = []
    for p in papers:
        if len(p['wordbank']) != 15: bad.append((p['id'], '词库', len(p['wordbank'])))
        if len(p['analysis']) != 10: bad.append((p['id'], '解析', len(p['analysis'])))
        en = sum(1 for s in p['passage'] if s['lang'] == 'en')
        cn = sum(1 for s in p['passage'] if s['lang'] == 'cn')
        if en != cn: bad.append((p['id'], '段落', f'en{en}/cn{cn}'))
        noans = [q['num'] for q in p['analysis'] if not q['answer']]
        if noans: bad.append((p['id'], '无答案', noans))
    print('异常:', bad if bad else '无 ✓')
    print('词池去重后:', len(pool_list))
    # 答案词性分布统计（偷分技巧素材）
    from collections import Counter
    c = Counter()
    for p in papers:
        for q in p['analysis']:
            if q['answer']:
                c[q['answer']['pos'][:3]] += 1
    print('答案词性分布:', dict(c))


if __name__ == '__main__':
    main()
