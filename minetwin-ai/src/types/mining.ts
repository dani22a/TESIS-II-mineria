/**
 * MineTwin AI - Industrial Mining Digital Twin Domain Types
 * Spans Geology, Drill, Blast, Fragmentation, Load, Haul, Crusher, Mill, DRL, and Simulation
 */

export type CycleState =
  | 'AVAILABLE'
  | 'ASSIGNED'
  | 'EMPTY_TRAVEL'
  | 'QUEUE_SHOVEL'
  | 'SPOTTING'
  | 'LOADING'
  | 'HAULING'
  | 'QUEUE_DESTINATION'
  | 'DUMPING'
  | 'RETURNING'
  | 'STANDBY'
  | 'MAINTENANCE';

export type OperatingState = 'OPERATIONAL' | 'IDLE' | 'DELAYED' | 'DOWN' | 'MAINTENANCE';

export type MaterialType = 'HIGH_GRADE_CU' | 'LOW_GRADE_CU' | 'OXIDE_ORE' | 'WASTE_ANDESITE' | 'WASTE_OVERBURDEN';

export type DispatchStrategy =
  | 'STATIC_ASSIGNMENT'
  | 'SHORTEST_QUEUE'
  | 'SHORTEST_TRAVEL_TIME'
  | 'MIN_CYCLE_TIME'
  | 'PRODUCTION_BALANCING'
  | 'CRUSHER_PRIORITY'
  | 'DRL_MULTI_OBJECTIVE';

export interface Position3D {
  x: number; // Local coordinates in meters
  y: number; // Elevation (Z in mining GIS, Y in Three.js)
  z: number;
  lat?: number;
  lng?: number;
  elevation?: number;
}

export interface TruckTwin {
  id: string;
  name: string;
  model: string; // e.g., 'Cat 797F' | 'Komatsu 930E-5'
  manufacturer: string;
  payloadCapacity: number; // tons (e.g. 360t)
  payloadCurrent: number; // current load tons
  position: Position3D;
  speed: number; // km/h
  heading: number; // degrees 0-360
  destinationId: string;
  destinationType: 'SHOVEL' | 'CRUSHER' | 'WASTE_DUMP' | 'STOCKPILE';
  assignedShovelId: string;
  routeId: string;
  currentRoadSegmentId: string;
  routeProgress: number; // 0 to 1 along current path
  engineState: 'ON' | 'IDLE' | 'OFF';
  fuelLevel: number; // % (0-100)
  fuelRate: number; // L/h
  cycleState: CycleState;
  cycleTimeMinutes: number;
  queueTimeMinutes: number;
  availability: number; // %
  utilization: number; // %
  healthScore: number; // 0-100
  predictedFailureProbability: number; // 0-1
  materialType: MaterialType;
  oreGrade: number; // % Cu
  estimatedArrivalMinutes: number;
  operatorId: string;
  odometerKm: number;
  tireWearPercent: number;
  engineTemperatureC: number;
  telemetryConfidence: number; // 0-100%
}

export interface ShovelTwin {
  id: string;
  name: string;
  model: string; // 'P&H 4100XPC' | 'Cat 7495'
  position: Position3D;
  benchElevation: number; // m RL
  operatingState: OperatingState;
  bucketCapacity: number; // m3 or tons (~56m3 / 95t)
  diggingTimeSeconds: number; // current pass
  swingTimeSeconds: number;
  dumpTimeSeconds: number;
  cycleTimePerPassSeconds: number;
  passesPerTruck: number; // e.g., 4 passes
  currentTruckLoadingId: string | null;
  truckQueue: string[]; // truck IDs
  productivityTph: number; // tons per operating hour
  targetProductivityTph: number;
  availability: number; // %
  utilization: number; // %
  materialType: MaterialType;
  materialGrade: number; // % Cu
  rockHardnessUCS: number; // MPa (Uniaxial Compressive Strength)
  diggabilityIndex: number; // 0-100
  totalMinedTodayTons: number;
  digFaceWidth: number;
}

