/**
 * MineTwin AI - Road Network & Pit Topography Geometry
 * Defines 3D waypoints, road ramps, gradients, and spline interpolation for haul truck agents.
 */

import { Position3D, RoadSegment } from '../types/mining';

export const PIT_BENCHES = [
  { elevation: 4000, name: 'Bench 4000 (Surface Rim / Crusher)', radius: 320, color: '#64748b' },
  { elevation: 3920, name: 'Bench 3920 (Upper Berm)', radius: 270, color: '#78716c' },
  { elevation: 3840, name: 'Bench 3840 (Active Face EX-01 & Pattern 104)', radius: 210, color: '#a8a29e' },
  { elevation: 3760, name: 'Bench 3760 (Mid Ramp Switchback)', radius: 150, color: '#71717a' },
  { elevation: 3680, name: 'Bench 3680 (Pit Bottom EX-02 High Grade)', radius: 90, color: '#d97706' },
];

export const MINE_LOCATIONS = {
  CRUSHER_HOPPER: { x: 180, y: 12, z: -140, elevation: 4000, name: 'Primary Crusher CR-01' } as Position3D,
  WASTE_DUMP_NORTH: { x: -220, y: 14, z: -180, elevation: 4005, name: 'North Waste Dump WD-01' } as Position3D,
  STOCKPILE_ROM: { x: 230, y: 11, z: 80, elevation: 4000, name: 'ROM Stockpile SP-01' } as Position3D,
  SHOVEL_EX01: { x: 45, y: 4.8, z: 90, elevation: 3840, name: 'Shovel EX-01 (Bench 3840)' } as Position3D,
  SHOVEL_EX02: { x: -25, y: -2.4, z: -15, elevation: 3680, name: 'Shovel EX-02 (Bench 3680 Pit Bottom)' } as Position3D,
  DRILL_PAD_01: { x: 85, y: 5.0, z: 60, elevation: 3840, name: 'Drill Pad #104' } as Position3D,
  DRILL_PAD_02: { x: -60, y: -2.2, z: -40, elevation: 3680, name: 'Drill Pad #105' } as Position3D,
  MILL_CIRCUIT: { x: 280, y: 10, z: -160, elevation: 3995, name: 'SAG/Ball Mill Plant ML-01' } as Position3D,
};

