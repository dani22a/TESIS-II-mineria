/**
 * MineTwin AI - Deep Reinforcement Learning (DRL) Engine & Multi-Objective Optimizer
 * Features Gymnasium-compatible state-action mapping, MAPPO policy scoring,
 * Shadow-mode verification, and human-in-the-loop recommendation synthesis.
 */

import {
  DigitalTwinState,
  DRLRecommendation,
  DRLRewardWeights,
  PolicyComparison,
} from '../types/mining';

export interface CurriculumStage {
  stageNumber: number;
  name: string;
  description: string;
  status: 'COMPLETED' | 'IN_TRAINING' | 'QUEUED';
  episodesCompleted: number;
  targetEpisodes: number;
  meanReward: number;
  convergenceRatePercent: number;
}

export const CURRICULUM_STAGES: CurriculumStage[] = [
  {
    stageNumber: 1,
    name: 'Fase 1: Single Shovel / Basic Haul (1 Pala + 4 Camiones)',
    description: 'Entrenamiento base de asignación simple y tiempos de ciclo estándar.',
    status: 'COMPLETED',
    episodesCompleted: 50000,
    targetEpisodes: 50000,
    meanReward: 84.5,
    convergenceRatePercent: 99.2,
  },
  {
    stageNumber: 2,
    name: 'Fase 2: Multi-Shovel Pit (2 Palas + 10-14 Camiones)',
    description: 'Balanceo dinámico de colas entre bancos de diferente cota y distancia.',
    status: 'COMPLETED',
    episodesCompleted: 120000,
    targetEpisodes: 120000,
    meanReward: 91.8,
    convergenceRatePercent: 98.6,
  },
  {
    stageNumber: 3,
    name: 'Fase 3: Multi-Destination & Blending (Chancador + Acopio + Botadero)',
    description: 'Enrutamiento por ley de corte, litología y restricciones de tolva.',
    status: 'COMPLETED',
    episodesCompleted: 180000,
    targetEpisodes: 180000,
    meanReward: 94.2,
    convergenceRatePercent: 97.4,
  },
  {
    stageNumber: 4,
    name: 'Fase 4: Congestión de Tráfico & Rampas con Pendiente',
    description: 'Gestión de cuellos de botella en rampas angostas y desaceleración por carga.',
    status: 'COMPLETED',
    episodesCompleted: 240000,
    targetEpisodes: 240000,
    meanReward: 95.1,
    convergenceRatePercent: 96.8,
  },
  {
    stageNumber: 5,
    name: 'Fase 5: Resiliencia ante Fallas & Mantenimiento No Programado',
    description: 'Respuesta ante caída súbita de pala, cierre de rampa o atasco de chancador.',
    status: 'COMPLETED',
    episodesCompleted: 300000,
    targetEpisodes: 300000,
    meanReward: 96.0,
    convergenceRatePercent: 95.9,
  },
  {
    stageNumber: 6,
    name: 'Fase 6: Integración Causal Mine-to-Mill (Fragmentación a Molienda)',
    description: 'Optimización conjunta de P80 de tronadura y alimentación continua a molino SAG.',
    status: 'IN_TRAINING',
    episodesCompleted: 385000,
    targetEpisodes: 450000,
    meanReward: 97.4,
    convergenceRatePercent: 94.2,
  },
  {
    stageNumber: 7,
    name: 'Fase 7: Optimización Multiobjetivo Total (Producción vs Energía vs CO2)',
    description: 'Optimización global de frontera de Pareto con restricciones duras de seguridad.',
    status: 'QUEUED',
    episodesCompleted: 42000,
    targetEpisodes: 500000,
    meanReward: 89.0,
    convergenceRatePercent: 88.5,
  },
];

