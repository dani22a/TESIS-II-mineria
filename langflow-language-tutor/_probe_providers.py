import gzip, json, urllib.request

base = "http://127.0.0.1:7860"
with urllib.request.urlopen(base + "/api/v1/auto_login", timeout=30) as r:
    token = json.loads(r.read())["access_token"]

def get(path):
    req = urllib.request.Request(base+path, headers={"Authorization": f"Bearer {token}", "Accept-Encoding":"identity"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            if raw[:2]==b"\x1f\x8b":
                raw = gzip.decompress(raw)
            data = json.loads(raw)
            print("OK", path, type(data).__name__, (list(data)[:15] if isinstance(data, dict) else len(data) if hasattr(data,"__len__") else data) )
            return data
    except Exception as e:
        print("ERR", path, e)

for path in [
    "/api/v1/model_providers",
    "/api/v1/providers",
    "/api/v1/config",
    "/api/v2/mcp",
    "/api/v1/store",
    "/api/v1/variables/",
]:
    get(path)
