# Guía: Copiloto LangGraph en MineTwin AI

Esta guía explica, en lenguaje simple, **qué se implementó**, **si hace falta una API key**, **cómo probarlo** y **qué deberías ver**.

---

## 1. Respuesta corta: ¿debo configurar una API key?

**LangGraph no pide API key.** Es una librería que orquesta el flujo (supervisor → agente → tools → aprobación humana). Ya está instalada en el proyecto. No te registras en LangGraph ni pagas por usarla.

**Gemini sí es opcional.** Es el modelo de Google que redacta la respuesta en un español más natural.

| Situación | Qué pasa |
|---|---|
| **Sin API key** | El copiloto **igual funciona**. Calcula con Kuz-Ram, Scenario Lab y el estado del gemelo. El badge dice `Gemini OFF · tools locales`. El texto es más técnico (JSON de tools). |
| **Con `GEMINI_API_KEY`** | El badge dice `Gemini ON`. El supervisor puede elegir mejor el agente y la respuesta se lee como un informe operativo. **Las cifras siguen saliendo de las tools**, no las inventa el modelo. |

Para la tesis y una demo, **puedes probar ya sin key**. La key solo mejora la redacción.

No existe una “API key de LangGraph”. No configures OpenAI a menos que más adelante cambies el modelo.

---

## 2. Qué hace este módulo (sin jerga)

En el sidebar aparece **Copiloto IA** (badge `LangGraph`).

Tú preguntas en español, por ejemplo: *“¿Por qué EX-02 tiene cola?”*.

El sistema:

1. Un **supervisor** decide qué especialista atiende (despacho, tronadura, planta, escenario o explicación DRL).
2. Ese agente **llama tools** que ya existían: gemelo vivo, Kuz-Ram, what-if, motor DRL.
3. Si la acción **cambia la mina** (reasignar camiones, subir powder factor, mandar mineral al chancador), **se pausa** y te pide **Aprobar** o **Rechazar**.
4. Solo si apruebas se actualiza el gemelo. También aparece en el modal Human-in-the-Loop del header.

Eso es LangGraph: un grafo con pausa humana, no un chat suelto.

```
Tú preguntas
    → Supervisor (elige agente)
        → Tool determinista (números reales)
            → ¿Es una acción de escritura?
                 sí → HITL (aprobar / rechazar)
                 no → solo respuesta + citas
```

---

## 3. Cómo arrancar la app

En la carpeta `minetwin-ai`:

```bash
npm install
npm run dev
```

Abre `http://localhost:3000`.

En el menú izquierdo: **Copiloto IA**.

---

## 4. Cómo poner la API key (opcional)

