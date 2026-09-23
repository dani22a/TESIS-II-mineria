import gzip, json, urllib.request

base = "http://127.0.0.1:7860"
with urllib.request.urlopen(base + "/api/v1/auto_login", timeout=30) as r:
    token = json.loads(r.read())["access_token"]

def get(path):
    req = urllib.request.Request(base+path, headers={"Authorization": f"Bearer {token}", "Accept-Encoding":"identity"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
        if raw[:2]==b"\x1f\x8b":
            raw = gzip.decompress(raw)
        return json.loads(raw)

vars_ = get("/api/v1/variables/")
print("variables:")
for v in vars_:
    print(" -", {k:v.get(k) for k in v if k != "value"}, "value_len", len(str(v.get("value") or "")))

# list flows named Basic Prompting
flows = get("/api/v1/flows/")
basic = next(f for f in flows if f.get("name")=="Basic Prompting")
print("\nBasic Prompting nodes:")
for n in basic["data"]["nodes"]:
    node = n["data"]["node"]
    print(n["id"], n["data"].get("type"), "outputs", [(o.get("name"), o.get("selected"), o.get("hidden")) for o in node.get("outputs") or []])
    extra = {k: node.get(k) for k in node if "output" in k.lower() or k in ("selected","showNode")}
    print(" extra", extra)
print("edges:")
for e in basic["data"]["edges"]:
    sh = (e.get("data") or {}).get("sourceHandle") or {}
    th = (e.get("data") or {}).get("targetHandle") or {}
    print(e["source"], sh.get("name"), "->", e["target"], th.get("fieldName"))
