# Prompt mejorado: investigación de módulo LangChain / LangGraph para MineTwin AI

**Uso:** copiar el bloque de la sección 2 y pegarlo en un chat nuevo (o en este mismo proyecto) **antes de implementar código**.  
**Objetivo del prompt:** que el agente investigue el repositorio, recomiende **un módulo concreto** y entregue **un Markdown de investigación**, sin escribir features.

El pedido original era corto y ambiguo (“qué módulo se puede agregar”). Este prompt fuerza auditoría de código, comparación LangChain vs LangGraph, alternativas descartadas, fuentes y un entregable MD con estructura fija.

---

## 1. Pedido original (para contraste)

```text
Basándote en este proyecto minetwin-ai, dime qué módulo usando LangChain o LangGraph se puede agregar a la aplicación.
Ejecuta esto y dame un MD a modo de documentación mencionando la investigación.
```

**Qué le faltaba:** alcance (¿un módulo o varios?), criterio de selección, si se podía implementar, idioma, qué auditar, qué no inventar, y el índice del documento.

---

## 2. Prompt mejorado (copiar desde aquí)

```text
Rol
Eres un investigador técnico de tesis (ingeniería / sistemas / minería) y auditor de código. No eres un generador de features. Tu única entrega es un documento Markdown de investigación.

Contexto
Trabajas sobre el proyecto minetwin-ai, un gemelo digital minero (ciclo Drill–Blast–Load–Haul–Crush–Mill) con UI React/Vite, simulación en cliente, motor Kuz-Ram, Scenario Lab what-if, optimizador DRL MAPPO simulado, modal Human-in-the-Loop y alertas. Hay ocho módulos de navegación. Puede existir GEMINI_API_KEY y @google/genai declarados: verifica en código si realmente se usan.

Tarea (única)
Responde esta pregunta con evidencia del repositorio y de literatura/documentación actual:

“Dado el estado real de MineTwin AI, ¿qué UN módulo usando LangChain o LangGraph se puede agregar a la aplicación, de forma coherente con la arquitectura, el dominio minero y el control humano que ya existe?”

Restricciones duras
- NO implementes código, no instales paquetes, no refactors, no crees componentes, no levantes servidores.
- SÍ crea un archivo Markdown de investigación (el usuario lo pide explícitamente).
- Idioma: español latino neutro. Textos de UI citados pueden quedar como están en el código.
- No inventes endpoints, modelos entrenados, backends ni integraciones OT que no estén en el código. Si algo es mock, hardcoded o solo UI, dilo explícitamente.
- No recomiendes reemplazar el DRL MAPPO ni Kuz-Ram por un LLM. El módulo debe complementarlos.
- Elige UN módulo principal. Puedes listar alternativas, pero debe haber un ganador justificado.
- Distingue LangChain (primitivas: LLM, tools, RAG) de LangGraph (orquestación con estado, HITL, multiagente).

Método obligatorio (en este orden)
1. Audita el código, no solo el README. Como mínimo:
   - src/App.tsx
   - src/components/NavigationSidebar.tsx
   - src/types/mining.ts
   - src/services/simulationEngine.ts
   - src/services/drlEngine.ts
   - src/services/kuzRamModel.ts
   - src/services/mockData.ts
   - vistas: AiOptimizerView, ScenarioLabView, DrillBlastView, MineToMillView, LoadHaulView, AnalyticsView, SystemDataView, DigitalTwinView
   - modales: HumanInTheLoopModal, AlertsModal
   - package.json, .env.example, README.md, metadata.json si existe
2. Inventario de módulos actuales (ID, etiqueta UI, función).
3. Diagnóstico de IA real vs simulada vs ausente (DRL, Gemini, LangChain, LangGraph, recomendaciones, what-if).
4. Brecha: qué no puede hacer hoy un operador/ingeniero/metalurgista que sí debería poder hacer con un agente.
5. Consulta documentación actual de LangGraph/LangChain (HITL interrupt, checkpointers, supervisor/handoff, tools). No te bases solo en conocimiento memorizado.
6. Busca precedentes 2025–2026 de agentes + gemelo digital + HITL industrial (cita enlaces).
7. Evalúa al menos 4 opciones con la rúbrica de abajo. Declara un ganador.

Rúbrica de selección (puntúa 1–5 cada criterio y justifica)
A. Complementariedad: no duplica DRL/Kuz-Ram; los usa como tools.
B. Cierre de brecha real: ataca algo mock, hardcoded o inexistente.
C. Factibilidad: aprovecha UI, tipos y servicios ya existentes (HITL, Scenario Lab, roles).
D. Rigor de tesis: patrón defendible (multiagente, neuro-simbólico, HITL, gemelo como entorno).
E. Seguridad operacional: acciones de alto impacto requieren aprobación humana.
F. Encaje LangGraph vs LangChain: por qué el runtime elegido es el correcto.

Opciones mínimas a evaluar (aunque descartes)
1. Chat RAG de SOP/incidentes (solo LangChain).
2. Triage de alertas (grafo lineal).
3. Capa XAI que solo explica recomendaciones MAPPO.
4. Reemplazar el despacho DRL por un LLM.
5. Copiloto operacional Mine-to-Mill (supervisor + especialistas + tools + HITL).
Puedes añadir otra opción si el código la justifica mejor.

Entregable
Crea UN archivo Markdown en:
minetwin-ai/INVESTIGACION-MODULO-LANGGRAPH.md

Estructura obligatoria del MD:
1. Resumen ejecutivo (el módulo ganador en las primeras 10 líneas, y por qué no es “un chatbot”).
2. Pregunta de investigación y criterios.
3. Metodología (qué archivos, docs y papers se usaron).
4. Diagnóstico del estado actual (módulos + IA real vs mock).
5. Brecha identificada.
6. LangChain vs LangGraph aplicado a ESTE proyecto (tabla).
7. Módulo propuesto: nombre, ID de navegación, qué es / qué no es, preguntas de demo por rol (UserRole).
8. Arquitectura recomendada (diagrama ASCII): UI, grafo, tools, motores existentes, HITL.
9. Diseño del grafo: estado, agentes, tools de lectura vs escritura (escritura siempre con interrupt).
10. Integración con archivos existentes (tabla archivo → uso).
11. Alternativas evaluadas y veredicto (incluida la rúbrica puntuada).
12. Contribución esperada para la tesis.
13. Fuentes (código + docs oficiales + literatura, con URL).
14. Conclusión y siguiente paso de implementación (solo descrito, no ejecutado).

Criterio de calidad
Un lector que no vio el chat debe poder defender oralmente: (a) qué hay hoy, (b) qué falta, (c) por qué LangGraph, (d) por qué ese módulo y no RAG, (e) cómo se engancha al HITL y a Kuz-Ram/DRL sin reemplazarlos.

Al terminar
Resume en el chat, en 8–12 líneas, el módulo ganador y la ruta del MD. No implementes.
```

---

## 3. Cómo usarlo

1. Abre un chat nuevo con el workspace `TESIS II` / `minetwin-ai`.
2. Pega el bloque de la sección 2.
3. Adjunta o menciona `@minetwin-ai`.
4. Espera el MD de investigación. **No pidas “aplicalo” en el mismo mensaje.**
5. Recién después, en otro turno: implementar el módulo ganador.

---

## 4. Variante corta (si el contexto ya está cargado)

```text
No implementes. Audita minetwin-ai (App, sidebar, types/mining, simulationEngine, drlEngine, kuzRamModel, mockData, HITL, Scenario Lab, package.json).
Pregunta: ¿qué UN módulo LangChain o LangGraph se puede agregar sin reemplazar DRL ni Kuz-Ram?
Distingue IA real vs mock. Consulta docs actuales de LangGraph (interrupt, supervisor) y precedentes de gemelo + HITL.
Entrega solo minetwin-ai/INVESTIGACION-MODULO-LANGGRAPH.md en español latino neutro, con resumen ejecutivo, brecha, rúbrica, arquitectura, alternativas descartadas y fuentes. Un ganador, no un catálogo.
```
