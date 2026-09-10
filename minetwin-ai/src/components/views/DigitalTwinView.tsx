/**
 * MineTwin AI - Digital Twin 3D View & Command Interface
 */

import React from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CheckCircle,
  Clock,
  Compass,
  Crosshair,
  Flame,
  Fuel,
  Gauge,
  Layers,
  Sparkles,
  Truck,
  Zap,
} from 'lucide-react';
import { DigitalTwinState } from '../../types/mining';
import { ThreeMineScene } from '../ThreeMineScene';

interface DigitalTwinViewProps {
  state: DigitalTwinState;
  onSelectAsset: (id: string, type: 'TRUCK' | 'SHOVEL' | 'DRILL' | 'BLAST' | 'CRUSHER' | 'BLOCK' | 'ROAD') => void;
  onOpenAssetDetail: (id: string) => void;
  onOpenRecommendations: () => void;
  onApproveRecommendation: (id: string) => void;
}

export const DigitalTwinView: React.FC<DigitalTwinViewProps> = ({
  state,
  onSelectAsset,
  onOpenAssetDetail,
  onOpenRecommendations,
  onApproveRecommendation,
}) => {
  const selectedTruck = state.trucks.find((t) => t.id === state.selectedAssetId);
  const selectedShovel = state.shovels.find((s) => s.id === state.selectedAssetId);
  const selectedDrill = state.drills.find((d) => d.id === state.selectedAssetId);

  const pendingRec = state.recommendations.find((r) => r.status === 'PENDING_REVIEW');

  return (
    <div className="relative w-full h-full flex flex-col overflow-hidden bg-slate-950">
      {/* Main 3D Canvas */}
      <div className="flex-1 relative w-full h-full">
        <ThreeMineScene state={state} onSelectAsset={onSelectAsset} />

        {/* Top-Right Mini Status Telemetry Panel */}
        <div className="absolute top-4 right-4 z-10 w-72 bg-slate-900/90 backdrop-blur-md border border-slate-800/90 rounded-xl p-3 shadow-2xl text-xs space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="font-bold text-slate-200 flex items-center gap-1.5">
              <Compass className="w-3.5 h-3.5 text-amber-400" /> Monitoreo de Pit Activo
            </span>
            <span className="font-mono text-[10px] text-emerald-400 font-bold bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
              14/14 FLOTA ACTIVA
            </span>
          </div>

          {/* Shovels Status Summary */}
          <div className="space-y-2">
            {state.shovels.map((sh) => (
              <div
                key={sh.id}
                onClick={() => onSelectAsset(sh.id, 'SHOVEL')}
                className={`p-2 rounded-lg border transition cursor-pointer ${
                  sh.id === state.selectedAssetId
                    ? 'bg-amber-500/15 border-amber-500/50 text-amber-200'
                    : 'bg-slate-950/60 border-slate-800 hover:border-slate-700 text-slate-300'
                }`}
              >
                <div className="flex items-center justify-between font-semibold">
                  <span className="flex items-center gap-1">
                    ⛏️ {sh.name.split('(')[0]}
                  </span>
                  <span className="font-mono text-amber-400">{sh.productivityTph} t/h</span>
                </div>
                <div className="flex items-center justify-between text-[11px] text-slate-400 mt-1">
                  <span>Cargando: <b className="text-slate-200 font-mono">{sh.currentTruckLoadingId || 'Ninguno'}</b></span>
                  <span>Cola: <b className="text-amber-400 font-mono">{sh.truckQueue.length} camiones</b></span>
                </div>
              </div>
            ))}
          </div>

          {/* Primary Crusher Level */}
          <div
            onClick={() => onSelectAsset('CR-01', 'CRUSHER')}
            className="bg-slate-950/60 border border-slate-800 hover:border-slate-700 p-2 rounded-lg cursor-pointer text-slate-300 transition"
          >
            <div className="flex items-center justify-between font-semibold">
              <span className="flex items-center gap-1">🏭 Chancador CR-01</span>
              <span className="font-mono text-sky-400">{state.crusher.throughputTph} t/h</span>
            </div>
            <div className="mt-1.5">
              <div className="flex justify-between text-[10px] text-slate-400 mb-0.5">
                <span>Nivel Tolva</span>
                <span className="font-mono text-slate-200">{state.crusher.chokeLevelPercent}%</span>
              </div>
              <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${
                    state.crusher.chokeLevelPercent > 80 ? 'bg-rose-500' : 'bg-sky-500'
                  }`}
                  style={{ width: `${state.crusher.chokeLevelPercent}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Selected Asset Quick Inspector Card */}
        {(selectedTruck || selectedShovel || selectedDrill) && (
          <div className="absolute bottom-4 left-4 z-10 max-w-md w-full bg-slate-900/95 backdrop-blur-md border border-amber-500/40 rounded-xl p-3.5 shadow-2xl text-xs space-y-2.5 animate-in fade-in slide-in-from-bottom-2">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <div className="flex items-center gap-2">
                <div className="p-1.5 bg-amber-500/20 text-amber-400 rounded-lg">
                  {selectedTruck ? <Truck className="w-4 h-4" /> : <Flame className="w-4 h-4" />}
                </div>
                <div>
                  <h3 className="font-bold text-white text-sm">
                    {selectedTruck ? selectedTruck.name : selectedShovel ? selectedShovel.name : selectedDrill?.name}
                  </h3>
                  <p className="text-[10px] text-slate-400 font-mono">
                    {selectedTruck?.model || selectedShovel?.model || selectedDrill?.model}
                  </p>
                </div>
              </div>

              <button
                onClick={() => onOpenAssetDetail(state.selectedAssetId!)}
                className="px-2.5 py-1 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded-lg transition text-[11px] flex items-center gap-1 shadow-md shadow-amber-500/20"
              >
                <span>Inspeccionar Twin</span>
                <ArrowRight className="w-3 h-3" />
              </button>
            </div>

            {selectedTruck && (
              <div className="grid grid-cols-4 gap-2 text-center pt-1 font-mono">
                <div className="bg-slate-950/70 p-1.5 rounded-lg border border-slate-800">
                  <div className="text-[9px] text-slate-400 font-sans">Estado</div>
                  <div className="font-bold text-emerald-400 text-[11px] truncate">{selectedTruck.cycleState}</div>
                </div>
                <div className="bg-slate-950/70 p-1.5 rounded-lg border border-slate-800">
                  <div className="text-[9px] text-slate-400 font-sans">Carga</div>
                  <div className="font-bold text-amber-400 text-[11px]">{Math.round(selectedTruck.payloadCurrent)} t</div>
                </div>
                <div className="bg-slate-950/70 p-1.5 rounded-lg border border-slate-800">
                  <div className="text-[9px] text-slate-400 font-sans">Velocidad</div>
                  <div className="font-bold text-sky-400 text-[11px]">{Math.round(selectedTruck.speed)} km/h</div>
                </div>
                <div className="bg-slate-950/70 p-1.5 rounded-lg border border-slate-800">
                  <div className="text-[9px] text-slate-400 font-sans">Salud Twin</div>
                  <div className="font-bold text-emerald-300 text-[11px]">{selectedTruck.healthScore}%</div>
                </div>
              </div>
            )}

            {selectedShovel && (
              <div className="grid grid-cols-4 gap-2 text-center pt-1 font-mono">
                <div className="bg-slate-950/70 p-1.5 rounded-lg border border-slate-800">
                  <div className="text-[9px] text-slate-400 font-sans">Productividad</div>
                  <div className="font-bold text-amber-400 text-[11px]">{selectedShovel.productivityTph} t/h</div>
                </div>
                <div className="bg-slate-950/70 p-1.5 rounded-lg border border-slate-800">
                  <div className="text-[9px] text-slate-400 font-sans">Pase Actual</div>
                  <div className="font-bold text-sky-400 text-[11px]">{selectedShovel.diggingTimeSeconds}s</div>
                </div>
                <div className="bg-slate-950/70 p-1.5 rounded-lg border border-slate-800">
                  <div className="text-[9px] text-slate-400 font-sans">Dureza UCS</div>
                  <div className="font-bold text-purple-400 text-[11px]">{selectedShovel.rockHardnessUCS} MPa</div>
                </div>
                <div className="bg-slate-950/70 p-1.5 rounded-lg border border-slate-800">
                  <div className="text-[9px] text-slate-400 font-sans">Disponibilidad</div>
                  <div className="font-bold text-emerald-400 text-[11px]">{selectedShovel.availability}%</div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* AI Recommendation Banner (Human-in-the-Loop) */}
        {pendingRec && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 max-w-xl w-full mx-auto px-4">
            <div className="bg-gradient-to-r from-slate-900/95 via-amber-950/70 to-slate-900/95 border border-amber-500/60 rounded-xl p-3 shadow-2xl backdrop-blur-md flex items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2.5 flex-1 min-w-0">
                <div className="p-2 bg-amber-500/20 text-amber-400 rounded-lg flex-shrink-0 animate-pulse">
                  <Sparkles className="w-4 h-4" />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-amber-300 truncate">{pendingRec.title}</span>
                    <span className="font-mono text-[10px] text-emerald-400 bg-emerald-500/10 px-1 rounded border border-emerald-500/30">
                      {Math.round(pendingRec.confidence * 100)}% Confianza
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-300 truncate mt-0.5">{pendingRec.what}</p>
                </div>
              </div>

              <div className="flex items-center gap-1.5 flex-shrink-0">
                <button
                  onClick={() => onApproveRecommendation(pendingRec.id)}
                  className="px-2.5 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded-lg transition flex items-center gap-1 text-[11px]"
                >
                  <CheckCircle className="w-3 h-3" />
                  <span>Aprobar</span>
                </button>
                <button
                  onClick={onOpenRecommendations}
                  className="px-2 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium rounded-lg transition text-[11px]"
                >
                  Detalles
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
