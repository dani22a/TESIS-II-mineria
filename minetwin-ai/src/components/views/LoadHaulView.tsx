/**
 * MineTwin AI - Load & Haul Fleet Operations & Dispatch Command
 */

import React, { useState } from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock,
  Compass,
  Filter,
  Fuel,
  Gauge,
  Navigation,
  RefreshCw,
  Search,
  Sliders,
  TrendingUp,
  Truck,
  Zap,
} from 'lucide-react';
import { CycleState, DigitalTwinState, TruckTwin } from '../../types/mining';

interface LoadHaulViewProps {
  state: DigitalTwinState;
  onSelectTruck: (truckId: string) => void;
  onOpenAssetDetail: (assetId: string) => void;
  onManualReassignTruck: (truckId: string, newShovelId: string) => void;
}

export const LoadHaulView: React.FC<LoadHaulViewProps> = ({
  state,
  onSelectTruck,
  onOpenAssetDetail,
  onManualReassignTruck,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [stateFilter, setStateFilter] = useState<string>('ALL');

  const filteredTrucks = state.trucks.filter((truck) => {
    const matchesSearch =
      truck.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      truck.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      truck.model.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesState = stateFilter === 'ALL' || truck.cycleState === stateFilter;
    return matchesSearch && matchesState;
  });

  const getCycleBadgeColor = (cycleState: CycleState) => {
    switch (cycleState) {
      case 'HAULING':
        return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40';
      case 'RETURNING':
      case 'EMPTY_TRAVEL':
        return 'bg-sky-500/15 text-sky-300 border-sky-500/40';
      case 'LOADING':
        return 'bg-purple-500/15 text-purple-300 border-purple-500/40';
      case 'QUEUE_SHOVEL':
      case 'QUEUE_DESTINATION':
        return 'bg-amber-500/15 text-amber-300 border-amber-500/40';
      case 'DUMPING':
        return 'bg-rose-500/15 text-rose-300 border-rose-500/40';
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  return (
    <div className="w-full h-full flex flex-col p-4 gap-4 overflow-y-auto bg-slate-950 text-slate-100 select-none">
      {/* Top Banner with Fleet KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        <div className="bg-slate-900/90 border border-slate-800 p-3 rounded-xl shadow-lg">
          <div className="text-[10px] text-slate-400 font-medium uppercase tracking-wider flex items-center justify-between">
            <span>Flota Activa</span>
            <Truck className="w-3.5 h-3.5 text-amber-400" />
          </div>
          <div className="text-xl font-bold font-mono text-white mt-1">
            {state.trucks.length} <span className="text-xs text-slate-400 font-normal">Camiones</span>
          </div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 p-3 rounded-xl shadow-lg">
          <div className="text-[10px] text-slate-400 font-medium uppercase tracking-wider flex items-center justify-between">
            <span>Velocidad Promedio</span>
            <Gauge className="w-3.5 h-3.5 text-sky-400" />
          </div>
          <div className="text-xl font-bold font-mono text-white mt-1">
            {Math.round(state.trucks.reduce((acc, t) => acc + t.speed, 0) / state.trucks.length)}{' '}
            <span className="text-xs text-slate-400 font-normal">km/h</span>
          </div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 p-3 rounded-xl shadow-lg">
          <div className="text-[10px] text-slate-400 font-medium uppercase tracking-wider flex items-center justify-between">
            <span>Tiempo Ciclo Global</span>
            <Clock className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="text-xl font-bold font-mono text-emerald-400 mt-1">
            {Math.round((state.trucks.reduce((acc, t) => acc + t.cycleTimeMinutes, 0) / state.trucks.length) * 10) / 10}{' '}
            <span className="text-xs text-slate-400 font-normal">min</span>
          </div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 p-3 rounded-xl shadow-lg">
          <div className="text-[10px] text-slate-400 font-medium uppercase tracking-wider flex items-center justify-between">
            <span>Consumo Combustible</span>
            <Fuel className="w-3.5 h-3.5 text-purple-400" />
          </div>
          <div className="text-xl font-bold font-mono text-purple-300 mt-1">
            {Math.round(state.trucks.reduce((acc, t) => acc + t.fuelRate, 0)).toLocaleString()}{' '}
            <span className="text-xs text-slate-400 font-normal">L/h</span>
          </div>
        </div>

        <div className="col-span-2 lg:col-span-1 bg-slate-900/90 border border-slate-800 p-3 rounded-xl shadow-lg">
          <div className="text-[10px] text-slate-400 font-medium uppercase tracking-wider flex items-center justify-between">
            <span>Factor Utilización</span>
            <Zap className="w-3.5 h-3.5 text-amber-400" />
          </div>
          <div className="text-xl font-bold font-mono text-amber-400 mt-1">
            {Math.round((state.trucks.reduce((acc, t) => acc + t.utilization, 0) / state.trucks.length) * 10) / 10}%
          </div>
        </div>
      </div>

      {/* Shovels Real-time Loading Status Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {state.shovels.map((shovel) => (
          <div
            key={shovel.id}
            className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-xl text-xs space-y-3"
          >
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <div className="flex items-center gap-2">
                <div className="p-2 bg-amber-500/20 text-amber-400 rounded-lg font-bold">⛏️</div>
                <div>
                  <h3 className="font-bold text-white text-sm">{shovel.name}</h3>
                  <p className="text-[10px] text-slate-400 font-mono">
                    Banco {shovel.benchElevation}m RL • Mineral {shovel.materialType} (Ley {shovel.materialGrade}% Cu)
                  </p>
                </div>
              </div>
              <button
                onClick={() => onOpenAssetDetail(shovel.id)}
                className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-[11px] font-medium transition"
              >
                Detalles
              </button>
            </div>

            <div className="grid grid-cols-4 gap-2 text-center font-mono">
              <div className="bg-slate-950 p-2 rounded-lg border border-slate-800">
                <div className="text-[10px] text-slate-400 font-sans">Productividad</div>
                <div className="font-bold text-amber-400 text-xs mt-0.5">{shovel.productivityTph} t/h</div>
              </div>
              <div className="bg-slate-950 p-2 rounded-lg border border-slate-800">
                <div className="text-[10px] text-slate-400 font-sans">Carguío Activo</div>
                <div className="font-bold text-sky-400 text-xs mt-0.5">{shovel.currentTruckLoadingId || 'Libre'}</div>
              </div>
              <div className="bg-slate-950 p-2 rounded-lg border border-slate-800">
                <div className="text-[10px] text-slate-400 font-sans">En Espera (Cola)</div>
                <div className="font-bold text-amber-400 text-xs mt-0.5">{shovel.truckQueue.length} camiones</div>
              </div>
              <div className="bg-slate-950 p-2 rounded-lg border border-slate-800">
                <div className="text-[10px] text-slate-400 font-sans">Dureza UCS</div>
                <div className="font-bold text-purple-400 text-xs mt-0.5">{shovel.rockHardnessUCS} MPa</div>
              </div>
            </div>

            {/* Queue Visualization Strip */}
            <div className="bg-slate-950/70 p-2.5 rounded-lg border border-slate-800 flex items-center justify-between gap-2">
              <span className="text-[10px] text-slate-400 font-semibold uppercase">Camiones Asignados:</span>
              <div className="flex items-center gap-1.5 flex-wrap">
                {state.trucks
                  .filter((t) => t.assignedShovelId === shovel.id)
                  .map((t) => (
                    <button
                      key={t.id}
                      onClick={() => onSelectTruck(t.id)}
                      className={`px-2 py-0.5 rounded font-mono text-[10px] font-bold border transition ${
                        t.id === shovel.currentTruckLoadingId
                          ? 'bg-purple-500/20 text-purple-300 border-purple-500'
                          : shovel.truckQueue.includes(t.id)
                          ? 'bg-amber-500/20 text-amber-300 border-amber-500'
                          : 'bg-slate-800 text-slate-300 border-slate-700'
                      }`}
                    >
                      {t.id}
                    </button>
                  ))}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Main Fleet Matrix Table */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-xl space-y-3 flex-1 flex flex-col">
        {/* Table Search & Filter Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <h3 className="font-bold text-slate-200 uppercase tracking-wider text-xs">
              Matriz Operacional de Camiones de Extracción ({filteredTrucks.length})
            </h3>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {/* Search Input */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Buscar camión..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="bg-slate-950 border border-slate-800 rounded-lg pl-8 pr-3 py-1 text-xs text-slate-200 focus:outline-none focus:border-amber-500 w-36 sm:w-48 font-mono"
              />
            </div>

            {/* Cycle State Filter */}
            <select
              value={stateFilter}
              onChange={(e) => setStateFilter(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-amber-500 cursor-pointer"
            >
              <option value="ALL">Todos los Estados</option>
              <option value="HAULING">Cargado (Hauling)</option>
              <option value="LOADING">En Carguío (Loading)</option>
              <option value="QUEUE_SHOVEL">En Cola Pala</option>
              <option value="QUEUE_DESTINATION">En Cola Chancador</option>
              <option value="RETURNING">Retorno Vacío</option>
              <option value="DUMPING">Descarga</option>
            </select>
          </div>
        </div>

        {/* Fleet Table */}
        <div className="overflow-x-auto flex-1">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 text-slate-400 font-semibold uppercase text-[10px] tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-3">Camión / Modelo</th>
                <th className="py-2.5 px-3">Estado Ciclo</th>
                <th className="py-2.5 px-3">Pala Asignada</th>
                <th className="py-2.5 px-3">Destino</th>
                <th className="py-2.5 px-3 text-right">Carga (t)</th>
                <th className="py-2.5 px-3 text-right">Velocidad</th>
                <th className="py-2.5 px-3 text-right">Consumo (L/h)</th>
                <th className="py-2.5 px-3 text-right">Salud Twin</th>
                <th className="py-2.5 px-3 text-center">Acción Despacho</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {filteredTrucks.map((truck) => (
                <tr
                  key={truck.id}
                  className={`hover:bg-slate-800/40 transition cursor-pointer ${
                    truck.id === state.selectedAssetId ? 'bg-amber-500/10' : ''
                  }`}
                  onClick={() => onSelectTruck(truck.id)}
                >
                  <td className="py-2.5 px-3 font-semibold text-white font-sans flex items-center gap-2">
                    <span className="font-mono text-amber-400">{truck.id}</span>
                    <span className="text-[11px] text-slate-400 font-normal">({truck.model})</span>
                  </td>

                  <td className="py-2.5 px-3">
                    <span
                      className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-bold border ${getCycleBadgeColor(
                        truck.cycleState
                      )}`}
                    >
                      {truck.cycleState}
                    </span>
                  </td>

                  <td className="py-2.5 px-3 text-slate-200">
                    <span className="font-bold text-amber-400">{truck.assignedShovelId}</span>
                  </td>

                  <td className="py-2.5 px-3 text-slate-300 text-[11px]">
                    {truck.destinationId} ({truck.destinationType})
                  </td>

                  <td className="py-2.5 px-3 text-right font-bold text-slate-200">
                    {Math.round(truck.payloadCurrent)} <span className="text-[10px] text-slate-500">/ {truck.payloadCapacity}t</span>
                  </td>

                  <td className="py-2.5 px-3 text-right font-bold text-sky-400">
                    {Math.round(truck.speed)} km/h
                  </td>

                  <td className="py-2.5 px-3 text-right text-purple-300">
                    {Math.round(truck.fuelRate)}
                  </td>

                  <td className="py-2.5 px-3 text-right">
                    <span
                      className={`font-bold ${
                        truck.healthScore > 85
                          ? 'text-emerald-400'
                          : truck.healthScore > 70
                          ? 'text-amber-400'
                          : 'text-rose-400'
                      }`}
                    >
                      {truck.healthScore}%
                    </span>
                  </td>

                  <td className="py-2.5 px-3 text-center" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() =>
                        onManualReassignTruck(truck.id, truck.assignedShovelId === 'EX-01' ? 'EX-02' : 'EX-01')
                      }
                      className="px-2 py-1 bg-slate-800 hover:bg-amber-500 hover:text-slate-950 text-slate-300 rounded font-sans text-[10px] font-semibold transition border border-slate-700"
                      title={`Reasignar a Pala ${truck.assignedShovelId === 'EX-01' ? 'EX-02' : 'EX-01'}`}
                    >
                      ⇄ Reasignar a {truck.assignedShovelId === 'EX-01' ? 'EX-02' : 'EX-01'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
