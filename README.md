# book-deep-digest · 全书内容自动总结

输入一本书名，自动生成可反复翻阅的**精读回顾材料**：逐章提炼金句（附释义与位置）+ 章节总结，再汇总全书主线逻辑与思想框架，最后给出重点回顾提示与自测题。成品可直接渲染成单文件 HTML 温习页（搜索 / 折叠 / 答题遮罩 / 纸墨双主题）。

> 本仓库根目录即技能本身（`SKILL.md` + `scripts/` + `references/`），同时也是 GitHub Pages 站点（见下方 `docs/`）。

---

## 1. 能做什么

- **章节级**：每章自动提炼若干条核心金句（原文优先，附释义 + 位置 + 为什么重要）+ 简洁准确的章节总结。
- **全书级**：在所有章节总结的基础上归纳「全文总结」，梳理主线逻辑、观点关联与思想框架。
- **温习页**：把 Markdown 渲染成单文件 HTML——侧边目录、全文搜索、章节折叠、自测题答案遮罩、进度条、一键打印存 PDF、纸 / 墨双主题。

## 2. 安装方式

**方式一 · 一句话让 AI 助手帮你装**（推荐）

把下面任一段话直接发给 AI 助手，对方会自动完成下载 + 安装 + 验证。复制即可，无需改动：

- **完整仓库版**（让助手把仓库整个 clone 到技能目录）

  > 请帮我安装一个技能：从 https://github.com/Jesper26/book-deep-digest 下载仓库到本地，把 book-deep-digest 目录（含 SKILL.md、scripts/、references/）安装到你的技能目录（如 `~/.workbuddy/skills/book-deep-digest`），安装后告诉我如何使用。

- **一键包版**（让助手只下载打包好的 `.skill` 文件，体积更小、零依赖）

  > 请下载并安装这个技能包：https://github.com/Jesper26/book-deep-digest/raw/main/dist/book-deep-digest.skill

**方式二 · 自己手动下载**

- **导入 `.skill` 包**：从仓库 [dist/book-deep-digest.skill](https://github.com/Jesper26/book-deep-digest/raw/main/dist/book-deep-digest.skill) 下载单文件，在 AI 助手的技能面板「导入技能 / Install Skill」上传即可。
- **克隆源码**：

  ```bash
  git clone https://github.com/Jesper26/book-deep-digest.git <你的技能目录>/book-deep-digest
  ```

  克隆后目录应直接为 `<你的技能目录>/book-deep-digest/{SKILL.md, scripts, references}`（仓库根即技能根）。

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

`docs/` 目录已开启 GitHub Pages（源：main 分支 / `docs`），收录已生成的精读回顾网页，例如：

- 《聪明的投资者》精读回顾（示例）
- 《你当像鸟飞往你的山》精读回顾
- 《我胆小如鼠》精读回顾

入口：`docs/index.html`（仓库开启 Pages 后即为站点首页 `https://<用户名>.github.io/book-deep-digest/`）。

## 6. 目录结构

```
.
├── SKILL.md                 # 技能主文件（触发词 / 步骤 / 输出契约）
├── scripts/
│   ├── build_review_page.py # Markdown → 单文件 HTML 温习页
│   └── extract_book_text.py # 本地电子书切章
├── references/              # 输出模板 / 质量规则 / 来源策略 / 示例
├── docs/                    # GitHub Pages 站点（源分支 main /docs，精读回顾网页）
│   ├── index.html
│   └── *.html
└── dist/
    └── book-deep-digest.skill  # 可一键导入的打包产物
```

## 7. 设计说明

温习页为「编辑书卷风」：暖纸底 + 墨色正文 + 单一朱砂强调色，标题 / 金句用衬线（Spectral + Noto Serif SC），正文用系统无衬线以保证中文可读性。金句分三层排版（原句 / 中译 / 出处），兹威格点评自动以虚线边框与格雷厄姆原句区分。

## 8. 一键部署到 GitHub Pages

仓库根提供了 `deploy.sh`，一键完成：建仓库 → 推送 main → 开启 Pages（main 分支 /docs）。

```bash
./deploy.sh <github用户名> <PAT>
# PAT 需具备 repo 权限（classic token 勾 repo；fine-grained 勾 Contents + Pages 写）
```

不带参数运行会打印用法。执行后站点地址为 `https://<用户名>.github.io/book-deep-digest/`。

## 9. 开源许可

本项目以 [CC BY-NC-ND 4.0](LICENSE)（署名-非商业性-禁止演绎）永久开源：可自由**下载、原样使用、原样分享**；**不允许修改源码或基于其创作衍生作品**，也**不允许任何商业用途**，使用时须注明原作者与来源。详见 [LICENSE](LICENSE)。

