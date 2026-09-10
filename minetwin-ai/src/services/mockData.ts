/**
 * MineTwin AI - Initial Calibrated Digital Twin State & Domain Entities
 */

import {
  BlastHole,
  BlastPatternModel,
  CrusherTwin,
  DigitalTwinState,
  DrillRigTwin,
  GeologicalBlock,
  MillCircuitTwin,
  MineAlert,
  DRLRecommendation,
  ShovelTwin,
  StockpileTwin,
  TruckTwin,
} from '../types/mining';
import { calculateKuzRamFragmentation } from './kuzRamModel';
import { INITIAL_ROAD_SEGMENTS, MINE_LOCATIONS } from './roadNetwork';

export function createInitialBlastPatterns(): BlastPatternModel[] {
  // Pattern 104 - Active drilling & blasting on Bench 3840
  const holes104: BlastHole[] = [];
  const rows = 4;
  const cols = 8;
  const burden = 6.5;
  const spacing = 7.5;
  
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const id = `BH-104-${String(r * cols + c + 1).padStart(2, '0')}`;
      const isDrilled = (r * cols + c) < 22;
      const isLoaded = (r * cols + c) < 16;
      holes104.push({
        id,
        x: 70 + c * spacing * 0.4,
        y: 5.0,
        z: 45 + r * burden * 0.4,
        depth: 16.8, // 15m bench + 1.8m subdrill
        diameterMm: 311,
        burden,
        spacing,
        subdrill: 1.8,
        stemming: 5.8,
        explosiveType: 'EMULSION_70_30',
        explosiveMassKg: 1120,
        delayMs: (r * 25) + (c * 17),
        detonationSequence: r * cols + c + 1,
        isDrilled,
        isLoaded,
        isBlasted: false,
        waterDepthM: 0.4,
      });
    }
  }

  const kuzRam104 = calculateKuzRamFragmentation({
    burden: 6.5,
    spacing: 7.5,
    benchHeight: 15.0,
    holeDiameterMm: 311,
    stemmingLength: 5.8,
    subdrill: 1.8,
    powderFactorKgM3: 0.88,
    rockUCSMpa: 145,
    rockDensityTM3: 2.72,
    rqdPercent: 78,
    jointSpacingM: 1.4,
    jointOrientationDip: 45,
    explosiveType: 'EMULSION_70_30',
  });

  // Pattern 105 - Pit Bottom Bench 3680
  const holes105: BlastHole[] = [];
  for (let r = 0; r < 3; r++) {
    for (let c = 0; c < 6; c++) {
      holes105.push({
        id: `BH-105-${String(r * 6 + c + 1).padStart(2, '0')}`,
        x: -75 + c * 3.2,
        y: -2.2,
        z: -55 + r * 2.8,
        depth: 16.5,
        diameterMm: 311,
        burden: 6.2,
        spacing: 7.2,
        subdrill: 1.5,
        stemming: 5.5,
        explosiveType: 'HEAVY_ANFO',
        explosiveMassKg: 1050,
        delayMs: (r * 30) + (c * 15),
        detonationSequence: r * 6 + c + 1,
        isDrilled: (r * 6 + c) < 10,
        isLoaded: false,
        isBlasted: false,
        waterDepthM: 0.0,
      });
    }
  }

  const kuzRam105 = calculateKuzRamFragmentation({
    burden: 6.2,
    spacing: 7.2,
    benchHeight: 15.0,
    holeDiameterMm: 311,
    stemmingLength: 5.5,
    subdrill: 1.5,
    powderFactorKgM3: 0.92,
    rockUCSMpa: 165,
    rockDensityTM3: 2.78,
    rqdPercent: 82,
    jointSpacingM: 1.1,
    jointOrientationDip: 50,
    explosiveType: 'HEAVY_ANFO',
  });

  return [
    {
      id: 'PAT-104-B3840',
      name: 'Blast Pattern #104 (Porphyry Cu Ore)',
      bench: 'Bench 3840 East',
      benchElevation: 3840,
      rockUCS: 145,
      rockDensity: 2.72,
      totalHoles: 32,
      burden: 6.5,
      spacing: 7.5,
      benchHeight: 15.0,
      stemmingHeight: 5.8,
      subdrill: 1.8,
      powderFactor: 0.88,
      targetPowderFactor: 0.85,
      explosiveType: 'EMULSION_70_30',
      totalTonnageExpected: 145000,
      holes: holes104,
      status: 'DRILLING',
      kuzRamOutput: kuzRam104,
    },
    {
      id: 'PAT-105-B3680',
      name: 'Blast Pattern #105 (Skarn Cu-Au Pit Bottom)',
      bench: 'Bench 3680 West',
      benchElevation: 3680,
      rockUCS: 165,
      rockDensity: 2.78,
      totalHoles: 18,
      burden: 6.2,
      spacing: 7.2,
      benchHeight: 15.0,
      stemmingHeight: 5.5,
      subdrill: 1.5,
      powderFactor: 0.92,
      targetPowderFactor: 0.90,
      explosiveType: 'HEAVY_ANFO',
      totalTonnageExpected: 88000,
      holes: holes105,
      status: 'DESIGN',
      kuzRamOutput: kuzRam105,
    },
  ];
}

