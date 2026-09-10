/**
 * MineTwin AI - Scenario Lab & What-If Monte Carlo Simulation
 */

import React, { useState } from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  CheckCircle2,
  Copy,
  Flame,
  Layers,
  Play,
  RotateCcw,
  Sliders,
  TrendingDown,
  TrendingUp,
  Truck,
  Zap,
} from 'lucide-react';
import { DigitalTwinState, DispatchStrategy, ScenarioSimulationResult } from '../../types/mining';
import { runWhatIfSimulation } from '../../services/scenarioEngine';

interface ScenarioLabViewProps {
  state: DigitalTwinState;
}

export const ScenarioLabView: React.FC<ScenarioLabViewProps> = ({ state }) => {
  // Preset or custom scenario configuration
  const [trucksDelta, setTrucksDelta] = useState<number>(3); // +3 trucks
  const [shovelOutage, setShovelOutage] = useState<string>('NONE'); // NONE | EX-01 | EX-02
  const [roadBlocked, setRoadBlocked] = useState<string>('NONE'); // NONE | RD-RAMP-BENCH-3840-CRUSHER
  const [powderFactorDelta, setPowderFactorDelta] = useState<number>(10); // +10%
  const [weather, setWeather] = useState<'CLEAR' | 'RAIN' | 'MUD'>('CLEAR');
  const [strategy, setStrategy] = useState<DispatchStrategy>('DRL_MULTI_OBJECTIVE');

  const [isSimulating, setIsSimulating] = useState<boolean>(false);
  const [simulationResult, setSimulationResult] = useState<ScenarioSimulationResult | null>(null);

  const handleRunSimulation = () => {
    setIsSimulating(true);

    setTimeout(() => {
      setSimulationResult(
        runWhatIfSimulation(state, {
          trucksDelta,
          shovelOutage,
          roadBlocked,
          powderFactorDelta,
          weather,
          strategy,
        })
      );
      setIsSimulating(false);
    }, 800);
  };

  return (
    <div className="w-full h-full flex flex-col p-4 gap-4 overflow-y-auto bg-slate-950 text-slate-100 select-none">
      {/* Title Header */}
      <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-xl shadow-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-amber-500/20 text-amber-400 rounded-xl">
            <Sliders className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white tracking-tight">
              Scenario Lab: Simulación What-If Monte Carlo Acelerada
            </h2>
            <p className="text-xs text-slate-400">
              Clonación del estado gemelo para experimentar escenarios operacionales sin riesgo
            </p>
          </div>
        </div>

        <button
          onClick={handleRunSimulation}
          disabled={isSimulating}
          className="px-4 py-2.5 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-bold rounded-xl shadow-lg shadow-amber-500/20 text-xs flex items-center gap-2 transition disabled:opacity-50"
        >
          {isSimulating ? (
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 border-2 border-slate-950 border-t-transparent rounded-full animate-spin"></span>
              Ejecutando Simulación 100x...
            </span>
          ) : (
            <>
              <Play className="w-4 h-4 fill-current" />
              <span>Ejecutar Simulación What-If</span>
            </>
          )}
        </button>
      </div>

      {/* Grid: Scenario Configuration Controls (5 Cols) vs Results (7 Cols) */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
        {/* Left: Configuration Builder (5 Cols) */}
        <div className="xl:col-span-5 bg-slate-900/90 border border-slate-800 rounded-xl p-4 space-y-4 shadow-xl text-xs">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <h3 className="font-bold text-slate-200 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
              <Copy className="w-4 h-4 text-amber-400" /> Parámetros del Escenario What-If
            </h3>
            <span className="text-[10px] text-slate-400 font-mono">Snapshot Digital Twin</span>
          </div>

          {/* Truck Fleet Variation */}
          <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800 space-y-1.5">
            <div className="flex justify-between items-center">
              <span className="font-semibold text-slate-300">Variación de Flota Camiones (Δ Camiones)</span>
              <span className="font-mono font-bold text-amber-400 text-sm">
                {trucksDelta >= 0 ? `+${trucksDelta}` : trucksDelta} camiones ({14 + trucksDelta} Total)
              </span>
            </div>
            <input
              type="range"
              min="-6"
              max="8"
              step="1"
              value={trucksDelta}
              onChange={(e) => setTrucksDelta(parseInt(e.target.value, 10))}
              className="w-full accent-amber-500 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-500 font-mono">
              <span>-6 Camiones</span>
              <span>0 (Actual 14)</span>
              <span>+8 Camiones</span>
            </div>
          </div>

          {/* Shovel Breakdown Outage */}
          <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800 space-y-1.5">
            <label className="font-semibold text-slate-300 block">Indisponibilidad de Pala (Falla Mecánica)</label>
            <div className="grid grid-cols-3 gap-2">
              {[
                { id: 'NONE', label: 'Ambas Operativas' },
                { id: 'EX-01', label: 'Pala EX-01 DOWN' },
                { id: 'EX-02', label: 'Pala EX-02 DOWN' },
              ].map((opt) => (
                <button
                  key={opt.id}
                  onClick={() => setShovelOutage(opt.id)}
                  className={`py-1.5 px-2 rounded-lg font-semibold text-[10px] border transition ${
                    shovelOutage === opt.id
                      ? 'bg-rose-500/20 border-rose-500 text-rose-300'
                      : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Road Blocked Ramp */}
          <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800 space-y-1.5">
            <label className="font-semibold text-slate-300 block">Restricción de Tráfico en Rampa</label>
            <div className="grid grid-cols-2 gap-2">
              {[
                { id: 'NONE', label: 'Rampas 100% Abiertas' },
                { id: 'RD-RAMP-BENCH-3840-CRUSHER', label: 'Cierre Rampa B3840' },
              ].map((opt) => (
                <button
                  key={opt.id}
                  onClick={() => setRoadBlocked(opt.id)}
                  className={`py-1.5 px-2 rounded-lg font-semibold text-[10px] border transition ${
                    roadBlocked === opt.id
                      ? 'bg-amber-500/20 border-amber-500 text-amber-300'
                      : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Powder Factor Adjustment */}
          <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800 space-y-1.5">
            <div className="flex justify-between items-center">
              <span className="font-semibold text-slate-300">Ajuste de Energía Tronadura (Powder Factor)</span>
              <span className="font-mono font-bold text-sky-400 text-sm">
                {powderFactorDelta >= 0 ? `+${powderFactorDelta}%` : `${powderFactorDelta}%`}
              </span>
            </div>
            <input
              type="range"
              min="-20"
              max="30"
              step="5"
              value={powderFactorDelta}
              onChange={(e) => setPowderFactorDelta(parseInt(e.target.value, 10))}
              className="w-full accent-sky-500 cursor-pointer"
            />
          </div>

          {/* Weather Condition */}
          <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800 space-y-1.5">
            <label className="font-semibold text-slate-300 block">Condición Meteorológica de Pista</label>
            <div className="grid grid-cols-3 gap-2">
              {[
                { id: 'CLEAR', label: '☀️ Despejado (100%)' },
                { id: 'RAIN', label: '🌧️ Lluvia (-15% vel)' },
                { id: 'MUD', label: '💧 Barro (-35% vel)' },
              ].map((opt) => (
                <button
                  key={opt.id}
                  onClick={() => setWeather(opt.id as any)}
                  className={`py-1.5 px-1.5 rounded-lg font-semibold text-[10px] border transition ${
                    weather === opt.id
                      ? 'bg-sky-500/20 border-sky-500 text-sky-300'
                      : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right: Simulation Outcomes & Side-by-Side Comparison (7 Cols) */}
        <div className="xl:col-span-7 bg-slate-900/90 border border-slate-800 rounded-xl p-4 space-y-4 shadow-xl text-xs flex flex-col">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <h3 className="font-bold text-slate-200 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
              <Activity className="w-4 h-4 text-emerald-400" /> Resultados Comparativos vs Estado Real Actual
            </h3>
            {simulationResult && (
              <span className="text-[10px] font-mono text-emerald-400 font-bold bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/30">
                Simulación Completada
              </span>
            )}
          </div>

          {!simulationResult ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8 bg-slate-950/60 rounded-xl border border-slate-800 text-slate-400 space-y-3">
              <Sliders className="w-12 h-12 text-slate-600 animate-pulse" />
              <div>
                <h4 className="font-bold text-slate-300 text-sm">Listo para Ejecutar Simulación What-If</h4>
                <p className="text-xs text-slate-500 max-w-sm mt-1">
                  Ajuste los parámetros a la izquierda y haga clic en "Ejecutar Simulación What-If" para calcular la respuesta del sistema.
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-4 flex-1">
              {/* Main KPIs Delta Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {/* Production Delta */}
                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                  <div className="text-[10px] text-slate-400">Producción Mina</div>
                  <div className="text-lg font-bold font-mono text-white mt-0.5">
                    {simulationResult.productionTonsPerHour.toLocaleString()} <span className="text-xs text-slate-500">t/h</span>
                  </div>
                  <div
                    className={`flex items-center gap-1 text-[11px] font-mono font-bold mt-1 ${
                      simulationResult.productionDeltaPercent >= 0 ? 'text-emerald-400' : 'text-rose-400'
                    }`}
                  >
                    {simulationResult.productionDeltaPercent >= 0 ? (
                      <ArrowUpRight className="w-3.5 h-3.5" />
                    ) : (
                      <ArrowDownRight className="w-3.5 h-3.5" />
                    )}
                    <span>{simulationResult.productionDeltaPercent}% vs Base</span>
                  </div>
                </div>

                {/* Cycle Time Delta */}
                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                  <div className="text-[10px] text-slate-400">Ciclo de Camión</div>
                  <div className="text-lg font-bold font-mono text-white mt-0.5">
                    {simulationResult.totalCycleTimeMin} <span className="text-xs text-slate-500">min</span>
                  </div>
                  <div
                    className={`flex items-center gap-1 text-[11px] font-mono font-bold mt-1 ${
                      simulationResult.cycleTimeDeltaMin <= 0 ? 'text-emerald-400' : 'text-rose-400'
                    }`}
                  >
                    {simulationResult.cycleTimeDeltaMin <= 0 ? '-' : '+'}
                    {Math.abs(simulationResult.cycleTimeDeltaMin)} min
                  </div>
                </div>

                {/* SAG Mill Throughput */}
                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                  <div className="text-[10px] text-slate-400">Throughput Molino SAG</div>
                  <div className="text-lg font-bold font-mono text-emerald-400 mt-0.5">
                    {simulationResult.millThroughputTph.toLocaleString()} <span className="text-xs text-slate-500">t/h</span>
                  </div>
                  <div className="text-[10px] text-slate-400 font-mono mt-1">
                    Esp: {simulationResult.specificEnergyKwhT} kWh/t
                  </div>
                </div>

                {/* Unit Cost */}
                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                  <div className="text-[10px] text-slate-400">Costo Unitario Total</div>
                  <div className="text-lg font-bold font-mono text-amber-400 mt-0.5">
                    ${simulationResult.unitCostUsdPerTon} <span className="text-xs text-slate-500">/t</span>
                  </div>
                  <div className="text-[10px] text-slate-400 font-mono mt-1">
                    Diésel: {simulationResult.fuelRateTotalLph} L/h
                  </div>
                </div>
              </div>

              {/* Identified Bottlenecks */}
              <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-2">
                <h4 className="font-bold text-slate-200 text-xs uppercase tracking-wider flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-400" /> Cuellos de Botella Detectados en el Escenario
                </h4>
                {simulationResult.bottlenecks.length === 0 ? (
                  <p className="text-emerald-400 font-medium text-xs">
                    ✓ No se detectaron cuellos de botella severos. Operación balanceada.
                  </p>
                ) : (
                  <ul className="space-y-1 text-slate-300 text-xs">
                    {simulationResult.bottlenecks.map((b, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-rose-400 font-bold">•</span>
                        <span>{b}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
