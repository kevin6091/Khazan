import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const deck = JSON.parse(await fs.readFile(path.join(root, 'deck.json'), 'utf8'));
const e = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const text = s => e(s).replaceAll('\n', '<br>');
const item = ([title, body]) => `<section><h2>${text(title)}</h2><p>${text(body)}</p></section>`;
const img = (name, cls = '') => `<img class="${cls}" src="../assets/${e(name)}" alt="">`;
const slides = deck.slides.map((s, i) => {
  const heading = `<header><h1>${text(s.title)}</h1>${s.subtitle ? `<p class="subtitle">${text(s.subtitle)}</p>` : ''}</header>`;
  let body = '';
  if (s.layout === 'cover') body = `${img(s.image, 'cover-art')}<div class="cover-copy"><p class="cover-label">${text(s.caption)}</p><h1>${text(s.title)}</h1><p>Unreal Engine 5.8</p></div>`;
  if (s.layout === 'wide_image') body = `${heading}${img(s.image, 'wide')}<div class="two">${s.items.map(item).join('')}</div>`;
  if (s.layout === 'controls') body = `${heading}<div class="control-columns">${s.columns.map(c => `<div><h2>${text(c.heading)}</h2><table>${c.rows.map(row => `<tr><th>${text(row[0])}</th><td>${text(row[1])}</td></tr>`).join('')}</table></div>`).join('')}</div>`;
  if (s.layout === 'roles') body = `${heading}<div class="roles">${s.items.map(item).join('')}</div>`;
  if (s.layout === 'sequence') body = `${heading}<div class="sequence">${s.items.map(([title,body]) => `<section><h2>${text(title)}</h2><p>${text(body)}</p></section>`).join('')}</div>`;
  if (s.layout === 'table') body = `${heading}<table class="matrix"><thead><tr>${s.headers.map(x => `<th>${text(x)}</th>`).join('')}</tr></thead><tbody>${s.rows.map(row=>`<tr>${row.map(x=>`<td>${text(x)}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
  if (s.layout === 'split') body = `${heading}<div class="split"><figure>${s.id==='portal'?`<div class="portal-frame">${img(s.image,'portal-image')}</div>`:img(s.image)}<figcaption>${text(s.caption)}</figcaption></figure><div class="split-copy">${s.items.map(item).join('')}</div></div>`;
  if (s.layout === 'comparison') body = `${heading}<div class="comparison">${s.images.map(x=>`<figure>${img(x.path)}<figcaption>${text(x.label)}</figcaption></figure>`).join('')}</div>`;
  return `<main class="slide layout-${s.layout}" id="s${i}" data-index="${i}">${body}${s.footnote ? `<p class="footnote">${text(s.footnote)}</p>` : ''}${s.layout!=='cover'?`<span class="page">${String(i+1).padStart(2,'0')}</span>`:''}</main>`;
}).join('\n');
const css = `
*{box-sizing:border-box}html,body{margin:0;background:#130c20;color:#f5f0f8;font-family:'Malgun Gothic',sans-serif;overflow:hidden}
.slide{width:1280px;height:720px;position:relative;padding:48px 64px;background:#130c20;display:none;overflow:hidden}.slide.active{display:block}
header{position:relative}h1{font-size:44px;font-weight:700;line-height:1.27;margin:0;letter-spacing:-1.6px}h2{margin:0 0 22px;font-size:30px;color:#b49aff;line-height:1.35;letter-spacing:-.8px}p{margin:0;font-size:27px;line-height:1.65;word-break:keep-all}p.subtitle{font-size:25px;color:#bdb1ce;margin-top:14px}
.page{position:absolute;bottom:28px;right:36px;font-size:21px;color:#ae9bbb}.footnote{position:absolute;bottom:46px;left:64px;width:1100px;font-size:24px;color:#bdb1ce;line-height:1.45}
.layout-cover{padding:0}.cover-art{width:1280px;height:720px;position:absolute;inset:0;object-fit:cover}.cover-copy{position:absolute;left:56px;bottom:46px;width:520px;text-shadow:0 2px 16px #000}.cover-copy h1{font-size:48px;line-height:1.25;margin:12px 0 16px}.cover-copy p{font-size:24px;line-height:1.4}.cover-copy .cover-label{font-size:24px;color:#ded1f8;font-weight:700}
.wide{width:1152px;height:340px;object-fit:cover;display:block;margin:30px 0 30px}.two{display:grid;grid-template-columns:1fr 1fr;column-gap:64px}.two h2{font-size:27px;margin-bottom:8px;color:#f14b63}.two p{font-size:25px;line-height:1.55}
.control-columns{display:grid;grid-template-columns:1fr 1fr;gap:58px;margin-top:36px}.control-columns h2{font-size:29px;color:#f14b63;margin:0 0 16px}table{border-collapse:collapse;width:100%}td,th{text-align:left;font-weight:400}.control-columns tr{height:64px;border-bottom:1px solid #44344f}.control-columns th{width:170px;font-size:27px;color:#b49aff;font-weight:700;white-space:nowrap}.control-columns td{font-size:25px;line-height:1.4;padding-left:16px}
.roles{display:grid;grid-template-columns:repeat(3,1fr);gap:48px;margin-top:78px}.roles h2{font-size:33px;margin-bottom:34px;color:#b49aff}.roles section:nth-child(2) h2{color:#f14b63}.roles p{font-size:28px;line-height:2.05}
.sequence{margin-top:38px;display:grid;grid-template-columns:1fr 1fr;column-gap:78px;row-gap:30px}.sequence section{min-height:176px}.sequence h2{font-size:31px;margin:0 0 14px;color:#b49aff}.sequence section:nth-child(even) h2{color:#f14b63}.sequence p{font-size:28px;line-height:1.7}
.matrix{margin-top:35px;table-layout:fixed}.matrix thead th{font-size:26px;color:#b49aff;font-weight:700;padding:14px 18px 22px 0}.matrix th:first-child{width:23%}.matrix th:nth-child(2){width:39%}.matrix tbody tr{height:87px;border-top:1px solid #51405c}.matrix td{padding:16px 20px 16px 0;font-size:25px;line-height:1.45;word-break:keep-all}.matrix td:first-child{color:#f14b63;font-weight:700}
.split{display:grid;grid-template-columns:650px 1fr;gap:42px;margin-top:40px;align-items:start}figure{margin:0}.split img{width:650px;height:386px;object-fit:cover;object-position:center 58%}.portal-frame{width:650px;height:386px;overflow:hidden}.split img.portal-image{width:1030px;height:560px;position:relative;left:-190px;top:-160px}.split figcaption{font-size:20px;color:#bdb1ce;line-height:1.4;margin-top:15px}.split-copy h2{font-size:29px;color:#b49aff;margin-bottom:14px}.split-copy section+section{margin-top:40px}.split-copy section+section h2{color:#f14b63}.split-copy p{font-size:26px;line-height:1.7}
.comparison{display:grid;grid-template-columns:1fr 1fr;gap:32px;margin-top:36px}.comparison img{width:560px;height:326px;object-fit:cover}.comparison figcaption{font-size:27px;margin-top:22px;color:#b49aff;font-weight:700}.comparison figure+figure figcaption{color:#f14b63}
`;
const html=`<!doctype html><html lang="ko"><meta charset="utf-8"><title>${e(deck.title)} 미리보기</title><style>${css}</style><body>${slides}<script>let at=Number(new URLSearchParams(location.search).get('slide')||0);function show(){document.querySelectorAll('.slide').forEach((s,i)=>s.classList.toggle('active',i===at));document.title=(at+1)+' / '+${deck.slides.length}+' KHAZAN';}show();addEventListener('keydown',e=>{if(['ArrowRight','PageDown',' '].includes(e.key))at=Math.min(${deck.slides.length-1},at+1);if(['ArrowLeft','PageUp'].includes(e.key))at=Math.max(0,at-1);show();});</script></body></html>`;
await fs.writeFile(path.join(root,'preview','index.html'),html,'utf8');
await fs.writeFile(path.join(root,'build','preview-layout.json'),JSON.stringify({width:1280,height:720,slideCount:deck.slides.length,layouts:deck.slides.map(s=>s.layout),status:'html_preview_only_not_native_google_slides'},null,2));
console.log(JSON.stringify({slideCount:deck.slides.length,html:path.join(root,'preview','index.html')}));
