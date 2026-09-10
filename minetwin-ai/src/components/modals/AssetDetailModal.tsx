/**
 * MineTwin AI - Asset Digital Twin Detailed Inspector Modal
 */

import React from 'react';
import {
  Activity,
  AlertTriangle,
  BatteryCharging,
  Clock,
  Compass,
  Flame,
  Fuel,
  Gauge,
  Layers,
  Thermometer,
  Truck,
  Wrench,
  X,
  Zap,
} from 'lucide-react';
import { DigitalTwinState } from '../../types/mining';

interface AssetDetailModalProps {
  assetId: string | null;
  state: DigitalTwinState;
  onClose: () => void;
  onReassignTruck?: (truckId: string, shovelId: string) => void;
}

export const AssetDetailModal: React.FC<AssetDetailModalProps> = ({
  assetId,
  state,
  onClose,
  onReassignTruck,
}) => {
  if (!assetId) return null;

  const truck = state.trucks.find((t) => t.id === assetId);
  const shovel = state.shovels.find((s) => s.id === assetId);
  const drill = state.drills.find((d) => d.id === assetId);
  const pattern = state.blastPatterns.find((p) => p.id === assetId);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200 select-none">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-amber-500/20 text-amber-400 rounded-xl">
              {truck ? <Truck className="w-6 h-6" /> : shovel ? <span className="text-xl">⛏️</span> : drill ? <span className="text-xl">🚜</span> : <Flame className="w-6 h-6" />}
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">
                {truck ? truck.name : shovel ? shovel.name : drill ? drill.name : pattern?.name || assetId}
              </h2>
              <p className="text-xs text-slate-400 font-mono">
                ID: {assetId} • {truck?.model || shovel?.model || drill?.model || 'Activo Mina'}
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

        {/* Truck Specific Inspector */}
        {truck && (
          <div className="space-y-4 text-xs">
            {/* Live Operational Metrics Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono">
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                <div className="text-[10px] text-slate-400 font-sans">Estado de Ciclo</div>
                <div className="text-sm font-bold text-emerald-400 mt-1">{truck.cycleState}</div>
              </div>
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                <div className="text-[10px] text-slate-400 font-sans">Carga Actual</div>
                <div className="text-sm font-bold text-amber-400 mt-1">{Math.round(truck.payloadCurrent)} / {truck.payloadCapacity} t</div>
              </div>
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                <div className="text-[10px] text-slate-400 font-sans">Velocidad GPS</div>
                <div className="text-sm font-bold text-sky-400 mt-1">{Math.round(truck.speed)} km/h</div>
              </div>
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                <div className="text-[10px] text-slate-400 font-sans">Salud Mecánica Twin</div>
                <div className="text-sm font-bold text-emerald-300 mt-1">{truck.healthScore}%</div>
              </div>
            </div>

            {/* Sub-system Sensors */}
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3">
              <h3 className="font-bold text-slate-200 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
                <Thermometer className="w-4 h-4 text-amber-400" /> Sensores Telemetría CAN-Bus en Vivo
              </h3>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 font-mono">
                <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                  <div className="text-[10px] text-slate-400 font-sans">Temperatura Motor</div>
                  <div className="font-bold text-slate-200 mt-0.5">{truck.engineTempCelsius}°C</div>
                </div>
                <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                  <div className="text-[10px] text-slate-400 font-sans">Presión Neumáticos</div>
                  <div className="font-bold text-slate-200 mt-0.5">{truck.tirePressurePsi} PSI</div>
                </div>
                <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                  <div className="text-[10px] text-slate-400 font-sans">Consumo Instantáneo</div>
                  <div className="font-bold text-purple-300 mt-0.5">{Math.round(truck.fuelRate)} L/h</div>
                </div>
                <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                  <div className="text-[10px] text-slate-400 font-sans">Nivel Estanque Diésel</div>
                  <div className="font-bold text-amber-400 mt-0.5">{truck.fuelLevelLiters.toFixed(0)} L</div>
                </div>
                <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                  <div className="text-[10px] text-slate-400 font-sans">Pala Asignada</div>
                  <div className="font-bold text-sky-400 mt-0.5">{truck.assignedShovelId}</div>
                </div>
                <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                  <div className="text-[10px] text-slate-400 font-sans">Destino Actual</div>
                  <div className="font-bold text-slate-200 mt-0.5">{truck.destinationId}</div>
                </div>
              </div>
            </div>

            {/* Quick Reassignment Controls */}
            {onReassignTruck && (
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 flex items-center justify-between">
                <div>
                  <div className="font-bold text-slate-200">Reasignar Pala de Carguío</div>
                  <div className="text-[11px] text-slate-400">Modificar ruta de despacho manualmente</div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => onReassignTruck(truck.id, 'EX-01')}
                    className={`px-3 py-1.5 rounded-lg font-bold transition font-mono ${
                      truck.assignedShovelId === 'EX-01'
                        ? 'bg-amber-500 text-slate-950'
                        : 'bg-slate-800 hover:bg-slate-700 text-slate-300'
                    }`}
                  >
                    EX-01 (Banco 3840)
                  </button>
                  <button
                    onClick={() => onReassignTruck(truck.id, 'EX-02')}
                    className={`px-3 py-1.5 rounded-lg font-bold transition font-mono ${
                      truck.assignedShovelId === 'EX-02'
                        ? 'bg-amber-500 text-slate-950'
                        : 'bg-slate-800 hover:bg-slate-700 text-slate-300'
                    }`}
                  >
                    EX-02 (Banco 3680)
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Shovel Specific Inspector */}
        {shovel && (
          <div className="space-y-4 text-xs font-sans">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono">
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                <div className="text-[10px] text-slate-400 font-sans">Productividad Horaria</div>
                <div className="text-sm font-bold text-amber-400 mt-1">{shovel.productivityTph} t/h</div>
              </div>
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                <div className="text-[10px] text-slate-400 font-sans">Pase Actual (s)</div>
                <div className="text-sm font-bold text-sky-400 mt-1">{shovel.diggingTimeSeconds}s</div>
              </div>
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                <div className="text-[10px] text-slate-400 font-sans">Dureza Roca (UCS)</div>
                <div className="text-sm font-bold text-purple-400 mt-1">{shovel.rockHardnessUCS} MPa</div>
              </div>
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                <div className="text-[10px] text-slate-400 font-sans">Disponibilidad</div>
                <div className="text-sm font-bold text-emerald-400 mt-1">{shovel.availability}%</div>
              </div>
            </div>

            <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-2">
              <h4 className="font-bold text-slate-200">Cola de Camiones en Espera:</h4>
              <p className="text-slate-400 font-mono">
                {shovel.truckQueue.length > 0 ? shovel.truckQueue.join(', ') : 'No hay camiones en espera actualmente.'}
              </p>
            </div>
          </div>
        )}

        <div className="flex justify-end pt-2">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl font-medium transition text-xs"
          >
            Cerrar Inspector
          </button>
        </div>
      </div>
    </div>
  );
};
