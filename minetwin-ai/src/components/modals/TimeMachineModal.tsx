/**
 * MineTwin AI - Time Machine & Predictive Forward Projection Modal
 */

import React, { useState } from 'react';
import {
  Activity,
  AlertCircle,
  Calendar,
  Clock,
  FastForward,
  Flame,
  Layers,
  Pause,
  Play,
  RotateCcw,
  Sparkles,
  TrendingUp,
  X,
  Zap,
} from 'lucide-react';
import { DigitalTwinState } from '../../types/mining';

interface TimeMachineModalProps {
  isOpen: boolean;
  onClose: () => void;
  state: DigitalTwinState;
}

export const TimeMachineModal: React.FC<TimeMachineModalProps> = ({
  isOpen,
  onClose,
  state,
}) => {
  if (!isOpen) return null;

  const [timeOffsetHours, setTimeOffsetHours] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [speedMultiplier, setSpeedMultiplier] = useState<number>(1);

  const forecastEvents = [
    { offset: -4, time: '10:00', title: 'Inicio de turno A', type: 'HISTORICAL' },
    { offset: -2, time: '12:00', title: 'Disparo malla #103 (banco 3840)', type: 'HISTORICAL' },
    { offset: 0, time: '14:24', title: 'Tiempo real actual', type: 'NOW' },
    { offset: 3, time: '17:30', title: 'Tronadura malla #104 (P80 = 178 mm)', type: 'FORECAST' },
    { offset: 8, time: '22:30', title: 'Mantenimiento preventivo pala EX-01', type: 'FORECAST' },
    { offset: 16, time: '06:30 (+1d)', title: 'Cambio de fase y cambio de turno B', type: 'FORECAST' },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200 select-none">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-sky-500/20 text-sky-400 rounded-xl">
              <Clock className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">
                Línea de tiempo: historial y proyección (+24 h)
              </h2>
              <p className="text-xs text-slate-400">
                Navegación temporal para auditoría retrospectiva y predicción de cuellos de botella
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

        {/* Time Slider Controls */}
        <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-300">Línea de Tiempo del Gemelo</span>
            <span
              className={`font-mono font-bold text-sm px-2.5 py-0.5 rounded-lg border ${
                timeOffsetHours === 0
                  ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                  : timeOffsetHours > 0
                  ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                  : 'bg-sky-500/20 text-sky-300 border-sky-500/40'
              }`}
            >
              {timeOffsetHours === 0
                ? '🔴 TIEMPO REAL (0h)'
                : timeOffsetHours > 0
                ? `🔮 PROYECCIÓN +${timeOffsetHours}h`
                : `⏪ REPLAY HISTÓRICO ${timeOffsetHours}h`}
            </span>
          </div>

          <input
            type="range"
            min="-8"
            max="24"
            step="1"
            value={timeOffsetHours}
            onChange={(e) => setTimeOffsetHours(parseInt(e.target.value, 10))}
            className="w-full accent-amber-500 cursor-pointer"
          />

          <div className="flex justify-between text-[10px] text-slate-500 font-mono">
            <span>-8h (Inicio Turno)</span>
            <span>-4h</span>
            <span className="text-emerald-400 font-bold">0h (Ahora)</span>
            <span>+8h</span>
            <span>+16h</span>
            <span>+24h (Fin Ciclo)</span>
          </div>

          {/* Playback Speed Controls */}
          <div className="flex items-center justify-between pt-2 border-t border-slate-800/80">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setIsPlaying(!isPlaying)}
                className="px-3 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded-lg transition text-xs flex items-center gap-1.5"
              >
                {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 fill-current" />}
                <span>{isPlaying ? 'Pausar' : 'Reproducir'}</span>
              </button>

              <button
                onClick={() => setTimeOffsetHours(0)}
                className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs transition flex items-center gap-1"
              >
                <RotateCcw className="w-3 h-3" /> Ahora
              </button>
            </div>

            <div className="flex items-center gap-1 text-xs">
              <span className="text-slate-400 text-[11px] mr-1">Velocidad:</span>
              {[1, 2, 5, 10].map((spd) => (
                <button
                  key={spd}
                  onClick={() => setSpeedMultiplier(spd)}
                  className={`px-2 py-0.5 rounded font-mono text-[11px] font-bold border transition ${
                    speedMultiplier === spd
                      ? 'bg-amber-500/20 border-amber-500 text-amber-300'
                      : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {spd}x
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Milestone Schedule Strip */}
        <div className="space-y-2">
          <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
            Eventos Operacionales Programados
          </h3>

          <div className="space-y-1.5">
            {forecastEvents.map((evt, idx) => (
              <div
                key={idx}
                onClick={() => setTimeOffsetHours(evt.offset)}
                className={`p-2.5 rounded-xl border text-xs flex items-center justify-between transition cursor-pointer ${
                  timeOffsetHours === evt.offset
                    ? 'bg-amber-500/15 border-amber-500/60 text-amber-200'
                    : 'bg-slate-950 border-slate-800 hover:border-slate-700 text-slate-300'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <span className="font-mono text-[11px] text-amber-400 font-bold">{evt.time}</span>
                  <span className="font-medium text-slate-200">{evt.title}</span>
                </div>
                <span
                  className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded ${
                    evt.type === 'NOW'
                      ? 'bg-emerald-500/20 text-emerald-300'
                      : evt.type === 'FORECAST'
                      ? 'bg-purple-500/20 text-purple-300'
                      : 'bg-sky-500/20 text-sky-300'
                  }`}
                >
                  {evt.type === 'NOW' ? 'Ahora' : evt.type === 'FORECAST' ? 'Pronóstico' : 'Histórico'}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="flex justify-end pt-2">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl font-medium transition text-xs"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
};