export function createGeologicalBlocks(): GeologicalBlock[] {
  const blocks: GeologicalBlock[] = [];
  let idCounter = 1;

  // Generate grid of 3D block model cells across pit benches
  const benches = [
    { y: 12, elevation: 4000, defaultLith: 'ANDESITE_WASTE' as const, grade: 0.12, ucs: 110, classif: 'WASTE' as const },
    { y: 8, elevation: 3920, defaultLith: 'LEACHED_CAP' as const, grade: 0.28, ucs: 125, classif: 'LOW_GRADE' as const },
    { y: 4.8, elevation: 3840, defaultLith: 'PORPHYRY_CU' as const, grade: 0.84, ucs: 145, classif: 'ORE' as const },
    { y: 1.0, elevation: 3760, defaultLith: 'PORPHYRY_CU' as const, grade: 0.98, ucs: 155, classif: 'ORE' as const },
    { y: -2.4, elevation: 3680, defaultLith: 'SKARN_ORE' as const, grade: 1.42, ucs: 175, classif: 'ORE' as const },
  ];

  benches.forEach((bench) => {
    const range = bench.elevation >= 3920 ? 4 : bench.elevation >= 3840 ? 3 : 2;
    for (let ix = -range; ix <= range; ix++) {
      for (let iz = -range; iz <= range; iz++) {
        // Skip some outer cells to form open-pit amphitheater shape
        const distSq = ix * ix + iz * iz;
        if (distSq > (range + 0.5) * (range + 0.5)) continue;

        const x = ix * 35;
        const z = iz * 35;
        const isMined = bench.elevation > 3840 && distSq < 4;

        blocks.push({
          id: `BLK-${String(idCounter++).padStart(3, '0')}`,
          x,
          y: bench.y,
          z,
          lithology: bench.defaultLith,
          density: bench.classif === 'ORE' ? 2.76 : 2.65,
          cuGrade: bench.grade + (Math.random() * 0.2 - 0.1),
          auGradeGpt: bench.classif === 'ORE' ? 0.35 + Math.random() * 0.2 : 0.05,
          ucsMpa: bench.ucs + Math.floor(Math.random() * 20 - 10),
          rqdPercent: Math.min(95, Math.max(50, 70 + Math.floor(Math.random() * 25))),
          hardnessIndex: Math.min(100, Math.max(30, Math.floor((bench.ucs / 200) * 100))),
          classification: bench.classif,
          isMined,
        });
      }
    }
  });

  return blocks;
}

