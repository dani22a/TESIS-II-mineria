import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import type {IncomingMessage, ServerResponse} from 'http';
import path from 'path';
import {defineConfig, loadEnv} from 'vite';
import {generateGeminiTextWithKey} from './src/services/copilot/geminiServer';
import {createLangflowBridge, readJsonBody} from './src/services/langflow/bridgeServer';

export default defineConfig(({mode}) => {
  const env = loadEnv(mode, process.cwd(), '');
  const geminiKey = env.GEMINI_API_KEY || process.env.GEMINI_API_KEY || '';
  const langflowBridge = createLangflowBridge({
    langflowUrl: (env.LANGFLOW_URL || 'http://127.0.0.1:7861').replace(/\/$/, ''),
    flowId: env.LANGFLOW_FLOW_ID || 'minetwin-copilot',
    apiKey: env.LANGFLOW_API_KEY || '',
  });

  return {
    plugins: [
      react(),
      tailwindcss(),
      {
        name: 'minetwin-gemini-proxy',
        configureServer(server) {
          server.middlewares.use('/api/gemini', async (req: IncomingMessage, res: ServerResponse, next) => {
            if (req.method !== 'POST') {
              next();
              return;
            }
            res.setHeader('Content-Type', 'application/json');
            try {
              const body = await readJsonBody(req);
              const prompt = typeof body.prompt === 'string' ? body.prompt : '';
              if (!prompt) {
                res.statusCode = 400;
                res.end(JSON.stringify({error: 'Falta prompt'}));
                return;
              }
              if (!geminiKey) {
                res.statusCode = 200;
                res.end(JSON.stringify({text: null, reason: 'NO_KEY'}));
                return;
              }
              const text = await generateGeminiTextWithKey(geminiKey, prompt);
              res.statusCode = 200;
              res.end(JSON.stringify({text}));
            } catch (error) {
              console.warn('[MineTwin] Proxy Gemini falló', error);
              res.statusCode = 200;
              res.end(JSON.stringify({text: null}));
            }
          });
        },
      },
      {
        name: 'minetwin-langflow-bridge',
        configureServer(server) {
          server.middlewares.use(langflowBridge);
        },
      },
    ],
    define: {
      'process.env.GEMINI_API_KEY': JSON.stringify(geminiKey),
    },
    envPrefix: ['VITE_', 'GEMINI_'],
    optimizeDeps: {
      include: ['@langchain/core', '@langchain/langgraph/web', 'zod'],
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    server: {
      // Langflow (contenedor) llama a /api/twin/tools/* usando estos nombres de host.
      allowedHosts: ['host.containers.internal', 'host.docker.internal'],
      // HMR is disabled in AI Studio via DISABLE_HMR env var.
      // Do not modify—file watching is disabled to prevent flickering during agent edits.
      hmr: process.env.DISABLE_HMR !== 'true',
      // Disable file watching when DISABLE_HMR is true to save CPU during agent edits.
      watch: process.env.DISABLE_HMR === 'true' ? null : {},
    },
  };
});
