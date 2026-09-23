import copy
import gzip
import json
import os
import uuid
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:7860"
ROOT = Path(r"D:\UNIVERSIDAD\CICLO X\TESIS II\langflow-language-tutor")


def login():
    with urllib.request.urlopen(BASE + "/api/v1/auto_login", timeout=30) as r:
        return json.loads(r.read())["access_token"]


def request(method, path, token, payload=None):
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
        raise RuntimeError(f"{method} {path} -> {exc.code} {detail[:2000]}") from exc


def clone_node(catalog_node, node_id, data_type, display_name, position, tool_mode=False, field_values=None, description=None):
    node = copy.deepcopy(catalog_node)
    if description:
        node["display_name"] = display_name
        node["description"] = description
    else:
        node["display_name"] = display_name
    node["tool_mode"] = tool_mode
    if tool_mode:
        node["outputs"] = [
            {
                "allows_loop": False,
                "cache": True,
                "display_name": "Toolset",
                "group_outputs": False,
                "hidden": None,
                "loop_types": None,
                "method": "to_toolkit",
                "name": "component_as_tool",
                "options": None,
                "required_inputs": None,
                "selected": "Tool",
                "tool_mode": True,
                "types": ["Tool"],
                "value": "__UNDEFINED__",
            }
        ]
    for name, value in (field_values or {}).items():
        if name in node.get("template", {}) and isinstance(node["template"][name], dict):
            node["template"][name]["value"] = value
    return {
        "id": node_id,
        "type": "genericNode",
        "position": position,
        "data": {
            "id": node_id,
            "node": node,
            "type": data_type,
            "showNode": True,
            "display_name": display_name,
        },
        "selected": False,
        "measured": {"width": 320, "height": 280},
        "dragging": False,
    }


def encode_handle(payload: dict) -> str:
    dumped = json.dumps(payload, ensure_ascii=True)
    return dumped.replace('"', "œ")


def edge(source, target, source_handle, target_handle, source_type, target_type):
    source_str = encode_handle(source_handle)
    target_str = encode_handle(target_handle)
    return {
        "source": source,
        "target": target,
        "sourceHandle": source_str,
        "targetHandle": target_str,
        "data": {
            "sourceHandle": source_handle,
            "targetHandle": target_handle,
            "sourceType": source_type,
            "targetType": target_type,
        },
        "id": f"xy-edge__{source}{source_str}-{target}{target_str}",
        "animated": False,
        "className": "",
        "style": {"stroke": "#555"},
    }


def prompt_text_field(name, display_name, value=""):
    return {
        "type": "str",
        "required": False,
        "placeholder": "",
        "list": False,
        "show": True,
        "multiline": False,
        "value": value,
        "name": name,
        "display_name": display_name,
        "advanced": False,
        "dynamic": False,
        "info": "",
        "title_case": False,
        "input_types": ["Message", "Text"],
        "load_from_db": False,
        "trace_as_input": True,
        "trace_as_metadata": True,
    }


STORY_TEMPLATE = """Create a story in {language} using only words from the following list:
{words}

Rules:
- Write the entire story in the requested language.
- Supported languages: English, Spanish, Chinese.
- Beginner level, 8 to 12 short sentences.
- Use only words from the matching language list.
- Theme: school, family, friends, food, or daily life.
"""

LANGUAGE_AGENT_PROMPT = """You will help the user practice their language skills in English, Spanish, or Chinese. You will either be asked to create a story or to add a new word to the vocabulary.

- If the user asks you to create a story, use the story generation tool. Pass the requested language (English, Spanish, or Chinese).
- If the user asks you to add a word, use the word add tool. Include the word and its language (en, es, or zh / English, Spanish, or Chinese).
When using a tool, your answer should just be the result from the tool and nothing else.

You can reply in the same language the user used.
"""