export function createInitialShovels(): ShovelTwin[] {
  return [
    {
      id: 'EX-01',
      name: 'Shovel EX-01 (P&H 4100XPC)',
      model: 'P&H 4100XPC Electric Rope',
      position: { ...MINE_LOCATIONS.SHOVEL_EX01 },
      benchElevation: 3840,
      operatingState: 'OPERATIONAL',
      bucketCapacity: 56, // m³ (~95 tons per pass)
      diggingTimeSeconds: 27.2,
      swingTimeSeconds: 5.4,
      dumpTimeSeconds: 3.1,
      cycleTimePerPassSeconds: 35.7,
      passesPerTruck: 4, // 4 passes to fill 360t Cat 797F
      currentTruckLoadingId: 'DT-01',
      truckQueue: ['DT-03', 'DT-07'],
      productivityTph: 4150,
      targetProductivityTph: 4300,
      availability: 94.2,
      utilization: 88.6,
      materialType: 'HIGH_GRADE_CU',
      materialGrade: 0.86,
      rockHardnessUCS: 145,
      diggabilityIndex: 82,
      totalMinedTodayTons: 38400,
      digFaceWidth: 42,
    },
    {
      id: 'EX-02',
      name: 'Shovel EX-02 (Cat 7495 HD)',
      model: 'Cat 7495 High Density Rope',
      position: { ...MINE_LOCATIONS.SHOVEL_EX02 },
      benchElevation: 3680,
      operatingState: 'OPERATIONAL',
      bucketCapacity: 60, // m³ (~100 tons per pass)
      diggingTimeSeconds: 29.8,
      swingTimeSeconds: 5.8,
      dumpTimeSeconds: 3.4,
      cycleTimePerPassSeconds: 39.0,
      passesPerTruck: 4,
      currentTruckLoadingId: 'DT-02',
      truckQueue: ['DT-04'],
      productivityTph: 3920,
      targetProductivityTph: 4100,
      availability: 91.5,
      utilization: 84.1,
      materialType: 'HIGH_GRADE_CU',
      materialGrade: 1.38,
      rockHardnessUCS: 165,
      diggabilityIndex: 74,
      totalMinedTodayTons: 33800,
      digFaceWidth: 38,
    },
  ];
}

export function createInitialDrills(): DrillRigTwin[] {
  return [
    {
      id: 'DR-01',
      name: 'Drill Rig DR-01 (Epiroc PV-271)',
      model: 'Epiroc Pit Viper 271 Rotary',
      patternId: 'PAT-104-B3840',
      position: { ...MINE_LOCATIONS.DRILL_PAD_01 },
      currentHoleId: 'BH-104-23',
      currentHoleDepth: 9.4,
      targetHoleDepth: 16.8,
      holeDiameterMm: 311,
      penetrationRateMph: 38.4,
      targetPenetrationRateMph: 42.0,
      rockHardnessUCS: 145,
      bitConditionPercent: 78,
      energyConsumptionKw: 420,
      operatingState: 'OPERATIONAL',
      drilledHolesCount: 22,
      totalHolesInPattern: 32,
      estimatedCompletionMinutes: 145,
    },
    {
      id: 'DR-02',
      name: 'Drill Rig DR-02 (Cat MD6310)',
      model: 'Cat MD6310 Rotary Blasthole',
      patternId: 'PAT-105-B3680',
      position: { ...MINE_LOCATIONS.DRILL_PAD_02 },
      currentHoleId: 'BH-105-11',
      currentHoleDepth: 4.2,
      targetHoleDepth: 16.5,
      holeDiameterMm: 311,
      penetrationRateMph: 32.1,
      targetPenetrationRateMph: 35.0,
      rockHardnessUCS: 165,
      bitConditionPercent: 84,
      energyConsumptionKw: 460,
      operatingState: 'OPERATIONAL',
      drilledHolesCount: 10,
      totalHolesInPattern: 18,
      estimatedCompletionMinutes: 210,
    },
  ];
}

