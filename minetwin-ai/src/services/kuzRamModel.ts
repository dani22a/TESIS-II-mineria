/**
 * MineTwin AI - Kuz-Ram Blast Fragmentation & Mine-to-Mill Physics Engine
 * Formulates empirical Cunningham-Lilly rock fragmentation models and
 * propagates downstream impact across Digging, Haulage, Crushing, and SAG Milling.
 */

import { KuzRamResult } from '../types/mining';

export interface BlastInputParams {
  burden: number; // meters (e.g., 6.5 m)
  spacing: number; // meters (e.g., 7.8 m)
  benchHeight: number; // meters (e.g., 15.0 m)
  holeDiameterMm: number; // mm (e.g., 311 mm)
  stemmingLength: number; // meters (e.g., 6.0 m)
  subdrill: number; // meters (e.g., 1.8 m)
  powderFactorKgM3: number; // kg/m³ (e.g., 0.85 kg/m³)
  rockUCSMpa: number; // Rock Unconfined Compressive Strength in MPa (e.g. 140 MPa)
  rockDensityTM3: number; // t/m³ (e.g. 2.7 t/m³)
  rqdPercent: number; // Rock Quality Designation % (e.g. 75%)
  jointSpacingM: number; // Joint spacing in meters (e.g. 1.2 m)
  jointOrientationDip: number; // Joint dip degrees (e.g. 45°)
  explosiveType: 'ANFO' | 'EMULSION_70_30' | 'HEAVY_ANFO';
}

/**
 * Calculates Rock Mass Factor (A) based on Lilly (1986) Rock Description Index:
 * RMD (Rock Mass Description), JPS (Joint Plane Spacing), JPO (Joint Plane Orientation),
 * SGI (Specific Gravity Index), Hardness (UCS/Young's Modulus).
 */
export function calculateRockMassFactor(params: BlastInputParams): number {
  // RMD: 10 if powdery/friable, 20 if blocky, 50 if massive
  const rmd = params.rqdPercent > 80 ? 50 : params.rqdPercent > 40 ? 25 : 10;
  
  // JPS: Joint spacing index
  const jps = params.jointSpacingM < 0.1 ? 10 : params.jointSpacingM < 1.0 ? 20 : 50;
  
  // JPO: Joint plane orientation index (dip)
  const jpo = params.jointOrientationDip > 60 ? 40 : params.jointOrientationDip > 30 ? 30 : 20;
  
  // SGI: Specific gravity index
  const sgi = 25 * params.rockDensityTM3 - 50;
  
  // Hardness Factor (based on UCS in MPa)
  const hardness = params.rockUCSMpa > 180 ? 12 : params.rockUCSMpa > 100 ? 8 : 4;

  const blastabilityIndex = 0.06 * (rmd + jps + jpo + sgi + hardness);
  return Math.max(1.0, Math.min(14.0, blastabilityIndex));
}

/**
 * Relative Weight Strength (RWS) of explosive relative to ANFO (ANFO = 100)
 */
export function getExplosiveRWS(type: 'ANFO' | 'EMULSION_70_30' | 'HEAVY_ANFO'): number {
  switch (type) {
    case 'ANFO':
      return 100;
    case 'HEAVY_ANFO':
      return 115;
    case 'EMULSION_70_30':
      return 125;
    default:
      return 100;
  }
}

/**
 * Computes Kuz-Ram characteristic size (Xc), uniformity index (n),
 * and particle size distribution (PSD) curve.
 */
