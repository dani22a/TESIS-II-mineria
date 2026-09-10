/**
 * Optional Gemini layer. If GEMINI_API_KEY is missing, the graph still runs
 * with the heuristic supervisor and deterministic tools.
 */

export function getGeminiApiKey(): string {
  const env = (import.meta as { env?: Record<string, string | undefined> }).env;
  return (
    env?.GEMINI_API_KEY ||
    env?.VITE_GEMINI_API_KEY ||
    (typeof process !== 'undefined' ? process.env?.GEMINI_API_KEY : undefined) ||
    ''
  );
}

export async function generateGeminiText(prompt: string): Promise<string | null> {
  const apiKey = getGeminiApiKey();
  if (!apiKey) return null;

  try {
    const { GoogleGenAI } = await import('@google/genai');
    const ai = new GoogleGenAI({ apiKey });
    const response = await ai.models.generateContent({
      model: 'gemini-2.0-flash',
      contents: prompt,
    });
    const text = (response as { text?: string }).text;
    return text?.trim() || null;
  } catch {
    return null;
  }
}