export const INITIAL_ROAD_SEGMENTS: RoadSegment[] = [
  {
    id: 'RD-RAMP-BENCH-3840-CRUSHER',
    name: 'Main Haul Ramp (Bench 3840 to Crusher)',
    startPoint: MINE_LOCATIONS.SHOVEL_EX01,
    endPoint: MINE_LOCATIONS.CRUSHER_HOPPER,
    waypoints: [
      { x: 45, y: 4.8, z: 90 },
      { x: 95, y: 6.2, z: 120 },
      { x: 160, y: 8.5, z: 60 },
      { x: 190, y: 10.5, z: -40 },
      { x: 180, y: 12.0, z: -140 },
    ],
    distanceMeters: 1420,
    gradientPercent: 7.8,
    rollingResistancePercent: 2.8,
    speedLimitKmh: 42,
    currentTrafficCount: 4,
    capacityMaxTrucks: 8,
    roadCondition: 'GOOD',
    weatherEffectFactor: 1.0,
    currentTravelTimeSeconds: 145,
    predictedTravelTimeSeconds: 148,
    dustLevelPpm: 18,
  },
  {
    id: 'RD-RAMP-PIT-BOTTOM-3680-3840',
    name: 'Deep Pit Switchback (Bench 3680 to 3840)',
    startPoint: MINE_LOCATIONS.SHOVEL_EX02,
    endPoint: MINE_LOCATIONS.SHOVEL_EX01,
    waypoints: [
      { x: -25, y: -2.4, z: -15 },
      { x: -65, y: -0.5, z: 25 },
      { x: -30, y: 1.8, z: 70 },
      { x: 15, y: 3.5, z: 85 },
      { x: 45, y: 4.8, z: 90 },
    ],
    distanceMeters: 1650,
    gradientPercent: 9.4,
    rollingResistancePercent: 3.2,
    speedLimitKmh: 36,
    currentTrafficCount: 3,
    capacityMaxTrucks: 6,
    roadCondition: 'GOOD',
    weatherEffectFactor: 1.0,
    currentTravelTimeSeconds: 182,
    predictedTravelTimeSeconds: 185,
    dustLevelPpm: 24,
  },
  {
    id: 'RD-CRUSHER-TO-WASTE-DUMP',
    name: 'Surface Haul Road (Crusher to North Dump)',
    startPoint: MINE_LOCATIONS.CRUSHER_HOPPER,
    endPoint: MINE_LOCATIONS.WASTE_DUMP_NORTH,
    waypoints: [
      { x: 180, y: 12.0, z: -140 },
      { x: 80, y: 13.0, z: -190 },
      { x: -80, y: 13.5, z: -210 },
      { x: -220, y: 14.0, z: -180 },
    ],
    distanceMeters: 1850,
    gradientPercent: 2.1,
    rollingResistancePercent: 2.4,
    speedLimitKmh: 50,
    currentTrafficCount: 2,
    capacityMaxTrucks: 10,
    roadCondition: 'EXCELLENT',
    weatherEffectFactor: 1.0,
    currentTravelTimeSeconds: 140,
    predictedTravelTimeSeconds: 140,
    dustLevelPpm: 12,
  },
  {
    id: 'RD-CRUSHER-TO-STOCKPILE',
    name: 'Surface Ring (Crusher to ROM Stockpile)',
    startPoint: MINE_LOCATIONS.CRUSHER_HOPPER,
    endPoint: MINE_LOCATIONS.STOCKPILE_ROM,
    waypoints: [
      { x: 180, y: 12.0, z: -140 },
      { x: 220, y: 11.5, z: -40 },
      { x: 230, y: 11.0, z: 80 },
    ],
    distanceMeters: 890,
    gradientPercent: 1.5,
    rollingResistancePercent: 2.2,
    speedLimitKmh: 45,
    currentTrafficCount: 1,
    capacityMaxTrucks: 6,
    roadCondition: 'EXCELLENT',
    weatherEffectFactor: 1.0,
    currentTravelTimeSeconds: 78,
    predictedTravelTimeSeconds: 80,
    dustLevelPpm: 10,
  },
  {
    id: 'RD-RETURN-CRUSHER-TO-EX01',
    name: 'Empty Return Road (Crusher to EX-01)',
    startPoint: MINE_LOCATIONS.CRUSHER_HOPPER,
    endPoint: MINE_LOCATIONS.SHOVEL_EX01,
    waypoints: [
      { x: 180, y: 12.0, z: -140 },
      { x: 175, y: 10.0, z: -35 },
      { x: 145, y: 8.0, z: 55 },
      { x: 85, y: 5.8, z: 115 },
      { x: 45, y: 4.8, z: 90 },
    ],
    distanceMeters: 1420,
    gradientPercent: -7.8, // Downhill
    rollingResistancePercent: 2.8,
    speedLimitKmh: 48,
    currentTrafficCount: 3,
    capacityMaxTrucks: 8,
    roadCondition: 'GOOD',
    weatherEffectFactor: 1.0,
    currentTravelTimeSeconds: 115,
    predictedTravelTimeSeconds: 118,
    dustLevelPpm: 16,
  },
  {
    id: 'RD-RETURN-EX01-TO-EX02',
    name: 'Empty Return Road (EX-01 to Pit Bottom EX-02)',
    startPoint: MINE_LOCATIONS.SHOVEL_EX01,
    endPoint: MINE_LOCATIONS.SHOVEL_EX02,
    waypoints: [
      { x: 45, y: 4.8, z: 90 },
      { x: 10, y: 3.2, z: 80 },
      { x: -35, y: 1.5, z: 65 },
      { x: -60, y: -0.8, z: 20 },
      { x: -25, y: -2.4, z: -15 },
    ],
    distanceMeters: 1650,
    gradientPercent: -9.4, // Downhill
    rollingResistancePercent: 3.2,
    speedLimitKmh: 40,
    currentTrafficCount: 2,
    capacityMaxTrucks: 6,
    roadCondition: 'GOOD',
    weatherEffectFactor: 1.0,
    currentTravelTimeSeconds: 155,
    predictedTravelTimeSeconds: 158,
    dustLevelPpm: 20,
  },
];

/**
 * Spline interpolation helper for smooth truck 3D movement along road waypoints
 */
export function interpolateRoadPosition(waypoints: Position3D[], progress: number): { position: Position3D; heading: number } {
  if (!waypoints || waypoints.length === 0) {
    return { position: { x: 0, y: 0, z: 0 }, heading: 0 };
  }
  if (waypoints.length === 1) {
    return { position: { ...waypoints[0] }, heading: 0 };
  }

  const clampedProgress = Math.max(0, Math.min(0.9999, progress));
  const segmentCount = waypoints.length - 1;
  const scaledIndex = clampedProgress * segmentCount;
  const index = Math.floor(scaledIndex);
  const segmentProgress = scaledIndex - index;

  const p0 = waypoints[index];
  const p1 = waypoints[Math.min(waypoints.length - 1, index + 1)];

  const x = p0.x + (p1.x - p0.x) * segmentProgress;
  const y = p0.y + (p1.y - p0.y) * segmentProgress;
  const z = p0.z + (p1.z - p0.z) * segmentProgress;

  // Compute heading in degrees (0 to 360)
  const dx = p1.x - p0.x;
  const dz = p1.z - p0.z;
  let angleDeg = (Math.atan2(dx, dz) * 180) / Math.PI;
  if (angleDeg < 0) angleDeg += 360;

  return {
    position: { x, y, z },
    heading: Math.round(angleDeg),
  };
}
