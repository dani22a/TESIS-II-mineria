/** Run: npx tsx scripts/exportService.check.ts */
import assert from 'node:assert/strict';
import { deflateSync } from 'node:zlib';
import {
  buildFilename, crc32, estimatePng, parseCellValue, rowsToCsv, setPngDpi, slugify,
} from '../src/services/exportService';

function chunk(type: string, data: Uint8Array): Uint8Array {
  const out = new Uint8Array(12 + data.length);
  const dv = new DataView(out.buffer);
  dv.setUint32(0, data.length);
  for (let i = 0; i < 4; i++) out[4 + i] = type.charCodeAt(i);
  out.set(data, 8);
  dv.setUint32(8 + data.length, crc32(out.subarray(4, 8 + data.length)));
  return out;
}

function tinyPng(): Uint8Array {
  const ihdr = new Uint8Array(13);
  const dv = new DataView(ihdr.buffer);
  dv.setUint32(0, 1); dv.setUint32(4, 1);
  ihdr[8] = 8; ihdr[9] = 2; // 8-bit RGB
  const idat = new Uint8Array(deflateSync(Buffer.from([0, 255, 0, 0])));
  const parts = [new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]), chunk('IHDR', ihdr), chunk('IDAT', idat), chunk('IEND', new Uint8Array())];
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let o = 0;
  for (const p of parts) { out.set(p, o); o += p.length; }
  return out;
}

function parseChunks(png: Uint8Array) {
  const dv = new DataView(png.buffer, png.byteOffset, png.byteLength);
  const res: { type: string; data: Uint8Array; crcOk: boolean }[] = [];
  let pos = 8;
  while (pos < png.length) {
    const len = dv.getUint32(pos);
    const type = String.fromCharCode(...png.subarray(pos + 4, pos + 8));
    const data = png.subarray(pos + 8, pos + 8 + len);
    const crc = dv.getUint32(pos + 8 + len);
    res.push({ type, data, crcOk: crc === crc32(png.subarray(pos + 4, pos + 8 + len)) });
    pos += 12 + len;
  }
  return res;
}

// CRC32 known vector
assert.equal(crc32(new TextEncoder().encode('123456789')), 0xcbf43926);

// pHYs patching
const patched = setPngDpi(tinyPng(), 600);
const chunks = parseChunks(patched);
assert.deepEqual(chunks.map((c) => c.type), ['IHDR', 'pHYs', 'IDAT', 'IEND']);
assert.ok(chunks.every((c) => c.crcOk), 'all CRCs valid');
const phys = new DataView(chunks[1].data.buffer, chunks[1].data.byteOffset, 9);
assert.equal(phys.getUint32(0), 23622);
assert.equal(phys.getUint32(4), 23622);
assert.equal(chunks[1].data[8], 1);
// idempotent: patching again keeps a single pHYs
assert.equal(parseChunks(setPngDpi(patched, 300)).filter((c) => c.type === 'pHYs').length, 1);
assert.throws(() => setPngDpi(new Uint8Array(40), 600));

// CSV
const csv = rowsToCsv([['a,b', 'say "hi"', 'x'], ['1', 'line\nbreak', 'ñ']]);
assert.equal(csv.charCodeAt(0), 0xfeff);
assert.equal(csv, '﻿"a,b","say ""hi""","x"\r\n"1","line\nbreak","ñ"\r\n');

// estimatePng
const e = estimatePng(16, 600, 0.625);
assert.deepEqual([e.w, e.h, e.ok], [3780, 2363, true]);
assert.equal(estimatePng(100, 600, 1).ok, false); // 23622 px side
assert.equal(estimatePng(60, 600, 1).ok, false); // 14173 px side but 200 Mpx
assert.equal(estimatePng(0, 600, 1).ok, false);
assert.match(estimatePng(100, 600, 1).reason ?? '', /px/);

// misc
assert.equal(parseCellValue('12.5'), 12.5);
assert.equal(parseCellValue('12 t'), '12 t');
assert.equal(slugify('Descomposición de Tiempos de Ciclo'), 'descomposicion-de-tiempos-de-ciclo');
assert.equal(buildFilename('Gráfico A', 'png', new Date(2026, 0, 5)), 'grafico-a-20260105.png');

console.log('exportService checks passed');