export function createInitialTrucks(): TruckTwin[] {
  const trucks: TruckTwin[] = [];
  const truckModels = [
    { model: 'Cat 797F', manufacturer: 'Caterpillar', capacity: 360 },
    { model: 'Komatsu 930E-5', manufacturer: 'Komatsu', capacity: 320 },
    { model: 'Cat 797F', manufacturer: 'Caterpillar', capacity: 360 },
    { model: 'Liebherr T 284', manufacturer: 'Liebherr', capacity: 363 },
  ];

  const states: { state: TruckTwin['cycleState']; route: string; progress: number; shovel: string; dest: TruckTwin['destinationType'] }[] = [
    { state: 'LOADING', route: 'RD-RAMP-BENCH-3840-CRUSHER', progress: 0.0, shovel: 'EX-01', dest: 'CRUSHER' },
    { state: 'LOADING', route: 'RD-RAMP-PIT-BOTTOM-3680-3840', progress: 0.0, shovel: 'EX-02', dest: 'CRUSHER' },
    { state: 'QUEUE_SHOVEL', route: 'RD-RAMP-BENCH-3840-CRUSHER', progress: 0.02, shovel: 'EX-01', dest: 'CRUSHER' },
    { state: 'QUEUE_SHOVEL', route: 'RD-RAMP-PIT-BOTTOM-3680-3840', progress: 0.02, shovel: 'EX-02', dest: 'CRUSHER' },
    { state: 'HAULING', route: 'RD-RAMP-BENCH-3840-CRUSHER', progress: 0.42, shovel: 'EX-01', dest: 'CRUSHER' },
    { state: 'HAULING', route: 'RD-RAMP-BENCH-3840-CRUSHER', progress: 0.78, shovel: 'EX-01', dest: 'CRUSHER' },
    { state: 'HAULING', route: 'RD-RAMP-PIT-BOTTOM-3680-3840', progress: 0.55, shovel: 'EX-02', dest: 'CRUSHER' },
    { state: 'QUEUE_DESTINATION', route: 'RD-RAMP-BENCH-3840-CRUSHER', progress: 0.96, shovel: 'EX-01', dest: 'CRUSHER' },
    { state: 'DUMPING', route: 'RD-RAMP-BENCH-3840-CRUSHER', progress: 1.0, shovel: 'EX-01', dest: 'CRUSHER' },
    { state: 'RETURNING', route: 'RD-RETURN-CRUSHER-TO-EX01', progress: 0.35, shovel: 'EX-01', dest: 'SHOVEL' },
    { state: 'RETURNING', route: 'RD-RETURN-CRUSHER-TO-EX01', progress: 0.72, shovel: 'EX-01', dest: 'SHOVEL' },
    { state: 'RETURNING', route: 'RD-RETURN-EX01-TO-EX02', progress: 0.48, shovel: 'EX-02', dest: 'SHOVEL' },
    { state: 'HAULING', route: 'RD-CRUSHER-TO-WASTE-DUMP', progress: 0.60, shovel: 'EX-01', dest: 'WASTE_DUMP' },
    { state: 'HAULING', route: 'RD-CRUSHER-TO-STOCKPILE', progress: 0.30, shovel: 'EX-02', dest: 'STOCKPILE' },
  ];

  for (let i = 1; i <= 14; i++) {
    const id = `DT-${String(i).padStart(2, '0')}`;
    const tm = truckModels[(i - 1) % truckModels.length];
    const st = states[(i - 1) % states.length];
    const isLoaded = st.state === 'HAULING' || st.state === 'QUEUE_DESTINATION' || st.state === 'DUMPING';

    trucks.push({
      id,
      name: `Haul Truck ${id}`,
      model: tm.model,
      manufacturer: tm.manufacturer,
      payloadCapacity: tm.capacity,
      payloadCurrent: isLoaded ? tm.capacity * (0.94 + Math.random() * 0.08) : 0,
      position: { x: 0, y: 0, z: 0 }, // calculated dynamically by simulation engine
      speed: isLoaded ? 26.5 + Math.random() * 4 : 42.0 + Math.random() * 6,
      heading: 45,
      destinationId: st.dest === 'CRUSHER' ? 'CR-01' : st.dest === 'WASTE_DUMP' ? 'WD-01' : st.dest === 'STOCKPILE' ? 'SP-01' : st.shovel,
      destinationType: st.dest,
      assignedShovelId: st.shovel,
      routeId: st.route,
      currentRoadSegmentId: st.route,
      routeProgress: st.progress,
      engineState: 'ON',
      fuelLevel: Math.round(65 + Math.random() * 30),
      fuelRate: isLoaded ? 320 + Math.random() * 40 : 180 + Math.random() * 25, // L/h
      cycleState: st.state,
      cycleTimeMinutes: Math.round((28.5 + Math.random() * 4.2) * 10) / 10,
      queueTimeMinutes: st.state.includes('QUEUE') ? Math.round((3.5 + Math.random() * 2.5) * 10) / 10 : 0.8,
      availability: 92.8,
      utilization: 87.4,
      healthScore: Math.round(86 + Math.random() * 12),
      predictedFailureProbability: Math.round(Math.random() * 12) / 100,
      materialType: 'HIGH_GRADE_CU',
      oreGrade: st.shovel === 'EX-01' ? 0.86 : 1.38,
      estimatedArrivalMinutes: Math.round((1.2 + (1 - st.progress) * 8.0) * 10) / 10,
      operatorId: `OP-${String(100 + i)}`,
      odometerKm: 142000 + i * 3400,
      tireWearPercent: Math.round(35 + Math.random() * 40),
      engineTemperatureC: Math.round(88 + Math.random() * 8),
      telemetryConfidence: 99.4,
    });
  }

  return trucks;
}

