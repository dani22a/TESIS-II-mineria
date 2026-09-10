/**
 * LangGraph supervisor graph for the MineTwin operational copilot.
 * Specialist nodes call deterministic engines; write actions pause via interrupt().
 */

import {
  Annotation,
  Command,
  END,
  interrupt,
  MemorySaver,
  START,
  StateGraph,
} from '@langchain/langgraph/web';
import { DRLRecommendation, DigitalTwinState, UserRole } from '../../types/mining';
import { generateGeminiText } from './gemini';
import {
  CopilotAgentId,
  explainDrlRecommendation,
  formatDeterministicReply,
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

const CopilotAnnotation = Annotation.Root({
  userMessage: Annotation<string>,
  userRole: Annotation<UserRole>,
  route: Annotation<CopilotAgentId>,
  shouldWrite: Annotation<boolean>,
  assistantReply: Annotation<string>,
  toolTraces: Annotation<ToolTrace[]>({
    reducer: (_left, right) => right,
    default: () => [],
  }),
  pendingAction: Annotation<DRLRecommendation | null>({
    reducer: (_left, right) => right,
    default: () => null,
  }),
  hitlDecision: Annotation<'approve' | 'reject' | null>({
    reducer: (_left, right) => right,
    default: () => null,
  }),
});

export type CopilotGraphState = typeof CopilotAnnotation.State;

let liveTwin: DigitalTwinState | null = null;

export function bindTwin(state: DigitalTwinState) {
  liveTwin = state;
}

function requireTwin(): DigitalTwinState {
  if (!liveTwin) {
    throw new Error('El gemelo no está vinculado al grafo del copiloto.');
  }
  return liveTwin;
}

function parseRoute(text: string | null): CopilotAgentId | null {
  if (!text) return null;
  const t = text.toLowerCase();
  if (t.includes('scenario')) return 'scenario_agent';
  if (t.includes('blast')) return 'blast_agent';
  if (t.includes('mill')) return 'mill_agent';
  if (t.includes('xai')) return 'xai_agent';
  if (t.includes('dispatch')) return 'dispatch_agent';
  return null;
}

async function supervisorNode(state: CopilotGraphState) {
  const twin = requireTwin();
  const heuristic = heuristicRoute(state.userMessage, twin.currentUserRole);
  const llmRoute = await generateGeminiText(
    `Clasifica la consulta operacional en UN id: dispatch_agent, blast_agent, mill_agent, scenario_agent, xai_agent.\n` +
      `Rol: ${twin.currentUserRole}\nConsulta: ${state.userMessage}\nResponde solo el id.`
  );
  const route = parseRoute(llmRoute) ?? heuristic;
  return {
    route,
    shouldWrite: wantsWriteAction(state.userMessage, route),
    pendingAction: null,
    hitlDecision: null,
    toolTraces: [] as ToolTrace[],
    assistantReply: '',
  };
}

function dispatchNode(state: CopilotGraphState) {
  const twin = requireTwin();
  const traces: ToolTrace[] = [
    {
      tool: 'query_twin_state',
      agent: 'dispatch_agent',
      citation: 'simulationEngine / DigitalTwinState',
      result: queryTwinState(twin),
    },
  ];
  const pending = state.shouldWrite ? proposeDispatchRebalance(twin) : null;
  return {
    toolTraces: traces,
    pendingAction: pending,
    assistantReply: formatDeterministicReply('dispatch_agent', traces, pending),
  };
}

function blastNode(state: CopilotGraphState) {
  const twin = requireTwin();
  const current = runKuzRamFromState(twin);
  const plusEight = runKuzRamFromState(twin, Math.round((twin.blastPatterns[0].powderFactor * 1.08) * 100) / 100);
  const traces: ToolTrace[] = [
    {
      tool: 'run_kuz_ram',
      agent: 'blast_agent',
      citation: 'kuzRamModel.calculateKuzRamFragmentation',
      result: { actual: current, powderFactorMas8pct: plusEight },
    },
  ];
  const pending = state.shouldWrite ? proposePowderFactorAdjust(twin) : null;
  return {
    toolTraces: traces,
    pendingAction: pending,
    assistantReply: formatDeterministicReply('blast_agent', traces, pending),
  };
}

function millNode(state: CopilotGraphState) {
  const twin = requireTwin();
  const traces: ToolTrace[] = [
    {
      tool: 'query_twin_state',
      agent: 'mill_agent',
      citation: 'DigitalTwinState.crusher / mill',
      result: queryTwinState(twin),
    },
    {
      tool: 'evaluate_mine_to_mill',
      agent: 'mill_agent',
      citation: 'kuzRamModel.evaluateMineToMillImpact',
      result: runKuzRamFromState(twin),
    },
  ];
  const pending = state.shouldWrite ? proposeCrusherFeed(twin) : null;
  return {
    toolTraces: traces,
    pendingAction: pending,
    assistantReply: formatDeterministicReply('mill_agent', traces, pending),
  };
}

function scenarioNode(state: CopilotGraphState) {
  const twin = requireTwin();
  const traces: ToolTrace[] = [
    {
      tool: 'run_what_if_scenario',
      agent: 'scenario_agent',
      citation: 'scenarioEngine.runWhatIfSimulation',
      result: runWhatIfFromMessage(twin, state.userMessage),
    },
  ];
  return {
    toolTraces: traces,
    pendingAction: null,
    assistantReply: formatDeterministicReply('scenario_agent', traces, null),
  };
}

function xaiNode(state: CopilotGraphState) {
  const twin = requireTwin();
  const recId = state.userMessage.match(/REC-[A-Z0-9-]+/i)?.[0];
  const traces: ToolTrace[] = [
    {
      tool: 'explain_drl_recommendation',
      agent: 'xai_agent',
      citation: 'drlEngine + DRLRecommendation',
      result: explainDrlRecommendation(twin, recId),
    },
  ];
  return {
    toolTraces: traces,
    pendingAction: null,
    assistantReply: formatDeterministicReply('xai_agent', traces, null),
  };
}

function hitlNode(state: CopilotGraphState) {
  if (!state.pendingAction) {
    return { hitlDecision: null as 'approve' | 'reject' | null };
  }
  const decision = interrupt({
    action: 'human_approval',
    pending: state.pendingAction,
    traces: state.toolTraces,
    draft: state.assistantReply,
  }) as { action?: 'approve' | 'reject' };
  const hitlDecision: 'approve' | 'reject' = decision?.action === 'reject' ? 'reject' : 'approve';
  return { hitlDecision };
}

async function synthesizeNode(state: CopilotGraphState) {
  const twin = requireTwin();
  const decisionNote =
    state.hitlDecision === 'approve'
      ? 'El operador APROBÓ la acción. Confirma ejecución en el gemelo.'
      : state.hitlDecision === 'reject'
        ? 'El operador RECHAZÓ la acción. No mutar el gemelo.'
        : '';
  const llm = await generateGeminiText(
    `Eres el Copiloto Operacional Mine-to-Mill de MineTwin AI.\n` +
      `Regla: no inventes cifras; usa solo el JSON de tools.\n` +
      `Rol del usuario: ${twin.currentUserRole}\n` +
      `Consulta: ${state.userMessage}\n` +
      `Agente: ${state.route}\n` +
      `${decisionNote}\n` +
      `Tools JSON:\n${JSON.stringify(state.toolTraces)}\n` +
      `Pendiente HITL: ${state.pendingAction ? state.pendingAction.what : 'ninguna'}\n` +
      `Responde en español latino neutro, breve, con viñetas y cita la tool de cada número.`
  );
  return {
    assistantReply: llm || state.assistantReply,
  };
}

function routeAfterSupervisor(state: CopilotGraphState): CopilotAgentId {
  return state.route;
}

const checkpointer = new MemorySaver();

export const copilotGraph = new StateGraph(CopilotAnnotation)
  .addNode('supervisor', supervisorNode)
  .addNode('dispatch_agent', dispatchNode)
  .addNode('blast_agent', blastNode)
  .addNode('mill_agent', millNode)
  .addNode('scenario_agent', scenarioNode)
  .addNode('xai_agent', xaiNode)
  .addNode('hitl', hitlNode)
  .addNode('synthesize', synthesizeNode)
  .addEdge(START, 'supervisor')
  .addConditionalEdges('supervisor', routeAfterSupervisor, [
    'dispatch_agent',
    'blast_agent',
    'mill_agent',
    'scenario_agent',
    'xai_agent',
  ])
  .addEdge('dispatch_agent', 'hitl')
  .addEdge('blast_agent', 'hitl')
  .addEdge('mill_agent', 'hitl')
  .addEdge('scenario_agent', 'hitl')
  .addEdge('xai_agent', 'hitl')
  .addEdge('hitl', 'synthesize')
  .addEdge('synthesize', END)
  .compile({ checkpointer });

export { Command };
