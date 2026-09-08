# 内容来源策略与分批执行

## 三档来源，按优先级取

| 档位 | 条件 | 做法 | 置信度 |
| --- | --- | --- | --- |
| **A. 原文在手** | 用户给了 PDF/EPUB/TXT/MD/DOCX | 调 `scripts/extract_book_text.py` 切章，按原文逐章提炼 | 高 |
| **B. 联网检索** | 只有书名，且能查到目录/原文片段/权威书评 | 先查目录与章节结构，再逐章检索原文摘录 | 中 |
| **C. 模型知识** | 查不到、或用户明确要快速版 | 凭知识生成，但金句只取高置信度名句，其余转述并标注 | 低 |

**必须**在输出第六节写明实际用的是哪一档，以及金句置信度。混用时按章节分别标注。

## A 档：本地原文处理

```bash
python scripts/extract_book_text.py <file> --dump-dir ./chapters --min-chapter-words 300
python scripts/extract_book_text.py <file> --no-text          # 只看章节清单，省 token
python scripts/extract_book_text.py <file> --preview 800      # 抽查第 1 章切得对不对
python scripts/extract_book_text.py <file> --toc-file toc.txt # 用目录校准切章
```

- 先跑 `--no-text` 看章节清单是否与真实目录一致；不一致就调整 `--min-chapter-words` 或提供 `--toc-file`。
- 书很长时按批读：每次读 3–5 章的 `chapters/ch_XX.txt`，逐批产出该批的金句+总结，最后再合并。
- PDF 无文字层（扫描件）时脚本会退出，需先 OCR 或改走 B/C 档。
- PDF 需 `pypdf`（或 pdfplumber / PyMuPDF）：`<python> -m pip install pypdf`。EPUB/DOCX/TXT/MD 零依赖。

## B 档：检索要点

1. 先查「书名 + 目录 / 章节 / table of contents」，拿到准确章节划分——**没有准确目录就不要假装有**。
2. 再查「书名 + 金句 / 摘录 / quotes」逐章找原句；优先出版社官方、读书平台原文摘录、作者本人文章。
3. 同一句在两个以上独立来源一致时才记为高置信度金句。

## 长书分批策略（>15 章，或原文 > 20 万字）

1. 第 1 步：只产出"书籍基本信息 + 全书结构鸟瞰"，先让用户确认章节划分对不对。
2. 第 2 步：按批（3–5 章）产出"章节精读"，每批结束即写入 Markdown 文件，避免上下文丢失。
3. 第 3 步：全部章节完成后，再写"全书总结"和"重点回顾提示"——**全书总结必须基于已写好的各章总结，而不是重新凭印象写**。
4. 第 4 步：跑 `build_review_page.py` 生成温习页。

## 输入不足时的处理

- 书名有歧义（同名书多）：先列出 2–3 个候选让用户确认，不要自作主张。
- 用户要"精简版"：仍保留六节结构，但每章金句降到 1–2 条、章节总结压缩到 100 字内、自测题降到 5 道。
- 用户指定了重点（如"只看第 3、5 章"）：其余章节在鸟瞰表中保留一行，章节精读只展开指定章节，并在第六节注明覆盖不完整。
