/**
 * Optional Gemini layer. The browser badge can be ON while the SDK call
 * fails (CORS / model). Prefer the Vite /api/gemini proxy, then the SDK.
 */

import { DRLRecommendation, UserRole } from '../../types/mining';
import { CopilotAgentId, formatDeterministicReply, ToolTrace } from './tools';

const GEMINI_MODELS = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-flash-latest'];

export function getGeminiApiKey(): string {
  const env = (import.meta as { env?: Record<string, string | undefined> }).env;
  return (
    env?.GEMINI_API_KEY ||
    env?.VITE_GEMINI_API_KEY ||
    (typeof process !== 'undefined' ? process.env?.GEMINI_API_KEY : undefined) ||
    ''
  );
}

function extractGeminiText(response: unknown): string | null {
  if (!response || typeof response !== 'object') return null;
  const r = response as {
    text?: string | (() => string | undefined);
    candidates?: { content?: { parts?: { text?: string }[] } }[];
  };
  const direct = typeof r.text === 'function' ? r.text() : r.text;
  if (typeof direct === 'string' && direct.trim()) return direct.trim();
  const parts = r.candidates?.[0]?.content?.parts ?? [];
  const joined = parts.map((p) => p.text ?? '').join('').trim();
  return joined || null;
}

async function callGeminiWithKey(apiKey: string, prompt: string): Promise<string | null> {
  const { GoogleGenAI } = await import('@google/genai');
  const ai = new GoogleGenAI({ apiKey });
  let lastError: unknown;
  for (const model of GEMINI_MODELS) {
    try {
      const response = await ai.models.generateContent({ model, contents: prompt });
      const text = extractGeminiText(response);
      if (text) return text;
    } catch (error) {
      lastError = error;
    }
  }
  if (lastError) {
    console.warn('[MineTwin Copilot] Gemini no respondió. Se usa el resumen local de las tools.', lastError);
  }
  return null;
}

export function buildNarrationPrompt(params: {
  userMessage: string;
  userRole: UserRole;
  route: string;
  traces: ToolTrace[];
  pending: DRLRecommendation | null;
  hitlNote?: string;
}): string {
  return (
    `Eres el copiloto operacional de mina a planta de MineTwin AI.\n` +
    `Regla estricta: no inventes cifras. Usa solo el JSON de tools.\n` +
    `Si el JSON no incluye lluvia o un dato pedido, dilo explícitamente.\n` +
    `Rol: ${params.userRole}\n` +
    `Consulta: ${params.userMessage}\n` +
    `Agente: ${params.route}\n` +
    `${params.hitlNote ?? ''}\n` +
    `Tools JSON:\n${JSON.stringify(params.traces)}\n` +
    `Pendiente HITL: ${params.pending ? params.pending.what : 'ninguna'}\n` +
    `Responde en español latino neutro, breve, con viñetas. ` +
    `No pegues JSON. Cita de dónde sale cada número (Kuz-Ram, laboratorio de escenarios, gemelo).`
  );
}

export async function generateGeminiText(prompt: string): Promise<string | null> {
  try {
    const proxied = await fetch('/api/gemini', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt }),
    });
    if (proxied.ok) {
      const data = (await proxied.json()) as { text?: string };
      if (data.text?.trim()) return data.text.trim();
    }
  } catch {
    // Sin proxy (preview estático): intentar SDK en el cliente.
  }

  const apiKey = getGeminiApiKey();
  if (!apiKey) return null;
  try {
    return await callGeminiWithKey(apiKey, prompt);
  } catch (error) {
    console.warn('[MineTwin Copilot] Falló la llamada a Gemini.', error);
    return null;
  }
}

export async function narrateCopilotReply(params: {
  userMessage: string;
  userRole: UserRole;
  route: CopilotAgentId;
  traces: ToolTrace[];
  pending: DRLRecommendation | null;
  hitlNote?: string;
}): Promise<string> {
  const llm = await generateGeminiText(buildNarrationPrompt(params));
  return llm || formatDeterministicReply(params.route, params.traces, params.pending);
}
