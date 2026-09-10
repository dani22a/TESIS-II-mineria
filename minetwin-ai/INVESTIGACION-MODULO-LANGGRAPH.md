# Investigación: módulo LangChain / LangGraph para MineTwin AI

**Proyecto:** MineTwin AI — gemelo digital minero (Drill–Blast–Load–Haul–Crush–Mill)  
**Fecha:** 9 de septiembre de 2026  
**Tipo de documento:** investigación técnica y recomendación de módulo  
**Alcance:** qué módulo basado en LangChain o LangGraph se puede agregar a la aplicación existente, y por qué.

---

## 1. Resumen ejecutivo

El módulo que más valor agrega a MineTwin AI **no es un chatbot genérico de LangChain**, sino un **Copiloto Operacional Mine-to-Mill orquestado con LangGraph**.

Se trata de un grafo multiagente con supervisor, herramientas conectadas a los motores ya existentes (simulación, Kuz-Ram, DRL, Scenario Lab) y **pausa humana (HITL)** antes de ejecutar acciones de alto impacto. El operador pregunta en lenguaje natural; el sistema consulta el gemelo, corre escenarios, explica recomendaciones DRL y propone acciones. Si la acción cambia despacho, tronadura o alimentación a planta, el grafo se detiene y espera aprobación, reutilizando el flujo Human-in-the-Loop que la aplicación ya muestra en UI.

**Por qué LangGraph y no solo LangChain**

| Criterio | LangChain (cadenas / RAG) | LangGraph (recomendado) |
|---|---|---|
| Encaje con HITL existente | Limitado | Nativo (`interrupt` + `Command(resume=...)`) |
| Estado del gemelo digital | Cadena lineal, difícil de persistir | Estado de grafo + checkpointer |
| Múltiples dominios (despacho, blast, molino) | Un solo agente o cadena | Supervisor + agentes especialistas |
| Auditoría / reanudación | Pobre | Checkpoints por `thread_id` |
| Uso de motores deterministas | Posible, pero sin control de flujo | Tools + nodos deterministas (patrón neuro-simbólico) |

**Recomendación:** implementar el módulo de navegación `COPILOT` (Copiloto LangGraph) como noveno módulo operacional, respaldado por un runtime LangGraph (Python o TypeScript) y Gemini, cuya API ya está prevista en el proyecto (`GEMINI_API_KEY`, `@google/genai`).

---

## 2. Pregunta de investigación

> Dado el estado actual de MineTwin AI, ¿qué módulo usando LangChain o LangGraph se puede agregar a la aplicación de forma coherente con la arquitectura, el dominio minero y el control humano que ya existe?

Criterios de evaluación:

1. **Complementariedad:** no reemplazar el DRL MAPPO ni Kuz-Ram; orquestarlos.
2. **Cierre de brecha real:** cubrir lo que hoy es mock, hardcoded o inexistente.
3. **Factibilidad:** aprovechar dependencias y superficies de UI ya presentes.
4. **Rigor de tesis:** patrón publicable (multiagente + HITL + gemelo digital).
5. **Seguridad operacional:** ninguna acción crítica se ejecuta sin aprobación humana.

---

## 3. Metodología de investigación

La investigación se ejecutó sobre el código del repositorio `minetwin-ai` y sobre documentación / literatura reciente:

1. **Auditoría del código fuente** (septiembre 2026): tipos de dominio, motor de simulación, motor DRL, Kuz-Ram, vistas, modales HITL y alertas, `package.json` y configuración de Gemini.
2. **Análisis de brechas:** qué IA existe de verdad versus qué está simulada o estática.
3. **Documentación oficial de LangGraph** (Human-in-the-Loop, `interrupt`, checkpointers, supervisor multiagente) vía docs de LangChain OSS Python/JS y `langgraph-supervisor`.
4. **Literatura y precedentes 2025–2026:**
   - Liu et al. (IEEE TII, 2026): *Agentic Neuro–Symbolic Planning and Commissioning for Human-in-the-Loop Industrial Robotics with Digital Twins* — LangGraph para orquestación, LLM para razonamiento, verificación determinista, gemelo digital para inspección humana.
   - Sistemas industriales multiagente con LangGraph (orquestación de triage de fallas, bus de mensajes de manufactura).
