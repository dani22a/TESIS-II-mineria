import gzip, json, urllib.request

base = "http://127.0.0.1:7860"
with urllib.request.urlopen(base + "/api/v1/auto_login", timeout=30) as r:
    token = json.loads(r.read())["access_token"]

req = urllib.request.Request(base+"/api/v1/flows/", headers={"Authorization": f"Bearer {token}", "Accept-Encoding":"identity"})
with urllib.request.urlopen(req, timeout=30) as r:
    raw = r.read()
    if raw[:2]==b"\x1f\x8b":
        raw = gzip.decompress(raw)
    flows = json.loads(raw)
basic = next(f for f in flows if f.get("name")=="Basic Prompting")
lm = next(n for n in basic["data"]["nodes"] if n["data"].get("type")=="LanguageModelComponent")
print("model field:")
print(json.dumps(lm["data"]["node"]["template"]["model"], indent=2)[:4000])
print("\napi_key field:")
print(json.dumps(lm["data"]["node"]["template"]["api_key"], indent=2)[:1500])
