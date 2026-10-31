#!/usr/bin/env python3
"""Minimal Meshy image-to-3D helper (stdlib only).

Auth: in cloud sessions the proxy injects the key for api.meshy.ai, so no
key is needed. Locally, set MESHY_API_KEY and it is sent as a bearer token.
The key is never printed or stored.

  meshy.py balance
  meshy.py image-to-3d IMAGE [--no-texture] [--out DIR]   # create, wait, download GLB
  meshy.py status TASK_ID
  meshy.py text-to-image "PROMPT" [--out FILE] [--model nano-banana]   # clean reference image for image-to-3d
"""
import argparse, base64, json, mimetypes, os, sys, time, urllib.request, urllib.error

BASE = "https://api.meshy.ai/openapi/v1"

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
