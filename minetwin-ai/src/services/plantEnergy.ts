/**
 * MineTwin AI - Plant electrical consumption (kWh per 15 min).
 *
 * Reads the artifact exported by the energia-planta lab (XGBoost, inputs: hour,
 * weekday, load type) and answers "how much energy does the plant draw now?".
 * This is independent from the SAG specific energy (kWh/t, Kuz-Ram model), which
 * stays untouched in `mill.specificEnergyKwhPerTon`.
 *
 * Artifact location: `public/artefactos/planta_xgboost.json` (served at
 * `/artefactos/planta_xgboost.json`). It is a copy of
 * `energia-planta/artefactos/planta_xgboost.json`. To refresh it after retraining:
 *   copy energia-planta/artefactos/planta_xgboost.json minetwin-ai/public/artefactos/
 *
 * Loading: browser -> fetch once; Node (scripts, tests, SSR) -> fs read of the
 * file under `public/`. The result is cached in this module. If the artifact is
 * missing or invalid the service reports status 'unavailable' and every
 * prediction is `null`; nothing throws.
 */

import { PlantLoadType } from '../types/mining';

/**
 * Nominal SAG tonnage (t/h) used to derive the load type. The twin has no such
 * field, so it is defined here: the simulated baseline (~3550 t/h) is ~89 % of
 * it (medium load) and pushing SAG above 3600 t/h (> 90 %) means maximum load.
 */
export const SAG_NOMINAL_TPH = 4000;
/** Below this SAG/nominal ratio the plant is in light load. */
export const LOAD_LIGHT_BELOW = 0.75;
/** Up to (and including) this ratio the plant is in medium load; above it, maximum. */
export const LOAD_MEDIUM_UP_TO = 0.9;

/** Simulated wall clock start: Monday 06:00 (day index 0 = Monday). */
export const PLANT_CLOCK_START_DAY_INDEX = 0;
export const PLANT_CLOCK_START_HOUR = 6;
/**
 * Plant-clock seconds per simulation second. `simTimeSeconds` advances
 * `simSpeedMultiplier` (default 5) per real second, so with 60 the plant clock
 * moves 5 simulated minutes per real second at default speed: the hour changes
 * about every 12 s and the weekday about every 5 min, visible in a demo.
 */
export const PLANT_CLOCK_TIME_SCALE = 60;

export const PLANT_ENERGY_ARTIFACT_PATH = '/artefactos/planta_xgboost.json';

const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'] as const;
export type PlantWeekday = (typeof WEEKDAYS)[number];

const LOAD_TYPES: PlantLoadType[] = ['Light_Load', 'Medium_Load', 'Maximum_Load'];

interface PredictionRow {
  hour: number;
  day: string;
  load_type: PlantLoadType;
  kwh: number;
}

interface ScenarioRow extends PredictionRow {
  id: string;
  phrase: string;
}

interface PlantEnergyArtifact {
  model: string;
  unit: string;
  prediction_table: PredictionRow[];
  scenario_explanations: ScenarioRow[];
}

export type PlantEnergyStatus = 'idle' | 'loading' | 'ready' | 'unavailable';

export interface PlantEnergyPrediction {
  kwh15min: number;
  loadType: PlantLoadType;
  hour: number;
  day: PlantWeekday;
  sagRatio: number;
  phrase: string;
  /** false when the phrase comes from the nearest reference scenario (not this exact hour/day). */
  phraseExact: boolean;
  /** Hour/day of the scenario the phrase describes. */
  phraseScenario: { hour: number; day: string } | null;
  model: string;
  unit: string;
}

let status: PlantEnergyStatus = 'idle';
let loadPromise: Promise<PlantEnergyStatus> | null = null;
let table: Map<string, number> | null = null;
let scenarios: ScenarioRow[] = [];
let modelName = 'XGBoost';
let unitName = 'kWh/15min';

const rowKey = (hour: number, day: string, loadType: string) => `${hour}|${day}|${loadType}`;

function isPredictionRow(r: unknown): r is PredictionRow {
  if (!r || typeof r !== 'object') return false;
  const row = r as Partial<PredictionRow>;
  return (
    Number.isInteger(row.hour) &&
    typeof row.day === 'string' &&
    LOAD_TYPES.includes(row.load_type as PlantLoadType) &&
    typeof row.kwh === 'number' &&
    Number.isFinite(row.kwh)
  );
}

/** Installs an artifact (already parsed). Returns the resulting status. Never throws. */
export function setPlantEnergyArtifact(raw: unknown): PlantEnergyStatus {
  try {
    const art = raw as Partial<PlantEnergyArtifact> | null;
    if (!art || !Array.isArray(art.prediction_table) || art.prediction_table.length === 0) {
      throw new Error('prediction_table ausente');
    }
    const rows = art.prediction_table.filter(isPredictionRow);
    if (rows.length !== art.prediction_table.length) throw new Error('prediction_table inválida');
    table = new Map(rows.map((r) => [rowKey(r.hour, r.day, r.load_type), r.kwh]));
    scenarios = (Array.isArray(art.scenario_explanations) ? art.scenario_explanations : []).filter(
      (s): s is ScenarioRow => isPredictionRow(s) && typeof (s as ScenarioRow).phrase === 'string'
    );
    modelName = typeof art.model === 'string' ? art.model : 'XGBoost';
    unitName = typeof art.unit === 'string' ? art.unit : 'kWh/15min';
    status = 'ready';
  } catch {
    table = null;
    scenarios = [];
    status = 'unavailable';
  }
  return status;
}