export function createInitialCrusher(): CrusherTwin {
  return {
    id: 'CR-01',
    name: 'Primary Gyratory Crusher CR-01 (Fuller-Traylor 60x89)',
    type: 'PRIMARY_GYRATORY',
    position: { ...MINE_LOCATIONS.CRUSHER_HOPPER },
    operatingState: 'OPERATIONAL',
    throughputTph: 4320,
    nominalCapacityTph: 4800,
    openSideSettingMm: 150,
    closeSideSettingMm: 135,
    chokeLevelPercent: 68,
    trucksInQueue: ['DT-08'],
    powerConsumptionKw: 580,
    motorAmps: 64.5,
    vibrationMmS: 2.8,
    linerWearPercent: 42,
    accumulatedTonsToday: 48200,
    boulderAlarmActive: false,
  };
}

export function createInitialStockpile(): StockpileTwin {
  return {
    id: 'SP-01',
    name: 'Run of Mine Stockpile SP-01',
    type: 'ROM_ORE',
    currentTonnage: 185000,
    maxCapacityTons: 350000,
    averageGradeCu: 0.94,
    blendedHardnessUcs: 148,
    reclaimRateTph: 3600,
    fillPercentage: 52.8,
  };
}

export function createInitialMill(): MillCircuitTwin {
  return {
    id: 'ML-01',
    name: 'Grinding Circuit (40ft SAG + 2x Ball Mills)',
    sagMillPowerKw: 24200,
    sagMillThroughputTph: 3580,
    ballMillPowerKw: 18400,
    ballMillThroughputTph: 3580,
    specificEnergyKwhPerTon: 15.8,
    targetSpecificEnergy: 15.0,
    p80GrindMicrons: 145,
    targetP80Microns: 150,
    flotationCuRecoveryPercent: 88.9,
    pebbleCrusherActive: true,
    cycloneFeedPressureKpa: 110,
    bearingTemperatureC: 58.4,
    operatingState: 'OPERATIONAL',
    millBottleNeckFactor: 'Hardness UCS 155MPa on active feed',
  };
}

