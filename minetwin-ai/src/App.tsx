/**
 * MineTwin AI - Industrial Mining Digital Twin Application Entry Point
 * Drill-Blast-Load-Haul-Crush-Mill Integrated Simulation & Optimization
 */

import React, { useEffect, useRef, useState } from 'react';
import { CommandCenterHeader } from './components/CommandCenterHeader';
import { ActiveModule, NavigationSidebar } from './components/NavigationSidebar';
import { DigitalTwinView } from './components/views/DigitalTwinView';
import { DrillBlastView } from './components/views/DrillBlastView';
import { LoadHaulView } from './components/views/LoadHaulView';
import { MineToMillView } from './components/views/MineToMillView';
import { ScenarioLabView } from './components/views/ScenarioLabView';
import { AiOptimizerView } from './components/views/AiOptimizerView';
import { AnalyticsView } from './components/views/AnalyticsView';
import { SystemDataView } from './components/views/SystemDataView';
import { AssetDetailModal } from './components/modals/AssetDetailModal';
import { TimeMachineModal } from './components/modals/TimeMachineModal';
import { HumanInTheLoopModal } from './components/modals/HumanInTheLoopModal';
import { AlertsModal } from './components/modals/AlertsModal';
import {
  DigitalTwinState,
  DispatchStrategy,
  DRLRecommendation,
  DRLRewardWeights,
  UserRole,
} from './types/mining';
import { createInitialTwinState } from './services/mockData';
import { SimulationEngine } from './services/simulationEngine';
import { CopilotView } from './components/views/CopilotView';

