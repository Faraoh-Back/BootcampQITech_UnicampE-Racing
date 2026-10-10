// Ferramenta de entrega, independente das dependências/imagem da API.
import { readFile, writeFile, mkdtemp, rm } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';
import { createHash } from 'node:crypto';
import MarkdownIt from 'markdown-it';
import puppeteer from 'puppeteer-core';

const here = dirname(fileURLToPath(import.meta.url));
const delivery = resolve(here, '..');
const docs = resolve(delivery, '..');
const md = new MarkdownIt({ html: true, typographer: false });
const escape = value => value.replaceAll('&', '&amp;').replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;').replaceAll('"', '&quot;');
const rfc = await readFile(resolve(docs, 'RFC.md'), 'utf8');
const diagram = rfc.match(/```mermaid\s+(erDiagram[\s\S]*?)```/)?.[1];
if (!diagram) throw new Error('DER canônico ausente');
const entities = [...diagram.matchAll(/^\s*([A-Z_]+)\s*\{\s*(.*?)\s*\}$/gm)].map(match => {
  const fields = [...match[2].matchAll(/(\w+)\s+(\w+)(?:\s+(PK,FK|PK|FK|UK))?(?:\s+"([^"]*)")?/g)];
  return { name: match[1], fields: fields.map(field =>
    `${field[1]} ${field[2]}${field[3] ? ' '+field[3] : ''}${field[4] ? ' ['+field[4]+']' : ''}`) };
});
const relations = [...diagram.matchAll(/^\s*([A-Z_]+)\s+(\S+--\S+)\s+([A-Z_]+)\s*:\s*(\w+)/gm)];
const finance = new Set(['CUSTOMER', 'ACCOUNT', 'ACCOUNT_STATUS', 'ACCOUNT_STATUS_EVENT',
  'TRANSACTION', 'IDEMPOTENCY_KEY', 'BILLING_PLAN', 'BANK_SLIP', 'BANK_SLIP_STATUS',
  'BANK_SLIP_STATUS_EVENT', 'CREDIT_ADVANCE', 'QUOTE', 'CUSTOMER_DAILY_OUTGOING']);

function wrap(text, width = 37) {
  const lines = [];
  while (text.length > width) {
    let cut = text.lastIndexOf(' ', width);
    if (cut < width / 2) cut = width;
    lines.push(text.slice(0, cut));
    text = text.slice(cut).trimStart();
  }
  lines.push(text);
  return lines;
}

// DER vetorial em cartões: cada ligação conserva a notação de cardinalidade
// Mermaid junto à entidade de destino, evitando cruzamentos ilegíveis em A4.
function schemaSvg(selected, label) {
  const width = 710, gap = 10, cardWidth = 230, row = 13;
  const bottoms = [43, 43, 43];
  const cards = [];
  for (const entity of selected) {
    const links = relations.filter(link => link[3] === entity.name);
    const lines = entity.fields.flatMap(field => wrap(field));
    const linkLines = links.flatMap(link => wrap(`${link[1]} ${link[2]} ${link[4]}`));
    const height = 32 + row * (lines.length + linkLines.length) + (links.length ? 9 : 0);
    const col = bottoms.indexOf(Math.min(...bottoms));
    const x = col * (cardWidth + gap), y = bottoms[col];
    let contents = `<g data-entity="${entity.name}"><rect x="${x}" y="${y}" width="${cardWidth}" height="${height}" rx="4" fill="#fff" stroke="#b4c3cf"/>`;
    contents += `<rect x="${x}" y="${y}" width="${cardWidth}" height="23" rx="4" fill="#12384b"/>`;
    contents += `<text x="${x+7}" y="${y+16}" fill="#fff" font-weight="bold">${entity.name}</text>`;
    let textY = y + 39;
    for (const line of lines) {
      contents += `<text x="${x+7}" y="${textY}" fill="#132c3b">${escape(line)}</text>`;
      textY += row;
    }
    if (links.length) {
      contents += `<path d="M${x+6} ${textY-5}h${cardWidth-12}" stroke="#d5dfe6"/>`;
      textY += 5;
      for (const link of links) {
        contents += `<g data-relation="${escape(`${link[1]}:${link[2]}:${link[3]}:${link[4]}`)}">`;
        for (const line of wrap(`${link[1]} ${link[2]} ${link[4]}`)) {
          contents += `<text x="${x+7}" y="${textY}" fill="#345568">${escape(line)}</text>`;
          textY += row;
        }
        contents += '</g>';
      }
    }
    cards.push(contents+'</g>');
    bottoms[col] += height + gap;
  }
  const height = Math.max(...bottoms) + 34;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-label="${escape(label)}">
<style>text{font-family:DejaVu Sans Mono,monospace;font-size:10px}</style>
<text x="0" y="17" fill="#12384b" font-weight="bold">${escape(label)}</text>
<text x="0" y="32" fill="#345568">PK: chave interna | UK: única | FK: vínculo | relação aponta para este cartão; UUIDs são públicos</text>
${cards.join('\n')}
<text x="0" y="${height-18}" fill="#345568">||: exatamente 1 | |o: 0 ou 1 | o{: 0 a N | relações lógicas de snapshot sem FK não são inventadas</text>
<text x="0" y="${height-4}" fill="#345568">Fonte integral: docs/RFC.md; termos/checks complementares: DECISOES.md e database.sql</text>
</svg>`;
}
for (const [name, selected, label] of [
  ['der-financeiro.svg', entities.filter(entity => finance.has(entity.name)), 'DER 1/2 — contas, ledger, cobrança e lastro'],
  ['der-operacional.svg', entities.filter(entity => !finance.has(entity.name)), 'DER 2/2 — identidade, políticas, auditoria e outbox'],
]) await writeFile(resolve(delivery, name), schemaSvg(selected, label));

const css = `
*{box-sizing:border-box}body{margin:0;color:#142d3b;font-family:DejaVu Sans,Arial,sans-serif}
@page{size:A4;margin:0}.page{width:210mm;height:297mm;padding:10mm 11mm;break-after:page;position:relative;overflow:visible;font-size:8.4pt;line-height:1.25}
.page:last-child{break-after:auto}h1{font-size:15pt;line-height:1.12;margin:0 0 5pt;color:#12384b}h2{font-size:11pt;margin:7pt 0 3pt}h3{font-size:9pt;margin:5pt 0 3pt}p{margin:4pt 0}ul,ol{padding-left:13pt;margin:4pt 0}li{margin:2pt 0}a{color:#125f74;text-decoration:none}code{font-family:DejaVu Sans Mono,monospace;font-size:.91em;overflow-wrap:anywhere}blockquote{margin:4pt 0;border-left:2pt solid #16768a;padding-left:7pt}blockquote h2{font-size:10pt}table{width:100%;border-collapse:collapse;margin:5pt 0}td,th{border-bottom:.5pt solid #cfdae2;text-align:left;vertical-align:top;padding:2pt 3pt}th{background:#e8f0f4}table code{font-size:6.8pt}img{max-width:100%}.footer{position:absolute;bottom:5mm;left:11mm;right:11mm;border-top:.5pt solid #ccd8df;font-size:7pt;padding-top:3pt;display:flex;justify-content:space-between}.rfc .page:first-child table:last-of-type{font-size:7.1pt;line-height:1.16;table-layout:fixed}.rfc .page:first-child table:last-of-type th:nth-child(1){width:7%}.rfc .page:first-child table:last-of-type th:nth-child(2){width:40%}.rfc .page:first-child table:last-of-type th:nth-child(3){width:14%}.rfc .page:first-child table:last-of-type th:nth-child(4){width:13%}.rfc .page:first-child table:last-of-type th:nth-child(5){width:26%}.rfc .page:first-child table:first-of-type{font-size:7.8pt;margin:2pt 0}.rfc .page:first-child table:first-of-type td{padding:1pt 3pt}.diagram img{display:block;max-height:258mm;width:100%;object-fit:contain;object-position:top}.flows{column-count:2;column-gap:6mm}.flows p,.flows blockquote,.flows ol{break-inside:avoid}.flows{font-size:8.4pt}.slides .page{width:297mm;height:167mm;padding:13mm 17mm;font-size:17pt;line-height:1.4}.slides h1{font-size:28pt}.slides h2{font-size:24pt;margin:0 0 10pt}.slides h3{font-size:19pt}.slides p,.slides li{margin:9pt 0}.slides table{font-size:14pt}.slides .footer{left:17mm;right:17mm;font-size:9pt}.slides code{font-size:.83em}.slides .small{font-size:12pt}.slides .metric{font-size:35pt;color:#157086}.slides pre{font-size:16pt;padding:12pt;background:#edf4f6;white-space:pre-wrap}
` + `
.rfc .page:first-child table:last-of-type td{padding:1pt 2pt}
.rfc .page:first-child table:last-of-type{line-height:1.1}
.rfc .page:first-child table:last-of-type td{overflow-wrap:anywhere}
.rfc .page:first-child p{margin:3pt 0}
.flows{font-size:8pt;line-height:1.2}.flows p{margin:3pt 0}.flows ol{margin:3pt 0}
.slides pre{margin:6pt 0;padding:8pt}
`;
const profile = await mkdtemp(resolve(tmpdir(), 'baas-doc-browser-'));
let browser;
try {
  browser = await puppeteer.launch({ executablePath: process.env.CHROME_BIN || '/usr/bin/chromium',
    headless: true, userDataDir: profile, args: process.env.CHROME_NO_SANDBOX === '1' ? ['--no-sandbox'] : [] });
  for (const [source, output, kind, expected] of [
    ['RFC_FINAL.md', 'RFC_FINAL.pdf', 'rfc', 4],
    ['APRESENTACAO.md', 'APRESENTACAO.pdf', 'slides', 10],
  ]) {
    const sourceText = await readFile(resolve(delivery, source), 'utf8');
    const pages = sourceText.split('<!-- page -->');
    if (pages.length !== expected) throw new Error(`${source}: ${pages.length} páginas, esperadas ${expected}`);
    const sections = [];
    for (const [index, page] of pages.entries()) {
      let rendered = md.render(page);
      rendered = rendered.replace(/<img src="(der-[^"]+\.svg)"[^>]*>/g, match => match);
      for (const name of ['der-financeiro.svg', 'der-operacional.svg']) {
        const data = Buffer.from(await readFile(resolve(delivery, name))).toString('base64');
        rendered = rendered.replaceAll(`src="${name}"`, `src="data:image/svg+xml;base64,${data}"`);
      }
      sections.push(`<section class="page">${rendered}<footer class="footer"><span>BaaS PME · QI Tech · 10/10/2026 · garantias verificadas</span><span>${index+1}/${pages.length}</span></footer></section>`);
    }
    const tab = await browser.newPage();
    await tab.setContent(`<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>${output.replace('.pdf','')}</title><style>${css}${kind === 'slides' ? '@page{size:297mm 167mm;margin:0}' : ''}</style></head><body class="${kind}">${sections.join('')}</body></html>`, { waitUntil: 'networkidle0' });
    await tab.evaluate(() => document.fonts.ready);
    const overflow = await tab.evaluate(() => [...document.querySelectorAll('.page')].flatMap((page, index) => {
      const limit = page.querySelector('.footer').getBoundingClientRect().top - 5;
      return [...page.children].filter(child => !child.classList.contains('footer') && child.getBoundingClientRect().bottom > limit)
        .map(child => ({ page: index+1, element: child.tagName, overflow: Math.ceil(child.getBoundingClientRect().bottom-limit) }));
    }));
    if (overflow.length) throw new Error(`${source}: conteúdo ultrapassa a área útil: ${JSON.stringify(overflow)}`);
    await tab.pdf({ path: resolve(delivery, output), printBackground: true, preferCSSPageSize: true, tagged: true });
    console.log(`${output}: ${pages.length} páginas; conteúdo sem overflow`);
    await tab.close();
  }
  const sources = ['../RFC.md', 'RFC_FINAL.md', 'APRESENTACAO.md', 'der-financeiro.svg',
    'der-operacional.svg', 'tools/render.mjs', 'tools/package-lock.json', 'RFC_FINAL.pdf', 'APRESENTACAO.pdf'];
  const hashes = {};
  for (const source of sources) hashes[source] = createHash('sha256')
    .update(await readFile(resolve(delivery, source))).digest('hex');
  await writeFile(resolve(delivery, 'artefatos.json'), JSON.stringify({
    source_version: '3.3', rfc_pages: 4, presentation_pages: 10, sha256: hashes,
    note: 'Conteúdo e integridade rastreáveis; bytes de PDF podem variar com data/Chromium/fontes.',
  }, null, 2)+'\n');
} finally {
  if (browser) await browser.close();
  await rm(profile, { recursive: true, force: true }); // somente diretório exclusivo criado por mkdtemp
}
