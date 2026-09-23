import json
from pathlib import Path

data = json.loads(Path(r"D:\UNIVERSIDAD\CICLO X\TESIS II\langflow-language-tutor\_all_components.json").read_text(encoding="utf-8"))
agent = data["models_and_agents"]["Agent"]
lm = data["models_and_agents"]["LanguageModelComponent"]

print("=== AGENT model field ===")
print(json.dumps(agent["template"]["model"], indent=2)[:4000])
print("\n=== AGENT api_key ===")
print(json.dumps(agent["template"]["api_key"], indent=2)[:2000])
print("\n=== LM provider ===")
print(json.dumps(lm["template"].get("provider"), indent=2)[:2000])
print("\n=== LM model ===")
print(json.dumps(lm["template"].get("model"), indent=2)[:2500])
print("\n=== LM model_name ===")
print(json.dumps(lm["template"].get("model_name"), indent=2)[:1500])
print("\n=== LM api_key ===")
print(json.dumps(lm["template"].get("api_key"), indent=2)[:2000])
