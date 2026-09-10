/**
 * MineTwin AI - LangGraph operational copilot (Mine-to-Mill supervisor)
 */

import React, { useMemo, useRef, useState } from 'react';
import {
  Bot,
  CheckCircle,
  Cpu,
  Loader2,
  MessageSquare,
  Send,
  Sparkles,
  Wrench,
  XCircle,
} from 'lucide-react';
import { DigitalTwinState, DRLRecommendation, UserRole } from '../../types/mining';
import { getGeminiApiKey } from '../../services/copilot/gemini';
import { invokeCopilotTurn, resumeCopilotTurn } from '../../services/copilot/session';
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

const ROLE_PROMPTS: Record<UserRole, string[]> = {
  OPERATOR: [
    '¿Por qué EX-02 tiene cola y qué camiones reasigno?',
    'Propón un rebalanceo de flota ahora.',
  ],
  MINE_ENGINEER: [
    'Si EX-01 cae 2 horas y llueve, ¿cuál es el impacto?',
    'Escenario: +3 camiones y cierre de rampa.',
  ],
  DRILL_BLAST_ENGINEER: [
    'Si subo el powder factor 8%, ¿qué pasa con P80 y kWh/t del SAG?',
    'Propón un ajuste de powder factor con Kuz-Ram.',
  ],
  METALLURGIST: [
    'La tolva está baja. ¿Priorizo skarn a chancador?',
    '¿Cuál es el cuello de botella del molino SAG ahora?',
  ],
  DATA_SCIENTIST: [
    'Explícame la recomendación REC-DRL-001 como auditoría.',
    '¿Qué score de recompensa tiene la política MAPPO activa?',
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
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content:
        'Copiloto LangGraph listo. Consulto el gemelo y los motores Kuz-Ram / Scenario Lab / DRL. Las acciones de escritura se pausan para aprobación humana.',
    },
  ]);
  const threadRef = useRef(`thread-${Date.now()}`);
  const pendingThreadRef = useRef<string | null>(null);
  const geminiOn = Boolean(getGeminiApiKey());
  const prompts = useMemo(() => ROLE_PROMPTS[state.currentUserRole], [state.currentUserRole]);

  const runTurn = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || busy) return;
    setBusy(true);
    setInput('');
    threadRef.current = `thread-${Date.now()}`;
    const userMsg: ChatMessage = { id: `u-${Date.now()}`, role: 'user', content: trimmed };
    setMessages((prev) => [...prev, userMsg]);

    try {
      const result = await invokeCopilotTurn(state, trimmed, threadRef.current);
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
          content: `No se pudo ejecutar el grafo: ${error instanceof Error ? error.message : 'error desconocido'}`,
        },
      ]);
    } finally {
      setBusy(false);
    }
  };

  const handleHitl = async (rec: DRLRecommendation, action: 'approve' | 'reject') => {
    if (action === 'approve') onApproveRecommendation(rec.id);
    else onRejectRecommendation(rec.id);

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
              Copiloto Operacional Mine-to-Mill
            </h2>
            <p className="text-xs text-slate-400">
              Supervisor LangGraph + tools deterministas (Kuz-Ram, Scenario Lab, DRL). HITL antes de mutar el gemelo.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-3 py-1 bg-amber-500/10 border border-amber-500/40 text-amber-300 rounded-lg text-xs font-mono font-bold flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5" /> LangGraph
          </span>
          <span
            className={`px-3 py-1 rounded-lg text-xs font-mono font-bold border ${
              geminiOn
                ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300'
                : 'bg-slate-800 border-slate-700 text-slate-400'
            }`}
          >
            {geminiOn ? 'Gemini ON' : 'Gemini OFF · tools locales'}
          </span>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {prompts.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => runTurn(p)}
            disabled={busy}
            className="text-[11px] px-2.5 py-1.5 rounded-lg border border-slate-800 bg-slate-900/80 text-slate-300 hover:border-amber-500/40 hover:text-amber-200 transition disabled:opacity-50"
          >
            {p}
          </button>
        ))}
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
                    <span>Consulta · {state.currentUserRole}</span>
                  ) : (
                    <span className="flex items-center gap-1">
                      <Bot className="w-3 h-3 text-amber-400" /> Copiloto
                      {m.route && (
                        <span className="font-mono text-amber-300/80 normal-case">{m.route}</span>
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
                        onClick={() => handleHitl(m.pending!, 'reject')}
                        className="px-3 py-1.5 bg-slate-800 text-slate-300 rounded-lg text-[11px] flex items-center gap-1"
                      >
                        <XCircle className="w-3.5 h-3.5 text-rose-400" /> Rechazar
                      </button>
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => handleHitl(m.pending!, 'approve')}
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
                <Loader2 className="w-4 h-4 animate-spin" /> Ejecutando grafo LangGraph...
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
              placeholder="Pregunta al gemelo: colas, P80, what-if, recomendaciones DRL..."
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
            <Wrench className="w-4 h-4 text-sky-400" /> Timeline de tools (citas)
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
              Las cifras aparecerán aquí cuando el supervisor llame a una tool. El LLM no las inventa.
            </p>
          )}
        </div>
      </div>
    </div>
  );
};
