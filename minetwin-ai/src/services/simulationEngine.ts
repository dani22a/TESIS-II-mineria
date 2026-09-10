/**
 * MineTwin AI - Agent-Based & Discrete-Event Simulation Engine
 * Simulates real-time dynamics of trucks, shovels, drills, crusher, and mill.
 */

import {
  CycleState,
  DigitalTwinState,
  DispatchStrategy,
  DRLRecommendation,
  MineAlert,
  TruckTwin,
} from '../types/mining';
import { interpolateRoadPosition } from './roadNetwork';

export class SimulationEngine {
  /**
   * Advances the simulation by deltaSeconds (scaled by speedMultiplier)
   */
  public static tick(currentState: DigitalTwinState, realDeltaMs: number): DigitalTwinState {
    if (currentState.isPaused) return currentState;

    const dtSeconds = (realDeltaMs / 1000) * currentState.simSpeedMultiplier;
    const simTimeSeconds = currentState.simTimeSeconds + dtSeconds;

    // Clone mutable entities
    const trucks: TruckTwin[] = currentState.trucks.map((t) => ({ ...t }));
    const shovels = currentState.shovels.map((s) => ({ ...s, truckQueue: [...s.truckQueue] }));
    const crusher = { ...currentState.crusher, trucksInQueue: [...currentState.crusher.trucksInQueue] };
    const mill = { ...currentState.mill };
    const drills = currentState.drills.map((d) => ({ ...d }));
    const roads = currentState.roads.map((r) => ({ ...r }));
    const alerts: MineAlert[] = [...currentState.alerts];
    const recommendations: DRLRecommendation[] = [...currentState.recommendations];

    // 1. Process Shovel loading cycles
    shovels.forEach((shovel) => {
      if (shovel.currentTruckLoadingId) {
        const truck = trucks.find((t) => t.id === shovel.currentTruckLoadingId);
        if (truck && truck.cycleState === 'LOADING') {
          // Increment loading progress
          truck.routeProgress += dtSeconds / (shovel.cycleTimePerPassSeconds * shovel.passesPerTruck);
          truck.payloadCurrent = Math.min(truck.payloadCapacity, truck.payloadCapacity * Math.min(1.0, truck.routeProgress));

          if (truck.routeProgress >= 1.0) {
            // Loading finished -> Transition to HAULING
            truck.cycleState = 'HAULING';
            truck.routeProgress = 0.0;
            truck.payloadCurrent = truck.payloadCapacity * (0.95 + Math.random() * 0.07); // ~95-102% target load
            shovel.totalMinedTodayTons += truck.payloadCurrent;

            // Route selection based on material
            if (truck.materialType === 'HIGH_GRADE_CU') {
              truck.destinationType = 'CRUSHER';
              truck.destinationId = crusher.id;
              truck.routeId = shovel.id === 'EX-01' ? 'RD-RAMP-BENCH-3840-CRUSHER' : 'RD-RAMP-PIT-BOTTOM-3680-3840';
            } else if (truck.materialType === 'LOW_GRADE_CU') {
              truck.destinationType = 'STOCKPILE';
              truck.destinationId = 'SP-01';
              truck.routeId = 'RD-CRUSHER-TO-STOCKPILE';
            } else {
              truck.destinationType = 'WASTE_DUMP';
              truck.destinationId = 'WD-01';
              truck.routeId = 'RD-CRUSHER-TO-WASTE-DUMP';
            }
            truck.currentRoadSegmentId = truck.routeId;

            // Shovel grabs next truck from queue if available
            if (shovel.truckQueue.length > 0) {
              const nextTruckId = shovel.truckQueue.shift()!;
              shovel.currentTruckLoadingId = nextTruckId;
              const nextTruck = trucks.find((t) => t.id === nextTruckId);
              if (nextTruck) {
                nextTruck.cycleState = 'LOADING';
                nextTruck.routeProgress = 0.0;
              }
            } else {
              shovel.currentTruckLoadingId = null;
            }
          }
        }
      } else if (shovel.truckQueue.length > 0) {
        // Take next queued truck
        const nextTruckId = shovel.truckQueue.shift()!;
        shovel.currentTruckLoadingId = nextTruckId;
        const nextTruck = trucks.find((t) => t.id === nextTruckId);
        if (nextTruck) {
          nextTruck.cycleState = 'LOADING';
          nextTruck.routeProgress = 0.0;
        }
      }
    });

    // 2. Process Crusher dumping
    const dumpingTrucks = trucks.filter((t) => t.destinationType === 'CRUSHER' && t.cycleState === 'DUMPING');
    dumpingTrucks.forEach((truck) => {
      truck.routeProgress += dtSeconds / 35.0; // 35s dump time
      if (truck.routeProgress >= 1.0) {
        // Dumping complete -> Transition to RETURNING
        crusher.accumulatedTonsToday += truck.payloadCurrent;
        truck.payloadCurrent = 0;
        truck.cycleState = 'RETURNING';
        truck.routeProgress = 0.0;

        // Apply Dispatch Strategy to assign next shovel
        const assignedShovelId = this.applyDispatchStrategy(
          truck,
          shovels,
          currentState.activeDispatchStrategy
        );
        truck.assignedShovelId = assignedShovelId;
        truck.destinationId = assignedShovelId;
        truck.destinationType = 'SHOVEL';
        truck.routeId = assignedShovelId === 'EX-01' ? 'RD-RETURN-CRUSHER-TO-EX01' : 'RD-RETURN-EX01-TO-EX02';
        truck.currentRoadSegmentId = truck.routeId;

        // Remove from crusher queue
        crusher.trucksInQueue = crusher.trucksInQueue.filter((id) => id !== truck.id);
      }
    });

    // 3. Process each Truck movement and state logic
    trucks.forEach((truck) => {
      const currentRoad = roads.find((r) => r.id === truck.currentRoadSegmentId) || roads[0];

      // Calculate speed based on gradient, payload, and speed limit
      const isLoaded = truck.payloadCurrent > 0;
      let effectiveSpeed = currentRoad.speedLimitKmh;

      if (isLoaded) {
        if (currentRoad.gradientPercent > 4) {
          effectiveSpeed = Math.max(18, currentRoad.speedLimitKmh - (currentRoad.gradientPercent * 2.2));
        }
        truck.fuelRate = 340 + currentRoad.gradientPercent * 18;
      } else {
        if (currentRoad.gradientPercent < -4) {
          effectiveSpeed = currentRoad.speedLimitKmh * 1.05; // faster downhill empty
        }
        truck.fuelRate = 160 + Math.abs(currentRoad.gradientPercent) * 6;
      }

      truck.speed = effectiveSpeed;

      // Update travel progress along road segments
      if (truck.cycleState === 'HAULING' || truck.cycleState === 'RETURNING' || truck.cycleState === 'EMPTY_TRAVEL') {
        const distanceMetersTraveled = (effectiveSpeed * 1000 / 3600) * dtSeconds;
        const progressDelta = distanceMetersTraveled / Math.max(500, currentRoad.distanceMeters);
        truck.routeProgress += progressDelta;

        // Check if arrived at destination
        if (truck.routeProgress >= 1.0) {
          truck.routeProgress = 1.0;

          if (truck.cycleState === 'HAULING') {
            if (truck.destinationType === 'CRUSHER') {
              if (crusher.trucksInQueue.length === 0 && !dumpingTrucks.some((t) => t.id !== truck.id && t.cycleState === 'DUMPING')) {
                truck.cycleState = 'DUMPING';
                truck.routeProgress = 0.0;
              } else {
                truck.cycleState = 'QUEUE_DESTINATION';
                if (!crusher.trucksInQueue.includes(truck.id)) {
                  crusher.trucksInQueue.push(truck.id);
                }
              }
            } else {
              // Stockpile or Waste dump
              truck.cycleState = 'DUMPING';
              truck.routeProgress = 0.0;
            }
          } else if (truck.cycleState === 'RETURNING' || truck.cycleState === 'EMPTY_TRAVEL') {
            // Arrived at shovel
            const shovel = shovels.find((s) => s.id === truck.assignedShovelId) || shovels[0];
            if (!shovel.currentTruckLoadingId) {
              shovel.currentTruckLoadingId = truck.id;
              truck.cycleState = 'LOADING';
              truck.routeProgress = 0.0;
            } else {
              truck.cycleState = 'QUEUE_SHOVEL';
              if (!shovel.truckQueue.includes(truck.id)) {
                shovel.truckQueue.push(truck.id);
              }
            }
          }
        }
      }

      // If in destination queue and crusher becomes free
      if (truck.cycleState === 'QUEUE_DESTINATION' && truck.destinationType === 'CRUSHER') {
        const isCrusherEmpty = !trucks.some((t) => t.id !== truck.id && t.cycleState === 'DUMPING');
        if (isCrusherEmpty && crusher.trucksInQueue[0] === truck.id) {
          truck.cycleState = 'DUMPING';
          truck.routeProgress = 0.0;
        }
      }

      // Compute 3D world position & heading along road spline
      const { position, heading } = interpolateRoadPosition(currentRoad.waypoints, truck.routeProgress);
      truck.position = position;
      truck.heading = heading;

      // Fuel burn
      const fuelUsedLiters = (truck.fuelRate / 3600) * dtSeconds;
      truck.fuelLevel = Math.max(5, truck.fuelLevel - (fuelUsedLiters / 4500) * 100);
    });

    // 4. Update Drill Rigs progress
    drills.forEach((drill) => {
      if (drill.operatingState === 'OPERATIONAL') {
        const depthDelta = (drill.penetrationRateMph / 3600) * dtSeconds;
        drill.currentHoleDepth += depthDelta;
        if (drill.currentHoleDepth >= drill.targetHoleDepth) {
          drill.drilledHolesCount = Math.min(drill.totalHolesInPattern, drill.drilledHolesCount + 1);
          drill.currentHoleDepth = 0.0;
          drill.currentHoleId = `BH-${drill.patternId.split('-')[1]}-${String(drill.drilledHolesCount + 1).padStart(2, '0')}`;
        }
      }
    });

    // 5. Update Crusher & Mill circuits
    const activeCrushersThroughput = dumpingTrucks.length > 0 ? 4450 : 3800;
    crusher.throughputTph = Math.round(activeCrushersThroughput + (Math.random() * 80 - 40));
    crusher.chokeLevelPercent = Math.min(95, Math.max(30, Math.round(crusher.chokeLevelPercent + (dumpingTrucks.length * 4 - 1.5))));

    mill.sagMillThroughputTph = Math.round(3550 + Math.random() * 60 - 30);
    mill.specificEnergyKwhPerTon = Math.round((15.6 + Math.random() * 0.4) * 10) / 10;

    // 6. Aggregate Live KPIs
    const totalTonsToday = shovels.reduce((acc, s) => acc + s.totalMinedTodayTons, 0);
    const hourlyRate = Math.round(shovels.reduce((acc, s) => acc + s.productivityTph, 0));
    const avgCycle = Math.round((trucks.reduce((acc, t) => acc + t.cycleTimeMinutes, 0) / trucks.length) * 10) / 10;
    const avgQueue = Math.round((shovels.reduce((acc, s) => acc + s.truckQueue.length * 2.8, 0) / shovels.length) * 10) / 10;
    const totalFuelRate = Math.round(trucks.reduce((acc, t) => acc + t.fuelRate, 0));

    // Update historical KPI buffer periodically (every ~30 sim seconds)
    let kpiHistory = currentState.kpiHistory;
    if (Math.floor(simTimeSeconds / 30) > Math.floor(currentState.simTimeSeconds / 30)) {
      const now = new Date();
      const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
      kpiHistory = [
        ...kpiHistory.slice(-12),
        {
          time: timeStr,
          productionTph: hourlyRate,
          millThroughputTph: mill.sagMillThroughputTph,
          avgCycleTimeMin: avgCycle,
          avgQueueTimeMin: avgQueue,
          fuelLph: totalFuelRate,
          unitCost: Math.round((6.20 + (avgQueue * 0.15)) * 100) / 100,
        },
      ];
    }

    return {
      ...currentState,
      simTimeSeconds,
      trucks,
      shovels,
      drills,
      crusher,
      mill,
      alerts,
      recommendations,
      kpiHistory,
    };
  }

