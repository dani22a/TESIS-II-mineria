/**
 * MineTwin AI - Export service (charts, tables, 3D scene).
 * Pure functions, no React. Heavy libraries are loaded lazily.
 */

export type ExportBackground = 'white' | 'dark' | 'transparent';

export const MAX_CANVAS_SIDE = 16384;
export const MAX_CANVAS_PIXELS = 100_000_000;
const CM_PER_INCH = 2.54;

export class ExportError extends Error {
  readonly code: 'LIMIT' | 'INPUT' | 'RENDER' | 'UNSUPPORTED';
  constructor(code: ExportError['code'], message: string) {
    super(message);
    this.name = 'ExportError';
    this.code = code;
  }
}

/* ------------------------------------------------------------------ */
/* Pure helpers                                                        */
/* ------------------------------------------------------------------ */

export interface PngEstimate {
  w: number;
  h: number;
  ok: boolean;
  reason?: string;
}

/** `aspect` is height / width. */
export function estimatePng(widthCm: number, dpi: number, aspect: number): PngEstimate {
  if (!Number.isFinite(widthCm) || widthCm <= 0) return { w: 0, h: 0, ok: false, reason: 'Ingrese un ancho válido en cm.' };
  if (!Number.isFinite(dpi) || dpi <= 0) return { w: 0, h: 0, ok: false, reason: 'Ingrese un DPI válido.' };
  if (!Number.isFinite(aspect) || aspect <= 0) return { w: 0, h: 0, ok: false, reason: 'Proporción de la figura no válida.' };
  const w = Math.round((widthCm / CM_PER_INCH) * dpi);
  const h = Math.max(1, Math.round(w * aspect));
  if (w < 1) return { w, h, ok: false, reason: 'El ancho resultante es menor a 1 px.' };
  if (w > MAX_CANVAS_SIDE || h > MAX_CANVAS_SIDE) {
    return { w, h, ok: false, reason: `El lado mayor (${Math.max(w, h)} px) supera el máximo de ${MAX_CANVAS_SIDE} px. Reduzca el ancho o el DPI.` };
  }
  if (w * h > MAX_CANVAS_PIXELS) {
    return { w, h, ok: false, reason: `La imagen (${Math.round((w * h) / 1e6)} Mpx) supera el máximo de ${MAX_CANVAS_PIXELS / 1e6} Mpx. Reduzca el ancho o el DPI.` };
  }
  return { w, h, ok: true };
}

export function slugify(text: string): string {
  const s = text
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 60);
  return s || 'exportacion';
}

export function buildFilename(title: string, ext: string, now: Date = new Date()): string {
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  return `${slugify(title)}-${y}${m}${d}.${ext}`;
}

let crcTable: Uint32Array | null = null;
export function crc32(bytes: Uint8Array): number {
  if (!crcTable) {
    crcTable = new Uint32Array(256);
    for (let n = 0; n < 256; n++) {
      let c = n;
      for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
      crcTable[n] = c >>> 0;
    }
  }
  let crc = 0xffffffff;
  for (let i = 0; i < bytes.length; i++) crc = crcTable[(crc ^ bytes[i]) & 0xff] ^ (crc >>> 8);
  return (crc ^ 0xffffffff) >>> 0;
}

const PNG_SIG = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a];