export interface DrillRigTwin {
  id: string;
  name: string;
  model: string; // 'Epiroc Pit Viper 271' | 'Cat MD6310'
  patternId: string;
  position: Position3D;
  currentHoleId: string;
  currentHoleDepth: number; // meters drilled so far
  targetHoleDepth: number; // meters total
  holeDiameterMm: number; // e.g., 311 mm (12 1/4")
  penetrationRateMph: number; // meters per hour
  targetPenetrationRateMph: number;
  rockHardnessUCS: number; // MPa
  bitConditionPercent: number; // %
  energyConsumptionKw: number;
  operatingState: OperatingState;
  drilledHolesCount: number;
  totalHolesInPattern: number;
  estimatedCompletionMinutes: number;
}

export interface BlastHole {
  id: string;
  x: number;
  y: number;
  z: number;
  depth: number;
  diameterMm: number;
  burden: number; // m
  spacing: number; // m
  subdrill: number; // m
  stemming: number; // m
  explosiveType: 'ANFO' | 'EMULSION_70_30' | 'HEAVY_ANFO';
  explosiveMassKg: number;
  delayMs: number;
  detonationSequence: number;
  isDrilled: boolean;
  isLoaded: boolean;
  isBlasted: boolean;
  waterDepthM: number;
}

export interface BlastPatternModel {
  id: string;
  name: string;
  bench: string;
  benchElevation: number;
  rockUCS: number; // MPa
  rockDensity: number; // t/m3
  totalHoles: number;
  burden: number; // m
  spacing: number; // m
  benchHeight: number; // m
  stemmingHeight: number; // m
  subdrill: number; // m
  powderFactor: number; // kg/m3 or kg/t (e.g. 0.65 kg/t)
  targetPowderFactor: number;
  explosiveType: 'ANFO' | 'EMULSION_70_30' | 'HEAVY_ANFO';
  totalTonnageExpected: number;
  holes: BlastHole[];
  status: 'DESIGN' | 'DRILLING' | 'LOADING' | 'READY_TO_BLAST' | 'MUCKPILE_ACTIVE' | 'DEPLETED';
  // Fragmentation estimation (Kuz-Ram)
  kuzRamOutput: KuzRamResult;
}

export interface KuzRamResult {
  p20: number; // mm
  p50: number; // mm (Mean size)
  p80: number; // mm
  characteristicSizeXc: number; // mm
  uniformityIndexN: number;
  oversizePercent: number; // >1000mm boulders requiring secondary blasting
  finesPercent: number; // <25mm fines
  curveData: { sizeMm: number; passingPercent: number }[];
}

export interface GeologicalBlock {
  id: string;
  x: number;
  y: number;
  z: number;
  lithology: 'PORPHYRY_CU' | 'SKARN_ORE' | 'ANDESITE_WASTE' | 'BRECCIA' | 'LEACHED_CAP';
  density: number; // t/m3
  cuGrade: number; // %
  auGradeGpt: number; // g/t
  ucsMpa: number; // 20 - 250 MPa
  rqdPercent: number; // Rock Quality Designation 0-100%
  hardnessIndex: number; // 0-100
  classification: 'ORE' | 'WASTE' | 'LOW_GRADE';
  isMined: boolean;
}

export interface RoadSegment {
  id: string;
  name: string;
  startPoint: Position3D;
  endPoint: Position3D;
  waypoints: Position3D[];
  distanceMeters: number;
  gradientPercent: number; // -10% to +10%
  rollingResistancePercent: number; // typically 2-4%
  speedLimitKmh: number;
  currentTrafficCount: number;
  capacityMaxTrucks: number;
  roadCondition: 'EXCELLENT' | 'GOOD' | 'DUSTY' | 'SLIPPERY_WET' | 'ROUGH' | 'BLOCKED';
  weatherEffectFactor: number; // 1.0 is normal, 0.7 is rain
  currentTravelTimeSeconds: number;
  predictedTravelTimeSeconds: number;
  dustLevelPpm: number;
}

