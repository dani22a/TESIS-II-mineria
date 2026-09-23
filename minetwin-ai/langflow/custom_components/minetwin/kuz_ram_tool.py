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


class KuzRamTool(Component):
    display_name = "Calcular Kuz-Ram"
    description = (
        "Calcula la fragmentación de la tronadura con el modelo físico Kuz-Ram (P20, P50, P80, sobretamaño) "
        "y su impacto en el molino SAG (kWh/t, t/h, riesgo de atollo en chancador). Devuelve el caso actual "
        "y, si se indica, el caso con otro factor de carga. Úsala para preguntas de tronadura, P80 o "
        "factor de carga (powder factor)."
    )
    icon = "flame"
    name = "KuzRamTool"

    inputs = [
        MessageTextInput(
            name="powder_factor",
            display_name="Factor de carga",
            info=(
                "Opcional. Nuevo factor de carga a evaluar: un valor absoluto en kg/m3 (ej. 0.92) "
                "o una variación porcentual (ej. +8%). Vacío = solo el caso actual."
            ),
            tool_mode=True,
            value="",
        ),
    ]
    outputs = [
        Output(display_name="Resultado Kuz-Ram", name="output", method="calcular_kuz_ram"),
    ]

    def calcular_kuz_ram(self) -> Message:
        payload = {"powder_factor": str(self.powder_factor or "").strip()}
        data = _call_minetwin("run_kuz_ram", payload, _session_id(self))
        text = json.dumps(data, ensure_ascii=False)
        self.status = text[:500]
        return Message(text=text)
