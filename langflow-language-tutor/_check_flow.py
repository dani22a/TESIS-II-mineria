import gzip, json, urllib.request
from pathlib import Path

base = "http://127.0.0.1:7860"
with urllib.request.urlopen(base + "/api/v1/auto_login", timeout=30) as r:
    token = json.loads(r.read())["access_token"]
req = urllib.request.Request(
    base + "/api/v1/flows/ba5f8703-ee9b-4252-afab-ae91cda317f2",
    headers={"Authorization": f"Bearer {token}", "Accept-Encoding": "identity"},
)
with urllib.request.urlopen(req, timeout=30) as r:
    raw = r.read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    flow = json.loads(raw)

print("nodes:")
for n in flow["data"]["nodes"]:
    node = n["data"]["node"]
    tmpl = node.get("template") or {}
    api = tmpl.get("api_key") or {}
    print("-", n["id"], "type=", n["data"].get("type"), "tool_mode=", node.get("tool_mode"),
          "outputs=", [o.get("name") for o in node.get("outputs") or []],
          "api_len=", len(str(api.get("value") or "")))
print("\nedges:")
for e in flow["data"]["edges"]:
    sh = e.get("data", {}).get("sourceHandle") or {}
    th = e.get("data", {}).get("targetHandle") or {}
    print(e["source"], sh.get("name"), "->", e["target"], th.get("fieldName"))