export interface CrusherTwin {
  id: string;
  name: string;
  type: 'PRIMARY_GYRATORY' | 'JAW';
  position: Position3D;
  operatingState: OperatingState;
  throughputTph: number;
  nominalCapacityTph: number;
  openSideSettingMm: number; // OSS (e.g. 140 mm)
  closeSideSettingMm: number; // CSS
  chokeLevelPercent: number; // 0-100%
  trucksInQueue: string[];
  powerConsumptionKw: number;
  motorAmps: number;
  vibrationMmS: number;
  linerWearPercent: number;
  accumulatedTonsToday: number;
  boulderAlarmActive: boolean;
}

export interface StockpileTwin {
  id: string;
  name: string;
  type: 'ROM_ORE' | 'LOW_GRADE' | 'CRUSHED_ORE';
  currentTonnage: number;
  maxCapacityTons: number;
  averageGradeCu: number;
  blendedHardnessUcs: number;
  reclaimRateTph: number;
  fillPercentage: number;
}

export interface MillCircuitTwin {
  id: string;
  name: string;
  sagMillPowerKw: number;
  sagMillThroughputTph: number;
  ballMillPowerKw: number;
  ballMillThroughputTph: number;
  specificEnergyKwhPerTon: number; // e.g. 18.5 kWh/t
  targetSpecificEnergy: number;
  p80GrindMicrons: number; // e.g. 150 µm
  targetP80Microns: number;
  flotationCuRecoveryPercent: number; // e.g. 88.5%
  pebbleCrusherActive: boolean;
  cycloneFeedPressureKpa: number;
  bearingTemperatureC: number;
  operatingState: OperatingState;
  millBottleNeckFactor: string; // e.g. 'Coarse feed from P80=240mm' or 'UCS hardness 185MPa'
}

export interface MineAlert {
  id: string;
  timestamp: string;
  type: 'OPERATIONAL' | 'PREDICTION' | 'MAINTENANCE' | 'TRAFFIC' | 'MINE_TO_MILL' | 'AI_OPTIMIZER';
  severity: 'CRITICAL' | 'WARNING' | 'INFO';
  assetId: string;
  title: string;
  message: string;
  etaMinutes?: number;
  recommendedAction?: string;
  acknowledged: boolean;
}

export interface SuggestedTwinAction {
  targetAssetId: string;
  newShovelId?: string;
  truckIds?: string[];
  patternId?: string;
  powderFactor?: number;
  strategy?: DispatchStrategy;
  destinationType?: TruckTwin['destinationType'];
}

export interface DRLRecommendation {
  id: string;
  timestamp: string;
  category: 'DISPATCH_REASSIGNMENT' | 'SPEED_OPTIMIZATION' | 'CRUSHER_FEED_BALANCE' | 'POWDER_FACTOR_ADJUST' | 'PREVENTATIVE_REROUTE';
  title: string;
  what: string; // What action is proposed
  why: string; // Causal reason
  expectedImpact: {
    productionDeltaTph: number;
    productionDeltaPercent: number;
    cycleTimeDeltaMin: number;
    fuelSavedLitersPerShift: number;
    millThroughputDeltaTph: number;
    costSavingsUsd: number;
    co2ReducedKg: number;
  };
  confidence: number; // 0.0 - 1.0 (e.g. 94%)
  constraintsEvaluated: string[];
  status: 'PENDING_REVIEW' | 'APPROVED' | 'REJECTED' | 'EXECUTED';
  approvedBy?: string;
  suggestedAction?: SuggestedTwinAction;
  source?: 'DRL_MAPPO' | 'LANGGRAPH_COPILOT';
  auditTrail: { action: string; timestamp: string; user: string }[];
}

export interface PolicyComparison {
  policyName: string;
  description: string;
  productionTph: number;
  fleetProductivityTph: number;
  avgCycleTimeMin: number;
  avgQueueTimeMin: number;
  fuelConsumptionLph: number;
  crusherThroughputTph: number;
  millThroughputTph: number;
  energyConsumptionKwhT: number;
  co2EmissionsKgT: number;
  operatingCostPerTonUsd: number;
  starvationIncidentsCount: number;
  overallScore: number;
}

