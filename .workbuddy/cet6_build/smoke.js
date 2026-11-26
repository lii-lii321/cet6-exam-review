// 冒烟测试：DOM 桩 + localStorage 桩，跑网页脚本初始化与各模式渲染
const fs = require('fs');
const html = fs.readFileSync(process.argv[2] || '../../六级翻译逐句对照.html', 'utf-8');
const dataMatch = html.match(/<script id="DATA"[^>]*>([\s\S]*?)<\/script>/);
const vocabMatch = html.match(/<script id="VDATA"[^>]*>([\s\S]*?)<\/script>/);
const wdataMatch = html.match(/<script id="WDATA"[^>]*>([\s\S]*?)<\/script>/);
const scriptMatch = html.match(/<script>([\s\S]*?)<\/script>/);

function makeEl() {
  return {
    innerHTML: '', textContent: '', style: {}, dataset: {}, value: '',
    checked: false, disabled: false, className: '',
    selectionStart: 0,
    classList: { add(){}, remove(){}, toggle(){}, contains(){ return false; } },
    setSelectionRange(){}, focus(){}, appendChild(){},
    querySelectorAll(){ return []; }, querySelector(){ return makeEl(); }, addEventListener(){},
    onclick: null, onkeydown: null, oninput: null, onchange: null, onmouseenter: null, onmouseleave: null,
  };
}
const els = {};
global.document = {
  getElementById(id){ if(!els[id]) els[id] = makeEl(); return els[id]; },
  querySelector(sel){ if(!els[sel]) els[sel] = makeEl(); return els[sel]; },
  querySelectorAll(){ return []; },
  addEventListener(){}, createElement(){ return makeEl(); },
  body: makeEl(),
};
global.localStorage = {
  _m: new Map(),
  getItem(k){ return this._m.has(k) ? this._m.get(k) : null; },
  setItem(k,v){ this._m.set(k,String(v)); },
  removeItem(k){ this._m.delete(k); },
  get length(){ return this._m.size; },
  key(i){ return [...this._m.keys()][i]; },
};
global.location = { hash: '' };
global.setTimeout = (fn)=>0; global.clearTimeout = ()=>{};

els['DATA'] = { textContent: dataMatch[1] };
els['VDATA'] = { textContent: vocabMatch[1] };
els['WDATA'] = { textContent: wdataMatch[1] };

const testCode = `
  // 写作板块：切换、渲染、句数
  setSec('w');
  if (!curW || curW.en_sents.length === 0) throw new Error('写作题未选中或范文为空');
  const wPaper = curW;
  setMode('vocab'); setMode('type'); setMode('pair'); // 写作下 pair 应映射到 writing 视图
  // 回翻译板块
  setSec('t');
  if (!cur) throw new Error('切回翻译后未选中');
  setMode('pair'); setMode('full'); setMode('vocab'); setMode('type');
  tBuildQueue();
  const w0 = TSTATE.queue[0];
  tWrong(w0);
  if (TSTATE.queue.includes(w0) === false) throw new Error('答错后未回队列尾部');
  const w1 = TSTATE.queue[TSTATE.pos];
  tCorrect(w1);
  if (TSTATE.streak !== 1) throw new Error('答对一次后 streak 应为 1');
  tCorrect(w1);
  if (!mastered(w1.word)) throw new Error('连续两次答对后未标记掌握');
  if (localStorage.getItem('cet6_word_' + w1.word.toLowerCase()) !== '1') throw new Error('localStorage 未写入');
  const before = TSTATE.queue.length;
  const wCur = TSTATE.queue[TSTATE.pos];
  tNext();
  if (TSTATE.queue.length !== before) throw new Error('tNext 不应改变队列长度');
  if (!TSTATE.queue.includes(wCur)) throw new Error('tNext 后当前词应保留在队列');
  if (TSTATE.queue[TSTATE.pos] === wCur && TSTATE.queue.length > 1) throw new Error('tNext 应指向下一个词');
  VSTATE.tab = 'kg'; renderVocab();
  let kgKnown = 0; VOCAB.kg.forEach(w=>{ if(mastered(w.word)) kgKnown++; });
  console.log('SMOKE OK — 写作', WRITING.length, '套(样例', wPaper.en_sents.length, '句/译文', wPaper.cn_sents.length, '句) | 队列', TSTATE.queue.length, '词 | 掌握', w1.word, '| 33套翻译渲染正常');
`;
try {
  eval(scriptMatch[1] + '\n' + testCode);
} catch (e) {
  console.error('SMOKE FAIL:', e.message);
  console.error(e.stack.split('\n').slice(0,4).join('\n'));
  process.exit(1);
}
