#!/usr/bin/env python3
"""Minimal Meshy image-to-3D helper (stdlib only).

Auth: in cloud sessions the proxy injects the key for api.meshy.ai, so no
key is needed. Locally, set MESHY_API_KEY and it is sent as a bearer token.
The key is never printed or stored.

  meshy.py balance
  meshy.py image-to-3d IMAGE [--no-texture] [--out DIR]   # create, wait, download GLB
  meshy.py status TASK_ID
  meshy.py text-to-image "PROMPT" [--out FILE] [--model nano-banana]   # clean reference image for image-to-3d
  meshy.py image-to-image PROMPT_FILE --ref IMG [--ref IMG ...] --cls CLASS --stage STAGE [--multi-view] [--out DIR] [--confirm]
      # 1 to 5 reference images + prompt -> new image(s). Prints the price and balance first; spends only with --confirm.
      # Every task is archived under DIR (images, source.json) and logged in the ledger (see LEDGER below).
  meshy.py multi-image-to-3d IMG [IMG ...] --cls CLASS --out DIR --gate TEXT [--texture] [--confirm]
      # 1 to 4 views, FIRST = front. Mesh only by default (20 credits); --texture adds PBR texture in one task (30).
  meshy.py retexture TASK_ID IMG [IMG ...] --cls CLASS --out DIR --gate TEXT [--confirm]   # texture an existing mesh (10 credits)
"""
import argparse, base64, json, mimetypes, os, sys, time, urllib.request, urllib.error

BASE = "https://api.meshy.ai/openapi/v1"
# Meshy keeps API results for 3 days, so every task is downloaded and logged the day it runs.
LEDGER = os.environ.get("MESHY_LEDGER", "/mnt/project-files/meshy-sources/ledger.json")
I2I_PRICE = {"nano-banana": 3, "nano-banana-2": 6, "nano-banana-2-lite": 3, "nano-banana-2-1": 4, "nano-banana-pro": 9}

def ledger_add(row):
    rows = json.load(open(LEDGER)) if os.path.exists(LEDGER) else []
    rows.append(row)
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    json.dump(rows, open(LEDGER, "w"), indent=1)

def call(method, path, body=None):
    headers = {"Content-Type": "application/json"}
    key = os.environ.get("MESHY_API_KEY")
    if key:
        headers["Authorization"] = f"Bearer {key}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode()[:500]}")