export interface DRLRewardWeights {
  productionWeight: number; // w1
  millThroughputWeight: number; // w2
  costWeight: number; // w3
  fuelWeight: number; // w4
  cycleTimeWeight: number; // w5
  queueTimeWeight: number; // w6
  energyWeight: number; // w7
  safetyPenaltyWeight: number; // w8
}

export interface WhatIfScenarioConfig {
  id: string;
  name: string;
  description: string;
  trucksDelta: number; // e.g. +3 or -2 trucks
  shovelOutageId: string | null; // e.g. 'SH-01' down
  roadBlockedId: string | null; // e.g. 'RD-RAMP-3' closed
  powderFactorAdjustmentPercent: number; // e.g. +10% or -8%
  rockHardnessAdjustmentPercent: number; // e.g. +15%
  weatherCondition: 'CLEAR' | 'LIGHT_RAIN' | 'HEAVY_RAIN_MUD' | 'DUST_STORM';
  crusherSpeedLimitFactor: number;
  dispatchStrategy: DispatchStrategy;
}

export interface ScenarioSimulationResult {
  scenarioId: string;
  scenarioName: string;
  productionTonsPerHour: number;
  productionDeltaPercent: number;
  totalCycleTimeMin: number;
  cycleTimeDeltaMin: number;
  shovelProductivity: { shovelId: string; tph: number; deltaPercent: number }[];
  crusherThroughputTph: number;
  millThroughputTph: number;
  specificEnergyKwhT: number;
  fuelRateTotalLph: number;
  unitCostUsdPerTon: number;
  kuzRamP80: number;
  bottlenecks: string[];
}

export type UserRole =
  | 'OPERATOR'
  | 'MINE_ENGINEER'
  | 'DRILL_BLAST_ENGINEER'
  | 'METALLURGIST'
  | 'DATA_SCIENTIST';

export type DigitalTwinAlert = MineAlert;

export interface DigitalTwinState {
  timestamp: string;
  simTimeSeconds: number;
  timeMode: 'HISTORICAL' | 'LIVE' | 'PREDICTION' | 'SCENARIO_SIM';
  simSpeedMultiplier: number; // 1, 5, 10, 30, 100
  isPaused: boolean;
  isSimulating: boolean;
  simulationSpeed: number;
  currentStrategy: DispatchStrategy;
  currentUserRole: UserRole;
  selectedAssetId: string | null;
  selectedAssetType: 'TRUCK' | 'SHOVEL' | 'DRILL' | 'BLAST' | 'CRUSHER' | 'STOCKPILE' | 'MILL' | 'ROAD' | null;
  cameraFocus: 'GLOBAL_PIT' | 'SHOVEL_1' | 'SHOVEL_2' | 'CRUSHER' | 'DRILL_PAD' | 'CHASE_TRUCK';
  chaseTruckId: string | null;
  visibleLayers: {
    equipment: boolean;
    haulRoads: boolean;
    trafficHeatmap: boolean;
    blastPatterns: boolean;
    blockModelGeology: boolean;
    fragmentationVisual: boolean;
    crusherPlant: boolean;
    telemetryVectors: boolean;
    aiTrajectories: boolean;
  };
  activeDispatchStrategy: DispatchStrategy;
  trucks: TruckTwin[];
  shovels: ShovelTwin[];
  drills: DrillRigTwin[];
  blastPatterns: BlastPatternModel[];
  blocks: GeologicalBlock[];
  roads: RoadSegment[];
  crusher: CrusherTwin;
  stockpile: StockpileTwin;
  mill: MillCircuitTwin;
  alerts: MineAlert[];
  recommendations: DRLRecommendation[];
  rewardWeights: DRLRewardWeights;
  historicalTimeOffsetMinutes: number; // negative for past, 0 for live, positive for prediction
  kpiHistory: {
    time: string;
    productionTph: number;
    millThroughputTph: number;
    avgCycleTimeMin: number;
    avgQueueTimeMin: number;
    fuelLph: number;
    unitCost: number;
  }[];
}
