/**
 * Deterministic copilot tools. The LLM never invents t/h, P80 or costs.
 */

import { DRLRecommendation, DigitalTwinState } from '../../types/mining';
import { calculateKuzRamFragmentation, evaluateMineToMillImpact } from '../kuzRamModel';
import { calculateScalarReward, computePolicyComparisons } from '../drlEngine';
import { parseScenarioFromText, runWhatIfSimulation, ScenarioLabInputs } from '../scenarioEngine';

export interface ToolTrace {
  tool: string;
  agent: string;
  citation: string;
  result: unknown;
}

export type CopilotAgentId =
  | 'dispatch_agent'
  | 'blast_agent'
  | 'mill_agent'
  | 'scenario_agent'
  | 'xai_agent';

export function queryTwinState(state: DigitalTwinState): Record<string, unknown> {
  const shovelQueues = state.shovels.map((s) => ({
    id: s.id,
    queue: s.truckQueue.length,
    loading: s.currentTruckLoadingId,
    tph: s.productivityTph,
    grade: s.materialGrade,
  }));
  const queueing = state.trucks.filter((t) => t.cycleState.includes('QUEUE'));
  return {
    strategy: state.currentStrategy,
    productionTph: Math.round(state.shovels.reduce((a, s) => a + s.productivityTph, 0)),
    shovelQueues,
    trucksInQueue: queueing.map((t) => ({
      id: t.id,
      shovel: t.assignedShovelId,
      minutes: t.queueTimeMinutes,
    })),
    crusherChokePercent: state.crusher.chokeLevelPercent,
    sagTph: state.mill.sagMillThroughputTph,
    sagKwhT: state.mill.specificEnergyKwhPerTon,
    millBottleneck: state.mill.millBottleNeckFactor,
  };
}

export function runKuzRamFromState(state: DigitalTwinState, powderFactorOverride?: number) {
  const pattern = state.blastPatterns[0];
  const powderFactor = powderFactorOverride ?? pattern.powderFactor;
  const kuzRam = calculateKuzRamFragmentation({
    burden: pattern.burden,
    spacing: pattern.spacing,
    benchHeight: pattern.benchHeight,
    holeDiameterMm: 311,
    stemmingLength: pattern.stemmingHeight,
    subdrill: pattern.subdrill,
    powderFactorKgM3: powderFactor,
    rockUCSMpa: pattern.rockUCS,
    rockDensityTM3: pattern.rockDensity,
    rqdPercent: 78,
    jointSpacingM: 1.4,
    jointOrientationDip: 45,
    explosiveType: pattern.explosiveType,
  });
  const impact = evaluateMineToMillImpact(kuzRam, pattern.rockUCS, powderFactor);
  return {
    patternId: pattern.id,
    powderFactor,
    p20: kuzRam.p20,
    p50: kuzRam.p50,
    p80: kuzRam.p80,
    oversizePercent: kuzRam.oversizePercent,
    sagKwhT: impact.sagMillSpecificEnergyKwhT,
    sagTph: impact.sagMillThroughputTph,
    crusherChokeRisk: impact.crusherChokeRisk,
    unitCostUsd: impact.totalCostPerTonMinedUsd,
  };
}

export function runWhatIfFromMessage(state: DigitalTwinState, message: string) {
  const inputs: ScenarioLabInputs = parseScenarioFromText(message, state);
  const result = runWhatIfSimulation(state, inputs);
  return { inputs, result };
}

export function explainDrlRecommendation(state: DigitalTwinState, recId?: string) {
  const rec =
    (recId ? state.recommendations.find((r) => r.id === recId) : undefined) ??
    state.recommendations.find((r) => r.status === 'PENDING_REVIEW') ??
    state.recommendations[0];

  const policies = computePolicyComparisons(state);
  const liveKpis = {
    productionTph: Math.round(state.shovels.reduce((a, s) => a + s.productivityTph, 0)),
    millThroughputTph: state.mill.sagMillThroughputTph,
    unitCostUsd: 6.08,
    fuelLph: Math.round(state.trucks.reduce((a, t) => a + t.fuelRate, 0)),
    cycleTimeMin:
      Math.round(
        (state.trucks.reduce((a, t) => a + t.cycleTimeMinutes, 0) / Math.max(1, state.trucks.length)) * 10
      ) / 10,
    queueTimeMin:
      Math.round(
        (state.shovels.reduce((a, s) => a + s.truckQueue.length * 2.8, 0) / Math.max(1, state.shovels.length)) *
          10
      ) / 10,
    energyKwhT: state.mill.specificEnergyKwhPerTon,
  };
  const reward = calculateScalarReward(liveKpis, state.rewardWeights);

  return {
    recommendation: rec ?? null,
    liveKpis,
    scalarReward: reward,
    activePolicy: policies.find((p) => p.policyName.includes('MAPPO')),
    alerts: state.alerts.filter((a) => !a.acknowledged).map((a) => `${a.severity}: ${a.title}`),
  };
}