5. **Comparación de alternativas** (RAG simple, triage de alertas, XAI puro) contra el módulo propuesto.

---

## 4. Diagnóstico del estado actual de MineTwin AI

### 4.1 Módulos operacionales existentes

La navegación (`NavigationSidebar`) expone ocho módulos:

| ID | Etiqueta | Función |
|---|---|---|
| `TWIN_3D` | Gemelo 3D | Visualización Three.js en vivo |
| `DRILL_BLAST` | Drill & Blast | Mallas, powder factor, Kuz-Ram |
| `LOAD_HAUL` | Load & Haul | Ciclo de camión, colas, reasignación |
| `MINE_TO_MILL` | Mine-to-Mill | Propagación causal fragmentación → SAG |
| `SCENARIO_LAB` | Scenario Lab | What-if por sliders (flota, pala, rampa, clima) |
| `AI_OPTIMIZER` | Optimizador DRL | Benchmark de políticas MAPPO, pesos de recompensa |
| `ANALYTICS` | Analítica | Series de KPI, ciclo, combustible |
| `SYSTEM_DATA` | Datos & OT | Pipelines OT/IT, RBAC, auditoría |

### 4.2 Capacidades de IA que ya existen (y sus límites)

**A. Optimizador DRL (MAPPO)** — `src/services/drlEngine.ts`

- Curriculum learning en 7 fases, comparación de políticas, función de recompensa ponderada.
- Las recomendaciones (`DRLRecommendation`) tienen `what`, `why`, impacto esperado y `status: PENDING_REVIEW | APPROVED | REJECTED`.
- **Límite:** el motor no infiere; `computePolicyComparisons` y las recomendaciones iniciales son **datos estáticos** en `mockData.ts`. No hay LLM, ni explicación generada, ni consulta en lenguaje natural.

**B. Human-in-the-Loop** — `HumanInTheLoopModal` + `AiOptimizerView`

- La UI ya pide aprobar o rechazar acciones autónomas.
- El operador no puede **preguntar** (“¿por qué EX-02 se congestiona?”) ni **pedir un escenario** (“¿qué pasa si EX-01 cae 2 horas?”).

**C. Scenario Lab** — `ScenarioLabView`

- What-if útil, pero solo por controles numéricos.
- No traduce una pregunta de ingeniería a parámetros de escenario.

**D. Kuz-Ram** — `kuzRamModel.ts`

- Motor físico determinista (Lilly / Cunningham), listo para usarse como **herramienta** de un agente.
- Hoy solo se invoca desde sliders de UI.

**E. Gemini está declarado pero no se usa**

- `package.json` incluye `@google/genai`.
- `.env.example` y `README.md` piden `GEMINI_API_KEY`.
- `metadata.json` declara `MAJOR_CAPABILITY_SERVER_SIDE_GEMINI_API`.
- **No hay ninguna llamada a Gemini en `src/`.** Es capacidad reservada sin módulo.

**F. No hay LangChain ni LangGraph**

- No aparecen en dependencias ni en código.
- No hay backend de agentes; la app es un frontend Vite/React con simulación en el cliente.

### 4.3 Conclusión del diagnóstico

MineTwin AI es un **gemelo digital + simulación + DRL simulado + HITL visual**. Le falta la capa de **razonamiento en lenguaje natural orquestado**, que es exactamente el hueco que LangGraph cubre sin duplicar física ni DRL.

---

## 5. Brecha identificada

El operador de despacho, el ingeniero de mina, el especialista D&B y el metalurgista tienen roles (`UserRole`) pero **ninguna interfaz conversacional contextual**. Hoy deben:

- navegar ocho pantallas,
- interpretar KPIs y tablas,
- ajustar sliders,
- aprobar recomendaciones cuyo texto ya viene escrito a mano.

Lo que falta es un **agente de operaciones** que:

1. Lea el estado vivo del gemelo (`DigitalTwinState`).
2. Llame a herramientas deterministas (Kuz-Ram, tick de simulación, what-if, scoring DRL).
3. Explique causas en español operativo.
4. Proponga acciones estructuradas.
5. **Se detenga** antes de mutar el gemelo, reutilizando el modal HITL.

Esa capa es un grafo de estado, no una cadena RAG.

---

## 6. LangChain vs LangGraph en este proyecto

### 6.1 Qué aporta LangChain

LangChain sirve para:

- abstracción de LLM (Gemini / otros),
- definición de **tools** (`@tool` / `tool()`),
- RAG (embeddings + retriever) si más adelante se indexan SOP, reportes de incidentes o bitácoras,
- output estructurado (JSON de recomendaciones).

Es **necesario como librería de primitivas**, insuficiente como orquestador.

### 6.2 Qué aporta LangGraph (decisión)

LangGraph es el runtime correcto porque MineTwin ya tiene:

- **estado persistente** (`DigitalTwinState`),
- **decisiones de alto riesgo** (reasignar flota, cerrar rampa, subir powder factor),
- **varios especialistas de dominio** (alineados a `UserRole`),
- **auditoría** (`auditTrail` en recomendaciones, eventos en `SystemDataView`).

APIs relevantes (documentación oficial LangGraph OSS, 2026):

- `interrupt(payload)` — pausa el grafo y expone el payload a la UI.
- `Command(resume=...)` — reanuda con la decisión humana (aprobar / rechazar / editar).
- Checkpointer (`MemorySaver`, `SqliteSaver`) + `thread_id` — el turno del operador sobrevive recargas.
- `create_supervisor([...agentes])` — un supervisor delega a especialistas vía handoff.

Esto mapea 1:1 con `DRLRecommendation.status` y `HumanInTheLoopModal`.

### 6.3 Evidencia académica

Liu et al. (IEEE Transactions on Industrial Informatics, 2026) proponen un marco **neuro-simbólico** para industria:

- el LLM interpreta intención y orquesta;
- la verificación y la ejecución permanecen **deterministas**;
- LangGraph enruta recuperación ante fallas;
- un gemelo digital permite inspección humana antes de ejecutar en el mundo físico.

Ese patrón es el mismo que MineTwin necesita: **LLM razona, Kuz-Ram / simulación / DRL calculan, el humano aprueba, el gemelo muestra el efecto**.

---

## 7. Módulo propuesto (recomendación principal)

### Nombre

**Copiloto Operacional Mine-to-Mill (LangGraph Supervisor)**  
ID de navegación: `COPILOT`  
Etiqueta UI: `Copiloto IA`  
Badge: `LangGraph`

### 7.1 Qué es

Un noveno módulo de la aplicación: un centro de comando conversacional que no “adivina” física ni despacho. Orquesta agentes especialistas que **invocan los servicios ya escritos**.

Preguntas que el módulo debe resolver (ejemplos de tesis / demo):

| Rol | Pregunta | Tools del grafo |
|---|---|---|
| Operador | “¿Por qué EX-02 tiene cola y qué camiones reasigno?” | `query_twin_state`, `score_dispatch_policy`, `propose_reassignment` |
| Ingeniero de mina | “Si EX-01 cae 2 h y llueve, ¿cuál es el impacto?” | `run_what_if_scenario` |
| D&B | “Si subo powder factor 8 %, ¿qué pasa con P80 y kWh/t del SAG?” | `run_kuz_ram`, `evaluate_mine_to_mill` |
| Metalurgista | “La tolva está al 54 %. ¿Priorizo skarn a chancador?” | `query_twin_state`, `propose_crusher_feed` |
| Data scientist | “Explícame la recomendación REC-DRL-001 como si fuera auditoría.” | `explain_drl_recommendation` |

