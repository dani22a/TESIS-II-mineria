from langflow.custom import Component
from langflow.io import MessageTextInput, Output
from langflow.schema import Message

import json
import os
import urllib.error
import urllib.request


def _session_id(component) -> str | None:
    try:
        return component.graph.session_id
    except Exception:
        return None


def _candidate_urls() -> list[str]:
    # MINETWIN_API_URL admite varias URLs separadas por coma (start.ps1 pone las IPs de Windows).
    configured = [url.strip().rstrip("/") for url in os.getenv("MINETWIN_API_URL", "").split(",") if url.strip()]
    defaults = ["http://host.containers.internal:3000", "http://host.docker.internal:3000"]
    return configured + [url for url in defaults if url not in configured]


def _call_minetwin(tool: str, payload: dict, session_id: str | None) -> dict:
    body = json.dumps({**payload, "session_id": session_id}).encode("utf-8")
    failures = []
    for base in _candidate_urls():
        request = urllib.request.Request(
            f"{base}/api/twin/tools/{tool}",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            return {"error": f"MineTwin respondió {exc.code}: {detail[:300]}"}
        except Exception as exc:
            failures.append(f"{base} ({exc})")
    return {"error": "No se pudo conectar con MineTwin (¿npm run dev está corriendo?). Probado: " + "; ".join(failures)}


class ExplainDrlTool(Component):
    display_name = "Explicar recomendación DRL"
    description = (
        "Obtiene una recomendación del optimizador DRL (MAPPO) con su qué y por qué, los KPIs vivos, "
        "la recompensa escalar y las alertas activas, para explicarla como auditoría. Úsala cuando pregunten "
        "por qué la IA recomienda algo o por una recomendación REC-..."
    )
    icon = "scan-search"
    name = "ExplainDrlTool"

    inputs = [
        MessageTextInput(
            name="rec_id",
            display_name="ID de recomendación",
            info="Opcional: ID de la recomendación, ej. REC-DRL-001. Vacío = la pendiente de revisión.",
            tool_mode=True,
            value="",
        ),
    ]
    outputs = [
        Output(display_name="Explicación", name="output", method="explicar_recomendacion"),
    ]

    def explicar_recomendacion(self) -> Message:
        payload = {"rec_id": str(self.rec_id or "").strip()}
        data = _call_minetwin("explain_drl_recommendation", payload, _session_id(self))
        text = json.dumps(data, ensure_ascii=False)
        self.status = text[:500]
        return Message(text=text)