/** Insert (or replace) a pHYs chunk right after IHDR so viewers read the DPI. */
export function setPngDpi(png: Uint8Array, dpi: number): Uint8Array {
  if (png.length < 33 || PNG_SIG.some((b, i) => png[i] !== b)) {
    throw new ExportError('RENDER', 'El archivo generado no es un PNG válido.');
  }
  const view = new DataView(png.buffer, png.byteOffset, png.byteLength);
  const ihdrLen = view.getUint32(8);
  const afterIhdr = 8 + 12 + ihdrLen;

  const ppm = Math.round(dpi / 0.0254);
  const chunk = new Uint8Array(21);
  const cv = new DataView(chunk.buffer);
  cv.setUint32(0, 9);
  chunk.set([0x70, 0x48, 0x59, 0x73], 4); // "pHYs"
  cv.setUint32(8, ppm);
  cv.setUint32(12, ppm);
  chunk[16] = 1; // unit: metre
  cv.setUint32(17, crc32(chunk.subarray(4, 17)));

  // Drop any pre-existing pHYs chunk.
  const parts: Uint8Array[] = [png.subarray(0, afterIhdr), chunk];
  let pos = afterIhdr;
  while (pos + 12 <= png.length) {
    const len = view.getUint32(pos);
    const type = String.fromCharCode(png[pos + 4], png[pos + 5], png[pos + 6], png[pos + 7]);
    const end = pos + 12 + len;
    if (type !== 'pHYs') parts.push(png.subarray(pos, end));
    pos = end;
  }
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let o = 0;
  for (const p of parts) {
    out.set(p, o);
    o += p.length;
  }
  return out;
}

export function rowsToCsv(rows: string[][]): string {
  const esc = (v: string) => `"${String(v).replace(/"/g, '""')}"`;
  return '﻿' + rows.map((r) => r.map(esc).join(',')).join('\r\n') + '\r\n';
}

/** Numeric if the whole cell is a plain number; otherwise the original string. */
export function parseCellValue(text: string): string | number {
  const t = text.trim();
  if (/^-?\d+(\.\d+)?$/.test(t)) return Number(t);
  return text;
}

export function rowsToHtml(rows: string[][]): string {
  const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const body = rows
    .map((r, i) => `<tr>${r.map((c) => (i === 0 ? `<th>${esc(c)}</th>` : `<td>${esc(c)}</td>`)).join('')}</tr>`)
    .join('');
  return `<table border="1" cellspacing="0" cellpadding="4">${body}</table>`;
}

/* ------------------------------------------------------------------ */
/* Download                                                            */
/* ------------------------------------------------------------------ */

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.style.display = 'none';
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

/* ------------------------------------------------------------------ */
/* SVG standalone                                                      */
/* ------------------------------------------------------------------ */

const SVG_NS = 'http://www.w3.org/2000/svg';
const BG_COLORS: Record<Exclude<ExportBackground, 'transparent'>, string> = {
  white: '#ffffff',
  dark: '#0f172a',
};

