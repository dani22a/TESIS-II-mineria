import gzip
import json
import urllib.request

base = "http://127.0.0.1:7860"
with urllib.request.urlopen(base + "/api/v1/auto_login", timeout=20) as r:
    token = json.loads(r.read())["access_token"]


def get(path):
    req = urllib.request.Request(
        base + path,
        headers={"Authorization": f"Bearer {token}", "Accept-Encoding": "identity"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
        if raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        return json.loads(raw)


flow = get("/api/v1/flows/ba5f8703-ee9b-4252-afab-ae91cda317f2")
for n in flow["data"]["nodes"]:
    tmpl = n["data"]["node"].get("template") or {}
    model = tmpl.get("model") or {}
    api = tmpl.get("api_key") or {}
    temp = tmpl.get("temperature") or {}
    if n["id"].startswith("Agent") or "Google" in n["id"]:
        print("===", n["id"], n["data"].get("type"))
        print(" model.value", json.dumps(model.get("value"), ensure_ascii=False)[:500])
        print(" api.load_from_db", api.get("load_from_db"), "api.value_len", len(str(api.get("value") or "")), "password", api.get("password"))
        print(" temp", temp.get("value"))
        if "system_prompt" in tmpl:
            print(" prompt_len", len(str((tmpl.get("system_prompt") or {}).get("value") or "")))
        if "template" in tmpl and n["id"].startswith("Prompt"):
            print(" story_template", str((tmpl.get("template") or {}).get("value") or "")[:200])

print("\nvariables:")
for v in get("/api/v1/variables/"):
    print(v.get("name"), "type", v.get("type"), "has_value", v.get("has_value"), "valid", v.get("is_valid"), "id", v.get("id"))