def data_uri(path):
    mime = mimetypes.guess_type(path)[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(open(path, "rb").read()).decode()

def download(url, dest):
    urllib.request.urlretrieve(url, dest)
    print("saved", dest)

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("balance")
    s = sub.add_parser("status"); s.add_argument("task")
    t = sub.add_parser("text-to-image")
    t.add_argument("prompt"); t.add_argument("--out", default="ref.png"); t.add_argument("--model", default="nano-banana")
    i = sub.add_parser("image-to-image")
    i.add_argument("prompt_file"); i.add_argument("--ref", action="append", required=True)
    i.add_argument("--cls", required=True); i.add_argument("--stage", required=True)
    i.add_argument("--multi-view", action="store_true"); i.add_argument("--model", default="nano-banana")
    i.add_argument("--out", required=True); i.add_argument("--confirm", action="store_true")
    i.add_argument("--gate", default="", help="where Luke approved the input (thread message), for the ledger")
    m = sub.add_parser("multi-image-to-3d")
    m.add_argument("images", nargs="+"); m.add_argument("--cls", required=True); m.add_argument("--out", required=True)
    m.add_argument("--gate", required=True); m.add_argument("--texture", action="store_true"); m.add_argument("--confirm", action="store_true")
    r = sub.add_parser("retexture")
    r.add_argument("task"); r.add_argument("images", nargs="+", help="1-4 views, first = front"); r.add_argument("--cls", required=True); r.add_argument("--out", required=True)
    r.add_argument("--gate", required=True); r.add_argument("--confirm", action="store_true")
    g = sub.add_parser("image-to-3d")
    g.add_argument("image"); g.add_argument("--out", default="renders/meshy")
    g.add_argument("--no-texture", action="store_true")
    g.add_argument("--model", default="latest")
    a = ap.parse_args()
    if a.cmd == "balance":
        print(call("GET", "/balance"))
    elif a.cmd == "text-to-image":
        tid = call("POST", "/text-to-image", {"ai_model": a.model, "prompt": a.prompt})["result"]
        while True:
            t = call("GET", f"/text-to-image/{tid}")
            if t["status"] in ("SUCCEEDED", "FAILED", "CANCELED"):
                break
            time.sleep(4)
        if t["status"] != "SUCCEEDED":
            sys.exit(f"text-to-image {t['status']}: {t.get('task_error')}")
        download(t["image_urls"][0], a.out)
    elif a.cmd == "image-to-image":
        prompt = open(a.prompt_file).read().strip()
        price = I2I_PRICE[a.model]
        bal = call("GET", "/balance")["balance"]
        print(f"image-to-image {a.model}: {price} credits, balance {bal}, {len(a.ref)} refs")
        if not a.confirm:
            sys.exit("not spending without --confirm")
        body = {"ai_model": a.model, "prompt": prompt, "reference_image_urls": [data_uri(r) for r in a.ref]}
        if a.multi_view:
            body["generate_multi_view"] = True
        tid = call("POST", "/image-to-image", body)["result"]
        print("task", tid, flush=True)
        while True:
            t = call("GET", f"/image-to-image/{tid}")
            if t["status"] in ("SUCCEEDED", "FAILED", "CANCELED"):
                break
            time.sleep(4)
        if t["status"] != "SUCCEEDED":
            sys.exit(f"image-to-image {t['status']}: {t.get('task_error')}")
        d = os.path.join(a.out, tid)
        os.makedirs(d, exist_ok=True)
        for n, u in enumerate(t["image_urls"]):
            download(u, os.path.join(d, f"image-{n}.png"))
        json.dump({"task": tid, "prompt": prompt, "refs": a.ref, "model": a.model, "multi_view": a.multi_view,
                   "stage": a.stage, "cls": a.cls}, open(os.path.join(d, "source.json"), "w"), indent=1)
        ledger_add({"cls": a.cls, "stage": a.stage, "task": tid, "kind": "image-to-image", "credits": price,
                    "gate": a.gate, "dir": d, "date": time.strftime("%Y-%m-%d")})
        print("balance now", call("GET", "/balance")["balance"])
    elif a.cmd in ("multi-image-to-3d", "retexture"):
        if a.cmd == "multi-image-to-3d":
            path, price = "/multi-image-to-3d", 30 if a.texture else 20
            body = {"image_urls": [data_uri(i) for i in a.images], "ai_model": "latest",
                    "should_texture": a.texture, "enable_pbr": a.texture}
        else:
            path, price = "/retexture", 10
            body = {"input_task_id": a.task, "ai_model": "meshy-7", "enable_pbr": True, "enable_original_uv": True,
                    "multiview_image_urls": [data_uri(i) for i in a.images]}
        bal = call("GET", "/balance")["balance"]
        print(f"{a.cmd}: {price} credits, balance {bal}, gate: {a.gate}")
        if not a.confirm:
            sys.exit("not spending without --confirm")
        tid = call("POST", path, body)["result"]
        print("task", tid, flush=True)
        while True:
            t = call("GET", f"{path}/{tid}")
            print(t["status"], t.get("progress"), flush=True)
            if t["status"] in ("SUCCEEDED", "FAILED", "CANCELED"):
                break
            time.sleep(10)
        d = os.path.join(a.out, tid)
        os.makedirs(d, exist_ok=True)
        json.dump(t, open(os.path.join(d, "task.json"), "w"), indent=1)
        if t["status"] != "SUCCEEDED":
            sys.exit(json.dumps(t.get("task_error")))
        download(t["model_urls"]["glb"], os.path.join(d, "model.glb"))
        if t.get("thumbnail_url"):
            download(t["thumbnail_url"], os.path.join(d, "thumb.png"))
        ledger_add({"cls": a.cls, "stage": a.cmd, "task": tid, "kind": a.cmd, "credits": price,
                    "gate": a.gate, "dir": d, "date": time.strftime("%Y-%m-%d")})
        print("balance now", call("GET", "/balance")["balance"])
    elif a.cmd == "status":
        print(call("GET", f"/image-to-3d/{a.task}"))
    else:
        tid = call("POST", "/image-to-3d", {"image_url": data_uri(a.image), "ai_model": a.model,
              "should_texture": not a.no_texture, "enable_pbr": not a.no_texture})["result"]
        print("task", tid)
        while True:
            t = call("GET", f"/image-to-3d/{tid}")
            print(t["status"], t.get("progress"), flush=True)
            if t["status"] in ("SUCCEEDED", "FAILED", "CANCELED"):
                break
            time.sleep(10)
        if t["status"] != "SUCCEEDED":
            sys.exit(json.dumps(t.get("task_error")))
        os.makedirs(a.out, exist_ok=True)
        download(t["model_urls"]["glb"], os.path.join(a.out, f"{tid}.glb"))
        if t.get("thumbnail_url"):
            download(t["thumbnail_url"], os.path.join(a.out, f"{tid}-thumb.png"))

if __name__ == "__main__":
    main()