const STYLE_PROPS = [
  'fill', 'fill-opacity', 'fill-rule', 'stroke', 'stroke-width', 'stroke-opacity', 'stroke-dasharray',
  'stroke-dashoffset', 'stroke-linecap', 'stroke-linejoin', 'stroke-miterlimit', 'opacity',
  'font-family', 'font-size', 'font-weight', 'font-style', 'letter-spacing', 'text-anchor',
  'dominant-baseline', 'shape-rendering', 'stop-color', 'stop-opacity', 'visibility', 'paint-order',
];
const MODERN_COLOR = /(oklch|oklab|lab|lch|color|color-mix|hwb)\(|var\(/i;

let colorCtx: CanvasRenderingContext2D | null = null;
const colorCache = new Map<string, string>();

/** Convert any CSS color the browser understands (oklch, color-mix, ...) to rgb()/rgba(). */
export function resolveColor(value: string): string {
  if (!MODERN_COLOR.test(value)) return value;
  const cached = colorCache.get(value);
  if (cached) return cached;
  if (!colorCtx) {
    const c = document.createElement('canvas');
    c.width = c.height = 1;
    colorCtx = c.getContext('2d', { willReadFrequently: true });
  }
  if (!colorCtx) return value;
  colorCtx.clearRect(0, 0, 1, 1);
  colorCtx.fillStyle = '#000';
  colorCtx.fillStyle = value;
  colorCtx.fillRect(0, 0, 1, 1);
  const [r, g, b, a] = colorCtx.getImageData(0, 0, 1, 1).data;
  const out = a === 255 ? `rgb(${r},${g},${b})` : `rgba(${r},${g},${b},${+(a / 255).toFixed(3)})`;
  colorCache.set(value, out);
  return out;
}

function inlineStyles(src: Element, dst: Element): void {
  const cs = getComputedStyle(src);
  let css = '';
  for (const p of STYLE_PROPS) {
    let v = cs.getPropertyValue(p);
    if (!v) continue;
    if (p === 'fill' || p === 'stroke' || p === 'stop-color') {
      v = v.startsWith('url(') ? v.replace(/url\("?([^")]+)"?\)/, 'url($1)') : resolveColor(v);
    }
    css += `${p}:${v};`;
  }
  if (cs.display === 'none') css += 'display:none;';
  (dst as SVGElement).setAttribute('style', css);
  const sc = src.children;
  const dc = dst.children;
  for (let i = 0; i < sc.length && i < dc.length; i++) inlineStyles(sc[i], dc[i]);
}

export interface StandaloneSvg {
  svg: string;
  width: number;
  height: number;
  node: SVGSVGElement;
}

/** Locate the main Recharts svg (the legend icons are small svgs with the same class). */
export function findChartSvg(container: Element): SVGSVGElement | null {
  const direct = container.querySelector<SVGSVGElement>('.recharts-wrapper > svg.recharts-surface');
  if (direct) return direct;
  let best: SVGSVGElement | null = null;
  let area = 0;
  container.querySelectorAll<SVGSVGElement>('svg').forEach((s) => {
    const r = s.getBoundingClientRect();
    if (r.width * r.height > area) {
      area = r.width * r.height;
      best = s;
    }
  });
  return best;
}

function appendLegend(container: Element, svg: SVGSVGElement, clone: SVGSVGElement, light: boolean): void {
  const base = svg.getBoundingClientRect();
  const items = container.querySelectorAll<HTMLElement>('.recharts-legend-item');
  if (!items.length) return;
  const g = document.createElementNS(SVG_NS, 'g');
  items.forEach((li) => {
    const icon = li.querySelector<SVGElement>('svg');
    const label = li.querySelector<HTMLElement>('.recharts-legend-item-text') ?? li;
    if (!icon) return;
    const ir = icon.getBoundingClientRect();
    let color = '#94a3b8';
    for (const el of Array.from(icon.querySelectorAll('path,line,rect,circle'))) {
      const cs = getComputedStyle(el);
      const fill = cs.fill !== 'none' ? cs.fill : '';
      const stroke = cs.stroke !== 'none' ? cs.stroke : '';
      const c = fill || stroke;
      if (c) {
        color = resolveColor(c);
        break;
      }
    }
    const lr = label.getBoundingClientRect();
    const lcs = getComputedStyle(label);
    const sw = document.createElementNS(SVG_NS, 'rect');
    sw.setAttribute('x', String(ir.left - base.left));
    sw.setAttribute('y', String(ir.top - base.top + ir.height / 2 - 4));
    sw.setAttribute('width', '10');
    sw.setAttribute('height', '8');
    sw.setAttribute('rx', '1.5');
    sw.setAttribute('style', `fill:${color};stroke:none;`);
    const t = document.createElementNS(SVG_NS, 'text');
    t.setAttribute('x', String(lr.left - base.left));
    t.setAttribute('y', String(lr.top - base.top + lr.height / 2));
    t.setAttribute(
      'style',
      `fill:${light ? '#334155' : '#cbd5e1'};stroke:none;font-family:${lcs.fontFamily};font-size:${lcs.fontSize};dominant-baseline:central;`,
    );
    t.textContent = (label.textContent ?? '').trim();
    g.append(sw, t);
  });
  clone.appendChild(g);
}

export function buildStandaloneSvg(
  svgEl: SVGSVGElement,
  opts: { background?: ExportBackground; container?: Element } = {},
): StandaloneSvg {
  const background = opts.background ?? 'white';
  const rect = svgEl.getBoundingClientRect();
  const width = Math.round(rect.width * 100) / 100;
  const height = Math.round(rect.height * 100) / 100;
  if (!width || !height) throw new ExportError('INPUT', 'La figura no tiene tamaño visible; no se puede exportar.');

  const clone = svgEl.cloneNode(true) as SVGSVGElement;
  inlineStyles(svgEl, clone);
  clone.removeAttribute('class');
  clone.removeAttribute('tabindex');
  clone.setAttribute('xmlns', SVG_NS);
  clone.setAttribute('xmlns:xlink', 'http://www.w3.org/1999/xlink');
  clone.setAttribute('width', String(width));
  clone.setAttribute('height', String(height));
  clone.setAttribute('viewBox', `0 0 ${width} ${height}`);

  // Grid lines are tuned for the dark theme; soften them on light backgrounds.
  if (background === 'white') {
    clone.querySelectorAll('.recharts-cartesian-grid line').forEach((l) => {
      const st = l.getAttribute('style') ?? '';
      l.setAttribute('style', st.replace(/stroke:[^;]+;/, 'stroke:#cbd5e1;'));
    });
  }
  if (opts.container) appendLegend(opts.container, svgEl, clone, background === 'white');

  if (background !== 'transparent') {
    const bg = document.createElementNS(SVG_NS, 'rect');
    bg.setAttribute('x', '0');
    bg.setAttribute('y', '0');
    bg.setAttribute('width', String(width));
    bg.setAttribute('height', String(height));
    bg.setAttribute('style', `fill:${BG_COLORS[background]};stroke:none;`);
    clone.insertBefore(bg, clone.firstChild);
  }
  return { svg: new XMLSerializer().serializeToString(clone), width, height, node: clone };
}

function svgBlob(svg: string): Blob {
  return new Blob(['<?xml version="1.0" encoding="UTF-8"?>\n', svg], { type: 'image/svg+xml;charset=utf-8' });
}

export interface ChartExportOptions {
  filename: string;
  background?: ExportBackground;
  /** Container holding the chart (used to compose the HTML legend). */
  container?: Element;
}

export function exportSvg(svgEl: SVGSVGElement, opts: ChartExportOptions): void {
  const { svg } = buildStandaloneSvg(svgEl, opts);
  downloadBlob(svgBlob(svg), opts.filename);
}

/* ------------------------------------------------------------------ */
/* PNG                                                                 */
/* ------------------------------------------------------------------ */

function assertEstimate(widthCm: number, dpi: number, aspect: number): PngEstimate {
  const est = estimatePng(widthCm, dpi, aspect);
  if (!est.ok) throw new ExportError('LIMIT', est.reason ?? 'Dimensiones no válidas.');
  return est;
}

function canvasToPngBlob(canvas: HTMLCanvasElement, dpi: number): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(async (blob) => {
      if (!blob) {
        reject(new ExportError('LIMIT', 'El navegador no pudo crear la imagen (límite de memoria del canvas). Reduzca el ancho o el DPI.'));
        return;
      }
      try {
        const bytes = new Uint8Array(await blob.arrayBuffer());
        resolve(new Blob([setPngDpi(bytes, dpi) as BlobPart], { type: 'image/png' }));
      } catch (e) {
        reject(e);
      }
    }, 'image/png');
  });
}

