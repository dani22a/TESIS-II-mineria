/**
 * Server-side bridge between Langflow and the MineTwin digital twin.
 * Runs inside the Vite dev server:
 *  - /api/langflow/run    browser -> Langflow (stores the twin snapshot for the session)
 *  - /api/langflow/health browser -> Langflow availability
 *  - /api/twin/tools/*    Langflow custom components -> deterministic TS engines
 * Langflow never duplicates the physics: its tools call back into the same
 * Kuz-Ram / Scenario Lab / DRL code the UI uses. Write actions only become
 * proposals; the human approves them in the MineTwin UI (HITL).
 */

import type { IncomingMessage, ServerResponse } from 'http';
import { DigitalTwinState, DRLRecommendation } from '../../types/mining';
import {
  explainDrlRecommendation,
  proposeCrusherFeed,
  proposeDispatchRebalance,
  proposePowderFactorAdjust,
  queryTwinState,
  runKuzRamFromState,
  ToolTrace,
} from '../copilot/tools';
import { parseScenarioFromText, runWhatIfSimulation, ScenarioLabInputs } from '../scenarioEngine';

export interface LangflowBridgeConfig {
  langflowUrl: string;
  flowId: string;
  apiKey: string;
}

interface SessionContext {
  state: DigitalTwinState;
  traces: ToolTrace[];
  proposals: DRLRecommendation[];
  updatedAt: number;
}

const SESSION_TTL_MS = 60 * 60 * 1000;
const LANGFLOW_TIMEOUT_MS = 180_000;
const AGENT_ID = 'langflow_agent';

const sessions = new Map<string, SessionContext>();
let lastSessionId: string | null = null;

export function readJsonBody(req: IncomingMessage): Promise<Record<string, unknown>> {
  return new Promise((resolve, reject) => {
    const chunks: Uint8Array[] = [];
    req.on('data', (chunk) => chunks.push(chunk as Uint8Array));
    req.on('end', () => {
      try {
        const raw = Buffer.concat(chunks).toString('utf8');
        resolve(raw ? (JSON.parse(raw) as Record<string, unknown>) : {});
      } catch (error) {
        reject(error);
      }
    });
    req.on('error', reject);
  });
}

function sendJson(res: ServerResponse, status: number, body: unknown) {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json');
  res.end(JSON.stringify(body));
}

function str(value: unknown): string {
  return typeof value === 'string' ? value.trim() : value == null ? '' : String(value).trim();
}

function pruneSessions() {
  const now = Date.now();
  for (const [id, ctx] of sessions) {
    if (now - ctx.updatedAt > SESSION_TTL_MS) sessions.delete(id);
  }
}

function resolveSession(sessionId: string): SessionContext | null {
  return sessions.get(sessionId) ?? (lastSessionId ? sessions.get(lastSessionId) ?? null : null);
}

// ---------------------------------------------------------------------------
// Tools invocadas por los componentes custom de Langflow
// ---------------------------------------------------------------------------

function parsePowderFactor(raw: string, current: number): number | undefined {
  if (!raw) return undefined;
  const value = parseFloat(raw.replace(',', '.').replace(/[^\d.+-]/g, ''));
  if (Number.isNaN(value)) return undefined;
  // Un porcentaje explícito o un valor mayor a 3 (ningún factor de carga real supera 3 kg/m3) es relativo.
  if (raw.includes('%') || Math.abs(value) > 3) {
    return Math.round(current * (1 + value / 100) * 100) / 100;
  }
  return value;
}

function buildScenarioInputs(state: DigitalTwinState, args: Record<string, unknown>): ScenarioLabInputs {
  const inputs = parseScenarioFromText(str(args.description), state);

  const outage = str(args.shovel_outage).toUpperCase();
  if (/^EX-0[12]$/.test(outage) || outage === 'NONE') inputs.shovelOutage = outage;

  const weather = str(args.weather).toLowerCase();
  if (/rain|lluv/.test(weather)) inputs.weather = 'RAIN';
  else if (/mud|barro|lodo/.test(weather)) inputs.weather = 'MUD';
  else if (/clear|despej/.test(weather)) inputs.weather = 'CLEAR';

  const trucks = parseInt(str(args.trucks_delta), 10);
  if (!Number.isNaN(trucks)) inputs.trucksDelta = trucks;

  const road = str(args.road_blocked).toLowerCase();
  if (/^(si|sí|yes|true|1)$/.test(road)) inputs.roadBlocked = 'RD-RAMP-BENCH-3840-CRUSHER';
  else if (/^(no|false|0)$/.test(road)) inputs.roadBlocked = 'NONE';

  const pf = parseFloat(str(args.powder_factor_delta).replace('%', ''));
  if (!Number.isNaN(pf)) inputs.powderFactorDelta = pf;

  return inputs;
}