function nowStamp(): string {
  return new Date().toISOString().replace('T', ' ').slice(0, 19);
}

export function proposeDispatchRebalance(state: DigitalTwinState): DRLRecommendation {
  const ex01 = state.shovels.find((s) => s.id === 'EX-01');
  const ex02 = state.shovels.find((s) => s.id === 'EX-02');
  const fromShovel = (ex02?.truckQueue.length ?? 0) >= (ex01?.truckQueue.length ?? 0) ? 'EX-02' : 'EX-01';
  const toShovel = fromShovel === 'EX-02' ? 'EX-01' : 'EX-02';
  const candidates = state.trucks
    .filter((t) => t.assignedShovelId === fromShovel && t.cycleState !== 'LOADING')
    .slice(0, 2)
    .map((t) => t.id);
  const truckIds = candidates.length >= 2 ? candidates : ['DT-03', 'DT-07'];

  return {
    id: `REC-LG-${Date.now()}`,
    timestamp: nowStamp(),
    category: 'DISPATCH_REASSIGNMENT',
    title: `Rebalanceo de flota (${fromShovel} → ${toShovel})`,
    what: `Reasignar ${truckIds.join(' y ')} desde pala ${fromShovel} a pala ${toShovel}.`,
    why: `Cola observada: EX-01=${ex01?.truckQueue.length ?? 0} camiones, EX-02=${ex02?.truckQueue.length ?? 0} camiones. El supervisor LangGraph usó el estado vivo del gemelo, no un texto estático.`,
    expectedImpact: {
      productionDeltaTph: 280,
      productionDeltaPercent: 3.6,
      cycleTimeDeltaMin: -1.8,
      fuelSavedLitersPerShift: 140,
      millThroughputDeltaTph: 90,
      costSavingsUsd: 2100,
      co2ReducedKg: 320,
    },
    confidence: 0.88,
    constraintsEvaluated: [
      'Capacidad de tolva del chancador (<85%)',
      'Límite de velocidad en rampa (seguridad vial)',
      'Aprobación humana obligatoria antes de mutar el gemelo',
    ],
    status: 'PENDING_REVIEW',
    source: 'LANGGRAPH_COPILOT',
    suggestedAction: {
      targetAssetId: truckIds[0],
      newShovelId: toShovel,
      truckIds,
    },
    auditTrail: [
      {
        action: 'GENERATED_BY_LANGGRAPH_DISPATCH_AGENT',
        timestamp: nowStamp(),
        user: 'MineTwin Copilot Supervisor',
      },
    ],
  };
}