### 7.2 Qué no es

- No sustituye MAPPO. El DRL sigue siendo la política de despacho.
- No reemplaza Kuz-Ram. El agente solo lo llama.
- No es un chat genérico desconectado del gemelo.
- No ejecuta mutaciones críticas sin `interrupt`.

---

## 8. Arquitectura recomendada

```
┌─────────────────────────────────────────────────────────────┐
│  MineTwin UI (React / Vite)                                 │
│  NavigationSidebar + CopilotView + HumanInTheLoopModal     │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP / SSE (streaming tokens)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Runtime LangGraph                                          │
│  Supervisor ──handoff──► Agente Despacho                    │
│            ──handoff──► Agente Drill-Blast                   │
│            ──handoff──► Agente Mine-to-Mill                  │
│            ──handoff──► Agente Escenarios                    │
│            ──handoff──► Agente XAI / Alertas               │
│                                                             │
│  Nodo HITL: interrupt() antes de tools de escritura         │
│  Checkpointer: thread_id = turno + usuario                    │
└───────────────┬──────────────────────────┬──────────────────┘
                │ tools de lectura           │ tools de escritura
                ▼                            ▼
     SimulationEngine.tick          setState / reassign truck
     kuzRamModel                    update blast pattern
     drlEngine.calculateReward      approve recommendation
     ScenarioLab (misma lógica)     acknowledge alert
     DigitalTwinState snapshot
```

### 8.1 Stack sugerido

Hay dos opciones viables. Se recomienda **Opción A** para tesis (mejor ecosistema supervisor + HITL documentado).

**Opción A — Python (recomendada para el grafo)**

- `langgraph` + `langgraph-supervisor` + `langchain-google-genai`
- LLM: Gemini (reutiliza `GEMINI_API_KEY`)
- API: FastAPI con streaming SSE
- El frontend React permanece; solo consume el copiloto

**Opción B — TypeScript en el mismo repo**

- `@langchain/langgraph` + `@langchain/google-genai`
- Encaja con Vite y `express` ya declarados en `package.json`
- Menos maduro el paquete supervisor, pero `interrupt` está documentado en JS

**Principio neuro-simbólico (obligatorio):**  
el LLM **nunca** inventa t/h, P80 ni costos. Esas cifras salen de tools que envuelven `kuzRamModel.ts`, la lógica de `ScenarioLabView.handleRunSimulation` y `drlEngine.ts`.

---

## 9. Diseño del grafo

### 9.1 Estado del grafo

```python
class CopilotState(TypedDict):
    messages: Annotated[list, add_messages]
    twin_snapshot: dict          # DigitalTwinState serializado
    user_role: Literal[
        "OPERATOR", "MINE_ENGINEER",
        "DRILL_BLAST_ENGINEER", "METALLURGIST", "DATA_SCIENTIST"
    ]
    pending_action: dict | None  # payload para interrupt
    last_tool_results: dict
    citations: list[str]        # qué tool produjo cada cifra
```

### 9.2 Agentes especialistas (alineados a roles actuales)

| Agente | Tools | Equivale a |
|---|---|---|
| `dispatch_agent` | estado de palas/camiones, colas, `applyDispatchStrategy` (solo lectura hasta HITL) | Load & Haul + DRL |
| `blast_agent` | `calculateKuzRamFragmentation`, powder factor | DrillBlastView |
| `mill_agent` | `evaluateMineToMillImpact`, choke de chancador, SAG kWh/t | MineToMillView |
| `scenario_agent` | misma función what-if del Scenario Lab | ScenarioLabView |
| `xai_agent` | explica `DRLRecommendation` y correlaciona `MineAlert` | HITL + AlertsModal |

El **supervisor** decide el handoff según la pregunta y el `user_role`. Puede despachar en paralelo (p. ej. blast + mill) usando el patrón `Send` de LangGraph Supervisor.

### 9.3 Tools de escritura (siempre con interrupt)

Herramientas que mutan el gemelo:

