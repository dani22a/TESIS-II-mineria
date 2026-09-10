/**
 * MineTwin AI - DRL Policy Optimizer & Multi-Objective Decision Engine
 */

import React, { useState } from 'react';
import {
  Activity,
  AlertCircle,
  Award,
  CheckCircle,
  CheckCircle2,
  Clock,
  Compass,
  Cpu,
  Flame,
  Info,
  Layers,
  RotateCcw,
  ShieldAlert,
  Sliders,
  Sparkles,
  TrendingUp,
  XCircle,
  Zap,
} from 'lucide-react';
import {
  DigitalTwinState,
  DRLRecommendation,
  DRLRewardWeights,
} from '../../types/mining';
import {
  computePolicyComparisons,
  CURRICULUM_STAGES,
} from '../../services/drlEngine';

interface AiOptimizerViewProps {
  state: DigitalTwinState;
  onUpdateRewardWeights: (newWeights: DRLRewardWeights) => void;
  onApproveRecommendation: (id: string) => void;
  onRejectRecommendation: (id: string) => void;
}

export const AiOptimizerView: React.FC<AiOptimizerViewProps> = ({
  state,
  onUpdateRewardWeights,
  onApproveRecommendation,
  onRejectRecommendation,
}) => {
  const [weights, setWeights] = useState<DRLRewardWeights>({ ...state.rewardWeights });
  const policyComparisons = computePolicyComparisons(state);

  const handleWeightChange = (key: keyof DRLRewardWeights, val: number) => {
    const updated = { ...weights, [key]: val };
    setWeights(updated);
    onUpdateRewardWeights(updated);
  };

  return (
    <div className="w-full h-full flex flex-col p-4 gap-4 overflow-y-auto bg-slate-950 text-slate-100 select-none">
      {/* Title Header */}
      <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-xl shadow-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-gradient-to-br from-amber-500 to-amber-600 text-slate-950 font-bold rounded-xl shadow-lg shadow-amber-500/20">
            <Award className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white tracking-tight">
              Optimizador DRL Multi-Agente (MAPPO) & Función de Recompensa
            </h2>
            <p className="text-xs text-slate-400">
              Entrenamiento por refuerzo profundo contra simulación, evaluación Shadow-mode y control Human-in-the-loop
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-3 py-1 bg-amber-500/10 border border-amber-500/40 text-amber-300 rounded-lg text-xs font-mono font-bold flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5" /> Política Activa: MAPPO v3.2
          </span>
        </div>
      </div>

      {/* Policy Benchmark Matrix Table */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-xl space-y-3">
        <h3 className="font-bold text-slate-200 uppercase tracking-wider text-xs flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-emerald-400" /> Comparativa de Políticas Operacionales (Benchmark)
          </span>
          <span className="text-[10px] text-slate-400 font-mono font-normal">Escala normalizada 0-100</span>
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 text-slate-400 font-semibold uppercase text-[10px] tracking-wider border-b border-slate-800 font-sans">
              <tr>
                <th className="py-2.5 px-3">Estrategia / Algoritmo</th>
                <th className="py-2.5 px-3 text-right">Producción (t/h)</th>
                <th className="py-2.5 px-3 text-right">Ciclo Promedio</th>
                <th className="py-2.5 px-3 text-right">Espera en Colas</th>
                <th className="py-2.5 px-3 text-right">Molino SAG (t/h)</th>
                <th className="py-2.5 px-3 text-right">Energía (kWh/t)</th>
                <th className="py-2.5 px-3 text-right">Costo ($/t)</th>
                <th className="py-2.5 px-3 text-center">Score Pareto</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {policyComparisons.map((pol, idx) => (
                <tr
                  key={idx}
                  className={`hover:bg-slate-800/40 transition ${
                    idx === 2 ? 'bg-amber-500/10 border-l-2 border-amber-500' : ''
                  }`}
                >
                  <td className="py-2.5 px-3 font-semibold text-white font-sans">
                    <div className="font-bold text-slate-200">{pol.policyName}</div>
                    <div className="text-[10px] text-slate-400 font-normal">{pol.description}</div>
                  </td>
                  <td className="py-2.5 px-3 text-right font-bold text-amber-400">
                    {pol.productionTph.toLocaleString()}
                  </td>
                  <td className="py-2.5 px-3 text-right text-slate-200">{pol.avgCycleTimeMin} min</td>
                  <td className="py-2.5 px-3 text-right text-sky-400">{pol.avgQueueTimeMin} min</td>
                  <td className="py-2.5 px-3 text-right font-bold text-emerald-400">
                    {pol.millThroughputTph.toLocaleString()}
                  </td>
                  <td className="py-2.5 px-3 text-right text-purple-300">{pol.energyConsumptionKwhT}</td>
                  <td className="py-2.5 px-3 text-right text-slate-200">${pol.operatingCostPerTonUsd}</td>
                  <td className="py-2.5 px-3 text-center">
                    <span
                      className={`inline-block px-2.5 py-1 rounded-full font-bold text-xs ${
                        pol.overallScore >= 95
                          ? 'bg-amber-400 text-slate-950'
                          : pol.overallScore >= 75
                          ? 'bg-slate-800 text-emerald-400'
                          : 'bg-slate-800 text-slate-400'
                      }`}
                    >
                      {pol.overallScore} / 100
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Grid: Reward Function Weights Sliders (5 Cols) + Curriculum Learning Roadmap (7 Cols) */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
        {/* Left: Reward Function Weights (5 Cols) */}
        <div className="xl:col-span-5 bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-xl text-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <h3 className="font-bold text-slate-200 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
              <Sliders className="w-4 h-4 text-amber-400" /> Ponderación Función de Recompensa (DRL Reward)
            </h3>
          </div>

          <div className="space-y-3 font-sans">
            {/* w1 Production */}
            <div className="space-y-1">
              <div className="flex justify-between text-slate-300">
                <span>w1: Maximizar Producción Mina</span>
                <span className="font-mono font-bold text-amber-400">{(weights.productionWeight * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="0.05"
                max="0.60"
                step="0.05"
                value={weights.productionWeight}
                onChange={(e) => handleWeightChange('productionWeight', parseFloat(e.target.value))}
                className="w-full accent-amber-500 cursor-pointer"
              />
            </div>

            {/* w2 Mill Throughput */}
            <div className="space-y-1">
              <div className="flex justify-between text-slate-300">
                <span>w2: Maximizar Rendimiento Molino SAG</span>
                <span className="font-mono font-bold text-emerald-400">{(weights.millThroughputWeight * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="0.05"
                max="0.50"
                step="0.05"
                value={weights.millThroughputWeight}
                onChange={(e) => handleWeightChange('millThroughputWeight', parseFloat(e.target.value))}
                className="w-full accent-emerald-500 cursor-pointer"
              />
            </div>

            {/* w3 Operating Cost */}
            <div className="space-y-1">
              <div className="flex justify-between text-slate-300">
                <span>w3: Minimizar Costo Unitario ($/t)</span>
                <span className="font-mono font-bold text-sky-400">{(weights.costWeight * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="0.05"
                max="0.40"
                step="0.05"
                value={weights.costWeight}
                onChange={(e) => handleWeightChange('costWeight', parseFloat(e.target.value))}
                className="w-full accent-sky-500 cursor-pointer"
              />
            </div>

            {/* w4 Fuel Consumption */}
            <div className="space-y-1">
              <div className="flex justify-between text-slate-300">
                <span>w4: Minimizar Consumo Diésel (L/h)</span>
                <span className="font-mono font-bold text-purple-400">{(weights.fuelWeight * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="0.05"
                max="0.30"
                step="0.05"
                value={weights.fuelWeight}
                onChange={(e) => handleWeightChange('fuelWeight', parseFloat(e.target.value))}
                className="w-full accent-purple-500 cursor-pointer"
              />
            </div>

            {/* w5 Cycle Time */}
            <div className="space-y-1">
              <div className="flex justify-between text-slate-300">
                <span>w5: Minimizar Tiempo de Ciclo de Camión</span>
                <span className="font-mono font-bold text-amber-300">{(weights.cycleTimeWeight * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="0.02"
                max="0.25"
                step="0.02"
                value={weights.cycleTimeWeight}
                onChange={(e) => handleWeightChange('cycleTimeWeight', parseFloat(e.target.value))}
                className="w-full accent-amber-300 cursor-pointer"
              />
            </div>
          </div>
        </div>

        {/* Right: Curriculum Learning Progress (7 Cols) */}
        <div className="xl:col-span-7 bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-xl text-xs space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <h3 className="font-bold text-slate-200 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-sky-400" /> Fases de Curriculum Learning (Entrenamiento por Etapas)
            </h3>
            <span className="text-[10px] text-slate-400 font-mono">Simulador Gym / PPO</span>
          </div>

          <div className="space-y-2.5">
            {CURRICULUM_STAGES.map((stage) => (
              <div
                key={stage.stageNumber}
                className="bg-slate-950 p-2.5 rounded-xl border border-slate-800 space-y-1.5"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span
                      className={`w-2 h-2 rounded-full ${
                        stage.status === 'COMPLETED'
                          ? 'bg-emerald-400'
                          : stage.status === 'IN_TRAINING'
                          ? 'bg-amber-400 animate-pulse'
                          : 'bg-slate-600'
                      }`}
                    />
                    <span className="font-bold text-slate-200 text-[11px]">{stage.name}</span>
                  </div>
                  <span
                    className={`font-mono text-[10px] font-bold px-1.5 py-0.5 rounded ${
                      stage.status === 'COMPLETED'
                        ? 'bg-emerald-500/15 text-emerald-400'
                        : stage.status === 'IN_TRAINING'
                        ? 'bg-amber-500/15 text-amber-300'
                        : 'bg-slate-800 text-slate-400'
                    }`}
                  >
                    {stage.status === 'COMPLETED' ? '100% Completado' : stage.status === 'IN_TRAINING' ? 'En Entrenamiento' : 'En Cola'}
                  </span>
                </div>

                <p className="text-[10px] text-slate-400">{stage.description}</p>

                <div className="flex justify-between text-[10px] font-mono text-slate-500 pt-0.5">
                  <span>Episodios: {stage.episodesCompleted.toLocaleString()} / {stage.targetEpisodes.toLocaleString()}</span>
                  <span>Convergencia: <b className="text-slate-300">{stage.convergenceRatePercent}%</b></span>
                </div>

                <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${stage.status === 'COMPLETED' ? 'bg-emerald-500' : 'bg-amber-500'}`}
                    style={{ width: `${(stage.episodesCompleted / stage.targetEpisodes) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Human-in-the-Loop Active Recommendations Cards */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-xl space-y-3">
        <h3 className="font-bold text-slate-200 uppercase tracking-wider text-xs flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-amber-400" /> Cola de Recomendaciones de IA Pendientes (Human-in-the-Loop)
        </h3>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {state.recommendations.map((rec) => (
            <div
              key={rec.id}
              className={`p-3.5 rounded-xl border text-xs space-y-2.5 transition ${
                rec.status === 'APPROVED'
                  ? 'bg-emerald-500/10 border-emerald-500/40'
                  : rec.status === 'REJECTED'
                  ? 'bg-rose-500/10 border-rose-500/40'
                  : 'bg-slate-950 border-amber-500/50 shadow-lg shadow-amber-500/5'
              }`}
            >
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-slate-100">{rec.title}</span>
                </div>
                <span className="font-mono text-[10px] text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/30">
                  {Math.round(rec.confidence * 100)}% Confianza
                </span>
              </div>

              {/* What and Why */}
              <div className="space-y-1">
                <div>
                  <span className="font-semibold text-slate-400 text-[10px] uppercase">Qué propone: </span>
                  <span className="text-slate-200 font-medium">{rec.what}</span>
                </div>
                <div>
                  <span className="font-semibold text-slate-400 text-[10px] uppercase">Causa / Explicación: </span>
                  <span className="text-slate-300">{rec.why}</span>
                </div>
              </div>

              {/* Expected Impact Matrix */}
              <div className="grid grid-cols-3 gap-2 font-mono bg-slate-900/90 p-2 rounded-lg border border-slate-800 text-center">
                <div>
                  <div className="text-[9px] text-slate-400 font-sans">Producción</div>
                  <div className="font-bold text-emerald-400 text-xs">+{rec.expectedImpact.productionDeltaTph} t/h</div>
                </div>
                <div>
                  <div className="text-[9px] text-slate-400 font-sans">Tiempo Ciclo</div>
                  <div className="font-bold text-emerald-400 text-xs">{rec.expectedImpact.cycleTimeDeltaMin} min</div>
                </div>
                <div>
                  <div className="text-[9px] text-slate-400 font-sans">Ahorro Costo</div>
                  <div className="font-bold text-amber-400 text-xs">${rec.expectedImpact.costSavingsUsd} /turno</div>
                </div>
              </div>

              {/* Action Buttons for Operator Approval */}
              {rec.status === 'PENDING_REVIEW' && (
                <div className="flex items-center justify-end gap-2 pt-1 border-t border-slate-800">
                  <button
                    onClick={() => onRejectRecommendation(rec.id)}
                    className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg font-medium transition flex items-center gap-1 text-[11px]"
                  >
                    <XCircle className="w-3.5 h-3.5 text-rose-400" />
                    <span>Rechazar</span>
                  </button>

                  <button
                    onClick={() => onApproveRecommendation(rec.id)}
                    className="px-3.5 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded-lg transition flex items-center gap-1 text-[11px] shadow-md shadow-amber-500/20"
                  >
                    <CheckCircle className="w-3.5 h-3.5" />
                    <span>Aprobar & Despachar</span>
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