export function computePolicyComparisons(state: DigitalTwinState): PolicyComparison[] {
  return [
    {
      policyName: '1. Despacho Estático Tradicional',
      description: 'Asignación fija 1:1 de camiones por pala sin consideración de colas ni ley.',
      productionTph: 7350,
      fleetProductivityTph: 525,
      avgCycleTimeMin: 32.4,
      avgQueueTimeMin: 5.6,
      fuelConsumptionLph: 3980,
      crusherThroughputTph: 3850,
      millThroughputTph: 3340,
      energyConsumptionKwhT: 17.8,
      co2EmissionsKgT: 8.9,
      operatingCostPerTonUsd: 7.20,
      starvationIncidentsCount: 14,
      overallScore: 64,
    },
    {
      policyName: '2. Heurística Shortest Queue (Cola Mínima)',
      description: 'Regla reactiva enviando al camión disponible a la pala con menor fila.',
      productionTph: 7850,
      fleetProductivityTph: 560,
      avgCycleTimeMin: 29.5,
      avgQueueTimeMin: 3.8,
      fuelConsumptionLph: 3820,
      crusherThroughputTph: 4100,
      millThroughputTph: 3450,
      energyConsumptionKwhT: 16.5,
      co2EmissionsKgT: 8.2,
      operatingCostPerTonUsd: 6.65,
      starvationIncidentsCount: 6,
      overallScore: 78,
    },
    {
      policyName: '3. MineTwin MAPPO DRL Agent (Activa)',
      description: 'Agente multi-agente PPO con observación global de colas, rampas y molino SAG.',
      productionTph: 8380,
      fleetProductivityTph: 598,
      avgCycleTimeMin: 26.8,
      avgQueueTimeMin: 2.1,
      fuelConsumptionLph: 3610,
      crusherThroughputTph: 4380,
      millThroughputTph: 3610,
      energyConsumptionKwhT: 15.2,
      co2EmissionsKgT: 7.4,
      operatingCostPerTonUsd: 6.08,
      starvationIncidentsCount: 1,
      overallScore: 96,
    },
    {
      policyName: '4. Shadow Policy v3.4 (Candidata en Evaluación)',
      description: 'Variante con mayor ponderación de desvío predictivo antes de choke en chancador.',
      productionTph: 8490,
      fleetProductivityTph: 606,
      avgCycleTimeMin: 26.2,
      avgQueueTimeMin: 1.8,
      fuelConsumptionLph: 3570,
      crusherThroughputTph: 4420,
      millThroughputTph: 3650,
      energyConsumptionKwhT: 14.9,
      co2EmissionsKgT: 7.2,
      operatingCostPerTonUsd: 5.94,
      starvationIncidentsCount: 0,
      overallScore: 98,
    },
  ];
}

/**
 * Computes composite reward score based on customizable weight vector
 */
export function calculateScalarReward(
  kpis: {
    productionTph: number;
    millThroughputTph: number;
    unitCostUsd: number;
    fuelLph: number;
    cycleTimeMin: number;
    queueTimeMin: number;
    energyKwhT: number;
  },
  weights: DRLRewardWeights
): number {
  // Normalize components to 0-100 scale
  const normProd = (kpis.productionTph / 9000) * 100;
  const normMill = (kpis.millThroughputTph / 4000) * 100;
  const normCost = (1 - kpis.unitCostUsd / 10) * 100;
  const normFuel = (1 - kpis.fuelLph / 5000) * 100;
  const normCycle = (1 - kpis.cycleTimeMin / 45) * 100;
  const normQueue = (1 - kpis.queueTimeMin / 10) * 100;
  const normEnergy = (1 - kpis.energyKwhT / 25) * 100;

  const reward =
    weights.productionWeight * normProd +
    weights.millThroughputWeight * normMill +
    weights.costWeight * normCost +
    weights.fuelWeight * normFuel +
    weights.cycleTimeWeight * normCycle +
    weights.queueTimeWeight * normQueue +
    weights.energyWeight * normEnergy;

  return Math.round(reward * 10) / 10;
}