export function calculateKuzRamFragmentation(params: BlastInputParams): KuzRamResult {
  const rockFactorA = calculateRockMassFactor(params);
  const rws = getExplosiveRWS(params.explosiveType);
  const holeDiameterM = params.holeDiameterMm / 1000;
  
  // Hole volume and charge weight calculation
  const totalHoleDepth = params.benchHeight + params.subdrill;
  const chargeLength = Math.max(1.0, totalHoleDepth - params.stemmingLength);
  const holeAreaM2 = Math.PI * Math.pow(holeDiameterM / 2, 2);
  const explosiveDensity = params.explosiveType === 'ANFO' ? 0.82 : 1.18; // t/m3
  const chargeWeightKg = chargeLength * holeAreaM2 * (explosiveDensity * 1000);
  
  // Cunningham (1987) Mean / Characteristic size equation:
  // Xc = A * (K)^(-0.8) * Q^(1/6) * (115 / RWS)^(19/30) in cm, converted to mm
  // K = specific charge (powder factor in kg/m³)
  const k = Math.max(0.2, params.powderFactorKgM3);
  const q = Math.max(10, chargeWeightKg);
  
  const xcCm = rockFactorA * Math.pow(k, -0.8) * Math.pow(q, 0.1667) * Math.pow(115 / rws, 0.633);
  const xcMm = Math.max(15, xcCm * 10); // convert cm to mm

  // Uniformity Index n:
  // n = (2.2 - 14 * (B/d)) * sqrt((1 + S/B)/2) * (1 - W/B) * (L/H)
  const bOverD = params.burden / (params.holeDiameterMm / 1000); // burden to hole diameter in meters
  const sOverB = params.spacing / params.burden;
  const drillingAccuracyFactor = 1.0; // standard drill accuracy
  const chargeToBenchRatio = chargeLength / params.benchHeight;
  
  let n = (2.2 - 0.014 * bOverD) * Math.sqrt((1 + sOverB) / 2) * (1 - 0.1) * Math.min(1.5, Math.max(0.6, chargeToBenchRatio));
  n = Math.max(0.7, Math.min(2.1, n * drillingAccuracyFactor));

  // Rosin-Rammler: Cumulative Passing Y(x) = 1 - exp(- (x / Xc)^n)
  // Inverse for P20, P50, P80:
  // x = Xc * (-ln(1 - P))^(1/n)
  const p20 = Math.round(xcMm * Math.pow(-Math.log(1 - 0.20), 1 / n));
  const p50 = Math.round(xcMm * Math.pow(-Math.log(1 - 0.50), 1 / n));
  const p80 = Math.round(xcMm * Math.pow(-Math.log(1 - 0.80), 1 / n));

  // Oversize % (>1000 mm) & Fines % (<25 mm)
  const oversizePassing = 1 - Math.exp(-Math.pow(1000 / xcMm, n));
  const oversizePercent = Math.max(0.5, Math.round((1 - oversizePassing) * 1000) / 10);

  const finesPassing = 1 - Math.exp(-Math.pow(25 / xcMm, n));
  const finesPercent = Math.max(1.0, Math.round(finesPassing * 1000) / 10);

  // Generate 25 points along PSD curve for visualization (from 1mm to 1500mm)
  const sampleSizesMm = [5, 10, 25, 50, 75, 100, 150, 200, 250, 300, 400, 500, 600, 750, 900, 1000, 1200, 1500];
  const curveData = sampleSizesMm.map((size) => {
    const passing = (1 - Math.exp(-Math.pow(size / xcMm, n))) * 100;
    return {
      sizeMm: size,
      passingPercent: Math.min(100, Math.max(0, Math.round(passing * 10) / 10)),
    };
  });

  return {
    p20,
    p50,
    p80,
    characteristicSizeXc: Math.round(xcMm),
    uniformityIndexN: Math.round(n * 100) / 100,
    oversizePercent,
    finesPercent,
    curveData,
  };
}

/**
 * Mine-to-Mill Downstream Impact Propagation
 * Converts upstream fragmentation P80 & rock hardness into downstream operating metrics.
 */
export interface MineToMillImpact {
  shovelDigTimePassSeconds: number; // nominal 28s -> increases if coarse P80
  bucketFillFactorPercent: number; // nominal 95% -> drops if oversize
  shovelProductivityTph: number; // t/h
  crusherFeedRateTph: number; // nominal 4200 t/h -> drops if P80 > 250mm
  crusherChokeRisk: 'LOW' | 'MEDIUM' | 'HIGH';
  sagMillSpecificEnergyKwhT: number; // nominal 18.2 kWh/t
  sagMillThroughputTph: number; // nominal 3400 t/h -> increases with finer feed
  flotationCuRecoveryPercent: number; // %
  flotationRecoveryCuPercent?: number; // %
  totalCostPerTonMinedUsd: number; // Drill + Blast + Load + Haul + Crush + Mill
}

