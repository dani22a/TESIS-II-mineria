/**
 * MineTwin AI - Industrial Command Center Header HUD
 */

import React from 'react';
import {
  Activity,
  AlertTriangle,
  Award,
  Clock,
  Cpu,
  Flame,
  Gauge,
  Layers,
  Pause,
  Play,
  RotateCcw,
  Sparkles,
  TrendingUp,
  Zap,
} from 'lucide-react';
import { DigitalTwinState, DispatchStrategy } from '../types/mining';

interface CommandCenterHeaderProps {
  state: DigitalTwinState;
  onTogglePlay: () => void;
  onChangeSpeed: (speed: number) => void;
  onChangeStrategy: (strategy: DispatchStrategy) => void;
  onOpenAlerts: () => void;
  onOpenRecommendations: () => void;
  onOpenTimeMachine: () => void;
  onResetSimulation: () => void;
}

export const CommandCenterHeader: React.FC<CommandCenterHeaderProps> = ({
  state,
  onTogglePlay,
  onChangeSpeed,
  onChangeStrategy,
  onOpenAlerts,
  onOpenRecommendations,
  onOpenTimeMachine,
  onResetSimulation,
}) => {
  const totalProductionTph = Math.round(state.shovels.reduce((acc, s) => acc + s.productivityTph, 0));
  const avgCycle = Math.round((state.trucks.reduce((acc, t) => acc + t.cycleTimeMinutes, 0) / state.trucks.length) * 10) / 10;
  const activeAlertsCount = state.alerts.filter((a) => !a.acknowledged).length;
  const pendingRecsCount = state.recommendations.filter((r) => r.status === 'PENDING_REVIEW').length;

  return (
    <header className="bg-slate-950/95 border-b border-slate-800/80 px-4 py-2.5 flex flex-col xl:flex-row xl:items-center xl:justify-between gap-3 select-none backdrop-blur-md z-30">
      {/* Brand & Platform Identity */}
      <div className="flex items-center gap-3">
        <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-amber-700 shadow-lg shadow-amber-500/20 text-slate-950 font-black text-xl tracking-tighter">
          MT
          <span className="absolute -bottom-1 -right-1 flex h-3.5 w-3.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-emerald-500 border-2 border-slate-950"></span>
          </span>
        </div>

        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-extrabold tracking-tight text-white flex items-center gap-1.5">
              MineTwin <span className="text-amber-400">AI</span>
            </h1>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wide bg-amber-500/10 text-amber-300 border border-amber-500/30">
              DIGITAL TWIN 3D
            </span>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              {state.timeMode === 'LIVE' ? 'TIEMPO REAL OT/SCADA' : state.timeMode}
            </span>
          </div>
          <p className="text-[11px] text-slate-400 hidden sm:block">
            Gemelo Operacional Drill-Blast-Load-Haul & Optimización Causal Mine-to-Mill
          </p>
        </div>
      </div>

      {/* Industrial Key Performance Indicators (HUD Strip) */}
      <div className="flex items-center gap-2 sm:gap-4 overflow-x-auto py-1 scrollbar-none">
        {/* Total Production */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-lg px-3 py-1.5 min-w-[125px] flex flex-col justify-center">
          <div className="flex items-center justify-between text-[10px] font-medium text-slate-400 uppercase tracking-wider">
            <span>Producción Mina</span>
            <TrendingUp className="w-3.5 h-3.5 text-amber-400" />
          </div>
          <div className="flex items-baseline gap-1 mt-0.5">
            <span className="text-base font-bold font-mono text-white tracking-tight">
              {totalProductionTph.toLocaleString()}
            </span>
            <span className="text-[10px] font-mono text-slate-400">t/h</span>
          </div>
        </div>

        {/* Avg Cycle Time */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-lg px-3 py-1.5 min-w-[115px] flex flex-col justify-center">
          <div className="flex items-center justify-between text-[10px] font-medium text-slate-400 uppercase tracking-wider">
            <span>Ciclo Promedio</span>
            <Clock className="w-3.5 h-3.5 text-sky-400" />
          </div>
          <div className="flex items-baseline gap-1 mt-0.5">
            <span className="text-base font-bold font-mono text-white tracking-tight">{avgCycle}</span>
            <span className="text-[10px] font-mono text-slate-400">min</span>
          </div>
        </div>

        {/* Crusher Feed */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-lg px-3 py-1.5 min-w-[120px] flex flex-col justify-center">
          <div className="flex items-center justify-between text-[10px] font-medium text-slate-400 uppercase tracking-wider">
            <span>Chancado Primario</span>
            <Gauge className="w-3.5 h-3.5 text-blue-400" />
          </div>
          <div className="flex items-baseline gap-1 mt-0.5">
            <span className="text-base font-bold font-mono text-white tracking-tight">
              {state.crusher.throughputTph.toLocaleString()}
            </span>
            <span className="text-[10px] font-mono text-slate-400">t/h</span>
          </div>
        </div>

        {/* SAG Mill Throughput */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-lg px-3 py-1.5 min-w-[125px] flex flex-col justify-center">
          <div className="flex items-center justify-between text-[10px] font-medium text-slate-400 uppercase tracking-wider">
            <span>Molienda SAG</span>
            <Cpu className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="flex items-baseline gap-1 mt-0.5">
            <span className="text-base font-bold font-mono text-white tracking-tight">
              {state.mill.sagMillThroughputTph.toLocaleString()}
            </span>
            <span className="text-[10px] font-mono text-slate-400">t/h</span>
          </div>
        </div>

        {/* Specific Energy */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-lg px-3 py-1.5 min-w-[110px] flex flex-col justify-center">
          <div className="flex items-center justify-between text-[10px] font-medium text-slate-400 uppercase tracking-wider">
            <span>Energía Específica</span>
            <Zap className="w-3.5 h-3.5 text-purple-400" />
          </div>
          <div className="flex items-baseline gap-1 mt-0.5">
            <span className="text-base font-bold font-mono text-white tracking-tight">
              {state.mill.specificEnergyKwhPerTon}
            </span>
            <span className="text-[10px] font-mono text-slate-400">kWh/t</span>
          </div>
        </div>
      </div>

      {/* Control Actions & Engine Status */}
      <div className="flex items-center gap-2 flex-wrap">
        {/* Active Dispatch Selector */}
        <div className="flex items-center gap-1 bg-slate-900 border border-slate-800 rounded-lg p-1">
          <Award className="w-3.5 h-3.5 text-amber-400 ml-1.5" />
          <select
            value={state.activeDispatchStrategy}
            onChange={(e) => onChangeStrategy(e.target.value as DispatchStrategy)}
            aria-label="Estrategia de Despacho"
            className="bg-transparent text-xs text-slate-200 font-medium py-1 px-1.5 rounded focus:outline-none focus:ring-1 focus:ring-amber-500 cursor-pointer"
          >
            <option value="DRL_MULTI_OBJECTIVE" className="bg-slate-900 text-amber-400">
              🤖 DRL MAPPO Agent (Óptimo)
            </option>
            <option value="SHORTEST_QUEUE" className="bg-slate-900 text-slate-200">
              ⏱️ Cola Mínima (Heurística)
            </option>
            <option value="MIN_CYCLE_TIME" className="bg-slate-900 text-slate-200">
              ⚡ Menor Ciclo
            </option>
            <option value="CRUSHER_PRIORITY" className="bg-slate-900 text-slate-200">
              🏭 Prioridad Chancador
            </option>
            <option value="PRODUCTION_BALANCING" className="bg-slate-900 text-slate-200">
              ⚖️ Balanceo de Producción
            </option>
            <option value="STATIC_ASSIGNMENT" className="bg-slate-900 text-slate-400">
              🔒 Despacho Estático
            </option>
          </select>
        </div>

        {/* Simulation Speed Controls */}
        <div className="flex items-center bg-slate-900 border border-slate-800 rounded-lg p-0.5">
          <button
            onClick={onTogglePlay}
            className={`p-1.5 rounded-md transition ${
              state.isPaused ? 'bg-amber-500 text-slate-950 font-bold' : 'hover:bg-slate-800 text-slate-200'
            }`}
            title={state.isPaused ? 'Reanudar Simulación' : 'Pausar Simulación'}
          >
            {state.isPaused ? <Play className="w-4 h-4 fill-current" /> : <Pause className="w-4 h-4" />}
          </button>

          {[1, 5, 10, 30].map((spd) => (
            <button
              key={spd}
              onClick={() => onChangeSpeed(spd)}
              className={`px-2 py-1 text-[11px] font-mono rounded transition ${
                state.simSpeedMultiplier === spd
                  ? 'bg-amber-500/20 text-amber-300 font-bold border border-amber-500/40'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {spd}x
            </button>
          ))}

          <button
            onClick={onResetSimulation}
            className="p-1.5 text-slate-400 hover:text-slate-200 transition"
            title="Reiniciar a Estado Inicial Calibrado"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Time Machine Quick Button */}
        <button
          onClick={onOpenTimeMachine}
          className="flex items-center gap-1.5 px-2.5 py-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 text-slate-300 rounded-lg text-xs font-medium transition"
        >
          <Clock className="w-3.5 h-3.5 text-sky-400" />
          <span className="hidden md:inline">Time Machine</span>
        </button>

        {/* AI Recommendations Action Button */}
        <button
          onClick={onOpenRecommendations}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition border ${
            pendingRecsCount > 0
              ? 'bg-gradient-to-r from-amber-500/20 to-amber-600/20 border-amber-500/50 text-amber-300 animate-pulse'
              : 'bg-slate-900 border-slate-800 text-slate-300 hover:bg-slate-800'
          }`}
        >
          <Sparkles className="w-3.5 h-3.5 text-amber-400" />
          <span>IA Recs</span>
          {pendingRecsCount > 0 && (
            <span className="px-1.5 py-0.2 rounded-full bg-amber-500 text-slate-950 font-bold text-[10px]">
              {pendingRecsCount}
            </span>
          )}
        </button>

        {/* Alerts Notification Button */}
        <button
          onClick={onOpenAlerts}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition border ${
            activeAlertsCount > 0
              ? 'bg-rose-500/10 border-rose-500/40 text-rose-300'
              : 'bg-slate-900 border-slate-800 text-slate-300 hover:bg-slate-800'
          }`}
        >
          <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
          <span>Alertas</span>
          {activeAlertsCount > 0 && (
            <span className="px-1.5 py-0.2 rounded-full bg-rose-500 text-white font-bold text-[10px]">
              {activeAlertsCount}
            </span>
          )}
        </button>
      </div>
    </header>
  );
};