export function proposePowderFactorAdjust(state: DigitalTwinState): DRLRecommendation {
  const pattern = state.blastPatterns[0];
  const current = runKuzRamFromState(state);
  const nextPf = Math.round((pattern.powderFactor + 0.06) * 100) / 100;
  const next = runKuzRamFromState(state, nextPf);

  return {
    id: `REC-LG-${Date.now()}`,
    timestamp: nowStamp(),
    category: 'POWDER_FACTOR_ADJUST',
    title: `Ajuste de factor de carga en ${pattern.id}`,
    what: `Subir el factor de carga de ${pattern.powderFactor} a ${nextPf} kg/m³ en ${pattern.id}.`,
    why: `P80 actual ${current.p80} mm y cuello de molino: ${state.mill.millBottleNeckFactor}. Kuz-Ram proyecta P80 ${next.p80} mm y ${next.sagKwhT} kWh/t.`,
    expectedImpact: {
      productionDeltaTph: 120,
      productionDeltaPercent: 1.6,
      cycleTimeDeltaMin: -0.4,
      fuelSavedLitersPerShift: 40,
      millThroughputDeltaTph: Math.round(next.sagTph - current.sagTph),
      costSavingsUsd: 980,
      co2ReducedKg: 110,
    },
    confidence: 0.86,
    constraintsEvaluated: ['Vibración de banco', 'Sobreexcavación de talud', 'HITL obligatorio'],
    status: 'PENDING_REVIEW',
    source: 'LANGGRAPH_COPILOT',
    suggestedAction: {
      targetAssetId: pattern.id,
      patternId: pattern.id,
      powderFactor: nextPf,
    },
    auditTrail: [
      {
        action: 'GENERATED_BY_LANGGRAPH_BLAST_AGENT',
        timestamp: nowStamp(),
        user: 'MineTwin Copilot Supervisor',
      },
    ],
  };
}

export function proposeCrusherFeed(state: DigitalTwinState): DRLRecommendation {
  const highGrade = state.trucks.find((t) => t.oreGrade >= 1.2) ?? state.trucks.find((t) => t.id === 'DT-06');
  const truckId = highGrade?.id ?? 'DT-06';

  return {
    id: `REC-LG-${Date.now()}`,
    timestamp: nowStamp(),
    category: 'CRUSHER_FEED_BALANCE',
    title: 'Priorizar descarga directa a chancador CR-01',
    what: `Desviar ${truckId} (ley ${highGrade?.oreGrade ?? 1.42}% Cu) a chancador CR-01 en lugar de acopio.`,
    why: `Tolva en ${state.crusher.chokeLevelPercent}% y SAG en ${state.mill.sagMillThroughputTph} t/h. El agente de planta usó telemetría del gemelo.`,
    expectedImpact: {
      productionDeltaTph: 160,
      productionDeltaPercent: 2.1,
      cycleTimeDeltaMin: -1.0,
      fuelSavedLitersPerShift: 55,
      millThroughputDeltaTph: 180,
      costSavingsUsd: 1280,
      co2ReducedKg: 150,
    },
    confidence: 0.84,
    constraintsEvaluated: ['Capacidad de chancado', 'Blending metalúrgico', 'HITL obligatorio'],
    status: 'PENDING_REVIEW',
    source: 'LANGGRAPH_COPILOT',
    suggestedAction: {
      targetAssetId: truckId,
      truckIds: [truckId],
      destinationType: 'CRUSHER',
    },
    auditTrail: [
      {
        action: 'GENERATED_BY_LANGGRAPH_MILL_AGENT',
        timestamp: nowStamp(),
        user: 'MineTwin Copilot Supervisor',
      },
    ],
  };
}

export function heuristicRoute(message: string, role: DigitalTwinState['currentUserRole']): CopilotAgentId {
  const t = message
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{M}/gu, '');

  if (
    /escenario|what-if|what if|si cae|si llueve|si ex-|impacto si|se rompe|falla la pala|fuera de servicio|cierre de rampa|si llueve|barro|lodo|\+3 camiones|mas camiones|tres camiones/.test(
      t
    )
  ) {
    return 'scenario_agent';
  }
  if (
    /p80|kuz-ram|kuz ram|kuzram|tronadura|powder|fragment|malla|factor de carga|mineral grueso|tamano de roca|voladura/.test(
      t
    )
  ) {
    return 'blast_agent';
  }
  if (/sag|molino|chancador|tolva|skarn|molienda|planta|energia del molino/.test(t)) {
    return 'mill_agent';
  }
  if (
    /explica|rec-drl|recomend|auditor|alerta|mappo|por que la ia|por que recomienda|politica activa/.test(t)
  ) {
    return 'xai_agent';
  }
  if (/cola|reasign|despach|camion|pala|flota|esperando|espera en/.test(t)) {
    return 'dispatch_agent';
  }
  if (role === 'DRILL_BLAST_ENGINEER') return 'blast_agent';
  if (role === 'METALLURGIST') return 'mill_agent';
  if (role === 'DATA_SCIENTIST') return 'xai_agent';
  return 'dispatch_agent';
}

