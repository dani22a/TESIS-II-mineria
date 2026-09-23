/**
 * MineTwin AI - Mine-to-Mill Causal Graph & SAG Grinding Optimization
 */

import React, { useState } from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowDown,
  ArrowRight,
  CheckCircle,
  Cpu,
  Flame,
  Gauge,
  Layers,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Zap,
} from 'lucide-react';
import { DigitalTwinState } from '../../types/mining';
import { calculateKuzRamFragmentation, evaluateMineToMillImpact } from '../../services/kuzRamModel';

interface MineToMillViewProps {
  state: DigitalTwinState;
}

export const MineToMillView: React.FC<MineToMillViewProps> = ({ state }) => {
  const [rockUCS, setRockUCS] = useState<number>(145);
  const [powderFactor, setPowderFactor] = useState<number>(0.88);
  const [selectedNodeIndex, setSelectedNodeIndex] = useState<number>(3); // Default to Fragmentation

  // Compute live propagation
  const kuzRam = calculateKuzRamFragmentation({
    burden: 6.5,
    spacing: 7.5,
    benchHeight: 15.0,
    holeDiameterMm: 311,
    stemmingLength: 5.8,
    subdrill: 1.8,
    powderFactorKgM3: powderFactor,
    rockUCSMpa: rockUCS,
    rockDensityTM3: 2.72,
    rqdPercent: 78,
    jointSpacingM: 1.4,
    jointOrientationDip: 45,
    explosiveType: 'EMULSION_70_30',
  });

  const impact = evaluateMineToMillImpact(kuzRam, rockUCS, powderFactor);

  const causalNodes = [
    {
      id: 'geology',
      step: 1,
      title: 'Geología y roca',
      icon: '🪨',
      kpi: `UCS ${rockUCS} MPa`,
      status: rockUCS > 160 ? 'Duro / Abrasivo' : 'Competente Estándar',
      desc: 'Propiedades geomecánicas del macizo rocoso y resistencia a la compresión.',
    },
    {
      id: 'drill',
      step: 2,
      title: 'Perforación',
      icon: '🚜',
      kpi: `${(48 - (rockUCS - 100) * 0.15).toFixed(1)} m/h`,
      status: 'Tasa Penetración',
      desc: 'Velocidad de perforación rotativa y desgaste de broca de 311 mm.',
    },
    {
      id: 'blast',
      step: 3,
      title: 'Tronadura y energía',
      icon: '💥',
      kpi: `${powderFactor.toFixed(2)} kg/m³`,
      status: 'Factor de Carga',
      desc: 'Distribución de energía química de emulsión para fracturamiento de roca.',
    },
    {
      id: 'fragmentation',
      step: 4,
      title: 'Fragmentación Kuz-Ram',
      icon: '📊',
      kpi: `P80 = ${kuzRam.p80} mm`,
      status: `Sobretamaño: ${kuzRam.oversizePercent}%`,
      desc: 'Distribución de tamaño de partícula resultante del disparo.',
    },
    {
      id: 'loading',
      step: 5,
      title: 'Carguío (palas)',
      icon: '⛏️',
      kpi: `${impact.shovelDigTimePassSeconds} s / pase`,
      status: `Llenado: ${impact.bucketFillFactorPercent}%`,
      desc: 'Excavabilidad de la saca y tasa de productividad de palas de cable.',
    },
    {
      id: 'haulage',
      step: 6,
      title: 'Acarreo (Camiones)',
      icon: '🚛',
      kpi: `26.8 min ciclo`,
      status: 'Flota 14 Camiones',
      desc: 'Transporte continuo por rampas con pendiente y consumo de diésel.',
    },
    {
      id: 'crushing',
      step: 7,
      title: 'Chancado Primario',
      icon: '🏭',
      kpi: `${impact.crusherFeedRateTph.toLocaleString()} t/h`,
      status: `Riesgo: ${impact.crusherChokeRisk === 'HIGH' ? 'Alto' : impact.crusherChokeRisk === 'MEDIUM' ? 'Medio' : 'Bajo'}`,
      desc: 'Alimentación directa de tolva en Chancador Giratorio 60x89.',
    },
    {
      id: 'milling',
      step: 8,
      title: 'Molienda Molino SAG',
      icon: '⚙️',
      kpi: `${impact.sagMillSpecificEnergyKwhT} kWh/t`,
      status: `Rendimiento: ${impact.sagMillThroughputTph.toLocaleString()} t/h`,
      desc: 'Consumo de potencia eléctrica en circuito de molienda SAG de 40 pies.',
    },
    {
      id: 'flotation',
      step: 9,
      title: 'Recuperación Cu',
      icon: '🧪',
      kpi: `${impact.flotationCuRecoveryPercent}% Cu`,
      status: 'Flotación Concentrado',
      desc: 'Recuperación metalúrgica de cobre en celdas de flotación.',
    },
  ];

  return (
    <div className="w-full h-full flex flex-col p-4 gap-4 overflow-y-auto bg-slate-950 text-slate-100 select-none">
      {/* Header Banner */}
      <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-xl shadow-lg flex flex-col lg:flex-row lg:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-amber-500/20 text-amber-400 rounded-xl">
            <Cpu className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white tracking-tight">
              Cadena causal de mina a planta: energía y molienda
            </h2>
            <p className="text-xs text-slate-400">
              Impacto de la fragmentación de tronadura sobre la capacidad de molienda SAG
            </p>
          </div>
        </div>

        {/* Global Unit Cost Badge */}
        <div className="bg-slate-950 px-4 py-2 rounded-xl border border-amber-500/40 flex items-center gap-3">
          <div>
            <div className="text-[10px] text-slate-400 font-semibold uppercase">Costo Total Minado a Molino</div>
            <div className="text-xl font-bold font-mono text-amber-400">${impact.totalCostPerTonMinedUsd} /t</div>
          </div>
          <Zap className="w-6 h-6 text-amber-400" />
        </div>
      </div>

      {/* Upstream Parameter Sliders */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-xl space-y-3">
        <h3 className="font-bold text-slate-200 uppercase tracking-wider text-xs flex items-center gap-2">
          <Layers className="w-4 h-4 text-amber-400" /> Sensibilidad de variables de origen (simulador en vivo)
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-slate-950/80 p-3 rounded-xl border border-slate-800 space-y-1.5">
            <div className="flex justify-between items-center text-xs">
              <span className="font-semibold text-slate-300">Factor de carga de tronadura</span>
              <span className="font-mono font-bold text-amber-400 text-sm">{powderFactor.toFixed(2)} kg/m³</span>
            </div>
            <input
              type="range"
              min="0.50"
              max="1.30"
              step="0.02"
              value={powderFactor}
              onChange={(e) => setPowderFactor(parseFloat(e.target.value))}
              className="w-full accent-amber-500 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-500 font-mono">
              <span>0.50 (Fragmentación Gruesa)</span>
              <span>0.88 (Calibrado)</span>
              <span>1.30 (Ultra Fino / Alta Energía)</span>
            </div>
          </div>

          <div className="bg-slate-950/80 p-3 rounded-xl border border-slate-800 space-y-1.5">
            <div className="flex justify-between items-center text-xs">
              <span className="font-semibold text-slate-300">Resistencia Compresión de Roca (UCS)</span>
              <span className="font-mono font-bold text-purple-400 text-sm">{rockUCS} MPa</span>
            </div>
            <input
              type="range"
              min="80"
              max="220"
              step="5"
              value={rockUCS}
              onChange={(e) => setRockUCS(parseInt(e.target.value, 10))}
              className="w-full accent-purple-500 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-500 font-mono">
              <span>80 MPa (Blando)</span>
              <span>145 MPa (Pórfido Cu)</span>
              <span>220 MPa (Skarn Silicificado)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Causal Graph Node Pipeline */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-xl space-y-3">
        <h3 className="font-bold text-slate-200 uppercase tracking-wider text-xs">
          Cadena Causal de Transformación de Energía (9 Etapas)
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-9 gap-2">
          {causalNodes.map((node, index) => {
            const isSelected = selectedNodeIndex === index;
            return (
              <div
                key={node.id}
                onClick={() => setSelectedNodeIndex(index)}
                className={`p-3 rounded-xl border transition cursor-pointer flex flex-col justify-between text-xs relative ${
                  isSelected
                    ? 'bg-amber-500/15 border-amber-500/60 shadow-lg shadow-amber-500/10'
                    : 'bg-slate-950/80 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 mb-1">
                    <span>Etapa {node.step}</span>
                    <span>{node.icon}</span>
                  </div>
                  <h4 className="font-bold text-slate-200 text-[11px] truncate">{node.title}</h4>
                </div>

                <div className="mt-2 pt-2 border-t border-slate-800/80">
                  <div className="font-mono font-bold text-amber-400 text-xs">{node.kpi}</div>
                  <div className="text-[10px] text-slate-400 truncate mt-0.5">{node.status}</div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Detailed Node Inspector & Energy Tradeoff Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Selected Causal Node Details */}
        <div className="lg:col-span-6 bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-xl text-xs space-y-3">
          <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
            <span className="text-xl">{causalNodes[selectedNodeIndex].icon}</span>
            <div>
              <h3 className="font-bold text-white text-sm">{causalNodes[selectedNodeIndex].title}</h3>
              <p className="text-[11px] text-slate-400">{causalNodes[selectedNodeIndex].desc}</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 font-mono">
            <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
              <div className="text-[10px] text-slate-400 font-sans">Métrica Principal</div>
              <div className="text-base font-bold text-amber-400 mt-1">{causalNodes[selectedNodeIndex].kpi}</div>
            </div>
            <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
              <div className="text-[10px] text-slate-400 font-sans">Condición Operativa</div>
              <div className="text-sm font-bold text-slate-200 mt-1">{causalNodes[selectedNodeIndex].status}</div>
            </div>
          </div>

          <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800 text-[11px] text-slate-300 space-y-1.5">
            <h4 className="font-bold text-slate-200">Relación física de mina a planta:</h4>
            <p>
              Un aumento de <b className="text-amber-400">+0.10 kg/m³</b> en energía de tronadura reduce el tamaño P80 en aprox.{' '}
              <b className="text-emerald-400">~24 mm</b>, lo cual incrementa el rendimiento del molino SAG en{' '}
              <b className="text-emerald-400">~140 t/h</b> y ahorra <b className="text-sky-400">0.45 kWh/t</b> en la molienda primaria.
            </p>
          </div>
        </div>

        {/* Bottleneck Analysis & Optimization Summary */}
        <div className="lg:col-span-6 bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-xl text-xs space-y-3">
          <h3 className="font-bold text-slate-200 uppercase tracking-wider text-xs flex items-center gap-2">
            <Activity className="w-4 h-4 text-emerald-400" /> Diagnóstico de Cuellos de Botella en la Cadena
          </h3>

          <div className="space-y-2">
            <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-start gap-2.5">
              <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
              <div>
                <div className="font-bold text-emerald-300">Capacidad de Molienda SAG en Rango Óptimo</div>
                <div className="text-[11px] text-slate-300">
                  Rendimiento actual de {impact.sagMillThroughputTph.toLocaleString()} t/h, alimentado por fragmentación fina P80 = {kuzRam.p80} mm.
                </div>
              </div>
            </div>

            <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
              <div>
                <div className="font-bold text-amber-300">Vulnerabilidad de Sobretamaño en Chancador</div>
                <div className="text-[11px] text-slate-300">
                  Fracción de bolones &gt;1000mm es de {kuzRam.oversizePercent}%. Si supera el 6%, aumenta la probabilidad de choke en el chancador giratorio.
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
