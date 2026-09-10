/**
 * MineTwin AI - Drill & Blast Engineering & Kuz-Ram Fragmentation Suite
 */

import React, { useState } from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  Activity,
  AlertCircle,
  CheckCircle,
  Flame,
  Info,
  Layers,
  RotateCcw,
  Sparkles,
  Zap,
} from 'lucide-react';
import { BlastPatternModel, DigitalTwinState } from '../../types/mining';
import {
  calculateKuzRamFragmentation,
  evaluateMineToMillImpact,
} from '../../services/kuzRamModel';

interface DrillBlastViewProps {
  state: DigitalTwinState;
  onUpdatePattern: (patternId: string, updatedParams: Partial<BlastPatternModel>) => void;
}

export const DrillBlastView: React.FC<DrillBlastViewProps> = ({ state }) => {
  const [selectedPatternId, setSelectedPatternId] = useState<string>('PAT-104-B3840');
  const pattern = state.blastPatterns.find((p) => p.id === selectedPatternId) || state.blastPatterns[0];

  // Interactive local tuning parameters
  const [burden, setBurden] = useState<number>(pattern.burden);
  const [spacing, setSpacing] = useState<number>(pattern.spacing);
  const [powderFactor, setPowderFactor] = useState<number>(pattern.powderFactor);
  const [stemming, setStemming] = useState<number>(pattern.stemmingHeight);
  const [explosiveType, setExplosiveType] = useState<BlastPatternModel['explosiveType']>(pattern.explosiveType);
  const [rockUCS, setRockUCS] = useState<number>(pattern.rockUCS);

  // Recalculate Kuz-Ram on the fly
  const kuzRam = calculateKuzRamFragmentation({
    burden,
    spacing,
    benchHeight: pattern.benchHeight,
    holeDiameterMm: 311,
    stemmingLength: stemming,
    subdrill: pattern.subdrill,
    powderFactorKgM3: powderFactor,
    rockUCSMpa: rockUCS,
    rockDensityTM3: pattern.rockDensity,
    rqdPercent: 78,
    jointSpacingM: 1.3,
    jointOrientationDip: 45,
    explosiveType,
  });

  const mineToMillImpact = evaluateMineToMillImpact(kuzRam, rockUCS, powderFactor);

  return (
    <div className="w-full h-full flex flex-col p-4 gap-4 overflow-y-auto bg-slate-950 text-slate-100 select-none">
      {/* Module Title & Pattern Switcher */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 bg-slate-900/90 border border-slate-800 p-4 rounded-xl shadow-lg">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-2 bg-amber-500/20 text-amber-400 rounded-lg">
              <Flame className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white tracking-tight">
                Módulo Drill & Blast & Modelo de Fragmentación Kuz-Ram
              </h2>
              <p className="text-xs text-slate-400">
                Diseño de mallas de perforación, simulación granulométrica P80 e impacto causal Mine-to-Mill
              </p>
            </div>
          </div>
        </div>

        {/* Pattern Selector Tabs */}
        <div className="flex items-center gap-2 bg-slate-950 p-1 rounded-xl border border-slate-800">
          {state.blastPatterns.map((pat) => (
            <button
              key={pat.id}
              onClick={() => {
                setSelectedPatternId(pat.id);
                setBurden(pat.burden);
                setSpacing(pat.spacing);
                setPowderFactor(pat.powderFactor);
                setStemming(pat.stemmingHeight);
                setExplosiveType(pat.explosiveType);
                setRockUCS(pat.rockUCS);
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                pat.id === selectedPatternId
                  ? 'bg-amber-500 text-slate-950 font-bold shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {pat.name}
            </button>
          ))}
        </div>
      </div>

      {/* Main Grid: Design Controls + Kuz-Ram Curve + Mine-to-Mill Propagation */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
        {/* Left Column: Interactive Blast Pattern Parameters (4 Cols) */}
        <div className="xl:col-span-4 bg-slate-900/90 border border-slate-800 rounded-xl p-4 space-y-4 shadow-xl text-xs">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <h3 className="font-bold text-slate-200 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-amber-400" /> Parámetros de Diseño Malla
            </h3>
            <button
              onClick={() => {
                setBurden(pattern.burden);
                setSpacing(pattern.spacing);
                setPowderFactor(pattern.powderFactor);
                setStemming(pattern.stemmingHeight);
                setExplosiveType(pattern.explosiveType);
                setRockUCS(pattern.rockUCS);
              }}
              className="text-[10px] text-slate-400 hover:text-amber-400 transition flex items-center gap-1"
            >
              <RotateCcw className="w-3 h-3" /> Reset
            </button>
          </div>

          {/* Powder Factor Slider */}
          <div className="space-y-1.5 bg-slate-950/70 p-3 rounded-xl border border-slate-800">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-300">Factor de Carga (Powder Factor)</span>
              <span className="font-mono font-bold text-amber-400 text-sm">{powderFactor.toFixed(2)} kg/m³</span>
            </div>
            <input
              type="range"
              min="0.40"
              max="1.40"
              step="0.02"
              value={powderFactor}
              onChange={(e) => setPowderFactor(parseFloat(e.target.value))}
              className="w-full accent-amber-500 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-500 font-mono">
              <span>0.40 (Baja energía)</span>
              <span>0.85 (Estándar)</span>
              <span>1.40 (Alta energía)</span>
            </div>
          </div>

          {/* Burden & Spacing Inputs */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800 space-y-1">
              <div className="flex items-center justify-between text-slate-400">
                <span>Burden (B)</span>
                <span className="font-mono text-amber-400 font-bold">{burden.toFixed(1)} m</span>
              </div>
              <input
                type="range"
                min="4.5"
                max="9.0"
                step="0.1"
                value={burden}
                onChange={(e) => setBurden(parseFloat(e.target.value))}
                className="w-full accent-amber-500 cursor-pointer"
              />
            </div>

            <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800 space-y-1">
              <div className="flex items-center justify-between text-slate-400">
                <span>Espaciamiento (S)</span>
                <span className="font-mono text-amber-400 font-bold">{spacing.toFixed(1)} m</span>
              </div>
              <input
                type="range"
                min="5.0"
                max="10.5"
                step="0.1"
                value={spacing}
                onChange={(e) => setSpacing(parseFloat(e.target.value))}
                className="w-full accent-amber-500 cursor-pointer"
              />
            </div>
          </div>

          {/* Stemming & Rock UCS */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800 space-y-1">
              <div className="flex items-center justify-between text-slate-400">
                <span>Taco (Stemming)</span>
                <span className="font-mono text-sky-400 font-bold">{stemming.toFixed(1)} m</span>
              </div>
              <input
                type="range"
                min="3.5"
                max="8.0"
                step="0.1"
                value={stemming}
                onChange={(e) => setStemming(parseFloat(e.target.value))}
                className="w-full accent-sky-500 cursor-pointer"
              />
            </div>

            <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800 space-y-1">
              <div className="flex items-center justify-between text-slate-400">
                <span>Dureza Roca (UCS)</span>
                <span className="font-mono text-purple-400 font-bold">{rockUCS} MPa</span>
              </div>
              <input
                type="range"
                min="60"
                max="240"
                step="5"
                value={rockUCS}
                onChange={(e) => setRockUCS(parseInt(e.target.value, 10))}
                className="w-full accent-purple-500 cursor-pointer"
              />
            </div>
          </div>

          {/* Explosive Type Selector */}
          <div className="space-y-1.5">
            <label className="text-slate-400 font-medium text-[11px]">Tipo de Explosivo & Potencia Relativa (RWS)</label>
            <div className="grid grid-cols-3 gap-1.5">
              {(['ANFO', 'HEAVY_ANFO', 'EMULSION_70_30'] as const).map((exp) => (
                <button
                  key={exp}
                  onClick={() => setExplosiveType(exp)}
                  className={`py-1.5 px-2 rounded-lg text-[10px] font-mono font-semibold border transition text-center ${
                    explosiveType === exp
                      ? 'bg-amber-500/20 border-amber-500 text-amber-300'
                      : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {exp === 'ANFO' ? 'ANFO (100)' : exp === 'HEAVY_ANFO' ? 'H-ANFO (115)' : 'Emulsión (125)'}
                </button>
              ))}
            </div>
          </div>

          {/* Geometry Quick Overview */}
          <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800 font-mono text-[11px] space-y-1">
            <div className="flex justify-between text-slate-400">
              <span>Altura de Banco:</span> <b className="text-slate-200">{pattern.benchHeight} m</b>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Diámetro de Pozo:</span> <b className="text-slate-200">311 mm (12 ¼")</b>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Sobreperforación:</span> <b className="text-slate-200">{pattern.subdrill} m</b>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Total Pozos en Malla:</span> <b className="text-amber-400">{pattern.totalHoles}</b>
            </div>
          </div>
        </div>

        {/* Middle Column: Kuz-Ram Rosin-Rammler Curve & KPIs (5 Cols) */}
        <div className="xl:col-span-5 bg-slate-900/90 border border-slate-800 rounded-xl p-4 space-y-4 shadow-xl text-xs flex flex-col">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <h3 className="font-bold text-slate-200 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
              <Activity className="w-4 h-4 text-emerald-400" /> Curva Granulométrica Rosin-Rammler
            </h3>
            <span className="font-mono text-[10px] text-slate-400">
              Índice Uniformidad n: <b className="text-emerald-400">{kuzRam.uniformityIndexN}</b>
            </span>
          </div>

          {/* Kuz-Ram Key Output Cards */}
          <div className="grid grid-cols-4 gap-2 text-center font-mono">
            <div className="bg-slate-950 p-2 rounded-xl border border-slate-800">
              <div className="text-[10px] text-slate-400 font-sans">P20 (Finos)</div>
              <div className="text-sm font-bold text-sky-400 mt-0.5">{kuzRam.p20} mm</div>
            </div>
            <div className="bg-slate-950 p-2 rounded-xl border border-slate-800">
              <div className="text-[10px] text-slate-400 font-sans">P50 (Medio)</div>
              <div className="text-sm font-bold text-amber-400 mt-0.5">{kuzRam.p50} mm</div>
            </div>
            <div className="bg-slate-950 p-2 rounded-xl border border-amber-500/30 bg-amber-500/5">
              <div className="text-[10px] text-amber-400 font-sans font-semibold">P80 (Objetivo)</div>
              <div className="text-base font-extrabold text-amber-300 mt-0.5">{kuzRam.p80} mm</div>
            </div>
            <div className="bg-slate-950 p-2 rounded-xl border border-slate-800">
              <div className="text-[10px] text-slate-400 font-sans">Sobretamaño</div>
              <div className={`text-sm font-bold mt-0.5 ${kuzRam.oversizePercent > 5 ? 'text-rose-400' : 'text-emerald-400'}`}>
                {kuzRam.oversizePercent}%
              </div>
            </div>
          </div>

          {/* Recharts PSD Area Chart */}
          <div className="flex-1 min-h-[240px] w-full bg-slate-950/60 p-2 rounded-xl border border-slate-800">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={kuzRam.curveData} margin={{ top: 10, right: 15, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="curveGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.6} />
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="sizeMm" stroke="#64748b" tick={{ fontSize: 10 }} unit="mm" />
                <YAxis stroke="#64748b" tick={{ fontSize: 10 }} domain={[0, 100]} unit="%" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#090d16', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }}
                  formatter={(val: any) => [`${val}% Pasante`, 'Distribución']}
                  labelFormatter={(size) => `Tamaño Partícula: ${size} mm`}
                />
                <Area type="monotone" dataKey="passingPercent" stroke="#f59e0b" strokeWidth={2.5} fillOpacity={1} fill="url(#curveGradient)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <p className="text-[10px] text-slate-400 text-center italic">
            Tamaño característico Xc = <span className="font-mono text-amber-400">{kuzRam.characteristicSizeXc} mm</span>.
            Fracción finos (&lt;25mm) = <span className="font-mono text-sky-400">{kuzRam.finesPercent}%</span>.
          </p>
        </div>

        {/* Right Column: Downstream Mine-to-Mill Impact & Drill Rigs (3 Cols) */}
        <div className="xl:col-span-3 space-y-4 text-xs">
          {/* Downstream Cascade Impact */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 space-y-3 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <h3 className="font-bold text-slate-200 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-amber-400" /> Impacto Aguas Abajo
              </h3>
            </div>

            <div className="space-y-2">
              {/* Shovel Digability */}
              <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 flex justify-between items-center">
                <div>
                  <div className="text-slate-400 text-[10px]">Tiempo Pase Carguío</div>
                  <div className="font-bold text-amber-400 text-sm font-mono mt-0.5">
                    {mineToMillImpact.shovelDigTimePassSeconds} s/pase
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-slate-400 text-[10px]">Factor Llenado</div>
                  <div className="font-bold text-emerald-400 text-sm font-mono mt-0.5">
                    {mineToMillImpact.bucketFillFactorPercent}%
                  </div>
                </div>
              </div>

              {/* Crusher Feed Throughput */}
              <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 flex justify-between items-center">
                <div>
                  <div className="text-slate-400 text-[10px]">Capacidad Chancador</div>
                  <div className="font-bold text-sky-400 text-sm font-mono mt-0.5">
                    {mineToMillImpact.crusherFeedRateTph.toLocaleString()} t/h
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-slate-400 text-[10px]">Riesgo Atasco</div>
                  <span
                    className={`px-2 py-0.5 rounded font-bold text-[10px] ${
                      mineToMillImpact.crusherChokeRisk === 'HIGH'
                        ? 'bg-rose-500/20 text-rose-300'
                        : mineToMillImpact.crusherChokeRisk === 'MEDIUM'
                        ? 'bg-amber-500/20 text-amber-300'
                        : 'bg-emerald-500/20 text-emerald-300'
                    }`}
                  >
                    {mineToMillImpact.crusherChokeRisk}
                  </span>
                </div>
              </div>

              {/* SAG Mill Specific Energy */}
              <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 flex justify-between items-center">
                <div>
                  <div className="text-slate-400 text-[10px]">Energía Específica SAG</div>
                  <div className="font-bold text-purple-400 text-sm font-mono mt-0.5">
                    {mineToMillImpact.sagMillSpecificEnergyKwhT} kWh/t
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-slate-400 text-[10px]">Throughput SAG</div>
                  <div className="font-bold text-emerald-400 text-sm font-mono mt-0.5">
                    {mineToMillImpact.sagMillThroughputTph.toLocaleString()} t/h
                  </div>
                </div>
              </div>

              {/* Total Unit Cost */}
              <div className="bg-gradient-to-br from-slate-950 to-amber-950/40 p-3 rounded-xl border border-amber-500/30 flex justify-between items-center">
                <div>
                  <div className="text-slate-300 text-[10px] font-semibold">Costo Total Minado a Planta</div>
                  <div className="text-lg font-bold font-mono text-amber-300 mt-0.5">
                    ${mineToMillImpact.totalCostPerTonMinedUsd} <span className="text-xs text-slate-400 font-normal">/t</span>
                  </div>
                </div>
                <Zap className="w-5 h-5 text-amber-400" />
              </div>
            </div>
          </div>

          {/* Drill Rigs Telemetry Panel */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 space-y-2.5 shadow-xl">
            <h3 className="font-bold text-slate-200 uppercase tracking-wider text-[11px]">
              Perforadoras Activas en Malla
            </h3>
            {state.drills.map((drill) => (
              <div key={drill.id} className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 space-y-1.5">
                <div className="flex justify-between items-center font-semibold text-slate-200">
                  <span>🚜 {drill.name.split('(')[0]}</span>
                  <span className="font-mono text-emerald-400 text-[11px]">{drill.penetrationRateMph} m/h</span>
                </div>
                <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                  <span>Pozo Actual: <b className="text-slate-200">{drill.currentHoleId}</b></span>
                  <span>Profundidad: <b className="text-sky-400">{drill.currentHoleDepth.toFixed(1)} / {drill.targetHoleDepth}m</b></span>
                </div>
                <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-emerald-500"
                    style={{ width: `${(drill.currentHoleDepth / drill.targetHoleDepth) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
