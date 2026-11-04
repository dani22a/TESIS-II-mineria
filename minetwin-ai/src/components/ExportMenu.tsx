/**
 * MineTwin AI - Reusable export dropdown for charts, tables and the 3D scene.
 * Render it outside the target element so it never appears in the exported output.
 */

import React, { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Download, X } from 'lucide-react';
import {
  buildFilename,
  copyTableToClipboard,
  estimatePng,
  ExportBackground,
  ExportError,
  exportCsv,
  exportPdf,
  exportPng,
  exportSvg,
  exportTablePng,
  exportThreeCanvas,
  exportXlsx,
  findChartSvg,
  findTable,
  tableToRows,
} from '../services/exportService';

export interface ThreeExportContext {
  renderer: Parameters<typeof exportThreeCanvas>[0];
  scene: unknown;
  camera: Parameters<typeof exportThreeCanvas>[2];
}

interface ExportMenuProps {
  kind: 'chart' | 'table' | 'three';
  /** Container element holding the chart or table (not needed for `three`). */
  targetRef?: React.RefObject<HTMLElement | null>;
  /** Returns renderer/scene/camera for `three`. */
  getThree?: () => ThreeExportContext | null;
  title: string;
  className?: string;
}

type RasterFormat = 'png' | 'pdf';

const BG_LABELS: Record<ExportBackground, string> = {
  white: 'Blanco',
  dark: 'Oscuro (como la app)',
  transparent: 'Transparente',
};