export function createInitialAlerts(): MineAlert[] {
  return [
    {
      id: 'ALT-101',
      timestamp: '2026-09-02 07:12:30',
      type: 'PREDICTION',
      severity: 'WARNING',
      assetId: 'EX-02',
      title: 'Predicción de Cola Excesiva en Pala EX-02',
      message: 'El modelo DRL predice acumulación de 3.8 camiones en espera dentro de 14 minutos en Banco 3680.',
      etaMinutes: 14,
      recommendedAction: 'Reasignar DT-04 y DT-07 a Pala EX-01 para balancear ciclo de carguío.',
      acknowledged: false,
    },
    {
      id: 'ALT-102',
      timestamp: '2026-09-02 07:05:15',
      type: 'MINE_TO_MILL',
      severity: 'INFO',
      assetId: 'ML-01',
      title: 'Optimización de Fragmentación Mine-to-Mill',
      message: 'P80 actual de 182mm incrementa el consumo específico del molino SAG en +1.1 kWh/t.',
      recommendedAction: 'Aumentar Powder Factor en Patrón #105 de 0.88 a 0.94 kg/m³.',
      acknowledged: false,
    },
    {
      id: 'ALT-103',
      timestamp: '2026-09-02 06:50:00',
      type: 'TRAFFIC',
      severity: 'INFO',
      assetId: 'RD-RAMP-MAIN-UP',
      title: 'Tráfico Moderado en Rampa Principal',
      message: 'Densidad de 4 camiones simultáneos en pendiente 7.8%. Velocidad promedio reducida a 24 km/h.',
      acknowledged: true,
    },
  ];
}

export function createInitialRecommendations(): DRLRecommendation[] {
  return [
    {
      id: 'REC-DRL-001',
      timestamp: '2026-09-02 07:15:00',
      category: 'DISPATCH_REASSIGNMENT',
      title: 'Rebalanceo Dinámico de Flota (Pala EX-02 → EX-01)',
      what: 'Reasignar camiones DT-03 y DT-07 desde Pala EX-02 a Pala EX-01 (Banco 3840).',
      why: 'La pala EX-02 presenta congestión predictiva (cola de 4.1 min) mientras EX-01 entrará en sub-utilización en 12 minutos por falta de camiones.',
      expectedImpact: {
        productionDeltaTph: 340,
        productionDeltaPercent: 4.8,
        cycleTimeDeltaMin: -2.3,
        fuelSavedLitersPerShift: 180,
        millThroughputDeltaTph: 120,
        costSavingsUsd: 2850,
        co2ReducedKg: 470,
      },
      confidence: 0.94,
      constraintsEvaluated: [
        'Capacidad máxima de tolva en Chancador Primario (<85%)',
        'Ley mínima de alimentación a planta (>0.82% Cu)',
        'Límite de velocidad en rampa 7.8% (Seguridad vial)',
      ],
      status: 'PENDING_REVIEW',
      source: 'DRL_MAPPO',
      suggestedAction: {
        targetAssetId: 'DT-03',
        newShovelId: 'EX-01',
        truckIds: ['DT-03', 'DT-07'],
      },
      auditTrail: [
        { action: 'GENERATED_BY_DRL_MAPPO_AGENT', timestamp: '2026-09-02 07:15:00', user: 'MineTwin DRL Policy v3.2' },
      ],
    },
    {
      id: 'REC-DRL-002',
      timestamp: '2026-09-02 07:08:20',
      category: 'CRUSHER_FEED_BALANCE',
      title: 'Priorización de Descarga Directa a Chancador CR-01',
      what: 'Desviar DT-06 con mineral Skarn de alta ley (1.42% Cu) directamente a Chancador CR-01 en lugar de Stockpile SP-01.',
      why: 'El nivel de tolva del chancador cayó al 54% y la planta SAG requiere compensación de dureza con mineral de alto rendimiento.',
      expectedImpact: {
        productionDeltaTph: 160,
        productionDeltaPercent: 2.2,
        cycleTimeDeltaMin: -1.1,
        fuelSavedLitersPerShift: 65,
        millThroughputDeltaTph: 210,
        costSavingsUsd: 1420,
        co2ReducedKg: 170,
      },
      confidence: 0.91,
      constraintsEvaluated: ['Capacidad de chancado disponible', 'Blending metalúrgico'],
      status: 'PENDING_REVIEW',
      source: 'DRL_MAPPO',
      suggestedAction: {
        targetAssetId: 'DT-06',
        truckIds: ['DT-06'],
        destinationType: 'CRUSHER',
      },
      auditTrail: [
        { action: 'GENERATED_BY_DRL_MAPPO_AGENT', timestamp: '2026-09-02 07:08:20', user: 'MineTwin DRL Policy v3.2' },
      ],
    },
  ];
}

