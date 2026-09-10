/**
 * Compact digital-twin snapshot for LangGraph tools / LLM context.
 * Numbers always come from live state, never from the model.
 */

import { DigitalTwinState } from '../../types/mining';

export interface TwinSnapshot {
  role: DigitalTwinState['currentUserRole'];
  strategy: DigitalTwinState['currentStrategy'];
  productionTph: number;
  avgCycleMin: number;
  trucks: {
    id: string;
    cycleState: string;
    assignedShovelId: string;
    destinationType: string;
    queueTimeMinutes: number;
    cycleTimeMinutes: number;
    oreGrade: number;
    materialType: string;
  }[];
  shovels: {
    id: string;
    name: string;
    operatingState: string;
    queueLength: number;
    currentTruckLoadingId: string | null;
    productivityTph: number;
    materialGrade: number;
  }[];
  crusher: {
    id: string;
    chokeLevelPercent: number;
    throughputTph: number;
    queueCount: number;
    boulderAlarmActive: boolean;
  };
  mill: {
    sagMillThroughputTph: number;
    specificEnergyKwhPerTon: number;
    millBottleNeckFactor: string;
  };
  blastPatterns: {
    id: string;
    name: string;
    powderFactor: number;
    rockUCS: number;
    p80: number;
    status: string;
  }[];
  alerts: { id: string; severity: string; title: string; message: string }[];
  recommendations: {
    id: string;
    title: string;
    what: string;
    why: string;
    status: string;
    confidence: number;
  }[];
}

export function buildTwinSnapshot(state: DigitalTwinState): TwinSnapshot {
  return {
    role: state.currentUserRole,
    strategy: state.currentStrategy,
    productionTph: Math.round(state.shovels.reduce((acc, s) => acc + s.productivityTph, 0)),
    avgCycleMin:
      Math.round(
        (state.trucks.reduce((acc, t) => acc + t.cycleTimeMinutes, 0) / Math.max(1, state.trucks.length)) *
          10
      ) / 10,
    trucks: state.trucks.map((t) => ({
      id: t.id,
      cycleState: t.cycleState,
      assignedShovelId: t.assignedShovelId,
      destinationType: t.destinationType,
      queueTimeMinutes: t.queueTimeMinutes,
      cycleTimeMinutes: t.cycleTimeMinutes,
      oreGrade: t.oreGrade,
      materialType: t.materialType,
    })),
    shovels: state.shovels.map((s) => ({
      id: s.id,
      name: s.name,
      operatingState: s.operatingState,
      queueLength: s.truckQueue.length,
      currentTruckLoadingId: s.currentTruckLoadingId,
      productivityTph: s.productivityTph,
      materialGrade: s.materialGrade,
    })),
    crusher: {
      id: state.crusher.id,
      chokeLevelPercent: state.crusher.chokeLevelPercent,
      throughputTph: state.crusher.throughputTph,
      queueCount: state.crusher.trucksInQueue.length,
      boulderAlarmActive: state.crusher.boulderAlarmActive,
    },
    mill: {
      sagMillThroughputTph: state.mill.sagMillThroughputTph,
      specificEnergyKwhPerTon: state.mill.specificEnergyKwhPerTon,
      millBottleNeckFactor: state.mill.millBottleNeckFactor,
    },
    blastPatterns: state.blastPatterns.map((p) => ({
      id: p.id,
      name: p.name,
      powderFactor: p.powderFactor,
      rockUCS: p.rockUCS,
      p80: p.kuzRamOutput.p80,
      status: p.status,
    })),
    alerts: state.alerts
      .filter((a) => !a.acknowledged)
      .map((a) => ({
        id: a.id,
        severity: a.severity,
        title: a.title,
        message: a.message,
      })),
    recommendations: state.recommendations.map((r) => ({
      id: r.id,
      title: r.title,
      what: r.what,
      why: r.why,
      status: r.status,
      confidence: r.confidence,
    })),
  };
}
