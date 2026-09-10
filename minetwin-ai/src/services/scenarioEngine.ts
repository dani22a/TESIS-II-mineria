/**
 * MineTwin AI - What-If scenario engine (deterministic).
 * Shared by Scenario Lab UI and the LangGraph copilot tools.
 */

import {
  DigitalTwinState,
  DispatchStrategy,
  ScenarioSimulationResult,
} from '../types/mining';

export interface ScenarioLabInputs {
  trucksDelta: number;
  shovelOutage: string;
  roadBlocked: string;
  powderFactorDelta: number;
  weather: 'CLEAR' | 'RAIN' | 'MUD';
  strategy: DispatchStrategy;
}

export function computeBaselineKpis(state: DigitalTwinState): {
  productionTph: number;
  cycleTimeMin: number;
  unitCostUsd: number;
} {
  return {
    productionTph: Math.round(state.shovels.reduce((acc, s) => acc + s.productivityTph, 0)),
    cycleTimeMin:
      Math.round(
        (state.trucks.reduce((acc, t) => acc + t.cycleTimeMinutes, 0) / Math.max(1, state.trucks.length)) *
          10
      ) / 10,
    unitCostUsd: 6.08,
  };
}

export function runWhatIfSimulation(
  state: DigitalTwinState,
  inputs: ScenarioLabInputs
): ScenarioSimulationResult {
  const baseline = computeBaselineKpis(state);
  let simulatedProd = baseline.productionTph;
  let simulatedCycle = baseline.cycleTimeMin;
  let simulatedCost = baseline.unitCostUsd;
  const crusherThroughput = 4320;
  let millThroughput = 3580;
  let specificEnergy = 15.8;
  const bottlenecks: string[] = [];

  if (inputs.trucksDelta > 0) {
    simulatedProd += inputs.trucksDelta * 320;
    simulatedCycle += inputs.trucksDelta * 0.7;
  } else if (inputs.trucksDelta < 0) {
    simulatedProd += inputs.trucksDelta * 480;
    simulatedCycle += inputs.trucksDelta * 0.4;
    bottlenecks.push('Sub-utilización de palas por falta de camiones de acarreo');
  }

  if (inputs.shovelOutage === 'EX-01') {
    simulatedProd -= 3800;
    simulatedCycle += 4.5;
    simulatedCost += 1.45;
    bottlenecks.push('Pala EX-01 fuera de servicio: Congestión masiva en Pala EX-02');
  } else if (inputs.shovelOutage === 'EX-02') {
    simulatedProd -= 3600;
    simulatedCycle += 3.8;
    simulatedCost += 1.35;
    bottlenecks.push('Pala EX-02 fuera de servicio: Pérdida de alimentación de mineral alta ley');
  }

  if (inputs.roadBlocked !== 'NONE') {
    simulatedCycle += 5.2;
    simulatedProd -= 650;
    bottlenecks.push('Cierre de rampa principal: Desvío por rampa secundaria con mayor pendiente');
  }

  if (inputs.powderFactorDelta > 0) {
    millThroughput += Math.round(inputs.powderFactorDelta * 18);
    specificEnergy -= Math.round(inputs.powderFactorDelta * 0.04 * 10) / 10;
    simulatedProd += 180;
  } else if (inputs.powderFactorDelta < 0) {
    millThroughput -= Math.round(Math.abs(inputs.powderFactorDelta) * 24);
    specificEnergy += Math.round(Math.abs(inputs.powderFactorDelta) * 0.06 * 10) / 10;
    bottlenecks.push('Sobretamaño en disparo reduce rendimiento en molino SAG');
  }

  if (inputs.weather === 'RAIN') {
    simulatedCycle += 3.0;
    simulatedProd -= 420;
  } else if (inputs.weather === 'MUD') {
    simulatedCycle += 6.5;
    simulatedProd -= 950;
    bottlenecks.push('Condición de pista resbaladiza: Límite de velocidad reducido a 20 km/h');
  }

  if (inputs.strategy === 'DRL_MULTI_OBJECTIVE') {
    simulatedProd += 250;
    simulatedCycle -= 1.4;
  } else if (inputs.strategy === 'STATIC_ASSIGNMENT') {
    simulatedProd -= 450;
    simulatedCycle += 2.2;
  }

  const prodDeltaPercent =
    Math.round(((simulatedProd - baseline.productionTph) / Math.max(1, baseline.productionTph)) * 1000) /
    10;
  const cycleDeltaMin = Math.round((simulatedCycle - baseline.cycleTimeMin) * 10) / 10;

  return {
    scenarioId: 'SCENARIO-WHATIF-01',
    scenarioName: 'Escenario What-If Simulado',
    productionTonsPerHour: Math.max(1000, simulatedProd),
    productionDeltaPercent: prodDeltaPercent,
    totalCycleTimeMin: Math.max(15, simulatedCycle),
    cycleTimeDeltaMin: cycleDeltaMin,
    shovelProductivity: [
      {
        shovelId: 'EX-01',
        tph: inputs.shovelOutage === 'EX-01' ? 0 : 4250,
        deltaPercent: inputs.shovelOutage === 'EX-01' ? -100 : 2.4,
      },
      {
        shovelId: 'EX-02',
        tph: inputs.shovelOutage === 'EX-02' ? 0 : 4100,
        deltaPercent: inputs.shovelOutage === 'EX-02' ? -100 : 4.5,
      },
    ],
    crusherThroughputTph: crusherThroughput,
    millThroughputTph: millThroughput,
    specificEnergyKwhT: specificEnergy,
    fuelRateTotalLph: Math.round(3600 + inputs.trucksDelta * 240),
    unitCostUsdPerTon:
      Math.round((simulatedCost + cycleDeltaMin * 0.08 - prodDeltaPercent * 0.03) * 100) / 100,
    kuzRamP80: Math.round(180 - inputs.powderFactorDelta * 1.5),
    bottlenecks,
  };
}

