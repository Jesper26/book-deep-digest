#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从本地电子书提取正文并按章节切分。

用途：当用户手上有 PDF/EPUB/TXT/MD/DOCX 原文时，先把书切成"章节文本块"，
再交给模型逐章提炼金句与总结 —— 避免凭记忆编造内容。

用法：
  python extract_book_text.py <file> [--out chapters.json] [--dump-dir DIR]
                              [--min-chapter-words 300] [--max-chapters 200]
                              [--toc-file toc.txt] [--preview 0]

输出 JSON：
  {
    "source_file": "...", "format": "epub|pdf|txt|md|docx",
    "total_words": 123456, "chapter_count": 12,
    "chapters": [{"index":1,"title":"第1章 ...","start":0,"end":1234,"words":1234,
                  "text":"...","file":"DIR/ch_01.txt"}]
  }

只依赖标准库；PDF 需要 pypdf / pdfplumber / fitz 之一（脚本会给出安装提示）。
"""

import argparse
import json
import os
import re
import sys
import zipfile
from xml.etree import ElementTree as ET

# ---------------------------------------------------------------- 章节识别

CHAPTER_PATTERNS = [
    # 中文：第一章 / 第1章 / 第 1 章 / 第一篇 / 第一部分 / 第 3 节
    re.compile(r"^\s*第\s*[0-9]{1,3}\s*[章节篇部回讲]\s*[、\.：:－\-—\s]*.{0,60}$"),
    re.compile(r"^\s*第\s*[一二三四五六七八九十百千零〇]+\s*[章节篇部回讲]\s*[、\.：:－\-—\s]*.{0,60}$"),
    # 中文：序 / 前言 / 引言 / 绪论 / 后记 / 附录一
    re.compile(r"^\s*(序|序言|前言|自序|译者序|引言|绪论|导论|导言|结语|后记|跋|附录[一二三四五六七八九十0-9]?)\s*[、\.：:－\-—\s]*.{0,40}$"),
    # 英文
    re.compile(r"^\s*(Chapter|CHAPTER|Part|PART|Section)\s+([0-9]+|[IVXLCDM]+)\s*[\.\:：\-—\s]*.{0,80}$"),
    re.compile(r"^\s*(Introduction|Preface|Prologue|Epilogue|Conclusion|Foreword|Afterword)\s*[\.\:：\-—\s]*.{0,60}$"),
    # 编号式： 1. xxx / 01 xxx （仅当行首为纯编号且后面跟标题）
    re.compile(r"^\s*[0-9]{1,2}\s*[\.、]\s*\S.{0,60}$"),
]

# Markdown 标题
MD_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")

# 明显不是章节标题的噪声行
NOISE = re.compile(r"(^\s*$|版权|ISBN|图书在版编目|责任编辑|封面设计|http|www\.)")


def is_heading(line, fmt):
    line = line.strip()
    if not line or len(line) > 90:
        return False
    if NOISE.search(line):
        return False
    if fmt == "md":
        return bool(MD_HEADING.match(line))
    if line.startswith("#"):
        return bool(MD_HEADING.match(line))
    return any(p.match(line) for p in CHAPTER_PATTERNS)


def clean_title(line, fmt):
    line = line.strip()
    if fmt == "md":
        m = MD_HEADING.match(line)
        return m.group(2).strip() if m else line
    return re.sub(r"\s+", " ", line).strip(" .。、")


# ---------------------------------------------------------------- 格式解析

def read_txt(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def read_pdf(path):
    """依次尝试 pypdf / pdfplumber / fitz，都不在则给出安装建议。"""
    try:
        from pypdf import PdfReader  # type: ignore
        return "\n".join((p.extract_text() or "") for p in PdfReader(path).pages)
    except ImportError:
        pass
    try:
        import pdfplumber  # type: ignore
        out = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                out.append(page.extract_text() or "")
        return "\n".join(out)
    except ImportError:
        pass
    try:
        import fitz  # type: ignore
        return "\n".join(p.get_text() for p in fitz.open(path))
    except ImportError:
        pass
    sys.exit(
        "PDF 解析需要第三方库。请先安装（推荐装到隔离环境）：\n"
        "  <python> -m pip install pypdf\n"
        "若 PDF 是扫描件（无文字层），需先 OCR，本脚本无法处理。"
    )


def read_docx(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:tab[^>]*/>", "\t", xml)
    xml = re.sub(r"<[^>]+>", "", xml)
    return xml


def _strip_html(html):
    html = re.sub(r"(?is)<(script|style).*?</\1>", "", html)
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)
    html = re.sub(r"(?i)</(p|div|h[1-6]|li|tr)>", "\n", html)
    html = re.sub(r"<[^>]+>", "", html)
    import html as _h
    return _h.unescape(html)


def read_epub(path):
    """按 OPF spine 顺序拼正文，尽量保留章节边界。"""
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        opf = next((n for n in names if n.endswith(".opf")), None)
        if not opf:
            sys.exit("EPUB 缺少 .opf 文件，无法解析。")
        base = os.path.dirname(opf)
        root = ET.fromstring(z.read(opf))
        ns = {"o": "http://www.idpf.org/2007/opf"}
        manifest = {}
        for item in root.findall(".//o:manifest/o:item", ns):
            manifest[item.get("id")] = item.get("href")
        spine_ids = [i.get("idref") for i in root.findall(".//o:spine/o:itemref", ns)]
        chunks = []
        for sid in spine_ids:
            href = manifest.get(sid)
            if not href:
                continue
            target = os.path.join(base, href).replace("\\", "/")
            if target not in names:
                cand = next((n for n in names if n.endswith(href)), None)
                if not cand:
                    continue
                target = cand
            raw = z.read(target).decode("utf-8", "ignore")
            body = re.search(r"(?is)<body.*?>(.*)</body>", raw)
            chunks.append(_strip_html(body.group(1) if body else raw))
    return "\n\n".join(chunks)


# ---------------------------------------------------------------- 切章

def split_chapters(text, fmt, min_words=300, max_chapters=200, toc=None):
    lines = text.split("\n")
    hits = []  # (line_no, title)
    for i, line in enumerate(lines):
        if is_heading(line, fmt):
            hits.append((i, clean_title(line, fmt)))
    # 过滤掉彼此过近的误判（同一页内多处编号）；保留更"像标题"的
    if toc:
        # 用户提供了目录：只保留能在目录里找到的标题
        wanted = [re.sub(r"\s+", "", t) for t in toc]
        hits = [(i, t) for i, t in hits
                if any(re.sub(r"\s+", "", t).startswith(w[:6]) or w[:6] in re.sub(r"\s+", "", t)
                       for w in wanted if len(w) >= 4)]
    if not hits:
        return [{"index": 1, "title": "全文（未识别到章节标题）", "start": 0,
                 "end": len(lines), "words": len(text), "text": text}]

    chapters = []
    for k, (ln, title) in enumerate(hits[:max_chapters]):
        end = hits[k + 1][0] if k + 1 < len(hits) else len(lines)
        body = "\n".join(lines[ln:end]).strip()
        if len(body) < min_words and chapters:
            chapters[-1]["text"] += "\n" + body
            chapters[-1]["end"] = end
            continue
        chapters.append({"index": len(chapters) + 1, "title": title or "（无标题）",
                         "start": ln, "end": end, "words": len(body), "text": body})
    return chapters


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="提取电子书正文并按章节切分")
    ap.add_argument("file")
    ap.add_argument("--out", default="", help="JSON 输出路径；默认输出到同目录")
    ap.add_argument("--dump-dir", default="", help="把每章正文单独写成 txt，便于分批精读")
    ap.add_argument("--min-chapter-words", type=int, default=300)
    ap.add_argument("--max-chapters", type=int, default=200)
    ap.add_argument("--toc-file", default="", help="可选：目录文件（每行一个章节标题），用于校准切章")
    ap.add_argument("--preview", type=int, default=0, help=">0 时只在终端打印该章前 N 字")
    ap.add_argument("--no-text", action="store_true", help="JSON 中不带正文，只带元信息（省 token）")
    args = ap.parse_args()

    path = args.file
    if not os.path.exists(path):
        sys.exit(f"文件不存在: {path}")
    ext = os.path.splitext(path)[1].lower()
    fmt = {".pdf": "pdf", ".epub": "epub", ".docx": "docx",
           ".md": "md", ".markdown": "md", ".txt": "txt"}.get(ext, "txt")
    toc = None
    if args.toc_file and os.path.exists(args.toc_file):
        toc = [l.strip() for l in read_txt(args.toc_file).split("\n") if l.strip()]

    text = {"pdf": read_pdf, "epub": read_epub, "docx": read_docx}.get(fmt, read_txt)(path)
    text = re.sub(r"\n{3,}", "\n\n", text)
    chapters = split_chapters(text, fmt, args.min_chapter_words, args.max_chapters, toc)

    if args.dump_dir:
        os.makedirs(args.dump_dir, exist_ok=True)
        for ch in chapters:
            fn = os.path.join(args.dump_dir, "ch_%02d.txt" % ch["index"])
            with open(fn, "w", encoding="utf-8") as f:
                f.write("# %s\n\n%s\n" % (ch["title"], ch["text"]))
            ch["file"] = fn

    if args.preview:
        ch = chapters[0]
        print("[%s] 共 %d 章，预览第 1 章《%s》前 %d 字：\n" % (fmt, len(chapters), ch["title"], args.preview))
        print(ch["text"][:args.preview])
        return

    payload = {
        "source_file": os.path.abspath(path),
        "format": fmt,
        "total_words": sum(c["words"] for c in chapters),
        "chapter_count": len(chapters),
        "chapters": chapters,
    }
    if args.no_text:
        for c in payload["chapters"]:
            c.pop("text", None)
            c.pop("file", None)

    out = args.out or os.path.splitext(path)[0] + ".chapters.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print("已切出 %d 章 / 约 %d 字 -> %s" % (len(chapters), payload["total_words"], out))
    for c in chapters:
        print("  %2d. %s  (%d 字)" % (c["index"], c["title"][:40], c["words"]))


if __name__ == "__main__":
    main()
