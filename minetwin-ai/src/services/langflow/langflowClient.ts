/**
 * Browser client for the Langflow copilot engine.
 * Sends the live twin state with each turn so Langflow tools compute on the
 * same numbers the operator sees (see bridgeServer.ts).
 */

import { DigitalTwinState, DRLRecommendation } from '../../types/mining';
import { ToolTrace } from '../copilot/tools';
import type { CopilotTurnResult } from '../copilot/session';

export const LANGFLOW_AGENT_ID = 'langflow_agent';

export interface LangflowHealth {
  ok: boolean;
  url: string;
  flowId: string;
}

interface LangflowRunResponse {
  sessionId?: string;
  reply?: string;
  traces?: ToolTrace[];
  proposals?: DRLRecommendation[];
  error?: string;
}

export async function checkLangflowHealth(): Promise<LangflowHealth> {
  try {
    const response = await fetch('/api/langflow/health');
    if (!response.ok) return { ok: false, url: '', flowId: '' };
    return (await response.json()) as LangflowHealth;
  } catch {
    return { ok: false, url: '', flowId: '' };
  }
}

export async function invokeLangflowTurn(
  state: DigitalTwinState,
  userMessage: string,
  sessionId: string
): Promise<CopilotTurnResult> {
  const response = await fetch('/api/langflow/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: userMessage, sessionId, state }),
  });
  const data = (await response.json()) as LangflowRunResponse;
  if (!response.ok) {
    throw new Error(data.error ?? `El puente Langflow respondió ${response.status}`);
  }

  const proposals = data.proposals ?? [];
  const pending = proposals.length > 0 ? proposals[proposals.length - 1] : null;
  return {
    threadId: data.sessionId ?? sessionId,
    reply: data.reply ?? '',
    route: LANGFLOW_AGENT_ID,
    traces: data.traces ?? [],
    pending,
    interrupted: Boolean(pending),
  };
}

export function buildHitlNotice(rec: DRLRecommendation, action: 'approve' | 'reject'): string {
  const decision = action === 'approve' ? 'APROBÓ' : 'RECHAZÓ';
  return (
    `[HITL] El operador ${decision} la propuesta ${rec.id} ("${rec.title}": ${rec.what}). ` +
    `Registra esta decisión en la bitácora con categoría DECISION_HITL y confírmalo en una sola línea.`
  );
}
