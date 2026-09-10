/**
 * MineTwin AI - Data Ingestion, OT Connectivity & Security RBAC Audit
 */

import React from 'react';
import {
  Activity,
  CheckCircle2,
  Database,
  Key,
  Layers,
  Lock,
  Radio,
  Server,
  ShieldCheck,
  UserCheck,
  Zap,
} from 'lucide-react';
import { DigitalTwinState, UserRole } from '../../types/mining';

interface SystemDataViewProps {
  state: DigitalTwinState;
  onChangeRole: (role: UserRole) => void;
}

export const SystemDataView: React.FC<SystemDataViewProps> = ({ state, onChangeRole }) => {
  const pipelines = [
    { name: 'Kafka Dispatch Event Hub', protocol: 'Kafka 3.4', status: 'ONLINE', latency: '42 ms', throughput: '18.4 k msg/s' },
    { name: 'OPC-UA Plant & Crusher Bridge', protocol: 'OPC-UA TCP', status: 'ONLINE', latency: '65 ms', throughput: '4.2 k tags/s' },
    { name: 'CAN-Bus Fleet Telemetry Broker', protocol: 'MQTT / TLS', status: 'ONLINE', latency: '120 ms', throughput: '14 trucks active' },
    { name: 'Drill Rig LiDAR & MWD Stream', protocol: 'gRPC Stream', status: 'ONLINE', latency: '85 ms', throughput: '2 rigs active' },
    { name: 'Block Model Geostats Engine', protocol: 'PostgreSQL / PostGIS', status: 'SYNCED', latency: '18 ms', throughput: '1,240 blocks cached' },
  ];

  const roles: { role: UserRole; title: string; desc: string }[] = [
    { role: 'OPERATOR', title: 'Operador de Despacho', desc: 'Monitoreo en vivo, ejecución de reasignaciones y aprobación de alertas.' },
    { role: 'MINE_ENGINEER', title: 'Ingeniero de Planificación Mina', desc: 'Ajuste de fases, rutas, límites de velocidad y restricciones operacionales.' },
    { role: 'DRILL_BLAST_ENGINEER', title: 'Especialista Drill & Blast', desc: 'Diseño de mallas de perforación, factores de carga y física Kuz-Ram.' },
    { role: 'METALLURGIST', title: 'Metalurgista / Superintendente Planta', desc: 'Optimización de molienda SAG, chancado primario y recuperación Cu.' },
    { role: 'DATA_SCIENTIST', title: 'Científico de Datos / DRL Lead', desc: 'Ponderación de función de recompensa, curriculum learning y shadow evaluation.' },
  ];

  const auditEvents = [
    { time: '14:22:10', user: 'AI-MAPPO-Agent', action: 'Recomendó rebalanceo de HT-07 a Pala EX-02', status: 'PENDIENTE' },
    { time: '14:18:45', user: 'Op. C. Valenzuela', action: 'Aprobó recomendación DRL para optimización de tolva CR-01', status: 'APROBADO' },
    { time: '14:10:02', user: 'Ing. D&B R. Gomez', action: 'Ajustó Factor de Carga en Malla #104 a 0.88 kg/m³', status: 'EJECUTADO' },
    { time: '13:55:18', user: 'Sistema Twin', action: 'Ejecutó sincronización horaria de Modelo de Bloques 3D', status: 'COMPLETADO' },
  ];

  return (
    <div className="w-full h-full flex flex-col p-4 gap-4 overflow-y-auto bg-slate-950 text-slate-100 select-none">
      {/* Title Header */}
      <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-xl shadow-lg flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-amber-500/20 text-amber-400 rounded-xl">
            <Database className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white tracking-tight">
              Infraestructura de Datos OT/IT, Calidad de Sensores & RBAC
            </h2>
            <p className="text-xs text-slate-400">
              Arquitectura de streaming en tiempo real (Kafka, OPC-UA, MQTT), control de acceso por roles y auditoría
            </p>
          </div>
        </div>
      </div>

      {/* Grid: Pipelines & RBAC Switcher */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left: OT/IT Streaming Pipelines (7 Cols) */}
        <div className="lg:col-span-7 bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-xl text-xs space-y-3">
          <h3 className="font-bold text-slate-200 uppercase tracking-wider text-xs flex items-center gap-1.5 border-b border-slate-800 pb-2">
            <Server className="w-4 h-4 text-emerald-400" /> Pipelines de Ingestión en Tiempo Real (OT / SCADA)
          </h3>

          <div className="space-y-2">
            {pipelines.map((pip, idx) => (
              <div key={idx} className="bg-slate-950 p-3 rounded-xl border border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
                  <div>
                    <div className="font-bold text-slate-200 text-xs">{pip.name}</div>
                    <div className="text-[10px] text-slate-400 font-mono">{pip.protocol}</div>
                  </div>
                </div>

                <div className="text-right font-mono text-[11px]">
                  <div className="text-emerald-400 font-bold">{pip.status}</div>
                  <div className="text-slate-400 text-[10px]">Latencia: {pip.latency} • {pip.throughput}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: RBAC Security Role Selector (5 Cols) */}
        <div className="lg:col-span-5 bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-xl text-xs space-y-3">
          <h3 className="font-bold text-slate-200 uppercase tracking-wider text-xs flex items-center gap-1.5 border-b border-slate-800 pb-2">
            <ShieldCheck className="w-4 h-4 text-amber-400" /> Control de Acceso por Roles (RBAC)
          </h3>

          <div className="space-y-2">
            {roles.map((r) => {
              const isSelected = state.currentUserRole === r.role;
              return (
                <div
                  key={r.role}
                  onClick={() => onChangeRole(r.role)}
                  className={`p-2.5 rounded-xl border transition cursor-pointer ${
                    isSelected
                      ? 'bg-amber-500/15 border-amber-500/60 text-amber-200 shadow-md'
                      : 'bg-slate-950 border-slate-800 hover:border-slate-700 text-slate-300'
                  }`}
                >
                  <div className="flex items-center justify-between font-bold text-xs">
                    <span>{r.title}</span>
                    {isSelected && <span className="text-[10px] text-amber-400 font-mono">ACTIVO</span>}
                  </div>
                  <p className="text-[10px] text-slate-400 mt-1">{r.desc}</p>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Bottom: Audit Trail Log */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-xl text-xs space-y-3">
        <h3 className="font-bold text-slate-200 uppercase tracking-wider text-xs flex items-center gap-1.5 border-b border-slate-800 pb-2">
          <UserCheck className="w-4 h-4 text-sky-400" /> Registro Inmutable de Auditoría & Trazabilidad
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono text-xs">
            <thead className="bg-slate-950/80 text-slate-400 font-semibold uppercase text-[10px] tracking-wider border-b border-slate-800 font-sans">
              <tr>
                <th className="py-2 px-3">Hora UTC</th>
                <th className="py-2 px-3">Usuario / Entidad</th>
                <th className="py-2 px-3">Acción Operacional Registrada</th>
                <th className="py-2 px-3 text-center">Estado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {auditEvents.map((evt, idx) => (
                <tr key={idx} className="hover:bg-slate-800/40">
                  <td className="py-2 px-3 text-slate-400">{evt.time}</td>
                  <td className="py-2 px-3 text-amber-400 font-bold font-sans">{evt.user}</td>
                  <td className="py-2 px-3 text-slate-200 font-sans">{evt.action}</td>
                  <td className="py-2 px-3 text-center">
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${
                        evt.status === 'APROBADO' || evt.status === 'COMPLETADO'
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : evt.status === 'PENDIENTE'
                          ? 'bg-amber-500/20 text-amber-300'
                          : 'bg-sky-500/20 text-sky-300'
                      }`}
                    >
                      {evt.status}
                    </span>
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