/** Forgets the loaded artifact (tests / refresh). */
export function resetPlantEnergyModel(): void {
  table = null;
  scenarios = [];
  status = 'idle';
  loadPromise = null;
}

export function getPlantEnergyStatus(): PlantEnergyStatus {
  return status;
}

async function readArtifact(): Promise<unknown> {
  if (typeof window !== 'undefined' && typeof fetch === 'function') {
    const response = await fetch(PLANT_ENERGY_ARTIFACT_PATH);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }
  // Node: read the copy under public/. The specifier is a variable so bundlers skip it.
  const fsModule = 'node:fs/promises';
  const { readFile } = (await import(/* @vite-ignore */ fsModule)) as typeof import('node:fs/promises');
  const file = `${process.cwd()}/public${PLANT_ENERGY_ARTIFACT_PATH}`;
  return JSON.parse(await readFile(file, 'utf-8'));
}

/** Loads the artifact once (cached). Resolves to the final status; never rejects. */
export function loadPlantEnergyModel(): Promise<PlantEnergyStatus> {
  if (status === 'ready' || status === 'unavailable') return Promise.resolve(status);
  if (loadPromise) return loadPromise;
  status = 'loading';
  loadPromise = readArtifact()
    .then((raw) => setPlantEnergyArtifact(raw))
    .catch(() => {
      table = null;
      scenarios = [];
      status = 'unavailable';
      return status;
    });
  return loadPromise;
}

/** Load type from SAG tonnage against the nominal. */
export function classifyLoadType(sagTph: number): PlantLoadType {
  const ratio = sagTph / SAG_NOMINAL_TPH;
  if (ratio < LOAD_LIGHT_BELOW) return 'Light_Load';
  if (ratio <= LOAD_MEDIUM_UP_TO) return 'Medium_Load';
  return 'Maximum_Load';
}

/** Plant wall clock derived from the simulation clock. */
export function plantClockFromSimTime(simTimeSeconds: number): { hour: number; day: PlantWeekday } {
  const startMinutes = PLANT_CLOCK_START_DAY_INDEX * 1440 + PLANT_CLOCK_START_HOUR * 60;
  const elapsedMinutes = Math.floor(Math.max(0, simTimeSeconds) * PLANT_CLOCK_TIME_SCALE / 60);
  const total = (startMinutes + elapsedMinutes) % (7 * 1440);
  return { hour: Math.floor((total % 1440) / 60), day: WEEKDAYS[Math.floor(total / 1440)] };
}

function findScenario(hour: number, day: PlantWeekday, loadType: PlantLoadType) {
  const candidates = scenarios.filter((s) => s.load_type === loadType);
  const exact = candidates.find((s) => s.hour === hour && s.day === day);
  if (exact) return { scenario: exact, exact: true };
  const isWeekend = (d: string) => d === 'Saturday' || d === 'Sunday';
  const sameDayType = candidates.filter((s) => isWeekend(s.day) === isWeekend(day));
  const pool = sameDayType.length > 0 ? sameDayType : candidates;
  const hourDistance = (h: number) => Math.min(Math.abs(h - hour), 24 - Math.abs(h - hour));
  let best: ScenarioRow | undefined;
  for (const s of pool) {
    if (!best || hourDistance(s.hour) < hourDistance(best.hour)) best = s;
  }
  return { scenario: best ?? null, exact: false };
}

/**
 * Predicted plant consumption (kWh per 15 min) for a SAG tonnage at a given
 * simulation time. Returns null when the artifact is not loaded or has no row.
 */
export function predictPlantEnergy(sagTph: number, simTimeSeconds: number): PlantEnergyPrediction | null {
  if (status !== 'ready' || !table || !Number.isFinite(sagTph)) return null;
  const loadType = classifyLoadType(sagTph);
  const { hour, day } = plantClockFromSimTime(simTimeSeconds);
  const kwh = table.get(rowKey(hour, day, loadType));
  if (kwh === undefined) return null;
  const { scenario, exact } = findScenario(hour, day, loadType);
  return {
    kwh15min: kwh,
    loadType,
    hour,
    day,
    sagRatio: sagTph / SAG_NOMINAL_TPH,
    phrase: scenario?.phrase ?? '',
    phraseExact: exact,
    phraseScenario: scenario ? { hour: scenario.hour, day: scenario.day } : null,
    model: modelName,
    unit: unitName,
  };
}