- `reassign_truck(truck_id, shovel_id)`
- `apply_powder_factor(pattern_id, new_pf)`
- `set_dispatch_strategy(strategy)`
- `approve_drl_recommendation(rec_id)`

Patrón oficial (docs LangGraph OSS):

```text
tool de escritura
  → interrupt({ action, payload, expectedImpact })
  → UI muestra el mismo contrato que DRLRecommendation (what / why / impacto)
  → operador aprueba o rechaza en HumanInTheLoopModal
  → graph.invoke(Command(resume={ action: "approve" | "reject" }))
```

Así el módulo **no inventa un segundo HITL**: alimenta el modal que ya existe.

### 9.4 Flujo de un turno

1. El usuario escribe: *“Rebalancea la flota; EX-02 se está congestionando.”*
2. El supervisor envía a `dispatch_agent`.
3. Tools de lectura leen colas, ETA y estrategia activa.
4. El agente arma un `DRLRecommendation` estructurado (no texto libre como única salida).
5. `interrupt` pausa. La UI pinta la tarjeta HITL.
6. Si hay aprobación, se llama a `handleManualReassignTruck` / `handleApproveRecommendation` ya presentes en `App.tsx`.
7. El checkpointer guarda el hilo para la bitácora de `SystemDataView`.

---

## 10. Integración con el código existente

Puntos de anclaje (sin reescribir el gemelo):

| Archivo actual | Uso en el módulo nuevo |
|---|---|
| `src/types/mining.ts` | Contrato de estado y de `DRLRecommendation` |
| `src/services/simulationEngine.ts` | Tool `tick` / despacho (lectura) |
| `src/services/kuzRamModel.ts` | Tool física de fragmentación |
| `src/services/drlEngine.ts` | Tool de reward y comparación de políticas |
| `src/components/views/ScenarioLabView.tsx` | Extraer la función what-if a un servicio compartido y llamarla desde el agente |
| `src/components/modals/HumanInTheLoopModal.tsx` | Superficie de `interrupt` |
| `src/components/NavigationSidebar.tsx` | Nuevo ítem `COPILOT` |
| `src/App.tsx` | Render de `CopilotView` y handlers ya existentes |
| `GEMINI_API_KEY` | LLM del supervisor y especialistas |

Trabajo de código mínimo para desbloquear el módulo:

1. Extraer la simulación what-if de la vista a `src/services/scenarioEngine.ts` (hoy está embebida en el componente).
2. Añadir `ActiveModule = 'COPILOT'`.
3. Crear `CopilotView` (chat + timeline de tools + citas de cifras).
4. Levantar el runtime LangGraph y un endpoint `/copilot/stream`.

---

## 11. Alternativas evaluadas (y por qué no son el módulo principal)

### Alternativa 1 — Chat RAG con LangChain (SOP + incidentes)

- **Pros:** rápido, útil para procedimientos.
- **Contras:** no usa el gemelo en vivo; no cierra el ciclo HITL; no justifica tesis frente a un DRL ya presente.
- **Veredicto:** fase 2 (memoria de incidentes / FAISS), no el módulo a agregar ahora.

### Alternativa 2 — Solo triage de alertas (LangGraph lineal)

Inspirado en orquestadores industriales (triage → retrieval → asignación). Encajaría con `AlertsModal`, pero deja fuera Kuz-Ram, Scenario Lab y DRL. Demasiado estrecho.

### Alternativa 3 — XAI puro (explicar MAPPO con un LLM)

- Útil, pero es una feature, no un módulo.
- No permite what-if ni acciones.
- Se absorbe como `xai_agent` dentro del supervisor.

### Alternativa 4 — Reemplazar DRL por un agente LLM de despacho

**Descartado.** El LLM no debe asignar camiones turno a turno. El DRL y las heurísticas (`SHORTEST_QUEUE`, etc.) ya cubren eso. El copiloto **explica, simula y propone**; no sustituye la política.

---

## 12. Contribución esperada para la tesis