export function createInitialTwinState(): DigitalTwinState {
  const initialTrucks = createInitialTrucks();
  const initialShovels = createInitialShovels();
  const initialDrills = createInitialDrills();
  const initialPatterns = createInitialBlastPatterns();
  const initialBlocks = createGeologicalBlocks();
  const initialCrusher = createInitialCrusher();
  const initialStockpile = createInitialStockpile();
  const initialMill = createInitialMill();
  const initialAlerts = createInitialAlerts();
  const initialRecommendations = createInitialRecommendations();

  return {
    timestamp: new Date().toISOString(),
    simTimeSeconds: 0,
    timeMode: 'LIVE',
    simSpeedMultiplier: 1,
    isPaused: false,
    isSimulating: true,
    simulationSpeed: 1,
    currentStrategy: 'DRL_MULTI_OBJECTIVE',
    currentUserRole: 'MINE_ENGINEER',
    selectedAssetId: 'DT-01',
    selectedAssetType: 'TRUCK',
    cameraFocus: 'GLOBAL_PIT',
    chaseTruckId: null,
    visibleLayers: {
      equipment: true,
      haulRoads: true,
      trafficHeatmap: false,
      blastPatterns: true,
      blockModelGeology: true,
      fragmentationVisual: false,
      crusherPlant: true,
      telemetryVectors: true,
      aiTrajectories: true,
    },
    activeDispatchStrategy: 'DRL_MULTI_OBJECTIVE',
    trucks: initialTrucks,
    shovels: initialShovels,
    drills: initialDrills,
    blastPatterns: initialPatterns,
    blocks: initialBlocks,
    roads: INITIAL_ROAD_SEGMENTS,
    crusher: initialCrusher,
    stockpile: initialStockpile,
    mill: initialMill,
    alerts: initialAlerts,
    recommendations: initialRecommendations,
    rewardWeights: {
      productionWeight: 0.35,
      millThroughputWeight: 0.25,
      costWeight: 0.15,
      fuelWeight: 0.10,
      cycleTimeWeight: 0.08,
      queueTimeWeight: 0.05,
      energyWeight: 0.02,
      safetyPenaltyWeight: 1.0,
    },
    historicalTimeOffsetMinutes: 0,
    kpiHistory: [
      { time: '06:00', productionTph: 7450, millThroughputTph: 3420, avgCycleTimeMin: 31.2, avgQueueTimeMin: 4.8, fuelLph: 3820, unitCost: 6.85 },
      { time: '06:15', productionTph: 7680, millThroughputTph: 3480, avgCycleTimeMin: 29.8, avgQueueTimeMin: 3.9, fuelLph: 3780, unitCost: 6.64 },
      { time: '06:30', productionTph: 7920, millThroughputTph: 3520, avgCycleTimeMin: 28.6, avgQueueTimeMin: 3.2, fuelLph: 3710, unitCost: 6.42 },
      { time: '06:45', productionTph: 8100, millThroughputTph: 3560, avgCycleTimeMin: 27.9, avgQueueTimeMin: 2.8, fuelLph: 3680, unitCost: 6.30 },
      { time: '07:00', productionTph: 8250, millThroughputTph: 3580, avgCycleTimeMin: 27.2, avgQueueTimeMin: 2.4, fuelLph: 3640, unitCost: 6.18 },
      { time: '07:15', productionTph: 8380, millThroughputTph: 3610, avgCycleTimeMin: 26.8, avgQueueTimeMin: 2.1, fuelLph: 3610, unitCost: 6.08 },
    ],
  };
}
