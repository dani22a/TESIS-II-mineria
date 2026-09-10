/**
 * MineTwin AI - Operational Alerts & Exceptions Manager Modal
 */

import React from 'react';
import {
  Activity,
  AlertOctagon,
  AlertTriangle,
  Bell,
  CheckCircle,
  Info,
  ShieldAlert,
  X,
} from 'lucide-react';
import { DigitalTwinAlert, DigitalTwinState } from '../../types/mining';

interface AlertsModalProps {
  isOpen: boolean;
  onClose: () => void;
  state: DigitalTwinState;
  onAcknowledgeAlert: (alertId: string) => void;
}

export const AlertsModal: React.FC<AlertsModalProps> = ({
  isOpen,
  onClose,
  state,
  onAcknowledgeAlert,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200 select-none">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-rose-500/20 text-rose-400 rounded-xl">
              <Bell className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">
                Gestión de Alarmas & Eventos Críticos de Mina
              </h2>
              <p className="text-xs text-slate-400">
                Notificaciones automáticas de seguridad, cuellos de botella y desviaciones operacionales
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

        {/* Alerts List */}
        <div className="space-y-3">
          {state.alerts.map((alert) => (
            <div
              key={alert.id}
              className={`p-3.5 rounded-xl border text-xs space-y-2 transition ${
                alert.acknowledged
                  ? 'bg-slate-950/60 border-slate-800 opacity-60'
                  : alert.severity === 'CRITICAL'
                  ? 'bg-rose-500/10 border-rose-500/50'
                  : alert.severity === 'WARNING'
                  ? 'bg-amber-500/10 border-amber-500/50'
                  : 'bg-sky-500/10 border-sky-500/50'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {alert.severity === 'CRITICAL' ? (
                    <AlertOctagon className="w-4 h-4 text-rose-400" />
                  ) : alert.severity === 'WARNING' ? (
                    <AlertTriangle className="w-4 h-4 text-amber-400" />
                  ) : (
                    <Info className="w-4 h-4 text-sky-400" />
                  )}
                  <span className="font-bold text-slate-200">{alert.title}</span>
                </div>

                <div className="flex items-center gap-2">
                  <span className="font-mono text-[10px] text-slate-400">{alert.timestamp}</span>
                  <span
                    className={`font-mono text-[9px] font-bold px-1.5 py-0.5 rounded ${
                      alert.severity === 'CRITICAL'
                        ? 'bg-rose-500/20 text-rose-300'
                        : alert.severity === 'WARNING'
                        ? 'bg-amber-500/20 text-amber-300'
                        : 'bg-sky-500/20 text-sky-300'
                    }`}
                  >
                    {alert.severity}
                  </span>
                </div>
              </div>

              <p className="text-slate-300">{alert.message}</p>

              {alert.mitigatingAction && (
                <div className="bg-slate-900/80 p-2 rounded-lg border border-slate-800 text-[11px]">
                  <span className="font-bold text-amber-400">Acción Mitigadora Recomendada: </span>
                  <span className="text-slate-300">{alert.mitigatingAction}</span>
                </div>
              )}

              {!alert.acknowledged && (
                <div className="flex justify-end pt-1">
                  <button
                    onClick={() => onAcknowledgeAlert(alert.id)}
                    className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold transition flex items-center gap-1"
                  >
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Reconocer Alarma</span>
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="flex justify-end pt-2">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl font-medium transition text-xs"
          >
            Cerrar Alarmas
          </button>
        </div>
      </div>
    </div>
  );
};