function asLangflowProposal(rec: DRLRecommendation): DRLRecommendation {
  return {
    ...rec,
    id: rec.id.replace('REC-LG-', 'REC-LF-'),
    source: 'LANGFLOW_COPILOT',
    why: rec.why.replace('El supervisor LangGraph', 'El agente Langflow'),
    auditTrail: [
      {
        action: 'GENERATED_BY_LANGFLOW_COPILOT',
        timestamp: rec.timestamp,
        user: 'MineTwin Langflow Agent',
      },
    ],
  };
}

interface ToolOutcome {
  citation: string;
  result: unknown;
}

function runTool(name: string, ctx: SessionContext, args: Record<string, unknown>): ToolOutcome | null {
  const state = ctx.state;
  switch (name) {
    case 'query_twin_state':
      return { citation: 'simulationEngine / DigitalTwinState', result: queryTwinState(state) };

    case 'run_kuz_ram': {
      const current = state.blastPatterns[0].powderFactor;
      const override = parsePowderFactor(str(args.powder_factor), current);
      const actual = runKuzRamFromState(state);
      const result =
        override != null && override !== current
          ? { actual, propuesto: runKuzRamFromState(state, override) }
          : { actual };
      return { citation: 'kuzRamModel.calculateKuzRamFragmentation + evaluateMineToMillImpact', result };
    }

    case 'run_what_if_scenario': {
      const inputs = buildScenarioInputs(state, args);
      return {
        citation: 'scenarioEngine.runWhatIfSimulation',
        result: { inputs, result: runWhatIfSimulation(state, inputs) },
      };
    }

    case 'explain_drl_recommendation':
      return {
        citation: 'drlEngine + DRLRecommendation',
        result: explainDrlRecommendation(state, str(args.rec_id) || undefined),
      };

    case 'propose_action': {
      const kind = str(args.kind).toLowerCase();
      const base =
        /blast|tronad|powder|factor/.test(kind)
          ? proposePowderFactorAdjust(state)
          : /crusher|chanc|planta|mill/.test(kind)
            ? proposeCrusherFeed(state)
            : proposeDispatchRebalance(state);
      const proposal = asLangflowProposal(base);
      ctx.proposals.push(proposal);
      return {
        citation: 'copilot/tools.propose* (pendiente de aprobación humana)',
        result: {
          estado: 'PENDIENTE_APROBACION_HUMANA',
          nota: 'La acción NO se ejecutó. El operador debe aprobarla o rechazarla en MineTwin.',
          id: proposal.id,
          titulo: proposal.title,
          que: proposal.what,
          porque: proposal.why,
          impactoEsperado: proposal.expectedImpact,
          restricciones: proposal.constraintsEvaluated,
        },
      };
    }

    default:
      return null;
  }
}

async function handleToolCall(name: string, req: IncomingMessage, res: ServerResponse) {
  const args = await readJsonBody(req);
  const ctx = resolveSession(str(args.session_id));
  if (!ctx) {
    sendJson(res, 409, {
      error: 'No hay un gemelo activo. Abre MineTwin en el navegador y envía la consulta desde el Copiloto IA.',
    });
    return;
  }
  const outcome = runTool(name, ctx, args);
  if (!outcome) {
    sendJson(res, 404, { error: `Tool desconocida: ${name}` });
    return;
  }
  ctx.traces.push({ tool: name, agent: AGENT_ID, citation: outcome.citation, result: outcome.result });
  ctx.updatedAt = Date.now();
  sendJson(res, 200, { tool: name, fuente: outcome.citation, resultado: outcome.result });
}

/** Traces from Langflow tools that do not touch the twin (e.g. Postgres logbook writes). */
async function handleExternalTrace(req: IncomingMessage, res: ServerResponse) {
  const body = await readJsonBody(req);
  const ctx = resolveSession(str(body.session_id));
  if (ctx && str(body.tool)) {
    ctx.traces.push({ tool: str(body.tool), agent: AGENT_ID, citation: str(body.citation), result: body.result });
    ctx.updatedAt = Date.now();
  }
  sendJson(res, 200, { ok: Boolean(ctx) });
}

// ---------------------------------------------------------------------------
// Llamada a Langflow
// ---------------------------------------------------------------------------