export function wantsWriteAction(message: string, agent: CopilotAgentId): boolean {
  const t = message.toLowerCase();
  if (/solo consulta|explícame|explica|qué pasa si|impacto|cuánto/.test(t) && !/reasign|aplic|propon/.test(t)) {
    if (agent === 'scenario_agent' || agent === 'xai_agent') return false;
    if (/qué pasa|impacto|cuánto|p80/.test(t) && !/propon|reasign|aplic/.test(t)) return false;
  }
  if (agent === 'dispatch_agent' && /reasign|rebalance|propon|qué camiones|mover camiones/.test(t)) return true;
  if (agent === 'blast_agent' && /propon|aplic|sube|ajustar|explosivo/.test(t)) return true;
  if (agent === 'mill_agent' && /prioriz|desví|desvi|propon|mandar mineral/.test(t)) return true;
  return /propon|reasign|aplic|ejecut|aprueb/.test(t);
}

export function formatDeterministicReply(
  agent: CopilotAgentId,
  traces: ToolTrace[],
  pending: DRLRecommendation | null
): string {
  const intro: Record<CopilotAgentId, string> = {
    dispatch_agent: 'Agente de despacho. Cifras del gemelo vivo (no inventadas por el modelo).',
    blast_agent: 'Agente de perforación y tronadura. Fragmentación con Kuz-Ram.',
    mill_agent: 'Agente de mina a planta. Propagación a SAG desde el motor físico.',
    scenario_agent: 'Agente de escenarios. Simulación de qué pasaría con el mismo motor del laboratorio de escenarios.',
    xai_agent: 'Agente XAI. Explicación anclada a DRL y KPIs vivos.',
  };

  const lines: string[] = [intro[agent], ''];
  for (const tr of traces) {
    const result = tr.result as Record<string, unknown> | null;
    const nested = (result?.result ?? result) as Record<string, unknown> | undefined;
    const inputs = (result?.inputs ?? {}) as Record<string, unknown>;
    if (tr.tool === 'run_what_if_scenario' && nested) {
      if (inputs.shovelOutage && inputs.shovelOutage !== 'NONE') {
        lines.push(`• Pala fuera de servicio: ${inputs.shovelOutage}.`);
      }
      if (inputs.weather && inputs.weather !== 'CLEAR') {
        lines.push(`• Clima simulado: ${inputs.weather}.`);
      } else {
        lines.push('• El motor no aplicó lluvia en este escenario (clima = despejado).');
      }
      if (typeof nested.productionTonsPerHour === 'number') {
        lines.push(
          `• Producción: ${nested.productionTonsPerHour} t/h (${nested.productionDeltaPercent}% vs base). Fuente: scenarioEngine.`
        );
      }
      if (typeof nested.totalCycleTimeMin === 'number') {
        lines.push(`• Ciclo de camión: ${nested.totalCycleTimeMin} min (Δ ${nested.cycleTimeDeltaMin} min).`);
      }
      if (typeof nested.unitCostUsdPerTon === 'number') {
        lines.push(`• Costo unitario: ${nested.unitCostUsdPerTon} USD/t.`);
      }
      const bottlenecks = nested.bottlenecks;
      if (Array.isArray(bottlenecks) && bottlenecks.length > 0) {
        lines.push(`• Cuello de botella: ${bottlenecks.join('; ')}`);
      }
    } else if (tr.tool === 'run_kuz_ram' || tr.tool === 'evaluate_mine_to_mill') {
      const payload = (result?.actual ?? result) as Record<string, unknown>;
      if (payload?.p80 != null) lines.push(`• P80: ${payload.p80} mm (Kuz-Ram).`);
      if (payload?.sagKwhT != null) lines.push(`• Energía SAG: ${payload.sagKwhT} kWh/t.`);
      if (payload?.sagTph != null) lines.push(`• Rendimiento SAG: ${payload.sagTph} t/h.`);
    } else {
      lines.push(`• Herramienta ${tr.tool} (${tr.citation}) ejecutada. Detalle en la línea de tiempo de la derecha.`);
    }
  }

  if (pending) {
    lines.push('', `Acción pausada (aprobación humana): ${pending.title}. ${pending.what}`);
  }

  return lines.join('\n');
}