export function parseScenarioFromText(
  message: string,
  state: DigitalTwinState
): ScenarioLabInputs {
  const t = message.toLowerCase();
  const trucksMatch = t.match(/([+-]?\d+)\s*camiones/);
  let trucksDelta = 0;
  if (trucksMatch) {
    trucksDelta = parseInt(trucksMatch[1], 10);
  } else if (/\+\s*3|tres camiones más|sumar camiones/.test(t)) {
    trucksDelta = 3;
  } else if (/menos camiones|quitar camiones/.test(t)) {
    trucksDelta = -2;
  }

  let shovelOutage = 'NONE';
  if (/ex-01|pala 1|pala ex-01/.test(t) && /(cae|cae|falla|down|fuera|indisponib)/.test(t)) {
    shovelOutage = 'EX-01';
  } else if (/ex-02|pala 2|pala ex-02/.test(t) && /(cae|falla|down|fuera|indisponib)/.test(t)) {
    shovelOutage = 'EX-02';
  } else if (/cae.*ex-01|falla.*ex-01/.test(t)) {
    shovelOutage = 'EX-01';
  } else if (/cae.*ex-02|falla.*ex-02/.test(t)) {
    shovelOutage = 'EX-02';
  }

  const roadBlocked = /(rampa|cierre).*(cerr|bloque)|bloque.*rampa|cierra rampa/.test(t)
    ? 'RD-RAMP-BENCH-3840-CRUSHER'
    : 'NONE';

  let powderFactorDelta = 0;
  const pfMatch = t.match(/powder[^\d%]*([+-]?\d+)\s*%/) || t.match(/factor[^\d%]*([+-]?\d+)\s*%/);
  if (pfMatch) {
    powderFactorDelta = parseInt(pfMatch[1], 10);
  } else if (/subo.*powder|aument.*factor|más energía/.test(t)) {
    powderFactorDelta = 8;
  }

  let weather: ScenarioLabInputs['weather'] = 'CLEAR';
  if (/barro|lodo|mud/.test(t)) weather = 'MUD';
  else if (/lluv/.test(t)) weather = 'RAIN';

  return {
    trucksDelta,
    shovelOutage,
    roadBlocked,
    powderFactorDelta,
    weather,
    strategy: state.currentStrategy,
  };
}