async function langflowHeaders(config: LangflowBridgeConfig): Promise<Record<string, string>> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json', Accept: 'application/json' };
  if (config.apiKey) {
    headers['x-api-key'] = config.apiKey;
    return headers;
  }
  // Sin API key: se usa el auto-login local (LANGFLOW_AUTO_LOGIN=true en docker-compose).
  try {
    const login = await fetch(`${config.langflowUrl}/api/v1/auto_login`);
    if (login.ok) {
      const data = (await login.json()) as { access_token?: string };
      if (data.access_token) headers.Authorization = `Bearer ${data.access_token}`;
    }
  } catch {
    // Langflow caído: el error real se reporta en la llamada principal.
  }
  return headers;
}

function extractLangflowText(payload: unknown): string {
  const data = payload as {
    outputs?: {
      outputs?: {
        results?: { message?: { text?: string; data?: { text?: string } } };
        messages?: { message?: string }[];
        artifacts?: { message?: string };
      }[];
    }[];
  };
  const first = data.outputs?.[0]?.outputs?.[0];
  return (
    first?.results?.message?.text ??
    first?.results?.message?.data?.text ??
    first?.messages?.[0]?.message ??
    first?.artifacts?.message ??
    ''
  ).trim();
}

async function runLangflow(config: LangflowBridgeConfig, message: string, sessionId: string): Promise<string> {
  const headers = await langflowHeaders(config);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), LANGFLOW_TIMEOUT_MS);
  try {
    const response = await fetch(`${config.langflowUrl}/api/v1/run/${encodeURIComponent(config.flowId)}?stream=false`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        input_value: message,
        input_type: 'chat',
        output_type: 'chat',
        session_id: sessionId,
      }),
      signal: controller.signal,
    });
    const raw = await response.text();
    if (!response.ok) {
      throw new Error(`Langflow respondió ${response.status}: ${raw.slice(0, 400)}`);
    }
    return extractLangflowText(JSON.parse(raw));
  } finally {
    clearTimeout(timer);
  }
}

async function handleRun(config: LangflowBridgeConfig, req: IncomingMessage, res: ServerResponse) {
  const body = await readJsonBody(req);
  const message = str(body.message);
  const sessionId = str(body.sessionId);
  const state = body.state as DigitalTwinState | undefined;
  if (!message || !sessionId || !state?.shovels) {
    sendJson(res, 400, { error: 'Faltan message, sessionId o state' });
    return;
  }

  pruneSessions();
  const ctx: SessionContext = { state, traces: [], proposals: [], updatedAt: Date.now() };
  sessions.set(sessionId, ctx);
  lastSessionId = sessionId;

  try {
    const reply = await runLangflow(config, message, sessionId);
    sendJson(res, 200, {
      sessionId,
      reply: reply || 'Langflow no devolvió texto. Revisa el flujo en el editor de Langflow.',
      traces: ctx.traces,
      proposals: ctx.proposals,
    });
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    const hint = /429|Too Many Requests|spending cap|quota/i.test(detail)
      ? 'Gemini rechazó la llamada por cuota o tope de gasto (429). Revisa https://ai.studio/spend o usa otra GEMINI_API_KEY. '
      : '';
    sendJson(res, 502, {
      error: `${hint}No se pudo ejecutar el flujo de Langflow (${config.langflowUrl}, flujo "${config.flowId}"). ${detail}`,
      traces: ctx.traces,
      proposals: ctx.proposals,
    });
  }
}

async function handleHealth(config: LangflowBridgeConfig, res: ServerResponse) {
  const base = { url: config.langflowUrl, flowId: config.flowId };
  try {
    const health = await fetch(`${config.langflowUrl}/health_check`, { signal: AbortSignal.timeout(4000) });
    sendJson(res, 200, { ...base, ok: health.ok });
  } catch {
    sendJson(res, 200, { ...base, ok: false });
  }
}

export function createLangflowBridge(config: LangflowBridgeConfig) {
  return async (req: IncomingMessage, res: ServerResponse, next: () => void) => {
    const url = (req.url ?? '').split('?')[0];
    try {
      if (req.method === 'GET' && url === '/api/langflow/health') {
        await handleHealth(config, res);
        return;
      }
      if (req.method === 'POST' && url === '/api/langflow/run') {
        await handleRun(config, req, res);
        return;
      }
      if (req.method === 'POST' && url === '/api/twin/trace') {
        await handleExternalTrace(req, res);
        return;
      }
      const toolMatch = url.match(/^\/api\/twin\/tools\/([a-z_]+)$/);
      if (req.method === 'POST' && toolMatch) {
        await handleToolCall(toolMatch[1], req, res);
        return;
      }
    } catch (error) {
      sendJson(res, 500, { error: error instanceof Error ? error.message : 'Error interno del puente Langflow' });
      return;
    }
    next();
  };
}