  /**
   * Dispatch Engine Strategy Algorithm
   */
  public static applyDispatchStrategy(
    truck: TruckTwin,
    shovels: { id: string; truckQueue: string[]; productivityTph: number }[],
    strategy: DispatchStrategy
  ): string {
    const s1 = shovels.find((s) => s.id === 'EX-01') || shovels[0];
    const s2 = shovels.find((s) => s.id === 'EX-02') || shovels[1] || shovels[0];

    switch (strategy) {
      case 'SHORTEST_QUEUE':
        return s1.truckQueue.length <= s2.truckQueue.length ? s1.id : s2.id;

      case 'MIN_CYCLE_TIME':
        // Bench 3840 (EX-01) is closer to crusher than Pit Bottom Bench 3680 (EX-02)
        return s1.truckQueue.length < 3 ? s1.id : s2.id;

      case 'PRODUCTION_BALANCING':
        return s1.productivityTph < s2.productivityTph ? s1.id : s2.id;

      case 'CRUSHER_PRIORITY':
        // Favor high grade skarn ore at pit bottom (EX-02) unless queue is high
        return s2.truckQueue.length <= 1 ? s2.id : s1.id;

      case 'DRL_MULTI_OBJECTIVE':
      default:
        // Multi-Agent Reinforcement Learning policy balance
        // Dynamic balance based on queue length, travel time, and mill blend
        if (s2.truckQueue.length === 0) return s2.id;
        if (s1.truckQueue.length <= s2.truckQueue.length) return s1.id;
        return s2.id;
    }
  }
}
