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


class WhatIfTool(Component):
    display_name = "Simular escenario"
    description = (
        "Simula un escenario hipotético (what-if) con el mismo motor del Scenario Lab de MineTwin, sin "
        "modificar la mina: pala fuera de servicio, lluvia o barro, cierre de rampa, más o menos camiones, "
        "cambio de factor de carga. Devuelve producción, ciclo, costo unitario y cuellos de botella."
    )
    icon = "flask-conical"
    name = "WhatIfTool"

    inputs = [
        MessageTextInput(
            name="description",
            display_name="Descripción",
            info="Descripción del escenario en lenguaje natural, ej. 'se cae EX-01 y llueve'.",
            tool_mode=True,
            value="",
        ),
        MessageTextInput(
            name="shovel_outage",
            display_name="Pala fuera de servicio",
            info="Opcional: EX-01, EX-02 o NONE.",
            tool_mode=True,
            value="",
        ),
        MessageTextInput(
            name="weather",
            display_name="Clima",
            info="Opcional: CLEAR (despejado), RAIN (lluvia) o MUD (barro).",
            tool_mode=True,
            value="",
        ),
        MessageTextInput(
            name="trucks_delta",
            display_name="Variación de camiones",
            info="Opcional: número entero de camiones a sumar (positivo) o quitar (negativo).",
            tool_mode=True,
            value="",
        ),
        MessageTextInput(
            name="road_blocked",
            display_name="Rampa cerrada",
            info="Opcional: 'si' para simular el cierre de la rampa principal.",
            tool_mode=True,
            value="",
        ),
        MessageTextInput(
            name="powder_factor_delta",
            display_name="Variación factor de carga (%)",
            info="Opcional: variación porcentual del factor de carga, ej. 8 o -5.",
            tool_mode=True,
            value="",
        ),
    ]
    outputs = [
        Output(display_name="Resultado del escenario", name="output", method="simular_escenario"),
    ]

    def simular_escenario(self) -> Message:
        payload = {
            "description": str(self.description or ""),
            "shovel_outage": str(self.shovel_outage or ""),
            "weather": str(self.weather or ""),
            "trucks_delta": str(self.trucks_delta or ""),
            "road_blocked": str(self.road_blocked or ""),
            "powder_factor_delta": str(self.powder_factor_delta or ""),
        }
        data = _call_minetwin("run_what_if_scenario", payload, _session_id(self))
        text = json.dumps(data, ensure_ascii=False)
        self.status = text[:500]
        return Message(text=text)
