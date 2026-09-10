/**
 * MineTwin AI - Analytics & Telemetry Visualization Suite
 */

import React from 'react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  Activity,
  Award,
  BarChart3,
  Clock,
  Fuel,
  TrendingUp,
  Zap,
} from 'lucide-react';
import { DigitalTwinState } from '../../types/mining';

interface AnalyticsViewProps {
  state: DigitalTwinState;
}

export const AnalyticsView: React.FC<AnalyticsViewProps> = ({ state }) => {
  // Cycle time decomposition data
  const cycleBreakdownData = [
    { name: 'Retorno Vacío', minutes: 7.2, color: '#38bdf8' },
    { name: 'Cola en Pala', minutes: 2.8, color: '#f59e0b' },
    { name: 'Aculatamiento (Spotting)', minutes: 0.9, color: '#94a3b8' },
    { name: 'Carguío Efectivo (Loading)', minutes: 3.2, color: '#a855f7' },
    { name: 'Acarreo Cargado (Hauling)', minutes: 10.4, color: '#10b981' },
    { name: 'Cola en Destino/Chancador', minutes: 1.2, color: '#f97316' },
    { name: 'Descarga en Tolva (Dumping)', minutes: 1.1, color: '#ef4444' },
  ];

  // Fuel consumption rate vs road gradient
  const fuelGradientData = [
    { gradient: '-10% (Bajada)', fuelRate: 110, loaded: 160 },
    { gradient: '-5% (Bajada)', fuelRate: 130, loaded: 190 },
    { gradient: '0% (Plano)', fuelRate: 180, loaded: 260 },
    { gradient: '+4% (Subida)', fuelRate: 230, loaded: 340 },
    { gradient: '+8% (Rampa)', fuelRate: 290, loaded: 420 },
    { gradient: '+10% (Rampa Máx)', fuelRate: 340, loaded: 480 },
  ];

  return (
    <div className="w-full h-full flex flex-col p-4 gap-4 overflow-y-auto bg-slate-950 text-slate-100 select-none">
      {/* Title Header */}
      <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-xl shadow-lg flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-amber-500/20 text-amber-400 rounded-xl">
            <TrendingUp className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white tracking-tight">
              Módulo de Analítica & Telemetría Operacional
            </h2>
            <p className="text-xs text-slate-400">
              Tendencias históricas de producción horaria, descomposición de tiempos de ciclo y consumo energético
            </p>
          </div>
        </div>
      </div>

      {/* Grid: Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* 1. Production Trend Line Chart */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-xl space-y-3 flex flex-col min-h-[320px]">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <h3 className="font-bold text-slate-200 text-xs uppercase tracking-wider flex items-center gap-1.5">
              <Activity className="w-4 h-4 text-amber-400" /> Producción Mina (t/h) vs Molienda SAG (t/h)
            </h3>
          </div>

          <div className="flex-1 w-full min-h-[220px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={state.kpiHistory} margin={{ top: 10, right: 15, left: -15, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#090d16', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }}
                />
                <Legend wrapperStyle={{ fontSize: '11px' }} />
                <Line type="monotone" dataKey="productionTph" name="Producción Mina (t/h)" stroke="#f59e0b" strokeWidth={2.5} dot={{ r: 3 }} />
                <Line type="monotone" dataKey="millThroughputTph" name="Molienda SAG (t/h)" stroke="#10b981" strokeWidth={2.5} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 2. Cycle Time Decomposition Bar Chart */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-xl space-y-3 flex flex-col min-h-[320px]">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <h3 className="font-bold text-slate-200 text-xs uppercase tracking-wider flex items-center gap-1.5">
              <Clock className="w-4 h-4 text-sky-400" /> Descomposición de Tiempos de Ciclo de Camión
            </h3>
            <span className="font-mono text-[10px] text-slate-400">Total: 26.8 min</span>
          </div>

          <div className="flex-1 w-full min-h-[220px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={cycleBreakdownData} layout="vertical" margin={{ top: 10, right: 15, left: 40, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis type="number" stroke="#64748b" tick={{ fontSize: 10 }} unit=" min" />
                <YAxis dataKey="name" type="category" stroke="#94a3b8" tick={{ fontSize: 10 }} width={120} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#090d16', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }}
                  formatter={(val: any) => [`${val} minutos`, 'Duración']}
                />
                <Bar dataKey="minutes" fill="#38bdf8" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 3. Fuel Consumption vs Gradient Chart */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-xl space-y-3 flex flex-col min-h-[320px]">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <h3 className="font-bold text-slate-200 text-xs uppercase tracking-wider flex items-center gap-1.5">
              <Fuel className="w-4 h-4 text-purple-400" /> Consumo de Diésel (L/h) vs Pendiente de Rampa (%)
            </h3>
          </div>

          <div className="flex-1 w-full min-h-[220px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={fuelGradientData} margin={{ top: 10, right: 15, left: -15, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="gradient" stroke="#64748b" tick={{ fontSize: 10 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 10 }} unit=" L/h" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#090d16', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }}
                />
                <Legend wrapperStyle={{ fontSize: '11px' }} />
                <Bar dataKey="fuelRate" name="Camión Vacío (L/h)" fill="#38bdf8" />
                <Bar dataKey="loaded" name="Camión Cargado 360t (L/h)" fill="#f59e0b" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 4. Unit Cost & Specific Energy Trend */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-xl space-y-3 flex flex-col min-h-[320px]">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <h3 className="font-bold text-slate-200 text-xs uppercase tracking-wider flex items-center gap-1.5">
              <Zap className="w-4 h-4 text-emerald-400" /> Evolución del Costo Unitario ($/t)
            </h3>
          </div>

          <div className="flex-1 w-full min-h-[220px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={state.kpiHistory} margin={{ top: 10, right: 15, left: -15, bottom: 0 }}>
                <defs>
                  <linearGradient id="costGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.6} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 10 }} domain={[5.5, 7.5]} unit=" $" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#090d16', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }}
                  formatter={(val: any) => [`$${val} /t`, 'Costo Unitario']}
                />
                <Area type="monotone" dataKey="unitCost" stroke="#10b981" strokeWidth={2.5} fill="url(#costGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};
