import gzip, json, urllib.request

base = "http://127.0.0.1:7860"
with urllib.request.urlopen(base + "/api/v1/auto_login", timeout=30) as r:
    token = json.loads(r.read())["access_token"]

paths = [
    "/api/v1/models",
    "/api/v2/models",
    "/api/v1/llm",
    "/api/v1/llms",
    "/api/v1/settings",
    "/api/v2/settings",
    "/api/v1/users/whoami",
    "/openapi.json",
]
for path in paths:
    req = urllib.request.Request(base+path, headers={"Authorization": f"Bearer {token}", "Accept-Encoding":"identity"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            if raw[:2]==b"\x1f\x8b":
                raw = gzip.decompress(raw)
            print("OK", path, r.status, len(raw))
            if path.endswith("openapi.json"):
                spec = json.loads(raw)
                paths_ = spec.get("paths") or {}
                keys = [k for k in paths_ if any(s in k.lower() for s in ["model", "provider", "variable", "setting", "llm", "google"])]
                print(" matching paths:")
                for k in keys[:80]:
                    print("  ", k, list((paths_[k] or {}).keys()))
    except Exception as e:
        print("ERR", path, e)
