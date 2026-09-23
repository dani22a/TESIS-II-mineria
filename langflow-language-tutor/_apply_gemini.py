import gzip
import json
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(r"D:\UNIVERSIDAD\CICLO X\TESIS II\langflow-language-tutor")
BASE = "http://127.0.0.1:7860"
FLOW_ID = "ba5f8703-ee9b-4252-afab-ae91cda317f2"

STORY_TEMPLATE = """You are a language tutor writing a reading story in {language}.

User theme and extra instructions come from the tool input.
Prefer this known vocabulary:
{words}

Write ONE complete story. Never repeat the same text.

Format:
1) A short title
2) Two or three short paragraphs (about 120 to 180 words)
3) A beginning, a middle and an ending that fits the theme

Style:
- CEFR A2: simple, natural, pleasant to read. Not telegram sentences.
- Use correct grammar: conjugations, gender/number, articles, and connectors (porque, cuando, pero, también / because, when, but, also).
- Prefer words from the list, but you MAY use common function words and inflected forms so it sounds natural.
- Follow the user's topic (for example a cat).
- Do not list the vocabulary. Do not end with a forced "Adiós".
"""

LANGUAGE_AGENT_PROMPT = """You help the user practice reading in English, Spanish, or Chinese.

Use Gemini to answer.

- If the user asks for a story, call the story generation tool with the language and the theme. Then show that story ONCE. Add one short intro line in the user's language, for example: "Aquí tienes una historia para practicar:". Never paste the story twice.
- If the user asks to add a word, call the word add tool with the word and language, then confirm once.
- Keep the rest of your reply short.
"""


def env_key() -> str:
    key = ""
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("GOOGLE_API_KEY="):
            key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not key:
        raise SystemExit("missing GOOGLE_API_KEY in .env")
    return key


def login() -> str:
    with urllib.request.urlopen(BASE + "/api/v1/auto_login", timeout=20) as r:
        return json.loads(r.read())["access_token"]


def request(method: str, path: str, token: str, payload=None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE + path,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Accept-Encoding": "identity",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            if not raw:
                return None
            if raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} -> {exc.code}") from exc


def set_secret(tmpl: dict, key_name: str = "GOOGLE_API_KEY") -> None:
    api = tmpl.get("api_key")
    if isinstance(api, dict):
        api["load_from_db"] = True
        api["value"] = key_name
        api["password"] = True


def main() -> None:
    google_key = env_key()
    token = login()
    variables = request("GET", "/api/v1/variables/", token) or []
    existing = next((v for v in variables if v.get("name") == "GOOGLE_API_KEY"), None)
    payload = {
        "name": "GOOGLE_API_KEY",
        "value": google_key,
        "type": "Credential",
        "default_fields": ["api_key"],
    }
    if existing:
        payload["id"] = existing["id"]
        try:
            request("PATCH", f"/api/v1/variables/{existing['id']}", token, payload)
            print("updated GOOGLE_API_KEY variable")
        except RuntimeError as exc:
            if "422" not in str(exc) and "405" not in str(exc):
                raise
            print("variable already present, continuing")
    else:
        request("POST", "/api/v1/variables/", token, payload)
        print("created GOOGLE_API_KEY variable")

    flow = request("GET", f"/api/v1/flows/{FLOW_ID}", token)
    for node in flow["data"]["nodes"]:
        node_id = node["id"]
        tmpl = node["data"]["node"].get("template") or {}
        if node_id in {"GoogleGenerativeAI-story", "GoogleGenerativeAI-main", "Agent-CreateStory", "Agent-Language"}:
            set_secret(tmpl)
        if node_id == "GoogleGenerativeAI-story" and "temperature" in tmpl:
            tmpl["temperature"]["value"] = 0.75
        if node_id == "GoogleGenerativeAI-main" and "temperature" in tmpl:
            tmpl["temperature"]["value"] = 0.4
        if node_id == "PromptTemplate-tutor" and "template" in tmpl:
            tmpl["template"]["value"] = STORY_TEMPLATE
        if node_id == "Agent-Language" and "system_prompt" in tmpl:
            tmpl["system_prompt"]["value"] = LANGUAGE_AGENT_PROMPT
        gemini_model = [
            {
                "name": "gemini-2.5-flash",
                "icon": "GoogleGenerativeAI",
                "provider": "Google Generative AI",
                "metadata": {
                    "icon": "GoogleGenerativeAI",
                    "tool_calling": True,
                    "model_type": "llm",
                    "model_class": "ChatGoogleGenerativeAIFixed",
                    "api_key_param": "google_api_key",
                },
            }
        ]
        if node_id in {"Agent-CreateStory", "Agent-Language"} and "model" in tmpl:
            tmpl["model"]["value"] = gemini_model

    updated = request("PATCH", f"/api/v1/flows/{FLOW_ID}", token, {"data": flow["data"]})
    print("patched flow", updated.get("id") if isinstance(updated, dict) else "ok")


if __name__ == "__main__":
    main()
