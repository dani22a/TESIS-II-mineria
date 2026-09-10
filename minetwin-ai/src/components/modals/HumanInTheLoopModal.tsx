/**
 * MineTwin AI - Human-in-the-Loop & Explainable AI (XAI) Recommendation Modal
 */

import React from 'react';
import {
  Activity,
  AlertCircle,
  Award,
  CheckCircle,
  CheckCircle2,
  Cpu,
  Info,
  Layers,
  Sparkles,
  TrendingUp,
  X,
  XCircle,
  Zap,
} from 'lucide-react';
import { DigitalTwinState, DRLRecommendation } from '../../types/mining';

interface HumanInTheLoopModalProps {
  isOpen: boolean;
  onClose: () => void;
  state: DigitalTwinState;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
}

export const HumanInTheLoopModal: React.FC<HumanInTheLoopModalProps> = ({
  isOpen,
  onClose,
  state,
  onApprove,
  onReject,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200 select-none">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-3xl w-full p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-amber-500/20 text-amber-400 rounded-xl">
              <Sparkles className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">
                Centro de Recomendaciones Human-in-the-Loop (XAI)
              </h2>
              <p className="text-xs text-slate-400">
                Supervisión humana de decisiones autónomas del agente MAPPO con explicabilidad causal completa
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Recommendations List */}
        <div className="space-y-4">
          {state.recommendations.map((rec) => (
            <div
              key={rec.id}
              className={`p-4 rounded-xl border text-xs space-y-3 transition ${
                rec.status === 'APPROVED'
                  ? 'bg-emerald-500/10 border-emerald-500/40'
                  : rec.status === 'REJECTED'
                  ? 'bg-rose-500/10 border-rose-500/40'
                  : 'bg-slate-950 border-amber-500/50 shadow-lg'
              }`}
            >
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-white text-sm">{rec.title}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/30 font-bold">
                    {Math.round(rec.confidence * 100)}% Confianza AI
                  </span>
                  <span
                    className={`font-mono text-[10px] font-bold px-2 py-0.5 rounded ${
                      rec.status === 'APPROVED'
                        ? 'bg-emerald-500/20 text-emerald-300'
                        : rec.status === 'REJECTED'
                        ? 'bg-rose-500/20 text-rose-300'
                        : 'bg-amber-500/20 text-amber-300'
                    }`}
                  >
                    {rec.status}
                  </span>
                </div>
              </div>

              {/* Explainability What / Why */}
              <div className="space-y-1.5">
                <div className="bg-slate-900/80 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-amber-400 font-bold uppercase text-[10px]">Acción Propuesta: </span>
                  <span className="text-slate-200 font-medium">{rec.what}</span>
                </div>

                <div className="bg-slate-900/80 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-sky-400 font-bold uppercase text-[10px]">Justificación Causal: </span>
                  <span className="text-slate-300">{rec.why}</span>
                </div>
              </div>

              {/* Expected Impact */}
              <div className="grid grid-cols-3 gap-2 font-mono bg-slate-900 p-2.5 rounded-xl border border-slate-800 text-center">
                <div>
                  <div className="text-[10px] text-slate-400 font-sans">Delta Producción</div>
                  <div className="font-bold text-emerald-400 text-sm mt-0.5">+{rec.expectedImpact.productionDeltaTph} t/h</div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-400 font-sans">Delta Tiempo Ciclo</div>
                  <div className="font-bold text-emerald-400 text-sm mt-0.5">{rec.expectedImpact.cycleTimeDeltaMin} min</div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-400 font-sans">Ahorro Económico</div>
                  <div className="font-bold text-amber-400 text-sm mt-0.5">${rec.expectedImpact.costSavingsUsd} /turno</div>
                </div>
              </div>

              {/* Actions for Pending */}
              {rec.status === 'PENDING_REVIEW' && (
                <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
                  <button
                    onClick={() => onReject(rec.id)}
                    className="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl font-medium transition flex items-center gap-1.5 text-xs"
                  >
                    <XCircle className="w-4 h-4 text-rose-400" />
                    <span>Rechazar Recomendación</span>
                  </button>

                  <button
                    onClick={() => onApprove(rec.id)}
                    className="px-4 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded-xl transition flex items-center gap-1.5 text-xs shadow-lg shadow-amber-500/20"
                  >
                    <CheckCircle className="w-4 h-4" />
                    <span>Aprobar & Despachar a Flota</span>
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="flex justify-end pt-2">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl font-medium transition text-xs"
          >
            Cerrar Ventana
          </button>
        </div>
      </div>
    </div>
  );
};
