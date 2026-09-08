# book-deep-digest · 全书内容自动总结

输入一本书名，自动生成可反复翻阅的**精读回顾材料**：逐章提炼金句（附释义与位置）+ 章节总结，再汇总全书主线逻辑与思想框架，最后给出重点回顾提示与自测题。成品可直接渲染成单文件 HTML 温习页（搜索 / 折叠 / 答题遮罩 / 纸墨双主题）。

> 本仓库根目录即技能本身（`SKILL.md` + `scripts/` + `references/`），同时也是 GitHub Pages 站点（见下方 `pages/`）。

---

## 1. 能做什么

- **章节级**：每章自动提炼若干条核心金句（原文优先，附释义 + 位置 + 为什么重要）+ 简洁准确的章节总结。
- **全书级**：在所有章节总结的基础上归纳「全文总结」，梳理主线逻辑、观点关联与思想框架。
- **温习页**：把 Markdown 渲染成单文件 HTML——侧边目录、全文搜索、章节折叠、自测题答案遮罩、进度条、一键打印存 PDF、纸 / 墨双主题。

## 2. 安装到 WorkBuddy

两种方式：

**方式 A · 直接导入 `.skill` 包**（推荐，零依赖）

下载 `dist/book-deep-digest.skill`，在 WorkBuddy 技能面板「导入」即可。

**方式 B · 克隆源码**

```bash
git clone <本仓库地址> ~/.workbuddy/skills/book-deep-digest
```

克隆后目录应直接为 `~/.workbuddy/skills/book-deep-digest/{SKILL.md,scripts,references}`（仓库根即技能根）。

## 3. 使用

对话里直接说书名即可，无需其他参数：

- "帮我总结《聪明的投资者》"
- "《XXX》读完了，做个精读回顾"

可选参数（都有默认值，缺了不会追问）：书名、原文文件路径（PDF/EPUB/TXT/MD/DOCX，质量天差地别）、作者、详略、输出目录。

**执行流程**：消歧 + 拿目录 → 取原文（有文件先切章）→ 书籍信息 + 结构鸟瞰（长书此处暂停确认）→ 分批改章节精读 → 全书总结（必须基于已写好的各章总结归纳）→ 落盘 Markdown + 生成 HTML。

## 4. 命令行单独生成温习页

若已有一份符合输出契约的 Markdown（见 `references/output-template.md`），可直接渲染：

```bash
python scripts/build_review_page.py 你的书-精读回顾.md --out 你的书-精读回顾.html
```

本地电子书自动切章（EPUB/DOCX/TXT/MD 零依赖；PDF 需 `pip install pypdf`）：

```bash
python scripts/extract_book_text.py 你的书.pdf --dump-dir chapters
```

## 5. 在线预览（GitHub Pages）

`pages/` 目录已开启 GitHub Pages，收录已生成的精读回顾网页，例如：

- 《聪明的投资者》精读回顾
- 《孙子兵法》示例

入口：`pages/index.html`（仓库开启 Pages 后即为站点首页）。

## 6. 目录结构

```
.
├── SKILL.md                 # 技能主文件（触发词 / 步骤 / 输出契约）
├── scripts/
│   ├── build_review_page.py # Markdown → 单文件 HTML 温习页
│   └── extract_book_text.py # 本地电子书切章
├── references/              # 输出模板 / 质量规则 / 来源策略 / 示例
├── pages/                   # GitHub Pages 站点（精读回顾网页）
│   ├── index.html
│   └── *.html
└── dist/
    └── book-deep-digest.skill  # 可一键导入的打包产物
```

## 7. 设计说明

温习页为「编辑书卷风」：暖纸底 + 墨色正文 + 单一朱砂强调色，标题 / 金句用衬线（Spectral + Noto Serif SC），正文用系统无衬线以保证中文可读性。金句分三层排版（原句 / 中译 / 出处），兹威格点评自动以虚线边框与格雷厄姆原句区分。
