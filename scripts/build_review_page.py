#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把「全书精读回顾」Markdown 稿渲染成单文件 HTML 温习页。

特性：侧边目录 / 全文搜索 / 章节折叠 / 答案点击展开 / 阅读进度 / 打印友好。
零第三方依赖，输出单个 .html 文件，双击即可打开，适合日后反复翻阅。

用法：
  python build_review_page.py <review.md> [--out review.html] [--title "书名"]
"""

import argparse
import html as _h
import os
import re
import sys

# ---------------------------------------------------------------- Markdown 解析

RE_H = re.compile(r"^(#{1,6})\s+(.*)$")
RE_HR = re.compile(r"^\s*(---+|\*\*\*+|___+)\s*$")
RE_BQ = re.compile(r"^\s*>\s?(.*)$")
RE_UL = re.compile(r"^(\s*)([-*+])\s+(.*)$")
RE_OL = re.compile(r"^(\s*)(\d+)[.)]\s+(.*)$")
RE_TABLE_SEP = re.compile(r"^\s*\|?[\s:\-\|]+\|[\s:\-\|]*$")


def inline(s):
    s = _h.escape(s, quote=False)
    s = s.replace("[ ]", "☐").replace("[x]", "☑").replace("[X]", "☑")
    s = s.replace("[转述，非原文]", '<span class="badge">转述</span>')
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"~~([^~]+)~~", r"<del>\1</del>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)
    return s


RE_Q_TR = re.compile(r"^\s*(\*\*中译\*\*|中译)\s*[:：]?\s*(.*)$")
RE_Q_LOC = re.compile(r"^\s*(——|—)\s*(.*)$")


def _bq(lines, i):
    """多行引用块按角色拆分：原文 / 中译 / 出处。"""
    raw = []
    while i < len(lines):
        m = RE_BQ.match(lines[i])
        if not m:
            break
        raw.append(m.group(1).strip())
        i += 1
    if len(raw) <= 1:
        return "<blockquote><p class=\"q\">%s</p></blockquote>" % inline(raw[0] if raw else ""), i
    body, rest = [raw[0]], []
    for line in raw[1:]:
        if RE_Q_TR.match(line):
            rest.append('<p class="q-tr">%s</p>' % inline(RE_Q_TR.match(line).group(2)))
        elif RE_Q_LOC.match(line):
            rest.append('<p class="q-loc">%s</p>' % inline(line))
        else:
            rest.append('<p class="q-extra">%s</p>' % inline(line))
    return ('<blockquote><p class="q">%s</p>%s</blockquote>'
            % (inline(body[0]), "".join(rest))), i


def _table(lines, i):
    rows = []
    while i < len(lines) and lines[i].strip().startswith("|"):
        cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
        if not (len(rows) == 1 and all(re.fullmatch(r":?-{2,}:?", c or "-") for c in cells)):
            rows.append(cells)
        i += 1
    if not rows:
        return "", i
    head = "".join("<th>%s</th>" % inline(c) for c in rows[0])
    body = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % inline(c) for c in r) for r in rows[1:])
    return '<div class="table-wrap"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (head, body), i


def _list(lines, i):
    items = []  # (indent, ordered, text)

    def is_item(l):
        return RE_UL.match(l) or RE_OL.match(l)

    while i < len(lines) and (is_item(lines[i]) or (items and lines[i].startswith((" ", "\t")) and lines[i].strip() and not RE_BQ.match(lines[i]))):
        if is_item(lines[i]):
            m = RE_UL.match(lines[i]) or RE_OL.match(lines[i])
            indent = len(m.group(1).replace("\t", "  "))
            items.append((indent, bool(RE_OL.match(lines[i])), m.group(3)))
        elif items:
            items[-1] = (items[-1][0], items[-1][1], items[-1][2] + "\n" + lines[i].strip())
        i += 1

    def build(idx, indent):
        html_parts = []
        tag = "ol" if items[idx][1] else "ul"
        html_parts.append("<%s>" % tag)
        while idx < len(items):
            cur_indent, ordered, text = items[idx]
            if cur_indent < indent:
                break
            if cur_indent > indent:
                sub, idx = build(idx, cur_indent)
                if html_parts and html_parts[-1].startswith("<li>"):
                    html_parts[-1] = html_parts[-1][:-4] + sub + "</li>"
                continue
            lines_txt = [inline(t) for t in text.split("\n")]
            html_parts.append("<li>%s</li>" % "<br>".join(lines_txt))
            idx += 1
        html_parts.append("</%s>" % tag)
        return "".join(html_parts), idx

    body, _ = build(0, items[0][0])
    return body, i


def render(md):
    lines = md.replace("\r\n", "\n").split("\n")
    out, i, para = [], 0, []

    def flush():
        if para:
            out.append("<p>%s</p>" % "<br>".join(inline(x) for x in para))
            para.clear()

    while i < len(lines):
        line = lines[i]
        if not line.strip():
            flush(); i += 1; continue
        if line.strip().startswith("```"):
            flush(); i += 1; buf = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i]); i += 1
            i += 1
            out.append("<pre><code>%s</code></pre>" % _h.escape("\n".join(buf)))
            continue
        m = RE_H.match(line)
        if m:
            flush()
            lv, txt = len(m.group(1)), m.group(2).strip()
            if lv >= 2:
                out.append('<h%d id="h%d">%s</h%d>' % (lv, len(out), inline(txt), lv))
            else:
                out.append("<h%d>%s</h%d>" % (lv, inline(txt), lv))
            i += 1; continue
        if RE_HR.match(line):
            flush(); out.append("<hr>"); i += 1; continue
        if RE_BQ.match(line):
            flush(); b, i = _bq(lines, i); out.append(b); continue
        if line.strip().startswith("|"):
            flush(); t, i = _table(lines, i); out.append(t); continue
        if RE_UL.match(line) or RE_OL.match(line):
            flush(); l, i = _list(lines, i); out.append(l); continue
        para.append(line.strip()); i += 1
    flush()
    return "\n".join(out)


# ---------------------------------------------------------------- 页面模板

PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__ · 精读回顾</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,300;0,400;1,300;1,400&family=Noto+Serif+SC:wght@300;400;500;700&display=swap" rel="stylesheet">
<style>
:root{
  --paper:#F5F2EA; --panel:#FFFDF7; --panel-2:#FBF8F1;
  --ink:#1B1815; --mid:#5C5449; --faint:#9A9184;
  --line:#E3DCD0; --line-soft:#EFEAE0;
  --accent:#9C2B22; --gold:#9A7B3F;
  --serif:'Spectral','Noto Serif SC','Source Han Serif SC','Songti SC',Georgia,serif;
  --sans:-apple-system,'Segoe UI Variable Text','Segoe UI','PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;
}
html.dark{
  --paper:#14120F; --panel:#1B1916; --panel-2:#211E19;
  --ink:#EFE9DE; --mid:#A79E90; --faint:#7B7365;
  --line:#332F28; --line-soft:#262319;
  --accent:#D2604F; --gold:#C9A961;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--paper);color:var(--ink);font:400 15.5px/1.85 var(--sans);
  -webkit-font-smoothing:antialiased;transition:background .3s,color .3s}
body::before{content:'';position:fixed;inset:0;z-index:0;pointer-events:none;
  background:radial-gradient(70vw 60vh at 12% -10%,rgba(156,43,34,.055),transparent 60%),
             radial-gradient(60vw 50vh at 92% 8%,rgba(154,123,63,.07),transparent 62%);}
body::after{content:'';position:fixed;inset:0;z-index:0;pointer-events:none;opacity:.32;mix-blend-mode:multiply;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.42'/%3E%3C/svg%3E")}
#bar{position:fixed;top:0;left:0;height:2px;width:0;z-index:60;background:var(--accent);transition:width .12s linear}

/* ---------- shell ---------- */
.wrap{position:relative;z-index:1;display:flex;align-items:flex-start;max-width:1240px;margin:0 auto}
.rail{position:sticky;top:0;flex:0 0 268px;width:268px;height:100vh;overflow-y:auto;
  padding:44px 26px 40px;border-right:1px solid var(--line);scrollbar-width:thin}
.rail::-webkit-scrollbar{width:3px}.rail::-webkit-scrollbar-thumb{background:var(--line)}
.brand{font:400 15px/1.5 var(--serif);color:var(--ink);letter-spacing:.04em}
.brand small{display:block;margin-top:6px;font:500 9.5px/1.5 var(--sans);letter-spacing:.3em;
  text-transform:uppercase;color:var(--faint)}
#q{width:100%;margin:26px 0 6px;padding:8px 0;background:none;color:var(--ink);
  border:0;border-bottom:1px solid var(--line);outline:none;font:400 13px/1.6 var(--sans)}
#q::placeholder{color:var(--faint)}
#q:focus{border-bottom-color:var(--accent)}
nav{margin-top:18px}
nav a{position:relative;display:block;padding:7px 0 7px 14px;color:var(--mid);text-decoration:none;
  font-size:13px;line-height:1.55;opacity:0;animation:rise .55s cubic-bezier(.2,.7,.2,1) forwards;
  animation-delay:calc(var(--i,0)*16ms + .25s);transition:color .18s,padding .18s}
nav a:before{content:'';position:absolute;left:0;top:12px;width:5px;height:1px;background:var(--line);transition:.2s}
nav a.lv3{font-size:12.5px;color:var(--faint);padding-left:26px}
nav a:hover{color:var(--accent);padding-left:18px}
nav a.on{color:var(--ink);font-weight:500}
nav a.on:before{width:12px;background:var(--accent)}
.railfoot{margin-top:26px;padding-top:18px;border-top:1px solid var(--line);
  font-size:11px;letter-spacing:.1em;color:var(--faint)}

/* ---------- content ---------- */
main{flex:1;min-width:0;padding:0 0 200px}
.sheet{max-width:730px;margin:0 auto;padding:0 44px;position:relative;z-index:1}
.hero{padding:118px 0 64px;border-bottom:1px solid var(--line)}
.hero>*{opacity:0;transform:translateY(16px);animation:rise .95s cubic-bezier(.2,.75,.2,1) forwards}
.hero>*:nth-child(1){animation-delay:.05s}.hero>*:nth-child(2){animation-delay:.14s}
.hero>*:nth-child(3){animation-delay:.24s}.hero>*:nth-child(4){animation-delay:.34s}
.kicker{font:500 10px/1.6 var(--sans);letter-spacing:.32em;text-transform:uppercase;color:var(--faint)}
h1{font:300 clamp(36px,5.6vw,60px)/1.14 var(--serif);letter-spacing:.015em;margin:20px 0 0}
h1 em{font-style:italic;color:var(--mid)}
.sub{margin:26px 0 0;max-width:33em;font:italic 300 19px/1.75 var(--serif);color:var(--mid)}
.herofoot{margin-top:34px;display:flex;gap:22px;flex-wrap:wrap;
  font:400 11px/1.6 var(--sans);letter-spacing:.16em;color:var(--faint)}
h2{position:relative;margin:104px 0 10px;padding-top:30px;border-top:1px solid var(--line);
  font:300 27px/1.32 var(--serif);letter-spacing:.01em}
h2:before{content:counter(sec,decimal-leading-zero);display:block;margin-bottom:14px;
  font:500 10px/1 var(--sans);letter-spacing:.34em;color:var(--gold)}
h3{font:500 20px/1.4 var(--serif);margin:0}
h4{margin:26px 0 6px;font:500 10.5px/1 var(--sans);letter-spacing:.26em;color:var(--accent)}
p{margin:10px 0}
hr{border:0;border-top:1px solid var(--line);margin:26px 0}
a{color:var(--accent);text-decoration:none;border-bottom:1px solid rgba(156,43,34,.28)}
code{font-family:ui-monospace,'SFMono-Regular',Consolas,monospace;font-size:13px;
  background:var(--panel-2);padding:1px 5px;border-radius:3px}
pre{background:var(--panel-2);padding:14px 16px;border-radius:6px;overflow:auto;font-size:13px}
.badge{display:inline-block;margin-right:6px;padding:1px 6px;border-radius:3px;
  background:var(--panel-2);border:1px solid var(--line);font:500 10px/1.6 var(--sans);
  letter-spacing:.1em;color:var(--faint);vertical-align:1px}

/* quote */
blockquote{margin:16px 0;padding:2px 0 2px 22px;border-left:2px solid var(--accent)}
blockquote.cmt{border-left:2px dashed var(--gold)}
.q{margin:0;font:italic 400 17.5px/1.72 var(--serif);color:var(--ink)}
.q-tr{margin:7px 0 0;font:400 14.5px/1.8 var(--sans);color:var(--mid)}
.q-extra{margin:7px 0 0;font-size:14.5px;color:var(--mid)}
.q-loc{margin:9px 0 0;font:400 11px/1.6 var(--sans);letter-spacing:.1em;color:var(--faint)}

/* lists */
ul,ol{margin:10px 0;padding:0;list-style:none}
li{position:relative;padding-left:22px;margin:6px 0}
ul>li:before{content:'';position:absolute;left:2px;top:.85em;width:8px;height:1px;background:var(--line)}
ol{counter-reset:o}
ol>li{counter-increment:o}
ol>li:before{content:counter(o,decimal-leading-zero);position:absolute;left:0;top:0;
  font:500 11px/1.9 var(--sans);letter-spacing:.06em;color:var(--gold)}
ul ul,ol ol,ul ol,ol ul{margin:4px 0}

/* table */
.tw{overflow-x:auto;margin:20px 0}
table{width:100%;border-collapse:collapse;font:400 14px/1.65 var(--sans)}
th{text-align:left;padding:0 18px 10px 0;border-bottom:1px solid var(--line);
  font:500 9.5px/1 var(--sans);letter-spacing:.24em;text-transform:uppercase;color:var(--faint);white-space:nowrap}
td{padding:11px 18px 11px 0;border-bottom:1px solid var(--line-soft);vertical-align:top}
tbody tr{transition:background .15s}
tbody tr:hover td{background:var(--panel-2)}

/* chapter card */
.chap{border-top:1px solid var(--line-soft);margin-top:26px;padding-top:20px}
.chap>.hd{display:flex;align-items:baseline;gap:16px;cursor:pointer;user-select:none}
.chap>.hd .num{flex:0 0 42px;font:300 24px/1 var(--serif);color:var(--gold);letter-spacing:.02em}
.chap>.hd .num.dot:before{content:'';display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--gold);vertical-align:.35em}
.chap>.hd .t{flex:1;font:500 19px/1.45 var(--serif)}
.chap>.hd .tg{flex:0 0 auto;font:400 10px/1 var(--sans);letter-spacing:.2em;color:var(--faint)}
.chap>.hd:hover .t{color:var(--accent)}
.chap>.bd{max-height:0;overflow:hidden;opacity:0;transition:max-height .42s cubic-bezier(.4,0,.2,1),opacity .3s}
.chap.open>.bd{max-height:none;opacity:1}
.chap.open>.bd.openh{max-height:none}

/* reveal + search + answer */
.rv{opacity:0;transform:translateY(12px);transition:opacity .6s,transform .6s}
.rv.in{opacity:1;transform:none}
mark{background:rgba(201,169,97,.34);color:inherit;padding:0 1px;border-radius:2px}
.ans{position:relative;cursor:pointer;filter:blur(6px);transition:filter .25s;user-select:none}
.ans.open{filter:none}
.ans:after{content:'点击展开';position:absolute;right:2px;bottom:-2px;padding:0 6px;
  background:var(--panel);font:400 10px/1.7 var(--sans);letter-spacing:.12em;color:var(--faint)}
.ans.open:after{content:''}
.hide{display:none !important}

/* toolbar */
.tools{position:sticky;top:0;z-index:20;display:flex;gap:20px;align-items:center;
  margin:0 0 -1px;padding:14px 44px;background:var(--paper);background:color-mix(in srgb,var(--paper) 88%,transparent);
  backdrop-filter:blur(10px);border-bottom:1px solid transparent}
.tools button{background:none;border:0;padding:0;cursor:pointer;color:var(--faint);
  font:400 10px/1 var(--sans);letter-spacing:.2em;transition:color .18s}
.tools button:hover{color:var(--accent)}
.tools .sp{flex:1}

@keyframes rise{to{opacity:1;transform:none}}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important;opacity:1!important}}
@media(max-width:960px){
  .wrap{display:block}.rail{position:static;width:auto;height:auto;border-right:0;
    border-bottom:1px solid var(--line);padding:24px 22px}
  .sheet{padding:0 22px}.tools{padding:12px 22px}.hero{padding:56px 0 40px}h2{margin-top:64px}
}
@media print{
  body::before,body::after,#bar,.rail,.tools{display:none!important}
  body{background:#fff}.chap>.bd{max-height:none!important;opacity:1!important}
  .ans{filter:none!important}.hero{padding:0 0 24px}h2{margin-top:36px;page-break-after:avoid}
  .chap{page-break-inside:avoid}
}
</style></head><body>
<div id="bar"></div>
<div class="wrap">
<aside class="rail">
  <div class="brand">__TITLE__<small>Reading Review</small></div>
  <input id="q" placeholder="检索关键词…" autocomplete="off">
  <nav id="nav"></nav>
  <div class="railfoot">按 <b>/</b> 聚焦检索 · <b>P</b> 导出 PDF</div>
</aside>
<main id="main"><div class="sheet">__BODY__</div></main>
</div>
<script>
var main=document.getElementById('main'),sheet=main.querySelector('.sheet');
/* hero extraction */
var h1=sheet.querySelector('h1'),first=sheet.children[0];
if(h1){
  var hero=document.createElement('div');hero.className='hero';
  hero.innerHTML='<div class="kicker">The Intelligent Reader · 精读回顾</div>'
   +'<h1>'+h1.innerHTML.replace(/[《》]/g,'')+'</h1>';
  var bq=sheet.querySelector('h1 + blockquote, h1 ~ blockquote');
  if(bq&&bq.previousElementSibling===h1){var s=document.createElement('p');s.className='sub';
    s.innerHTML=bq.innerHTML;hero.appendChild(s);bq.parentNode.removeChild(bq);}
  hero.appendChild((function(){var f=document.createElement('div');f.className='herofoot';
    f.innerHTML='<span>按章节折叠</span><span>金句 · 释义</span><span>自测 · 回顾</span>';return f;})());
  sheet.insertBefore(hero,first);h1.parentNode.removeChild(h1);
}
/* sticky toolbar */
var tools=document.createElement('div');tools.className='tools';
[['全部展开',function(){chaps.forEach(function(c){openChap(c,1);});}],
 ['全部收起',function(){chaps.forEach(function(c){openChap(c,0);});}],
 ['显示全部答案',function(){main.querySelectorAll('.ans').forEach(function(a){a.classList.add('open');});}],
 ['纸 / 墨',function(){document.documentElement.classList.toggle('dark');}],
 ['打印',function(){window.print();}]].forEach(function(x){
  var b=document.createElement('button');b.textContent=x[0];b.onclick=x[1];tools.appendChild(b);});
var sp=document.createElement('span');sp.className='sp';tools.insertBefore(sp,tools.children[3]);
sheet.parentNode.insertBefore(tools,sheet);

/* build nav */
var nav=document.getElementById('nav'),hs=sheet.querySelectorAll('h2,h3'),html='';
hs.forEach(function(h,i){h.id=h.id||'s'+i;
  html+='<a class="'+(h.tagName==='H3'?'lv3':'')+'" href="#'+h.id+'" style="--i:'+i+'">'+h.textContent+'</a>';});
nav.innerHTML=html;
var links=[].slice.call(nav.children);

/* wrap chapters */
var chaps=[],els=[].slice.call(sheet.children),cur=null;
els.forEach(function(el){
  if(el.tagName==='H3'){
    var nm=(el.textContent.match(/第\s*([0-9]+)\s*章/)||[])[1];
    var card=document.createElement('div');card.className='chap';
    var hd=document.createElement('div');hd.className='hd';
    hd.innerHTML='<span class="num'+(nm?'':' dot')+'">'+(nm||'')+'</span><span class="t">'
      +el.textContent.replace(/^第\s*[0-9]+\s*章\s*·\s*/,'')+'</span><span class="tg">收起</span>';
    var bd=document.createElement('div');bd.className='bd';
    card.appendChild(hd);card.appendChild(bd);sheet.insertBefore(card,el);el.remove();
    hd.onclick=function(){openChap(card,!card.classList.contains('open'));};
    chaps.push(card);cur=bd;
  } else if(cur&&el.tagName!=='H2'&&el!==tools){cur.appendChild(el);}
  else if(el.tagName==='H2'){cur=null;}
});
function openChap(c,yes){
  c.classList.toggle('open',!!yes);
  c.querySelector('.tg').textContent=yes?'收起':'展开';
  var bd=c.querySelector('.bd');
  bd.style.maxHeight=yes?bd.scrollHeight+'px':'0';
  if(yes)bd.querySelectorAll('.rv').forEach(function(el){el.classList.add('in');});
}
/* default: open first chapter only */
chaps.forEach(function(c,i){openChap(c,i===0);});

/* 兹威格点评 -> dashed */
main.querySelectorAll('blockquote').forEach(function(b){
  if(b.textContent.indexOf('兹威格')>=0)b.classList.add('cmt');});

/* answer masking */
main.querySelectorAll('p,blockquote').forEach(function(el){
  if(/^(答案|答|【答案】)[:：]?/.test(el.textContent.trim())){
    el.classList.add('ans');el.onclick=function(){el.classList.toggle('open');};}});

/* reveal on scroll */
var io=new IntersectionObserver(function(es){
  es.forEach(function(e){if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target);}});
},{rootMargin:'0px 0px -12% 0px'});
sheet.querySelectorAll('h2,p,blockquote,table,ul,ol,h4').forEach(function(el){
  if(!el.closest('.hero')){el.classList.add('rv');io.observe(el);}});

/* nav active */
var io2=new IntersectionObserver(function(es){
  es.forEach(function(e){if(e.isIntersecting){
    links.forEach(function(a){a.classList.toggle('on',a.getAttribute('href')==='#'+e.target.id);});}});
},{rootMargin:'-10% 0px -80% 0px'});
hs.forEach(function(h){io2.observe(h);});

/* search */
var marks=[];
function clearMark(){marks.forEach(function(m){if(m.parentNode)m.parentNode.replaceChild(
  document.createTextNode(m.textContent),m);});marks=[];}
document.getElementById('q').oninput=function(){
  clearMark();var k=this.value.trim();
  chaps.forEach(function(c){c.classList.remove('hide');});
  if(!k){return;}
  chaps.forEach(function(c){
    if(c.textContent.toLowerCase().indexOf(k.toLowerCase())<0){c.classList.add('hide');return;}
    openChap(c,1);
    try{var r=new RegExp('('+k.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+')','gi');
      c.querySelectorAll('p,li,td').forEach(function(el){
        if(el.children.length===0&&el.textContent.indexOf(k)>=0){
          el.innerHTML=el.innerHTML.replace(r,'<mark>$1</mark>');
          [].slice.call(el.querySelectorAll('mark')).forEach(function(m){marks.push(m);});}});}catch(e){}
  });
};
document.addEventListener('keydown',function(e){
  if(e.key==='/'&&document.activeElement!==document.getElementById('q')){
    e.preventDefault();document.getElementById('q').focus();}
  if((e.key==='p'||e.key==='P')&&!e.metaKey&&!e.ctrlKey&&document.activeElement!==document.getElementById('q')){
    window.print();}
});
document.addEventListener('scroll',function(){
  var h=document.documentElement,p=h.scrollTop/(h.scrollHeight-h.clientHeight)*100;
  document.getElementById('bar').style.width=(isNaN(p)?0:p)+'%';});
function recalc(){chaps.forEach(function(c){if(c.classList.contains('open')){var bd=c.querySelector('.bd');bd.style.maxHeight=bd.scrollHeight+'px';}});}
window.addEventListener('resize',recalc);
if(document.fonts&&document.fonts.ready)document.fonts.ready.then(recalc);
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("md")
    ap.add_argument("--out", default="")
    ap.add_argument("--title", default="")
    a = ap.parse_args()
    if not os.path.exists(a.md):
        sys.exit("文件不存在: " + a.md)
    md = open(a.md, encoding="utf-8").read()
    m = re.search(r"^#\s+(.*)$", md, re.M)
    title = a.title or (m.group(1).strip("# 《》 ").strip() if m else "全书精读回顾")
    out = a.out or os.path.splitext(a.md)[0] + ".html"
    html = PAGE.replace("__TITLE__", _h.escape(title)).replace("__BODY__", render(md))
    open(out, "w", encoding="utf-8").write(html)
    print("已生成温习页: %s" % os.path.abspath(out))


if __name__ == "__main__":
    main()