function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new ExportError('RENDER', 'No se pudo rasterizar la figura.'));
    img.src = url;
  });
}

export interface RasterOptions extends ChartExportOptions {
  widthCm: number;
  dpi?: number;
}

export async function exportPng(svgEl: SVGSVGElement, opts: RasterOptions): Promise<{ w: number; h: number }> {
  const dpi = opts.dpi ?? 600;
  const { svg, width, height } = buildStandaloneSvg(svgEl, opts);
  const { w, h } = assertEstimate(opts.widthCm, dpi, height / width);
  const url = URL.createObjectURL(svgBlob(svg));
  try {
    const img = await loadImage(url);
    const canvas = document.createElement('canvas');
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new ExportError('LIMIT', 'El navegador no pudo crear un canvas de ese tamaño. Reduzca el ancho o el DPI.');
    ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(img, 0, 0, w, h);
    downloadBlob(await canvasToPngBlob(canvas, dpi), opts.filename);
    return { w, h };
  } finally {
    URL.revokeObjectURL(url);
  }
}

/* ------------------------------------------------------------------ */
/* PDF (vector)                                                        */
/* ------------------------------------------------------------------ */

export async function exportPdf(svgEl: SVGSVGElement, opts: ChartExportOptions & { widthCm: number }): Promise<void> {
  if (!Number.isFinite(opts.widthCm) || opts.widthCm <= 0) throw new ExportError('INPUT', 'Ingrese un ancho válido en cm.');
  const [{ jsPDF }, { svg2pdf }] = await Promise.all([import('jspdf'), import('svg2pdf.js')]);
  const { node, width, height } = buildStandaloneSvg(svgEl, opts);
  const wMm = opts.widthCm * 10;
  const hMm = (wMm * height) / width;
  const doc = new jsPDF({ unit: 'mm', format: [wMm, hMm], orientation: wMm > hMm ? 'landscape' : 'portrait' });

  // svg2pdf reads layout from the DOM, so the clone must be attached while converting.
  const host = document.createElement('div');
  host.style.cssText = 'position:fixed;left:-100000px;top:0;pointer-events:none;';
  host.appendChild(node);
  document.body.appendChild(host);
  try {
    await svg2pdf(node, doc, { x: 0, y: 0, width: wMm, height: hMm });
  } finally {
    host.remove();
  }
  downloadBlob(doc.output('blob'), opts.filename);
}

