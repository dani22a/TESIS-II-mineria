/**
 * Copilot session: invoke / resume the LangGraph graph from the React UI.
 */

import { DigitalTwinState, DRLRecommendation } from '../../types/mining';
import { narrateCopilotReply } from './gemini';
import { bindTwin, Command, copilotGraph } from './graph';
import {
  CopilotAgentId,
  explainDrlRecommendation,
  heuristicRoute,
  proposeCrusherFeed,
  proposeDispatchRebalance,
  proposePowderFactorAdjust,
  queryTwinState,
  runKuzRamFromState,
  runWhatIfFromMessage,
  ToolTrace,
  wantsWriteAction,
} from './tools';

export interface CopilotTurnResult {
  threadId: string;
  reply: string;
  route: string;
  traces: ToolTrace[];
  pending: DRLRecommendation | null;
  interrupted: boolean;
}

function readInterrupt(result: Record<string, unknown>): {
  pending: DRLRecommendation | null;
  traces: ToolTrace[];
  draft: string;
} | null {
  const interrupts = (result as { __interrupt__?: { value?: unknown }[] }).__interrupt__;
  const payload = interrupts?.[0]?.value as
    | { pending?: DRLRecommendation; traces?: ToolTrace[]; draft?: string }
    | undefined;
  if (!payload) return null;
  return {
    pending: payload.pending ?? null,
    traces: payload.traces ?? [],
    draft: payload.draft ?? '',
  };
}

async function runDeterministicTurn(
  state: DigitalTwinState,
  userMessage: string,
  threadId: string
): Promise<CopilotTurnResult> {
  const route = heuristicRoute(userMessage, state.currentUserRole);
  const shouldWrite = wantsWriteAction(userMessage, route);
  let traces: ToolTrace[] = [];
  let pending: DRLRecommendation | null = null;

  if (route === 'dispatch_agent') {
    traces = [
      {
        tool: 'query_twin_state',
        agent: route,
        citation: 'simulationEngine / DigitalTwinState',
        result: queryTwinState(state),
      },
    ];
    pending = shouldWrite ? proposeDispatchRebalance(state) : null;
  } else if (route === 'blast_agent') {
    traces = [
      {
        tool: 'run_kuz_ram',
        agent: route,
        citation: 'kuzRamModel.calculateKuzRamFragmentation',
        result: runKuzRamFromState(state),
      },
    ];
    pending = shouldWrite ? proposePowderFactorAdjust(state) : null;
  } else if (route === 'mill_agent') {
    traces = [
      {
        tool: 'evaluate_mine_to_mill',
        agent: route,
        citation: 'kuzRamModel.evaluateMineToMillImpact',
        result: runKuzRamFromState(state),
      },
    ];
    pending = shouldWrite ? proposeCrusherFeed(state) : null;
  } else if (route === 'scenario_agent') {
    traces = [
      {
        tool: 'run_what_if_scenario',
        agent: route,
        citation: 'scenarioEngine.runWhatIfSimulation',
        result: runWhatIfFromMessage(state, userMessage),
      },
    ];
  } else {
    traces = [
      {
        tool: 'explain_drl_recommendation',
        agent: route,
        citation: 'drlEngine + DRLRecommendation',
        result: explainDrlRecommendation(state, userMessage.match(/REC-[A-Z0-9-]+/i)?.[0]),
      },
    ];
  }

  const reply = await narrateCopilotReply({
    userMessage,
    userRole: state.currentUserRole,
    route: route as CopilotAgentId,
    traces,
    pending,
  });

  return {
    threadId,
    route,
    traces,
    pending,
    interrupted: Boolean(pending),
    reply,
  };
}

export async function invokeCopilotTurn(
  state: DigitalTwinState,
  userMessage: string,
  threadId: string
): Promise<CopilotTurnResult> {
  try {
    bindTwin(state);
    const result = (await copilotGraph.invoke(
      {
        userMessage,
        userRole: state.currentUserRole,
        route: 'dispatch_agent',
        shouldWrite: false,
        assistantReply: '',
        toolTraces: [],
        pendingAction: null,
        hitlDecision: null,
      },
      { configurable: { thread_id: threadId } }
    )) as Record<string, unknown>;

    const interrupted = readInterrupt(result);
    if (interrupted) {
      return {
        threadId,
        reply: interrupted.draft || 'El grafo se pausó para aprobación humana (HITL).',
        route: String(result.route ?? 'dispatch_agent'),
        traces: interrupted.traces,
        pending: interrupted.pending,
        interrupted: true,
      };
    }

    return {
      threadId,
      reply: String(result.assistantReply ?? ''),
      route: String(result.route ?? 'dispatch_agent'),
      traces: (result.toolTraces as ToolTrace[]) ?? [],
      pending: (result.pendingAction as DRLRecommendation | null) ?? null,
      interrupted: false,
    };
  } catch {
    return runDeterministicTurn(state, userMessage, threadId);
  }
}

export async function resumeCopilotTurn(
  state: DigitalTwinState,
  threadId: string,
  action: 'approve' | 'reject'
): Promise<CopilotTurnResult> {
  try {
    bindTwin(state);
    const result = (await copilotGraph.invoke(new Command({ resume: { action } }), {
      configurable: { thread_id: threadId },
    })) as Record<string, unknown>;

    return {
      threadId,
      reply: String(
        result.assistantReply ?? (action === 'approve' ? 'Acción aprobada.' : 'Acción rechazada.')
      ),
      route: String(result.route ?? 'dispatch_agent'),
      traces: (result.toolTraces as ToolTrace[]) ?? [],
      pending: null,
      interrupted: false,
    };
  } catch {
    return {
      threadId,
      route: 'dispatch_agent',
      traces: [],
      pending: null,
      interrupted: false,
      reply:
        action === 'approve'
          ? 'Acción aprobada. El gemelo se actualizó con la recomendación del copiloto.'
          : 'Acción rechazada. No se mutó el gemelo.',
    };
  }
}
