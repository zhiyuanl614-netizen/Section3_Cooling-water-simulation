// Build a fully self-contained HTML manuscript:
//  - math rendered by KaTeX at build time -> pure HTML+CSS (no JS, no CDN)
//  - SVG figures inlined (no external files)
//  - citations ^1^ / ^1,2^ / ^1-3^ -> superscript links
const fs = require('fs');
const path = require('path');
const katex = require('katex');
const MarkdownIt = require('markdown-it');

const ROOT = path.resolve(__dirname, '..', '..');
const SRC = path.join(ROOT, 'docs', 'manuscript_EN.md');
const OUT = path.join(ROOT, 'results', 'paper', 'manuscript.html');
const FIGDIR = path.join(ROOT, 'results', 'paper', 'figures');
// Build a KaTeX CSS with all woff2 fonts embedded as data URIs, so the
// document renders with no network access and no external files.
function katexCss() {
  const cssPath = require.resolve('katex/dist/katex.min.css');
  const fontDir = path.join(path.dirname(cssPath), 'fonts');
  let css = fs.readFileSync(cssPath, 'utf8');
  // keep only woff2 sources (cheapest + universally supported)
  css = css.replace(/src:\s*([^;}]+);/g, (m, inner) => {
    const keep = inner.split(',').map(s => s.trim()).filter(s => s.includes('woff2'));
    return keep.length ? 'src: ' + keep.join(', ') + ';' : m;
  });
  css = css.replace(/url\((fonts\/[^)]+)\)/g, (m, rel) => {
    const f = path.join(fontDir, path.basename(rel));
    if (!fs.existsSync(f)) return m;
    return 'url(data:font/woff2;base64,' + fs.readFileSync(f).toString('base64') + ')';
  });
  return css;
}
const KATEX_CSS = katexCss();

let md = fs.readFileSync(SRC, 'utf8');

// ---- 1. Protect math from markdown processing -------------------------------
const store = [];
function stash(html) { store.push(html); return `@@MATH${store.length - 1}@@`; }

// block math $$ ... $$
md = md.replace(/\$\$([\s\S]+?)\$\$/g, (m, tex) => {
  // strip \tag{N} -> render as an equation number on the right
  let tag = '';
  tex = tex.replace(/\\tag\{([^}]*)\}/g, (_, t) => { tag = t; return ''; });
  try {
    const body = katex.renderToString(tex.trim(), { displayMode: true, throwOnError: false, strict: false });
    const label = tag ? `<span class="eqnum">(${tag})</span>` : '';
    return stash(`<div class="eq">${body}${label}</div>`);
  } catch (e) {
    return stash(`<div class="eq err"><pre>${tex}</pre></div>`);
  }
});

// inline math $ ... $  (avoid $$ already handled)
md = md.replace(/(^|[^\\$])\$(?!\$)([^$\n]+?)\$/g, (m, pre, tex) => {
  try {
    return pre + stash(katex.renderToString(tex.trim(), { displayMode: false, throwOnError: false, strict: false }));
  } catch (e) {
    return pre + stash(`<code>${tex}</code>`);
  }
});

// ---- 2. Citations ^n^ -> superscript ---------------------------------------
md = md.replace(/\^([\d]+(?:[,\u2013-]\d+)*)\^/g, (m, inner) => {
  const nums = [];
  inner.split(',').forEach(part => {
    const r = part.match(/^(\d+)[\u2013-](\d+)$/);
    if (r) { for (let i = +r[1]; i <= +r[2]; i++) nums.push(i); }
    else nums.push(+part);
  });
  const links = nums.map(n => `<a href="#ref${n}" class="cite">${n}</a>`).join(',');
  return `<sup class="citeref">${links}</sup>`;
});

// ---- 3. Markdown -> HTML ----------------------------------------------------
const mdit = new MarkdownIt({ html: true, linkify: false, typographer: false, breaks: false });
let html = mdit.render(md);

// restore math
html = html.replace(/@@MATH(\d+)@@/g, (m, i) => store[+i]);

