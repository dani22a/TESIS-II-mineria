/**
 * MineTwin AI - Industrial Navigation Rail Sidebar
 */

import React from 'react';
import {
  Award,
  Cpu,
  Database,
  Eye,
  Flame,
  Globe,
  MessageSquare,
  Sliders,
  TrendingUp,
  Truck,
} from 'lucide-react';

export type ActiveModule =
  | 'TWIN_3D'
  | 'DRILL_BLAST'
  | 'LOAD_HAUL'
  | 'MINE_TO_MILL'
  | 'SCENARIO_LAB'
  | 'COPILOT'
  | 'AI_OPTIMIZER'
  | 'ANALYTICS'
  | 'SYSTEM_DATA';

interface NavigationSidebarProps {
  activeModule: ActiveModule;
  onChangeModule: (module: ActiveModule) => void;
  visibleLayers: {
    equipment: boolean;
    haulRoads: boolean;
    trafficHeatmap: boolean;
    blastPatterns: boolean;
    blockModelGeology: boolean;
    fragmentationVisual: boolean;
    crusherPlant: boolean;
  };
  onToggleLayer: (layerKey: keyof NavigationSidebarProps['visibleLayers']) => void;
}

export const NavigationSidebar: React.FC<NavigationSidebarProps> = ({
  activeModule,
  onChangeModule,
  visibleLayers,
  onToggleLayer,
}) => {
  const navItems: { id: ActiveModule; label: string; icon: React.ReactNode; badge?: string }[] = [
    { id: 'TWIN_3D', label: 'Gemelo 3D', icon: <Globe className="w-5 h-5" />, badge: 'LIVE' },
    { id: 'DRILL_BLAST', label: 'Drill & Blast', icon: <Flame className="w-5 h-5" /> },
    { id: 'LOAD_HAUL', label: 'Load & Haul', icon: <Truck className="w-5 h-5" /> },
    { id: 'MINE_TO_MILL', label: 'Mine-to-Mill', icon: <Cpu className="w-5 h-5" /> },
    { id: 'SCENARIO_LAB', label: 'Scenario Lab', icon: <Sliders className="w-5 h-5" />, badge: 'What-If' },
    { id: 'COPILOT', label: 'Copiloto IA', icon: <MessageSquare className="w-5 h-5" />, badge: 'LangGraph' },
    { id: 'AI_OPTIMIZER', label: 'Optimizador DRL', icon: <Award className="w-5 h-5" />, badge: 'MAPPO' },
    { id: 'ANALYTICS', label: 'Analítica', icon: <TrendingUp className="w-5 h-5" /> },
    { id: 'SYSTEM_DATA', label: 'Datos & OT', icon: <Database className="w-5 h-5" /> },
  ];

  return (
    <aside className="w-16 lg:w-56 bg-slate-950/95 border-r border-slate-800/80 flex flex-col justify-between p-2 select-none z-20">
      {/* Primary Module Navigation */}
      <div className="space-y-1">
        <div className="px-2 py-1.5 hidden lg:block text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
          Módulos Operacionales
        </div>

        {navItems.map((item) => {
          const isActive = activeModule === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onChangeModule(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition group text-left ${
                isActive
                  ? 'bg-amber-500/15 text-amber-300 border border-amber-500/40 shadow-md shadow-amber-500/5'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/80'
              }`}
              title={item.label}
            >
              <div className={`${isActive ? 'text-amber-400' : 'text-slate-400 group-hover:text-slate-200'}`}>
                {item.icon}
              </div>
              <span className="hidden lg:inline flex-1 truncate">{item.label}</span>
              {item.badge && (
                <span
                  className={`hidden lg:inline-block px-1.5 py-0.5 text-[9px] font-mono rounded font-bold ${
                    isActive ? 'bg-amber-400 text-slate-950' : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Layer Visibility Quick Controls (Shown on large screens) */}
      <div className="hidden lg:block bg-slate-900/80 border border-slate-800/80 rounded-xl p-2.5 space-y-2">
        <div className="flex items-center justify-between text-[10px] font-bold text-slate-400 uppercase tracking-wider">
          <span className="flex items-center gap-1">
            <Eye className="w-3 h-3 text-amber-400" /> Capas 3D
          </span>
        </div>

        <div className="space-y-1 text-xs">
          <label className="flex items-center justify-between cursor-pointer py-0.5 text-slate-300 hover:text-white">
            <span className="text-[11px]">Equipos Móviles</span>
            <input
              type="checkbox"
              checked={visibleLayers.equipment}
              onChange={() => onToggleLayer('equipment')}
              className="rounded accent-amber-500 w-3.5 h-3.5 bg-slate-950"
            />
          </label>

          <label className="flex items-center justify-between cursor-pointer py-0.5 text-slate-300 hover:text-white">
            <span className="text-[11px]">Rutas & Rampas</span>
            <input
              type="checkbox"
              checked={visibleLayers.haulRoads}
              onChange={() => onToggleLayer('haulRoads')}
              className="rounded accent-amber-500 w-3.5 h-3.5 bg-slate-950"
            />
          </label>

          <label className="flex items-center justify-between cursor-pointer py-0.5 text-slate-300 hover:text-white">
            <span className="text-[11px]">Mapa Calor Tráfico</span>
            <input
              type="checkbox"
              checked={visibleLayers.trafficHeatmap}
              onChange={() => onToggleLayer('trafficHeatmap')}
              className="rounded accent-amber-500 w-3.5 h-3.5 bg-slate-950"
            />
          </label>

          <label className="flex items-center justify-between cursor-pointer py-0.5 text-slate-300 hover:text-white">
            <span className="text-[11px]">Patrón Tronadura</span>
            <input
              type="checkbox"
              checked={visibleLayers.blastPatterns}
              onChange={() => onToggleLayer('blastPatterns')}
              className="rounded accent-amber-500 w-3.5 h-3.5 bg-slate-950"
            />
          </label>

          <label className="flex items-center justify-between cursor-pointer py-0.5 text-slate-300 hover:text-white">
            <span className="text-[11px]">Modelo Bloques 3D</span>
            <input
              type="checkbox"
              checked={visibleLayers.blockModelGeology}
              onChange={() => onToggleLayer('blockModelGeology')}
              className="rounded accent-amber-500 w-3.5 h-3.5 bg-slate-950"
            />
          </label>
        </div>
      </div>
    </aside>
  );
};