export const ExportMenu: React.FC<ExportMenuProps> = ({ kind, targetRef, getThree, title, className }) => {
  const [open, setOpen] = useState(false);
  const [dialog, setDialog] = useState<RasterFormat | null>(null);
  const [notice, setNotice] = useState<{ text: string; error: boolean } | null>(null);
  const [busy, setBusy] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const menuId = useId();

  const [widthCm, setWidthCm] = useState('16');
  const [dpi, setDpi] = useState('600');
  const [background, setBackground] = useState<ExportBackground>(kind === 'chart' ? 'white' : 'dark');
  const [dialogError, setDialogError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  useEffect(() => {
    if (!notice) return;
    const t = setTimeout(() => setNotice(null), 4000);
    return () => clearTimeout(t);
  }, [notice]);

  const aspect = useCallback((): number => {
    if (kind === 'three') {
      const c = getThree?.()?.renderer.domElement;
      return c && c.clientWidth ? c.clientHeight / c.clientWidth : 0;
    }
    const root = targetRef?.current;
    if (!root) return 0;
    const el: Element | null = kind === 'chart' ? findChartSvg(root) : findTable(root);
    const r = el?.getBoundingClientRect();
    return r && r.width ? r.height / r.width : 0;
  }, [kind, targetRef, getThree]);

  const estimate = useMemo(
    () => (dialog ? estimatePng(parseFloat(widthCm), parseFloat(dpi), aspect()) : null),
    // aspect() reads layout at open time; recomputed whenever inputs change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [dialog, widthCm, dpi, aspect],
  );

  const report = (text: string, error = false) => setNotice({ text, error });
  const fail = (e: unknown) => report(e instanceof Error ? e.message : 'No se pudo exportar.', true);

  const run = async (fn: () => Promise<string | void> | string | void) => {
    setBusy(true);
    try {
      const msg = await fn();
      if (msg) report(msg);
    } catch (e) {
      fail(e);
    } finally {
      setBusy(false);
    }
  };

  const getTarget = (): { svg?: SVGSVGElement; table?: HTMLTableElement; root: HTMLElement } => {
    const root = targetRef?.current;
    if (!root) throw new ExportError('INPUT', 'No se encontró el elemento a exportar.');
    if (kind === 'chart') {
      const svg = findChartSvg(root);
      if (!svg) throw new ExportError('INPUT', 'No se encontró la figura (aún cargando).');
      return { svg, root };
    }
    const table = findTable(root);
    if (!table) throw new ExportError('INPUT', 'No se encontró la tabla.');
    return { table, root };
  };

  const pick = (action: string) => {
    setOpen(false);
    if (action === 'png' || action === 'pdf') {
      setDialogError(null);
      setDialog(action);
      return;
    }
    void run(async () => {
      if (action === 'svg') {
        const { svg, root } = getTarget();
        exportSvg(svg!, { filename: buildFilename(title, 'svg'), container: root, background: 'white' });
        return 'SVG descargado';
      }
      const { table } = getTarget();
      if (action === 'copy') {
        await copyTableToClipboard(table!);
        return 'Tabla copiada';
      }
      const rows = tableToRows(table!);
      if (action === 'csv') {
        exportCsv(rows, buildFilename(title, 'csv'));
        return 'CSV descargado';
      }
      if (action === 'xlsx') {
        await exportXlsx(rows, buildFilename(title, 'xlsx'), title);
        return 'XLSX descargado';
      }
    });
  };

  const download = async () => {
    if (!dialog) return;
    const wCm = parseFloat(widthCm);
    const d = parseFloat(dpi);
    setDialogError(null);
    setBusy(true);
    try {
      let msg = '';
      if (kind === 'three') {
        const ctx = getThree?.();
        if (!ctx) throw new ExportError('INPUT', 'La escena 3D aún no está lista.');
        const r = await exportThreeCanvas(ctx.renderer, ctx.scene, ctx.camera, {
          widthCm: wCm,
          dpi: d,
          filename: buildFilename(title, 'png'),
        });
        msg = `PNG ${r.w} × ${r.h} px${r.clamped ? ' (reducido al límite del navegador)' : ''}`;
      } else if (dialog === 'pdf') {
        const { svg, root } = getTarget();
        await exportPdf(svg!, { widthCm: wCm, filename: buildFilename(title, 'pdf'), container: root, background });
        msg = 'PDF descargado';
      } else if (kind === 'chart') {
        const { svg, root } = getTarget();
        const r = await exportPng(svg!, { widthCm: wCm, dpi: d, filename: buildFilename(title, 'png'), container: root, background });
        msg = `PNG ${r.w} × ${r.h} px a ${d} DPI`;
      } else {
        const { table } = getTarget();
        const r = await exportTablePng(table!, { widthCm: wCm, dpi: d, filename: buildFilename(title, 'png'), background });
        msg = `PNG ${r.w} × ${r.h} px a ${d} DPI`;
      }
      setDialog(null);
      report(msg);
    } catch (e) {
      setDialogError(e instanceof Error ? e.message : 'No se pudo exportar.');
    } finally {
      setBusy(false);
    }
  };

  const items: { id: string; label: string }[] =
    kind === 'chart'
      ? [
          { id: 'svg', label: 'SVG (vectorial)' },
          { id: 'png', label: 'PNG (alta resolución)' },
          { id: 'pdf', label: 'PDF (vectorial)' },
        ]
      : kind === 'table'
        ? [
            { id: 'csv', label: 'CSV' },
            { id: 'xlsx', label: 'XLSX (Excel)' },
            { id: 'copy', label: 'Copiar tabla' },
            { id: 'png', label: 'PNG (alta resolución)' },
          ]
        : [{ id: 'png', label: 'PNG (alta resolución)' }];

  const inputCls =
    'w-full bg-slate-950 border border-slate-700 rounded-md px-2 py-1 text-xs text-slate-200 font-mono focus:outline-none focus:border-amber-500';
  const showDpi = dialog === 'png';
  const showBackground = kind !== 'three';
  const canDownload = !busy && (dialog === 'pdf' ? parseFloat(widthCm) > 0 : estimate?.ok);

  return (
    <div ref={rootRef} className={`relative inline-block font-sans normal-case tracking-normal ${className ?? ''}`}>
      <button
        type="button"
        aria-label={`Exportar ${title}`}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        onClick={() => setOpen((v) => !v)}
        disabled={busy}
        className="inline-flex items-center gap-1 px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-md text-[10px] font-medium border border-slate-700 transition disabled:opacity-50"
      >
        <Download className="w-3 h-3" /> Exportar
      </button>

      {open && (
        <div
          id={menuId}
          role="menu"
          className="absolute right-0 top-full mt-1 z-40 min-w-[11rem] bg-slate-900 border border-slate-700 rounded-lg shadow-2xl py-1"
        >
          {items.map((it) => (
            <button
              key={it.id}
              type="button"
              role="menuitem"
              onClick={() => pick(it.id)}
              className="block w-full text-left px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800 focus:bg-slate-800 focus:outline-none"
            >
              {it.label}
            </button>
          ))}
        </div>
      )}

      {notice && (
        <div
          role="status"
          className={`absolute right-0 top-full mt-1 z-40 whitespace-nowrap px-2 py-1 rounded-md text-[10px] border shadow-xl ${
            notice.error
              ? 'bg-rose-950 border-rose-700 text-rose-200 max-w-xs whitespace-normal'
              : 'bg-slate-900 border-slate-700 text-emerald-300'
          }`}
        >
          {notice.text}
        </div>
      )}

      {dialog &&
        createPortal(
          <div
            className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 p-4"
            onMouseDown={(e) => {
              if (e.target === e.currentTarget) setDialog(null);
            }}
            onKeyDown={(e) => {
              if (e.key === 'Escape') setDialog(null);
            }}
          >
            <div
              role="dialog"
              aria-modal="true"
              aria-label={`Exportar ${title}`}
              className="w-full max-w-sm bg-slate-900 border border-slate-700 rounded-xl shadow-2xl p-4 space-y-3 text-xs text-slate-200 font-sans"
            >
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <h4 className="font-bold uppercase tracking-wider text-[11px]">
                  Exportar {dialog === 'pdf' ? 'PDF' : 'PNG'}
                </h4>
                <button
                  type="button"
                  aria-label="Cerrar"
                  onClick={() => setDialog(null)}
                  className="text-slate-400 hover:text-slate-200"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <p className="text-[11px] text-slate-400 truncate">{title}</p>

              <label className="block space-y-1">
                <span className="text-slate-400">Ancho (cm)</span>
                <input
                  autoFocus
                  type="number"
                  min={1}
                  step={0.5}
                  value={widthCm}
                  onChange={(e) => setWidthCm(e.target.value)}
                  className={inputCls}
                />
              </label>

              {showDpi && (
                <label className="block space-y-1">
                  <span className="text-slate-400">DPI</span>
                  <input type="number" min={72} step={50} value={dpi} onChange={(e) => setDpi(e.target.value)} className={inputCls} />
                </label>
              )}

              {showBackground && (
                <label className="block space-y-1">
                  <span className="text-slate-400">Fondo</span>
                  <select value={background} onChange={(e) => setBackground(e.target.value as ExportBackground)} className={inputCls}>
                    {(Object.keys(BG_LABELS) as ExportBackground[]).map((k) => (
                      <option key={k} value={k}>
                        {BG_LABELS[k]}
                      </option>
                    ))}
                  </select>
                </label>
              )}

              {showDpi && estimate && (
                <div className="font-mono text-[11px] text-slate-300" aria-live="polite">
                  Resultado: {estimate.w} × {estimate.h} px
                </div>
              )}
              {showDpi && estimate && !estimate.ok && (
                <div role="alert" className="text-[11px] text-rose-300">
                  {estimate.reason}
                </div>
              )}
              {dialogError && (
                <div role="alert" className="text-[11px] text-rose-300">
                  {dialogError}
                </div>
              )}

              <div className="flex justify-end gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => setDialog(null)}
                  className="px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  onClick={() => void download()}
                  disabled={!canDownload}
                  className="px-3 py-1.5 rounded-md bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {busy ? 'Generando...' : 'Descargar'}
                </button>
              </div>
            </div>
          </div>,
          document.body,
        )}
    </div>
  );
};