def main():
    token = login()
    catalog = json.loads((ROOT / "_all_components.json").read_text(encoding="utf-8"))
    env = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    google_key = env.get("GOOGLE_API_KEY", "")

    projects = request("GET", "/api/v1/projects/", token)
    folder_id = projects[0]["id"]

    variables = request("GET", "/api/v1/variables/", token) or []
    has_google = any(v.get("name") == "GOOGLE_API_KEY" for v in variables)
    if google_key and not has_google:
        try:
            request(
                "POST",
                "/api/v1/variables/",
                token,
                {"name": "GOOGLE_API_KEY", "value": google_key, "type": "Credential", "default_fields": ["api_key"]},
            )
            print("created GOOGLE_API_KEY variable")
        except Exception as exc:
            print("variable create skipped:", exc)

    agent_cat = catalog["models_and_agents"]["Agent"]
    prompt_cat = catalog["models_and_agents"]["Prompt Template"]
    chat_in_cat = catalog["input_output"]["ChatInput"]
    chat_out_cat = catalog["input_output"]["ChatOutput"]
    google_cat = catalog["google"]["ext:google:GoogleGenerativeAIComponent@official"]
    loader_cat = catalog["language_tutor"]["ext:language_tutor:WordLoader@extra"]
    add_cat = catalog["language_tutor"]["ext:language_tutor:AddWordTool@extra"]
    upload_cat = catalog["language_tutor"]["ext:language_tutor:UploadWordFile@extra"]

    ids = {
        "upload": "UploadWordFile-tutor",
        "loader": "WordLoader-tutor",
        "prompt": "PromptTemplate-tutor",
        "story": "Agent-CreateStory",
        "add": "AddWordTool-tutor",
        "agent": "Agent-Language",
        "chat_in": "ChatInput-tutor",
        "chat_out": "ChatOutput-tutor",
        "llm_story": "GoogleGenerativeAI-story",
        "llm_main": "GoogleGenerativeAI-main",
    }

    prompt_node = clone_node(
        prompt_cat,
        ids["prompt"],
        "Prompt Template",
        "Prompt",
        {"x": 520, "y": 80},
        field_values={"template": STORY_TEMPLATE},
    )
    prompt_node["data"]["node"]["template"]["language"] = prompt_text_field(
        "language",
        "language",
        "the language requested in the user input (English, Spanish, or Chinese)",
    )
    prompt_node["data"]["node"]["template"]["words"] = prompt_text_field("words", "words", "")
    prompt_node["data"]["node"]["template"]["words"]["input_types"] = ["Message", "Text"]

    google_values = {
        "model_name": "gemini-2.5-flash",
        "tool_model_enabled": True,
        "temperature": 0.4,
        "api_key": google_key,
    }

    nodes = [
        clone_node(upload_cat, ids["upload"], "UploadWordFile", "Upload Word File", {"x": 40, "y": 560}),
        clone_node(loader_cat, ids["loader"], "WordLoader", "Word Loader", {"x": 40, "y": 80}, field_values={"language": "all"}),
        prompt_node,
        clone_node(
            google_cat,
            ids["llm_story"],
            "GoogleGenerativeAIModel",
            "Gemini Story",
            {"x": 980, "y": -40},
            field_values=google_values,
        ),
        clone_node(
            agent_cat,
            ids["story"],
            "Agent",
            "Create Story Tool",
            {"x": 980, "y": 80},
            tool_mode=True,
            description="Use this tool to create a story.",
            field_values={
                "system_prompt": "",
                "add_calculator_tool": False,
                "add_current_date_tool": False,
            },
        ),
        clone_node(
            add_cat,
            ids["add"],
            "AddWordTool",
            "Add word tool",
            {"x": 980, "y": 480},
            tool_mode=True,
        ),
        clone_node(
            google_cat,
            ids["llm_main"],
            "GoogleGenerativeAIModel",
            "Gemini Main",
            {"x": 1480, "y": 40},
            field_values=google_values,
        ),
        clone_node(
            agent_cat,
            ids["agent"],
            "Agent",
            "Language Agent",
            {"x": 1480, "y": 200},
            description="Help users practice their English, Spanish, and Chinese reading skills",
            field_values={
                "system_prompt": LANGUAGE_AGENT_PROMPT,
                "add_calculator_tool": False,
                "add_current_date_tool": False,
            },
        ),
        clone_node(chat_in_cat, ids["chat_in"], "ChatInput", "Chat Input", {"x": 980, "y": 760}),
        clone_node(chat_out_cat, ids["chat_out"], "ChatOutput", "Chat Output", {"x": 1980, "y": 280}),
    ]

    # If api_key supports load_from_db, prefer global variable name.
    for node in nodes:
        tmpl = node["data"]["node"].get("template") or {}
        if "api_key" in tmpl and isinstance(tmpl["api_key"], dict):
            tmpl["api_key"]["password"] = True
            tmpl["api_key"]["load_from_db"] = False
            tmpl["api_key"]["value"] = google_key

    edges = [
        edge(
            ids["loader"],
            ids["prompt"],
            {"dataType": "WordLoader", "id": ids["loader"], "name": "output", "output_types": ["Message"]},
            {"fieldName": "words", "id": ids["prompt"], "inputTypes": ["Message", "Text"], "type": "str"},
            "WordLoader",
            "Prompt Template",
        ),
        edge(
            ids["prompt"],
            ids["story"],
            {"dataType": "Prompt Template", "id": ids["prompt"], "name": "prompt", "output_types": ["Message"]},
            {"fieldName": "system_prompt", "id": ids["story"], "inputTypes": ["Message"], "type": "str"},
            "Prompt Template",
            "Agent",
        ),
        edge(
            ids["llm_story"],
            ids["story"],
            {"dataType": "GoogleGenerativeAIModel", "id": ids["llm_story"], "name": "model_output", "output_types": ["LanguageModel"]},
            {"fieldName": "model", "id": ids["story"], "inputTypes": ["LanguageModel"], "type": "model"},
            "GoogleGenerativeAIModel",
            "Agent",
        ),
        edge(
            ids["llm_main"],
            ids["agent"],
            {"dataType": "GoogleGenerativeAIModel", "id": ids["llm_main"], "name": "model_output", "output_types": ["LanguageModel"]},
            {"fieldName": "model", "id": ids["agent"], "inputTypes": ["LanguageModel"], "type": "model"},
            "GoogleGenerativeAIModel",
            "Agent",
        ),
        edge(
            ids["story"],
            ids["agent"],
            {"dataType": "Agent", "id": ids["story"], "name": "component_as_tool", "output_types": ["Tool"]},
            {"fieldName": "tools", "id": ids["agent"], "inputTypes": ["Tool"], "type": "other"},
            "Agent",
            "Agent",
        ),
        edge(
            ids["add"],
            ids["agent"],
            {"dataType": "AddWordTool", "id": ids["add"], "name": "component_as_tool", "output_types": ["Tool"]},
            {"fieldName": "tools", "id": ids["agent"], "inputTypes": ["Tool"], "type": "other"},
            "AddWordTool",
            "Agent",
        ),
        edge(
            ids["chat_in"],
            ids["agent"],
            {"dataType": "ChatInput", "id": ids["chat_in"], "name": "message", "output_types": ["Message"]},
            {"fieldName": "input_value", "id": ids["agent"], "inputTypes": ["Message"], "type": "str"},
            "ChatInput",
            "Agent",
        ),
        edge(
            ids["agent"],
            ids["chat_out"],
            {"dataType": "Agent", "id": ids["agent"], "name": "response", "output_types": ["Message"]},
            {"fieldName": "input_value", "id": ids["chat_out"], "inputTypes": ["Data", "JSON", "DataFrame", "Table", "Message"], "type": "other"},
            "Agent",
            "ChatOutput",
        ),
    ]

    payload = {
        "name": "Language Tutor",
        "description": "Tutor de lectura con vocabulario en ingles, espanol y chino. Replica la guia de Langflow.",
        "icon": "Languages",
        "icon_bg_color": "#1F6FEB",
        "gradient": "1",
        "data": {"nodes": nodes, "edges": edges, "viewport": {"x": 0, "y": 0, "zoom": 0.7}},
        "folder_id": folder_id,
        "is_component": False,
        "endpoint_name": "language-tutor",
    }

    created = request("POST", "/api/v1/flows/", token, payload)
    (ROOT / "flows" / "language-tutor.json").parent.mkdir(exist_ok=True)
    safe = copy.deepcopy(created)
    # do not persist api keys in the workspace export used for git
    for node in (safe.get("data") or {}).get("nodes") or []:
        tmpl = ((node.get("data") or {}).get("node") or {}).get("template") or {}
        if "api_key" in tmpl and isinstance(tmpl["api_key"], dict):
            tmpl["api_key"]["value"] = ""
    (ROOT / "flows" / "language-tutor.json").write_text(json.dumps(safe, ensure_ascii=False, indent=2), encoding="utf-8")
    print("created flow", created.get("id"), created.get("name"))
    print("endpoint", created.get("endpoint_name") or created.get("id"))


if __name__ == "__main__":
    main()