/* ------------------------------------------------------------------ */
/* Tables                                                              */
/* ------------------------------------------------------------------ */

const cellText = (el: Element) => (el.textContent ?? '').replace(/\s+/g, ' ').trim();

export function tableToRows(tableEl: HTMLTableElement): string[][] {
  const rows: string[][] = [];
  tableEl.querySelectorAll('tr').forEach((tr) => {
    const cells = Array.from(tr.children).filter((c) => c.tagName === 'TH' || c.tagName === 'TD');
    if (cells.length) rows.push(cells.map(cellText));
  });
  return rows;
}

export function findTable(container: Element): HTMLTableElement | null {
  return container instanceof HTMLTableElement ? container : container.querySelector('table');
}

export function exportCsv(rows: string[][], filename: string): void {
  downloadBlob(new Blob([rowsToCsv(rows)], { type: 'text/csv;charset=utf-8' }), filename);
}

export async function exportXlsx(rows: string[][], filename: string, sheetName = 'Datos'): Promise<void> {
  const ExcelJS = (await import('exceljs')).default;
  const wb = new ExcelJS.Workbook();
  const ws = wb.addWorksheet(sheetName.replace(/[\\/?*[\]:]/g, ' ').slice(0, 31) || 'Datos');
  rows.forEach((r, i) => ws.addRow(i === 0 ? r : r.map(parseCellValue)));
  if (rows.length) ws.getRow(1).font = { bold: true };
  ws.columns.forEach((col, ci) => {
    const max = rows.reduce((m, r) => Math.max(m, (r[ci] ?? '').length), 8);
    col.width = Math.min(60, max + 2);
  });
  const buf = await wb.xlsx.writeBuffer();
  downloadBlob(
    new Blob([buf as ArrayBuffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }),
    filename,
  );
}

export async function copyTableToClipboard(tableEl: HTMLTableElement): Promise<void> {
  const rows = tableToRows(tableEl);
  const html = rowsToHtml(rows);
  const text = rows.map((r) => r.join('\t')).join('\n');
  if (typeof ClipboardItem !== 'undefined' && navigator.clipboard?.write) {
    await navigator.clipboard.write([
      new ClipboardItem({
        'text/html': new Blob([html], { type: 'text/html' }),
        'text/plain': new Blob([text], { type: 'text/plain' }),
      }),
    ]);
  } else if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
  } else {
    throw new ExportError('UNSUPPORTED', 'El portapapeles no está disponible en este navegador.');
  }
}