// ---- 4. Inline SVG figures --------------------------------------------------
html = html.replace(/<img src="([^"]+)" alt="([^"]*)"([^>]*)>/g, (m, src, alt) => {
  const base = path.basename(src);
  const f = path.join(FIGDIR, base);
  if (!fs.existsSync(f)) { console.warn('MISSING FIGURE', f); return `<p class="err">[missing ${base}]</p>`; }
  let svg = fs.readFileSync(f, 'utf8');
  svg = svg.replace(/<\?xml[^>]*\?>\s*/i, '').replace(/<!DOCTYPE[^>]*>/i, '');
  svg = svg.replace(/width="([\d.]+)pt"\s+height="([\d.]+)pt"/, 'width="100%" preserveAspectRatio="xMidYMid meet"');
  return `<figure class="fig">${svg}<figcaption>${alt}</figcaption></figure>`;
});

// ---- 5. Anchor the reference list ------------------------------------------
html = html.replace(/<li>(\d+)\.\s/g, '<li id="ref$1">$1. ');
html = html.replace(/<ol>/, '<ol class="reflist">');

// ---- 6. Assemble ------------------------------------------------------------
const doc = `<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Concurrent cooling-water failure and cascading service loss in a six-unit test system</title>
<style>
${KATEX_CSS}
:root{--ink:#1a1a1a;--muted:#555;--rule:#dcdcdc;--acc:#0b4f8a;}
*{box-sizing:border-box}
body{margin:0 auto;padding:3rem 1.5rem 6rem;max-width:900px;
 font-family:"Charter","Bitstream Charter","Source Serif Pro",Georgia,"Times New Roman",serif;
 font-size:17px;line-height:1.62;color:var(--ink);background:#fff;}
h1{font-size:1.9rem;margin:2.5rem 0 .6rem;font-weight:600;letter-spacing:-.01em}
h2{font-size:1.42rem;margin:2.6rem 0 .5rem;padding-bottom:.3rem;border-bottom:1px solid var(--rule);font-weight:600}
h3{font-size:1.15rem;margin:1.9rem 0 .4rem;font-weight:600}
h4{font-size:1rem;margin:1.4rem 0 .3rem;font-weight:600;color:var(--acc)}
p{margin:.7rem 0;text-align:justify;hyphens:auto}
strong{font-weight:650}
em{font-style:italic}
hr{border:0;border-top:1px solid var(--rule);margin:2rem 0}
a{color:var(--acc);text-decoration:none}
a:hover{text-decoration:underline}
code{font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace;font-size:.86em;
 background:#f4f4f4;padding:.1em .3em;border-radius:3px}
table{border-collapse:collapse;width:100%;margin:1rem 0;font-size:.86rem;line-height:1.4}
th,td{border-top:1px solid var(--rule);border-bottom:1px solid var(--rule);
 padding:.42em .6em;text-align:left;vertical-align:top}
th{border-top:1.5px solid #999;border-bottom:1px solid var(--rule);font-weight:650;background:#fafafa}
td.num,th.num{text-align:right}
blockquote{margin:1rem 0;padding:.2rem 1rem;color:var(--muted);
 border-left:3px solid var(--rule);font-size:.92rem}
.eq{margin:1.05rem 0;text-align:center;overflow-x:auto;position:relative}
.eq .katex-display{margin:0}
.eqnum{position:absolute;right:.2rem;top:50%;transform:translateY(-50%);font-size:.9rem;color:var(--muted)}
sup.citeref{font-size:.74em;line-height:0}
a.cite{padding:0 .05em}
figure.fig{margin:1.5rem 0;text-align:center;page-break-inside:avoid}
figure.fig svg{max-width:100%;height:auto;display:block;margin:0 auto}
figcaption{font-size:.84rem;color:var(--muted);margin-top:.5rem;text-align:left;
 line-height:1.45;padding-left:.2rem}
ol.reflist{font-size:.86rem;line-height:1.5;padding-left:2.2rem;color:#222}
ol.reflist li{margin-bottom:.5em}
.err{color:#a00}
@media print{
 body{max-width:none;padding:0;font-size:10.5pt}
 h2{page-break-after:avoid}
 figure.fig,table,.eq{page-break-inside:avoid}
 a{color:inherit;text-decoration:none}
 @page{margin:20mm}
}
</style></head><body>
${html}
</body></html>`;

fs.writeFileSync(OUT, doc);
console.log('wrote', OUT, (doc.length / 1024).toFixed(0) + ' KB');
console.log('math blocks rendered:', store.length);
