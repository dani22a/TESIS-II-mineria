/**
 * MineTwin AI - operational copilot (Mine-to-Mill).
 * Two engines: LangGraph (in-browser supervisor) and Langflow (visual flow served by Docker).
 */

import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Bot,
  CheckCircle,
  Cpu,
  ExternalLink,
  Loader2,
  MessageSquare,
  Send,
  Sparkles,
  Wrench,
  Workflow,
  XCircle,
} from 'lucide-react';
import { DigitalTwinState, DRLRecommendation, UserRole } from '../../types/mining';
import { roleLabel, copilotAgentLabel } from '../../i18n/labels';
import { getGeminiApiKey } from '../../services/copilot/gemini';
import { invokeCopilotTurn, resumeCopilotTurn } from '../../services/copilot/session';
import {
  buildHitlNotice,
  checkLangflowHealth,
  invokeLangflowTurn,
  LANGFLOW_AGENT_ID,
  LangflowHealth,
} from '../../services/langflow/langflowClient';
import { ToolTrace } from '../../services/copilot/tools';

interface CopilotViewProps {
  state: DigitalTwinState;
  onProposeRecommendation: (rec: DRLRecommendation) => void;
  onApproveRecommendation: (id: string) => void;
  onRejectRecommendation: (id: string) => void;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  route?: string;
  traces?: ToolTrace[];
  pending?: DRLRecommendation | null;
  interrupted?: boolean;
}

const DEMO_PROMPT_GROUPS: { title: string; prompts: string[] }[] = [
  {
    title: 'Preguntar cómo está la mina (solo consulta)',
    prompts: [
      '¿Cuántos camiones están esperando en cada pala ahora?',
      '¿Cómo está la cola en la pala EX-02?',
      '¿La planta (molino SAG) está trabada por algo?',
      '¿El mineral que sale de la tronadura está muy grueso?',
    ],
  },
  {
    title: 'Qué pasaría si… (escenario, no cambia la mina)',
    prompts: [
      'Si se rompe la pala EX-01 y además llueve, ¿cuánto baja la producción?',
      '¿Qué pasa si sumo 3 camiones y cierran la rampa principal?',
      'Si la pista se pone con barro, ¿se atrasan los ciclos de acarreo?',
      'Si subo un poco la energía de tronadura, ¿el molino muele más fácil?',
    ],
  },
  {
    title: 'Pedir una acción (se pausa y tú apruebas)',
    prompts: [
      'Hay cola en una pala: propón mover camiones a la otra.',
      'Propón mandar mineral de mejor ley directo al chancador.',
      'Propón subir un poco el explosivo de la malla para romper mejor la roca.',
    ],
  },
  {
    title: 'Explicar la IA (auditoría)',
    prompts: [
      'Explícame en palabras simples por qué la IA quiere reasignar camiones.',
      'Resume la recomendación REC-DRL-001 como si fuera una auditoría.',
    ],
  },
];

type CopilotEngine = 'langgraph' | 'langflow';

const LANGFLOW_PROMPT_GROUP = {
  title: 'Solo Langflow · bitácora, procedimientos e informe de turno',
  prompts: [
    '¿Qué dice el procedimiento cuando una pala tiene mucha cola?',
    'Registra en la bitácora que empezó a llover en la rampa principal.',
    'Genera el informe de turno.',
  ],
};

const ROLE_PROMPTS: Record<UserRole, string[]> = {
  OPERATOR: [
    'Muéstrame qué camiones están parados en cola y a qué pala van.',
    'Propón un rebalanceo de flota ahora.',
  ],
  MINE_ENGINEER: [
    'Si EX-01 queda fuera de servicio 2 horas y llueve, ¿cuál es el impacto?',
    'Compara producción si cierro la rampa versus si dejo todo igual.',
  ],
  DRILL_BLAST_ENGINEER: [
    'Si subo el factor de carga 8%, ¿sale la roca más chica y el molino gasta menos energía?',
    'Propón un ajuste de factor de carga usando Kuz-Ram.',
  ],
  METALLURGIST: [
    'La tolva del chancador está baja. ¿Conviene priorizar mineral skarn a planta?',
    '¿Cuál es el cuello de botella del molino SAG ahora?',
  ],
  DATA_SCIENTIST: [
    'Explícame la recomendación REC-DRL-001 como auditoría.',
    '¿Qué tan bien puntúa hoy la política de despacho de la IA frente a una cola mínima?',
  ],
};