export async function exportTablePng(
  tableEl: HTMLTableElement,
  opts: { widthCm: number; dpi?: number; filename: string; background?: ExportBackground },
): Promise<{ w: number; h: number }> {
  const dpi = opts.dpi ?? 600;
  const cssW = tableEl.offsetWidth;
  const cssH = tableEl.offsetHeight;
  if (!cssW || !cssH) throw new ExportError('INPUT', 'La tabla no tiene tamaño visible; no se puede exportar.');
  const { w, h } = assertEstimate(opts.widthCm, dpi, cssH / cssW);
  const { domToCanvas } = await import('modern-screenshot');
  const bg = opts.background ?? 'dark';
  const canvas = await domToCanvas(tableEl, {
    scale: w / cssW,
    backgroundColor: bg === 'transparent' ? null : BG_COLORS[bg],
    font: false,
  });
  downloadBlob(await canvasToPngBlob(canvas, dpi), opts.filename);
  return { w: canvas.width || w, h: canvas.height || h };
}

/* ------------------------------------------------------------------ */
/* Three.js                                                            */
/* ------------------------------------------------------------------ */

interface ThreeRendererLike {
  domElement: HTMLCanvasElement;
  getSize(target: { width: number; height: number; set(x: number, y: number): unknown }): unknown;
  getPixelRatio(): number;
  setPixelRatio(v: number): void;
  setSize(w: number, h: number, updateStyle?: boolean): void;
  render(scene: unknown, camera: unknown): void;
  capabilities?: { maxTextureSize?: number };
}
interface CameraLike {
  aspect: number;
  updateProjectionMatrix(): void;
}

export interface ThreeExportResult {
  w: number;
  h: number;
  clamped: boolean;
}

export async function exportThreeCanvas(
  renderer: ThreeRendererLike,
  scene: unknown,
  camera: CameraLike,
  opts: { widthCm: number; dpi?: number; filename: string },
): Promise<ThreeExportResult> {
  const dpi = opts.dpi ?? 600;
  const canvas = renderer.domElement;
  const cssW = canvas.clientWidth || canvas.width;
  const cssH = canvas.clientHeight || canvas.height;
  const aspect = cssH / cssW;
  const maxSide = Math.min(MAX_CANVAS_SIDE, renderer.capabilities?.maxTextureSize ?? MAX_CANVAS_SIDE);

  let w = Math.round((opts.widthCm / CM_PER_INCH) * dpi);
  let h = Math.round(w * aspect);
  if (!(w > 0) || !(h > 0)) throw new ExportError('INPUT', 'Ingrese un ancho válido en cm.');
  let clamped = false;
  const k = Math.min(1, maxSide / Math.max(w, h), Math.sqrt(MAX_CANVAS_PIXELS / (w * h)));
  if (k < 1) {
    w = Math.floor(w * k);
    h = Math.floor(h * k);
    clamped = true;
  }

  const size = { width: 0, height: 0, set(x: number, y: number) { this.width = x; this.height = y; } };
  renderer.getSize(size);
  const prevRatio = renderer.getPixelRatio();
  const prevAspect = camera.aspect;
  try {
    renderer.setPixelRatio(1);
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.render(scene, camera);
    // toBlob snapshots the bitmap synchronously, before the buffer is cleared.
    const pending = canvasToPngBlob(canvas, dpi);
    renderer.setPixelRatio(prevRatio);
    renderer.setSize(size.width, size.height, false);
    camera.aspect = prevAspect;
    camera.updateProjectionMatrix();
    renderer.render(scene, camera);
    downloadBlob(await pending, opts.filename);
  } finally {
    renderer.setPixelRatio(prevRatio);
    renderer.setSize(size.width, size.height, false);
    camera.aspect = prevAspect;
    camera.updateProjectionMatrix();
  }
  return { w, h, clamped };
}
