/**
 * Server-side Gemini helper used by the Vite /api/gemini proxy.
 * Keeps the API call off the browser (avoids CORS) and tries current models.
 */

import { GoogleGenAI } from '@google/genai';

const GEMINI_MODELS = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-flash-latest'];

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

export async function generateGeminiTextWithKey(apiKey: string, prompt: string): Promise<string | null> {
  if (!apiKey) return null;
  const ai = new GoogleGenAI({ apiKey });
  for (const model of GEMINI_MODELS) {
    try {
      const response = await ai.models.generateContent({ model, contents: prompt });
      const text = extractGeminiText(response);
      if (text) return text;
    } catch {
      // probar el siguiente modelo
    }
  }
  return null;
}