export const CopilotView: React.FC<CopilotViewProps> = ({
  state,
  onProposeRecommendation,
  onApproveRecommendation,
  onRejectRecommendation,
}) => {
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [engine, setEngine] = useState<CopilotEngine>('langgraph');
  const [langflowHealth, setLangflowHealth] = useState<LangflowHealth | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content:
        'Copiloto listo. Consulto el gemelo y los motores Kuz-Ram, de escenarios y DRL. Las acciones de escritura se pausan para aprobación humana.',
    },
  ]);
  const threadRef = useRef(`thread-${Date.now()}`);
  const pendingThreadRef = useRef<string | null>(null);
  // Langflow keeps chat memory per session, so one session spans the whole conversation.
  const langflowSessionRef = useRef(`minetwin-${Date.now()}`);
  const geminiOn = Boolean(getGeminiApiKey());
  const prompts = useMemo(() => ROLE_PROMPTS[state.currentUserRole], [state.currentUserRole]);
  const promptGroups = engine === 'langflow' ? [...DEMO_PROMPT_GROUPS, LANGFLOW_PROMPT_GROUP] : DEMO_PROMPT_GROUPS;

  useEffect(() => {
    if (engine !== 'langflow') return;
    let cancelled = false;
    setLangflowHealth(null);
    void checkLangflowHealth().then((health) => {
      if (!cancelled) setLangflowHealth(health);
    });
    return () => {
      cancelled = true;
    };
  }, [engine]);

  const runTurn = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || busy) return;
    setBusy(true);
    setInput('');
    threadRef.current = `thread-${Date.now()}`;
    const userMsg: ChatMessage = { id: `u-${Date.now()}`, role: 'user', content: trimmed };
    setMessages((prev) => [...prev, userMsg]);

    try {
      const result =
        engine === 'langflow'
          ? await invokeLangflowTurn(state, trimmed, langflowSessionRef.current)
          : await invokeCopilotTurn(state, trimmed, threadRef.current);
      if (result.pending) {
        pendingThreadRef.current = result.threadId;
        onProposeRecommendation(result.pending);
      }
      setMessages((prev) => [
        ...prev,
        {
          id: `a-${Date.now()}`,
          role: 'assistant',
          content: result.reply,
          route: result.route,
          traces: result.traces,
          pending: result.pending,
          interrupted: result.interrupted,
        },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          id: `e-${Date.now()}`,
          role: 'assistant',
          content: `No se pudo ejecutar ${engine === 'langflow' ? 'el flujo de Langflow' : 'el grafo'}: ${
            error instanceof Error ? error.message : 'error desconocido'
          }`,
        },
      ]);
    } finally {
      setBusy(false);
    }
  };

  const markResolved = (rec: DRLRecommendation) =>
    setMessages((prev) => prev.map((m) => (m.pending?.id === rec.id ? { ...m, interrupted: false, pending: rec } : m)));

  const handleLangflowHitl = async (rec: DRLRecommendation, action: 'approve' | 'reject') => {
    // Langflow does not pause: the decision is applied here and then reported back so the agent logs it.
    markResolved(rec);
    setBusy(true);
    const outcome =
      action === 'approve' ? 'Acción aprobada y aplicada en el gemelo.' : 'Acción rechazada; el gemelo no se modificó.';
    try {
      const logged = await invokeLangflowTurn(state, buildHitlNotice(rec, action), langflowSessionRef.current);
      setMessages((prev) => [
        ...prev,
        {
          id: `r-${Date.now()}`,
          role: 'assistant',
          content: `${outcome}\n${logged.reply}`,
          route: logged.route,
          traces: logged.traces,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `r-${Date.now()}`,
          role: 'assistant',
          content: `${outcome} No se pudo registrar la decisión en la bitácora de Langflow.`,
        },
      ]);
    } finally {
      setBusy(false);
    }
  };

  const handleHitl = async (rec: DRLRecommendation, action: 'approve' | 'reject', route?: string) => {
    if (action === 'approve') onApproveRecommendation(rec.id);
    else onRejectRecommendation(rec.id);

    if (route === LANGFLOW_AGENT_ID) {
      await handleLangflowHitl(rec, action);
      return;
    }

    const threadId = pendingThreadRef.current;
    setBusy(true);
    try {
      if (threadId) {
        const resumed = await resumeCopilotTurn(state, threadId, action);
        setMessages((prev) => [
          ...prev.map((m) =>
            m.pending?.id === rec.id ? { ...m, interrupted: false, pending: rec } : m
          ),
          {
            id: `r-${Date.now()}`,
            role: 'assistant',
            content: resumed.reply,
            route: resumed.route,
            traces: resumed.traces,
          },
        ]);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `r-${Date.now()}`,
          role: 'assistant',
          content:
            action === 'approve'
              ? 'Acción aprobada en el gemelo. El grafo no pudo reanudarse; la mutación sí se aplicó.'
              : 'Acción rechazada. El gemelo no se modificó.',
        },
      ]);
    } finally {
      pendingThreadRef.current = null;
      setBusy(false);
    }
  };

  return (
    <div className="w-full h-full flex flex-col p-4 gap-4 overflow-hidden bg-slate-950 text-slate-100">
      <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-xl shadow-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-gradient-to-br from-amber-500 to-amber-600 text-slate-950 rounded-xl shadow-lg shadow-amber-500/20">
            <MessageSquare className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white tracking-tight">
              Copiloto operacional de mina a planta
            </h2>
            <p className="text-xs text-slate-400">
              {engine === 'langflow'
                ? 'Flujo visual de Langflow con herramientas conectadas al gemelo, procedimientos y bitácora de turno. Requiere aprobación humana antes de cambiar el gemelo.'
                : 'Supervisor con herramientas deterministas (Kuz-Ram, escenarios, DRL). Requiere aprobación humana antes de cambiar el gemelo.'}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex rounded-lg border border-slate-700 overflow-hidden text-xs font-mono font-bold">
            <button
              type="button"
              disabled={busy}
              onClick={() => setEngine('langgraph')}
              className={`px-3 py-1 flex items-center gap-1.5 transition ${
                engine === 'langgraph' ? 'bg-amber-500 text-slate-950' : 'bg-slate-900 text-slate-400 hover:text-slate-200'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" /> LangGraph
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => setEngine('langflow')}
              className={`px-3 py-1 flex items-center gap-1.5 transition ${
                engine === 'langflow' ? 'bg-sky-500 text-slate-950' : 'bg-slate-900 text-slate-400 hover:text-slate-200'
              }`}
            >
              <Workflow className="w-3.5 h-3.5" /> Langflow
            </button>
          </div>
          {engine === 'langflow' ? (
            <>
              <span
                className={`px-3 py-1 rounded-lg text-xs font-mono font-bold border ${
                  langflowHealth?.ok
                    ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300'
                    : langflowHealth
                      ? 'bg-rose-500/10 border-rose-500/40 text-rose-300'
                      : 'bg-slate-800 border-slate-700 text-slate-400'
                }`}
              >
                {langflowHealth?.ok ? 'Langflow conectado' : langflowHealth ? 'Langflow no disponible' : 'Verificando Langflow...'}
              </span>
              {langflowHealth?.url && (
                <a
                  href={langflowHealth.url}
                  target="_blank"
                  rel="noreferrer"
                  className="px-3 py-1 rounded-lg text-xs font-mono font-bold border border-sky-500/40 text-sky-300 hover:bg-sky-500/10 flex items-center gap-1.5"
                >
                  Abrir editor <ExternalLink className="w-3.5 h-3.5" />
                </a>
              )}
            </>
          ) : (
            <span
              className={`px-3 py-1 rounded-lg text-xs font-mono font-bold border ${
                geminiOn
                  ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300'
                  : 'bg-slate-800 border-slate-700 text-slate-400'
              }`}
            >
              {geminiOn ? 'Gemini activo' : 'Gemini inactivo · herramientas locales'}
            </span>
          )}
        </div>
      </div>

      <div className="space-y-2 max-h-44 overflow-y-auto pr-1">
        <p className="text-[11px] text-slate-400">
          No estás limitado a estos atajos: puedes escribir cualquier pregunta en el recuadro. Estos son ejemplos para la demostración.
        </p>
        {promptGroups.map((group) => (
          <div key={group.title} className="space-y-1.5">
            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">{group.title}</div>
            <div className="flex flex-wrap gap-2">
              {group.prompts.map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => runTurn(p)}
                  disabled={busy}
                  className="text-[11px] px-2.5 py-1.5 rounded-lg border border-slate-800 bg-slate-900/80 text-slate-300 hover:border-amber-500/40 hover:text-amber-200 transition disabled:opacity-50 text-left"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        ))}
        <div className="space-y-1.5">
          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
            Según el rol actual · {roleLabel(state.currentUserRole)}
          </div>
          <div className="flex flex-wrap gap-2">
            {prompts.map((p) => (
              <button
                key={`role-${p}`}
                type="button"
                onClick={() => runTurn(p)}
                disabled={busy}
                className="text-[11px] px-2.5 py-1.5 rounded-lg border border-amber-500/20 bg-amber-500/5 text-amber-100/90 hover:border-amber-500/40 transition disabled:opacity-50 text-left"
              >
                {p}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="flex-1 min-h-0 grid grid-cols-1 xl:grid-cols-12 gap-4">
        <div className="xl:col-span-7 bg-slate-900/90 border border-slate-800 rounded-xl flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.map((m) => (
              <div
                key={m.id}
                className={`rounded-xl border p-3 text-xs space-y-2 ${
                  m.role === 'user'
                    ? 'bg-slate-950 border-slate-800 ml-8'
                    : 'bg-slate-950/70 border-amber-500/20 mr-4'
                }`}
              >
                <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-slate-500 font-bold">
                  {m.role === 'user' ? (
                    <span>Consulta · {roleLabel(state.currentUserRole)}</span>
                  ) : (
                    <span className="flex items-center gap-1">
                      <Bot className="w-3 h-3 text-amber-400" /> Copiloto
                      {m.route && (
                        <span className="font-mono text-amber-300/80 normal-case">
                          {copilotAgentLabel(m.route)}
                        </span>
                      )}
                    </span>
                  )}
                </div>
                <p className="text-slate-200 whitespace-pre-wrap leading-relaxed">{m.content}</p>
                {m.pending && m.interrupted && (
                  <div className="bg-amber-500/10 border border-amber-500/40 rounded-lg p-2.5 space-y-2">
                    <div className="font-bold text-amber-200">{m.pending.title}</div>
                    <p className="text-slate-300">{m.pending.what}</p>
                    <p className="text-slate-400">{m.pending.why}</p>
                    <div className="flex justify-end gap-2">
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => handleHitl(m.pending!, 'reject', m.route)}
                        className="px-3 py-1.5 bg-slate-800 text-slate-300 rounded-lg text-[11px] flex items-center gap-1"
                      >
                        <XCircle className="w-3.5 h-3.5 text-rose-400" /> Rechazar
                      </button>
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => handleHitl(m.pending!, 'approve', m.route)}
                        className="px-3 py-1.5 bg-amber-500 text-slate-950 font-bold rounded-lg text-[11px] flex items-center gap-1"
                      >
                        <CheckCircle className="w-3.5 h-3.5" /> Aprobar y despachar
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
            {busy && (
              <div className="flex items-center gap-2 text-xs text-amber-300">
                <Loader2 className="w-4 h-4 animate-spin" />{' '}
                {engine === 'langflow' ? 'Ejecutando el flujo de Langflow...' : 'Ejecutando el grafo del copiloto...'}
              </div>
            )}
          </div>

          <form
            className="border-t border-slate-800 p-3 flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              void runTurn(input);
            }}
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Escribe con tus palabras: colas, lluvia, pala caída, roca gruesa, molino, o pide una acción para aprobar..."
              className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-100 outline-none focus:border-amber-500/50"
            />
            <button
              type="submit"
              disabled={busy || !input.trim()}
              className="px-3 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded-xl disabled:opacity-40"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>

        <div className="xl:col-span-5 bg-slate-900/90 border border-slate-800 rounded-xl p-4 overflow-y-auto space-y-3">
          <h3 className="font-bold text-slate-200 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
            <Wrench className="w-4 h-4 text-sky-400" /> Línea de tiempo de herramientas
          </h3>
          {messages
            .filter((m) => m.traces && m.traces.length > 0)
            .slice(-3)
            .map((m) => (
              <div key={`t-${m.id}`} className="space-y-2">
                {m.traces!.map((tr, idx) => (
                  <div key={`${m.id}-${idx}`} className="bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-[11px]">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-amber-300">{tr.tool}</span>
                      <span className="text-slate-500">{tr.agent}</span>
                    </div>
                    <div className="text-sky-300/80 mt-1 flex items-center gap-1">
                      <Cpu className="w-3 h-3" /> {tr.citation}
                    </div>
                    <pre className="mt-2 text-[10px] text-slate-400 overflow-x-auto whitespace-pre-wrap">
                      {JSON.stringify(tr.result, null, 2)}
                    </pre>
                  </div>
                ))}
              </div>
            ))}
          {messages.every((m) => !m.traces?.length) && (
            <p className="text-xs text-slate-500">
              Las cifras aparecerán aquí cuando el supervisor llame a una herramienta. El modelo no las inventa.
            </p>
          )}
        </div>
      </div>
    </div>
  );
};