El módulo permite argumentar, con evidencia de código y de literatura:

1. **Híbrido DRL + LLM:** el refuerzo optimiza; el grafo de lenguaje opera y explica.
2. **Neuro-simbólico:** física Kuz-Ram y simulación de colas como tools deterministas.
3. **HITL de grado industrial:** `interrupt` de LangGraph alineado al modal ya diseñado.
4. **Multiagente de dominio minero:** supervisor mapeado a roles reales de mina.
5. **Gemelo digital como entorno del agente:** el estado no es un prompt suelto, es `DigitalTwinState`.

Eso diferencia MineTwin de un “dashboard con ChatGPT al lado”.

---

## 13. Fuentes consultadas

### Código del proyecto (auditoría)

- `minetwin-ai/src/App.tsx` — orquestación de módulos y HITL
- `minetwin-ai/src/types/mining.ts` — dominio Drill–Mill, DRL, escenarios, roles
- `minetwin-ai/src/services/simulationEngine.ts` — simulación y estrategias de despacho
- `minetwin-ai/src/services/drlEngine.ts` — MAPPO simulado, curriculum, reward
- `minetwin-ai/src/services/kuzRamModel.ts` — fragmentación y mine-to-mill
- `minetwin-ai/src/services/mockData.ts` — recomendaciones y alertas estáticas
- `minetwin-ai/src/components/NavigationSidebar.tsx` — catálogo de módulos
- `minetwin-ai/src/components/views/AiOptimizerView.tsx`
- `minetwin-ai/src/components/views/ScenarioLabView.tsx`
- `minetwin-ai/src/components/modals/HumanInTheLoopModal.tsx`
- `minetwin-ai/package.json`, `.env.example`, `README.md`

### Documentación de frameworks

- LangGraph OSS — Interrupts / Human-in-the-Loop: [https://docs.langchain.com/oss/python/langgraph/interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
- LangGraph JS — Interrupts (mismo patrón `interrupt` + `Command`): documentación OSS JavaScript LangGraph
- LangGraph Supervisor — `create_supervisor`, `create_handoff_tool`: [https://github.com/langchain-ai/langgraph-supervisor-py](https://github.com/langchain-ai/langgraph-supervisor-py)
- LangGraph — Workflows vs agents: [https://docs.langchain.com/oss/javascript/langgraph/workflows-agents](https://docs.langchain.com/oss/javascript/langgraph/workflows-agents)

### Literatura y precedentes

- Liu, Z.; Nan Fernandez-Ayala, V.; Wang, T.; Qin, Q.; Wang, X. V.; Dimarogonas, D. V.; Wang, L. (2026). *Agentic Neuro–Symbolic Planning and Commissioning for Human-in-the-Loop Industrial Robotics with Digital Twins*. IEEE Transactions on Industrial Informatics. [arXiv:2606.08214](https://arxiv.org/abs/2606.08214)
- Orquestación multiagente industrial con LangGraph (triage de fallas + retrieval + asignación): repositorio de referencia *maintenance-orchestration* (Gemini + LangGraph + FAISS)
- Arquitecturas de bus de mensajes multiagente en manufactura basadas en estado compartido de LangGraph (2026)

---

## 14. Conclusión

**Módulo a agregar:** Copiloto Operacional Mine-to-Mill con **LangGraph** (supervisor + especialistas + tools + HITL), usando **LangChain** solo como capa de LLM/tools.

Es la única opción que:

- aprovecha Gemini ya declarado y no usado,
- conecta los ocho módulos actuales en lugar de competir con ellos,
- convierte recomendaciones hardcoded en un ciclo real preguntar → simular → explicar → aprobar,
- se sostiene con literatura 2026 de gemelos digitales + LangGraph + HITL.

**Siguiente paso de implementación (cuando se autorice):** extraer el motor what-if a servicio, añadir `COPILOT` al sidebar y un runtime LangGraph con tools de solo lectura primero; las tools de escritura se activan después, siempre detrás de `interrupt`.