export function App() {
  const [state, setState] = useState<DigitalTwinState>(() => createInitialTwinState());
  const [activeModule, setActiveModule] = useState<ActiveModule>('TWIN_3D');

  // Modals state
  const [detailAssetId, setDetailAssetId] = useState<string | null>(null);
  const [isTimeMachineOpen, setIsTimeMachineOpen] = useState<boolean>(false);
  const [isRecommendationsOpen, setIsRecommendationsOpen] = useState<boolean>(false);
  const [isAlertsOpen, setIsAlertsOpen] = useState<boolean>(false);

  // Simulation loop reference
  const stateRef = useRef(state);
  stateRef.current = state;
  const lastTimeRef = useRef<number>(performance.now());

  useEffect(() => {
    let animationFrameId: number;

    const loop = (time: number) => {
      const dt = Math.min((time - lastTimeRef.current) / 1000, 0.1);
      lastTimeRef.current = time;

      if (stateRef.current.isSimulating) {
        setState((prevState) => SimulationEngine.tick(prevState, dt));
      }

      animationFrameId = requestAnimationFrame(loop);
    };

    animationFrameId = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(animationFrameId);
  }, []);

  // Handlers
  const handleChangeSpeed = (speed: number) => {
    setState((prev) => ({ ...prev, simulationSpeed: speed, simSpeedMultiplier: speed }));
  };

  const handleTogglePlay = () => {
    setState((prev) => {
      const nextPaused = !prev.isPaused;
      return { ...prev, isPaused: nextPaused, isSimulating: !nextPaused };
    });
  };

  const handleResetSimulation = () => {
    setState(createInitialTwinState());
  };

  const handleChangeStrategy = (strategy: DispatchStrategy) => {
    setState((prev) => ({ ...prev, currentStrategy: strategy }));
  };

  const handleSelectAsset = (
    id: string,
    type: 'TRUCK' | 'SHOVEL' | 'DRILL' | 'BLAST' | 'CRUSHER' | 'BLOCK' | 'ROAD'
  ) => {
    setState((prev) => ({
      ...prev,
      selectedAssetId: id,
      selectedAssetType: type,
    }));
  };

  const handleToggleLayer = (layerKey: keyof DigitalTwinState['visibleLayers']) => {
    setState((prev) => ({
      ...prev,
      visibleLayers: {
        ...prev.visibleLayers,
        [layerKey]: !prev.visibleLayers[layerKey],
      },
    }));
  };

  const handleManualReassignTruck = (truckId: string, newShovelId: string) => {
    setState((prev) => ({
      ...prev,
      trucks: prev.trucks.map((t) =>
        t.id === truckId ? { ...t, assignedShovelId: newShovelId } : t
      ),
    }));
  };

  const handleApproveRecommendation = (recId: string) => {
    setState((prev) => {
      const rec = prev.recommendations.find((r) => r.id === recId);
      if (!rec) return prev;

      const action = rec.suggestedAction;
      let updatedTrucks = [...prev.trucks];
      let blastPatterns = prev.blastPatterns;
      let currentStrategy = prev.currentStrategy;
      let activeDispatchStrategy = prev.activeDispatchStrategy;

      if (action) {
        const truckIds =
          action.truckIds && action.truckIds.length > 0
            ? action.truckIds
            : action.targetAssetId
              ? action.targetAssetId.split(',').map((id) => id.trim())
              : [];

        if (action.newShovelId && truckIds.length > 0) {
          updatedTrucks = updatedTrucks.map((t) =>
            truckIds.includes(t.id) ? { ...t, assignedShovelId: action.newShovelId || t.assignedShovelId } : t
          );
        }

        if (action.destinationType && truckIds.length > 0) {
          updatedTrucks = updatedTrucks.map((t) =>
            truckIds.includes(t.id)
              ? {
                  ...t,
                  destinationType: action.destinationType!,
                  destinationId: action.destinationType === 'CRUSHER' ? prev.crusher.id : t.destinationId,
                }
              : t
          );
        }

        if (action.patternId && action.powderFactor != null) {
          blastPatterns = blastPatterns.map((p) =>
            p.id === action.patternId ? { ...p, powderFactor: action.powderFactor! } : p
          );
        }

        if (action.strategy) {
          currentStrategy = action.strategy;
          activeDispatchStrategy = action.strategy;
        }
      }

      return {
        ...prev,
        trucks: updatedTrucks,
        blastPatterns,
        currentStrategy,
        activeDispatchStrategy,
        recommendations: prev.recommendations.map((r) =>
          r.id === recId ? { ...r, status: 'APPROVED' } : r
        ),
      };
    });
  };

  const handleProposeRecommendation = (rec: DRLRecommendation) => {
    setState((prev) => {
      if (prev.recommendations.some((r) => r.id === rec.id)) return prev;
      return { ...prev, recommendations: [rec, ...prev.recommendations] };
    });
  };

  const handleRejectRecommendation = (recId: string) => {
    setState((prev) => ({
      ...prev,
      recommendations: prev.recommendations.map((r) =>
        r.id === recId ? { ...r, status: 'REJECTED' } : r
      ),
    }));
  };

  const handleAcknowledgeAlert = (alertId: string) => {
    setState((prev) => ({
      ...prev,
      alerts: prev.alerts.map((a) =>
        a.id === alertId ? { ...a, acknowledged: true } : a
      ),
    }));
  };

  const handleUpdateRewardWeights = (weights: DRLRewardWeights) => {
    setState((prev) => ({
      ...prev,
      rewardWeights: weights,
    }));
  };

  const handleChangeRole = (role: UserRole) => {
    setState((prev) => ({
      ...prev,
      currentUserRole: role,
    }));
  };

  return (
    <div className="flex flex-col w-screen h-screen overflow-hidden bg-slate-950 text-slate-100 font-sans">
      {/* Top Industrial HUD Command Center */}
      <CommandCenterHeader
        state={state}
        onTogglePlay={handleTogglePlay}
        onChangeSpeed={handleChangeSpeed}
        onChangeStrategy={handleChangeStrategy}
        onOpenTimeMachine={() => setIsTimeMachineOpen(true)}
        onOpenAlerts={() => setIsAlertsOpen(true)}
        onOpenRecommendations={() => setIsRecommendationsOpen(true)}
        onResetSimulation={handleResetSimulation}
      />

      {/* Main App Layout: Sidebar + Active Module View */}
      <div className="flex flex-1 overflow-hidden">
        <NavigationSidebar
          activeModule={activeModule}
          onChangeModule={setActiveModule}
          visibleLayers={state.visibleLayers}
          onToggleLayer={handleToggleLayer}
        />

        <main className="flex-1 relative overflow-hidden bg-slate-950">
          {activeModule === 'TWIN_3D' && (
            <DigitalTwinView
              state={state}
              onSelectAsset={handleSelectAsset}
              onOpenAssetDetail={(id) => setDetailAssetId(id)}
              onOpenRecommendations={() => setIsRecommendationsOpen(true)}
              onApproveRecommendation={handleApproveRecommendation}
            />
          )}

          {activeModule === 'DRILL_BLAST' && (
            <DrillBlastView
              state={state}
              onUpdatePattern={(id, params) => {
                setState((prev) => ({
                  ...prev,
                  blastPatterns: prev.blastPatterns.map((p) =>
                    p.id === id ? { ...p, ...params } : p
                  ),
                }));
              }}
            />
          )}

          {activeModule === 'LOAD_HAUL' && (
            <LoadHaulView
              state={state}
              onSelectTruck={(truckId) => {
                handleSelectAsset(truckId, 'TRUCK');
                setDetailAssetId(truckId);
              }}
              onOpenAssetDetail={(id) => setDetailAssetId(id)}
              onManualReassignTruck={handleManualReassignTruck}
            />
          )}

          {activeModule === 'MINE_TO_MILL' && <MineToMillView state={state} />}

          {activeModule === 'SCENARIO_LAB' && <ScenarioLabView state={state} />}

          {activeModule === 'COPILOT' && (
            <CopilotView
              state={state}
              onProposeRecommendation={handleProposeRecommendation}
              onApproveRecommendation={handleApproveRecommendation}
              onRejectRecommendation={handleRejectRecommendation}
            />
          )}

          {activeModule === 'AI_OPTIMIZER' && (
            <AiOptimizerView
              state={state}
              onUpdateRewardWeights={handleUpdateRewardWeights}
              onApproveRecommendation={handleApproveRecommendation}
              onRejectRecommendation={handleRejectRecommendation}
            />
          )}

          {activeModule === 'ANALYTICS' && <AnalyticsView state={state} />}

          {activeModule === 'SYSTEM_DATA' && (
            <SystemDataView state={state} onChangeRole={handleChangeRole} />
          )}
        </main>
      </div>

      {/* Modal Dialogs */}
      <AssetDetailModal
        assetId={detailAssetId}
        state={state}
        onClose={() => setDetailAssetId(null)}
        onReassignTruck={handleManualReassignTruck}
      />

      <TimeMachineModal
        isOpen={isTimeMachineOpen}
        onClose={() => setIsTimeMachineOpen(false)}
        state={state}
      />

      <HumanInTheLoopModal
        isOpen={isRecommendationsOpen}
        onClose={() => setIsRecommendationsOpen(false)}
        state={state}
        onApprove={handleApproveRecommendation}
        onReject={handleRejectRecommendation}
      />

      <AlertsModal
        isOpen={isAlertsOpen}
        onClose={() => setIsAlertsOpen(false)}
        state={state}
        onAcknowledgeAlert={handleAcknowledgeAlert}
      />
    </div>
  );
}

export default App;