1. Crea una clave en [Google AI Studio](https://aistudio.google.com/apikey).
2. En `minetwin-ai` copia `.env.example` a `.env.local` (o `.env`).
3. Deja esto (sin comillas raras ni la palabra `MY_GEMINI_API_KEY`):

```env
GEMINI_API_KEY=tu_clave_real_aqui
```

4. **Reinicia** `npm run dev`. Vite lee la variable al arrancar.

Si el badge sigue en `Gemini OFF`, la key no se cargó: revisa el nombre exacto `GEMINI_API_KEY` y que el servidor se haya reiniciado.

---

## 5. Cómo probarlo (paso a paso)

### Paso 0 — Cambiar de rol (recomendado)

Ve a **Datos & OT** y elige un rol. Las sugerencias del chat cambian:

| Rol | Sirve para probar |
|---|---|
| Operador de despacho | Colas y reasignación de camiones |
| Ingeniero de mina | Escenarios what-if (pala caída, lluvia) |
| Especialista Drill & Blast | P80 y powder factor (Kuz-Ram) |
| Metalurgista | Tolva / chancador / SAG |
| Científico de datos | Explicar `REC-DRL-001` |

Luego vuelve a **Copiloto IA**.

### Prueba A — Solo consulta (no cambia la mina)

Escribe o pulsa:

> Si EX-01 cae 2 horas y llueve, ¿cuál es el impacto?

**Resultado esperado**

- El agente es `scenario_agent`.
- A la derecha, timeline de tools con `run_what_if_scenario` y cifras (producción, ciclo, cuellos de botella).
- **No** aparece el recuadro amarillo de aprobar/rechazar.
- El gemelo no cambia.

### Prueba B — Acción con aprobación humana

Con rol operador:

> Propón un rebalanceo de flota ahora.

**Resultado esperado**

- Agente `dispatch_agent`.
- Recuadro HITL: título, qué propone, por qué.
- Botones **Rechazar** y **Aprobar y despachar**.
- La misma recomendación entra a la cola HITL del header (ícono de recomendaciones).

Si **apruebas**: el texto confirma ejecución y los camiones `DT-…` cambian de pala (Load & Haul / gemelo 3D).  
Si **rechazas**: el gemelo no se muta.

### Prueba C — Física Kuz-Ram

> Si subo el powder factor 8%, ¿qué pasa con P80 y kWh/t del SAG?

**Resultado esperado**

- Agente `blast_agent`.
- Tool `run_kuz_ram` con P80 actual vs +8 %.
- Números coherentes con Drill & Blast / Mine-to-Mill (no un texto inventado).

### Prueba D — Explicar el DRL

> Explícame la recomendación REC-DRL-001 como auditoría.

**Resultado esperado**

- Agente `xai_agent`.
- Resume `what` / `why` de la recomendación MAPPO y KPIs vivos.
- No reemplaza al Optimizador DRL; solo lo explica.

---

## 6. Qué deberías ver en pantalla

En la cabecera del módulo:

- Badge **LangGraph** (siempre).
- **Gemini ON** o **Gemini OFF · tools locales**.

En el chat:

- Tu pregunta.
- Respuesta del copiloto con el nombre del agente (`dispatch_agent`, `blast_agent`, etc.).

A la derecha, **Timeline de tools (citas)**:

- Nombre de la tool (`query_twin_state`, `run_kuz_ram`, …).
- De dónde salió el número (`kuzRamModel`, `scenarioEngine`, …).
- JSON con las cifras. Eso es la evidencia para la tesis: el LLM no inventa t/h ni P80.

---

## 7. Si algo no cuadra

| Lo que ves | Qué significa |
|---|---|
| `Gemini OFF` y texto con JSON | Normal sin key. El módulo está bien. |
| `No se pudo ejecutar el grafo` | Recarga la página. Si sigue, el fallback local igual debería responder. |
| Apruebas y no cambia nada | Mira Load & Haul: la pala asignada de esos `DT-`. El approve ahora usa IDs `DT-`, no `HT-`. |
| Pregunta de blast y responde despacho | Cambia el rol en Datos & OT o usa las frases sugeridas (el enrutador busca palabras como “P80”, “llueve”, “reasigna”). |
| Key puesta y sigue OFF | Reinicia `npm run dev`. El archivo debe llamarse `.env` o `.env.local` junto a `package.json`. |

---

## 8. Qué no hace (a propósito)

- No sustituye al **Optimizador DRL (MAPPO)**. El DRL sigue siendo la política de despacho.
- No sustituye a **Kuz-Ram**. El copiloto lo llama.
- No ejecuta cambios críticos sin tu aprobación.
- No es un ChatGPT genérico: si no hay tool, no debería inventar un P80.

---

## 9. Mapa rápido de archivos

| Archivo | Para qué |
|---|---|
| `src/components/views/CopilotView.tsx` | Pantalla del chat |
| `src/services/copilot/graph.ts` | Grafo LangGraph (supervisor + HITL) |
| `src/services/copilot/tools.ts` | Cálculos reales (gemelo, Kuz-Ram, what-if, DRL) |
| `src/services/copilot/gemini.ts` | Gemini opcional |
| `src/services/scenarioEngine.ts` | Motor what-if (UI + copiloto) |
| `.env.example` | Plantilla de `GEMINI_API_KEY` |

Si quieres profundizar el “por qué” técnico, está en `INVESTIGACION-MODULO-LANGGRAPH.md`. Esta guía es solo para **usar y demostrar** el módulo.