export function evaluateMineToMillImpact(
  kuzRam: KuzRamResult,
  rockUCSMpa: number,
  powderFactorKgM3: number,
  baseShovelCapacityTons = 95,
  truckCount = 14
): MineToMillImpact {
  // 1. Shovel Performance
  // Dig time increases non-linearly when P80 exceeds 300mm or rock UCS > 140MPa
  const coarsenessFactor = Math.max(0, (kuzRam.p80 - 200) / 300);
  const hardnessFactor = Math.max(0, (rockUCSMpa - 100) / 100);
  const shovelDigTimePassSeconds = Math.round((24 + coarsenessFactor * 12 + hardnessFactor * 6) * 10) / 10;
  
  // Bucket fill factor decreases with high oversize
  const bucketFillFactorPercent = Math.max(70, Math.min(98, Math.round((96 - kuzRam.oversizePercent * 1.8) * 10) / 10));
  
  const effectivePayloadPerPass = baseShovelCapacityTons * (bucketFillFactorPercent / 100);
  const cyclePassSeconds = shovelDigTimePassSeconds + 8.5; // swing + dump + return
  const shovelProductivityTph = Math.round((effectivePayloadPerPass * (3600 / cyclePassSeconds)) * 0.85); // 85% operational efficiency

  // 2. Crusher Performance
  // Primary Gyratory crusher throughput drops when fed coarse muckpile
  const crusherBaseCapacity = 4500; // t/h
  const crusherCoarsePenalty = Math.max(0, (kuzRam.p80 - 180) * 3.5);
  const crusherBoulderPenalty = kuzRam.oversizePercent * 60;
  const crusherFeedRateTph = Math.max(2200, Math.round(crusherBaseCapacity - crusherCoarsePenalty - crusherBoulderPenalty));
  const crusherChokeRisk = kuzRam.oversizePercent > 8 ? 'HIGH' : kuzRam.oversizePercent > 4 ? 'MEDIUM' : 'LOW';

  // 3. SAG Milling & Specific Energy (Bond / Morrell approach)
  // SAG mill throughput is strongly tied to feed size P80. Finer blast fragmentation saves massive mill power!
  const baseSpecificEnergy = 14.5; // kWh/t for standard 150mm P80
  const fragmentationEnergyDelta = (kuzRam.p80 - 150) * 0.028; // +0.28 kWh/t per 10mm coarser
  const rockHardnessEnergyDelta = (rockUCSMpa - 120) * 0.045; // +0.45 kWh/t per 10MPa harder
  const sagMillSpecificEnergyKwhT = Math.max(11.0, Math.min(26.0, Math.round((baseSpecificEnergy + fragmentationEnergyDelta + rockHardnessEnergyDelta) * 100) / 100));

  const totalMillInstalledPowerKw = 28000; // 28 MW SAG Mill motor
  const sagMillThroughputTph = Math.round((totalMillInstalledPowerKw * 0.92) / sagMillSpecificEnergyKwhT);

  // 4. Flotation Cu Recovery
  const flotationCuRecoveryPercent = Math.round((89.2 - Math.max(0, (sagMillSpecificEnergyKwhT - 18) * 0.4)) * 10) / 10;

  // 5. Total Operating Cost ($/t of ore through to mill)
  const drillCost = 0.45;
  const blastCost = powderFactorKgM3 * 1.85; // explosive $/kg
  const loadCost = (shovelDigTimePassSeconds / 24) * 0.85;
  const haulCost = (truckCount / 14) * 2.10;
  const crushCost = 0.55 + (kuzRam.oversizePercent > 5 ? 0.25 : 0);
  const millPowerCost = sagMillSpecificEnergyKwhT * 0.085; // $0.085 per kWh
  const totalCostPerTonMinedUsd = Math.round((drillCost + blastCost + loadCost + haulCost + crushCost + millPowerCost) * 100) / 100;

  return {
    shovelDigTimePassSeconds,
    bucketFillFactorPercent,
    shovelProductivityTph,
    crusherFeedRateTph,
    crusherChokeRisk,
    sagMillSpecificEnergyKwhT,
    sagMillThroughputTph,
    flotationCuRecoveryPercent,
    totalCostPerTonMinedUsd,
  };
}
