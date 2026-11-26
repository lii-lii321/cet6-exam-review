# 六级真题精练（CET-6 Exam Review）

一个**单文件、离线可用**的英语六级备考网页：把历年真题（汉译英段落翻译、写作）拆成一句对一句 / 一段对一段的对照视图，配上解析、词汇表和打字背诵。双击打开 `六级翻译逐句对照.html` 即可使用，无需联网、无需安装。

> 2 MB 不到的 HTML 里装着：翻译 33 套 · 写作 33 套 · 词汇 2097 词。

## 功能

### 翻译（33 套，2022.6 – 2026.6）
- **逐句对照**：中文原句 ↔ 英文译文左右对齐，点击展开解析（主干 / 降级 / 语法点 / 定稿译文）
- **整篇连读**：整段中文对整篇译文，悬停任意一句两侧同时高亮
- **遮罩自测**：遮英文 / 遮中文，点对应半区单独揭示

### 写作（33 套，2022.6 – 2026.6）
- **范文 · 译文逐句对照**（32/33 套句数完全 1:1）
- 逐段拆解、审题立意、谋篇句架（填空式功能句架）、自检避坑

### 词汇（2097 词）
- **三表合一**：超纲词 263 + CEFR C1–C2 高频词 204 + 考纲高频词 1834，去重合并
- 词表浏览：搜索 / CEFR 等级 / 已掌握过滤、句频排序、点击标记掌握
- **打字背诵**：只显示中文释义，打出单词提交；**连续两次无提示打对才算掌握**；打错自动排队尾，空回车跳下一个
- 掌握状态与词表浏览双向同步，全部存 localStorage

### 通用
- 范文 / 译文中自动高亮超纲词（橙点线）与 C1–C2 高频词（红线），悬停显示释义
- 侧栏可收起（☰）、←/→ 切套、三档字号、每套「已掌握」进度

## 仓库结构

```
六级翻译逐句对照.html      # 成品：单文件网页，数据已内嵌，直接打开
.workbuddy/cet6_build/    # 全部构建产物（可复现）
├── template.html         #   网页模板（数据占位符）
├── build.py              #   构建：注入 JSON → 成品 HTML
├── parse_cet6.py         #   翻译真题解析 → data.json（33 套 180 句）
├── parse_vocab.py        #   词表解析 + 合并去重 → vocab.json
├── parse_writing.py      #   写作真题解析 → writing.json
├── smoke.js              #   冒烟测试（Node DOM 桩）
├── extracted/            #   翻译 PDF 提取的中间 markdown
├── extracted_writing/    #   写作 PDF 提取的中间 markdown
└── vocab/                #   词表 PDF 提取的中间 markdown
```

PDF 原件不入库（见 `.gitignore`），如需复现提取流程请自备同源 PDF。

## 重新构建

```bash
# 1. 修改 PDF 后重新提取（示例：workbuddy-pdf CLI）
# 2. 解析
python .workbuddy/cet6_build/parse_cet6.py
python .workbuddy/cet6_build/parse_vocab.py
python .workbuddy/cet6_build/parse_writing.py
# 3. 构建成品
python .workbuddy/cet6_build/build.py
# 4. 测试
node .workbuddy/cet6_build/smoke.js
```

## 免责声明

本项目仅供个人学习备考使用。真题为公开考试内容，题目解析整理自[懒笔记](https://english-exam.lazynote.cn/)（懒笔记基于历年真题译审整理）。如有侵权请联系仓库所有者删除。请勿将本项目内容用于任何商业用途。
