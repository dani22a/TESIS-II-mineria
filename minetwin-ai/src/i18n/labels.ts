/**
 * Etiquetas de UI en español latino neutro.
 * Los códigos internos (HAULING, CRUSHER, etc.) se mantienen en el dominio.
 */

import {
  CycleState,
  DigitalTwinAlert,
  DRLRecommendation,
  MaterialType,
  UserRole,
} from '../types/mining';

export const CYCLE_STATE_LABELS: Record<CycleState, string> = {
  AVAILABLE: 'Disponible',
  ASSIGNED: 'Asignado',
  EMPTY_TRAVEL: 'Viaje vacío',
  QUEUE_SHOVEL: 'En cola de pala',
  SPOTTING: 'Aculatamiento',
  LOADING: 'En carguío',
  HAULING: 'Acarreo cargado',
  QUEUE_DESTINATION: 'En cola de destino',
  DUMPING: 'En descarga',
  RETURNING: 'Retorno vacío',
  STANDBY: 'En espera',
  MAINTENANCE: 'Mantenimiento',
};

export const DESTINATION_TYPE_LABELS: Record<
  'SHOVEL' | 'CRUSHER' | 'WASTE_DUMP' | 'STOCKPILE',
  string
> = {
  SHOVEL: 'Pala',
  CRUSHER: 'Chancador',
  WASTE_DUMP: 'Botadero',
  STOCKPILE: 'Acopio',
};

export const MATERIAL_TYPE_LABELS: Record<MaterialType, string> = {
  HIGH_GRADE_CU: 'Cobre de alta ley',
  LOW_GRADE_CU: 'Cobre de baja ley',
  OXIDE_ORE: 'Mineral oxidado',
  WASTE_ANDESITE: 'Estéril (andesita)',
  WASTE_OVERBURDEN: 'Estéril (sobrecarga)',
};

export const ROLE_LABELS: Record<UserRole, string> = {
  OPERATOR: 'Operador',
  MINE_ENGINEER: 'Ingeniero de mina',
  DRILL_BLAST_ENGINEER: 'Especialista en tronadura',
  METALLURGIST: 'Metalurgista',
  DATA_SCIENTIST: 'Científico de datos',
};

export const ALERT_SEVERITY_LABELS: Record<DigitalTwinAlert['severity'], string> = {
  CRITICAL: 'Crítica',
  WARNING: 'Advertencia',
  INFO: 'Informativa',
};

export const RECOMMENDATION_STATUS_LABELS: Record<DRLRecommendation['status'], string> = {
  PENDING_REVIEW: 'Pendiente',
  APPROVED: 'Aprobada',
  REJECTED: 'Rechazada',
  EXECUTED: 'Ejecutada',
};

export const CHOKE_RISK_LABELS: Record<'LOW' | 'MEDIUM' | 'HIGH', string> = {
  LOW: 'Bajo',
  MEDIUM: 'Medio',
  HIGH: 'Alto',
};

export const TIME_MODE_LABELS: Record<'HISTORICAL' | 'LIVE' | 'PREDICTION' | 'SCENARIO_SIM', string> = {
  LIVE: 'Tiempo real planta / SCADA',
  HISTORICAL: 'Histórico',
  PREDICTION: 'Predicción',
  SCENARIO_SIM: 'Simulación',
};

export const COPILOT_AGENT_LABELS: Record<string, string> = {
  dispatch_agent: 'Despacho',
  blast_agent: 'Tronadura',
  mill_agent: 'Planta',
  scenario_agent: 'Escenarios',
  xai_agent: 'Explicación',
  langflow_agent: 'Agente Langflow',
};

export function cycleStateLabel(state: CycleState): string {
  return CYCLE_STATE_LABELS[state] ?? state;
}

export function destinationTypeLabel(
  type: 'SHOVEL' | 'CRUSHER' | 'WASTE_DUMP' | 'STOCKPILE'
): string {
  return DESTINATION_TYPE_LABELS[type] ?? type;
}

export function materialTypeLabel(type: MaterialType): string {
  return MATERIAL_TYPE_LABELS[type] ?? type;
}

export function roleLabel(role: UserRole): string {
  return ROLE_LABELS[role] ?? role;
}

export function alertSeverityLabel(severity: DigitalTwinAlert['severity']): string {
  return ALERT_SEVERITY_LABELS[severity] ?? severity;
}

export function recommendationStatusLabel(status: DRLRecommendation['status']): string {
  return RECOMMENDATION_STATUS_LABELS[status] ?? status;
}

export function chokeRiskLabel(risk: 'LOW' | 'MEDIUM' | 'HIGH'): string {
  return CHOKE_RISK_LABELS[risk] ?? risk;
}

export function timeModeLabel(mode: 'HISTORICAL' | 'LIVE' | 'PREDICTION' | 'SCENARIO_SIM'): string {
  return TIME_MODE_LABELS[mode] ?? mode;
}

export function copilotAgentLabel(agent: string): string {
  return COPILOT_AGENT_LABELS[agent] ?? agent;
}
