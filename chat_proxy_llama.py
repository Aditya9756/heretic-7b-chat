"""Thin chat proxy: same page + key auth as chat_server_7b.py, but the
model runs in llama-server (GGUF Q4_K_M + Trial 6 LoRA) on localhost:8080.
This process uses ~50 MB RAM; llama-server holds the ~4.3 GB model.

Env: CHAT_PORT (default 8765), CHAT_KEY (required), LLAMA_URL
(default http://127.0.0.1:8080).
"""
import json
import os
import time
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

PORT = int(os.environ.get("CHAT_PORT", "8765"))
KEY = os.environ["CHAT_KEY"]
LLAMA_URL = os.environ.get("LLAMA_URL", "http://127.0.0.1:8080")
TITLE = os.environ.get("MODEL_TITLE", "7B Model se baat karo")
MAX_TOKENS = 1000

PAGE = """<!DOCTYPE html>
<html lang="hi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>7B Model Chat</title>
<style>
body{font-family:sans-serif;max-width:640px;margin:0 auto;padding:12px;background:#111;color:#eee}
h2{margin:4px 0 12px} #log{margin-bottom:12px}
.msg{padding:10px 12px;border-radius:10px;margin:8px 0;white-space:pre-wrap;word-break:break-word}
.me{background:#1e4d7b;margin-left:40px}
.bot{background:#2a2a2a;margin-right:40px}
#row{display:flex;gap:8px}
#q{flex:1;padding:12px;border-radius:10px;border:1px solid #555;background:#222;color:#eee;font-size:16px}
#send{padding:12px 18px;border-radius:10px;border:0;background:#2e8b57;color:#fff;font-size:16px}
#send:disabled{opacity:.5}
small{color:#999}
</style></head><body>
<h2>🤖 7B Model se baat karo</h2>
<small>Jawab aane me thoda time lag sakta hai (CPU pe chal raha hai).</small>
<div id="log"></div>
<div id="row"><input id="q" placeholder="Apna sawaal likho..." autocomplete="off">
<button id="send" onclick="ask()">Bhejo</button></div>
<script>
const key = new URLSearchParams(location.search).get('key') || '';
const log = document.getElementById('log');
const q = document.getElementById('q');
const send = document.getElementById('send');
q.addEventListener('keydown', e => { if (e.key === 'Enter') ask(); });
function add(cls, text) {
  const d = document.createElement('div');
  d.className = 'msg ' + cls; d.textContent = text;
  log.appendChild(d); window.scrollTo(0, document.body.scrollHeight);
  return d;
}
async function ask() {
  const prompt = q.value.trim();
  if (!prompt) return;
  q.value = ''; send.disabled = true;
  add('me', prompt);
  const wait = add('bot', 'Soch raha hai...');
  try {
    const r = await fetch('/chat', {method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({prompt, key})});
    const t = await r.text();
    let j = null;
    try { j = JSON.parse(t); } catch (e) { j = null; }
    if (j && r.ok) { wait.textContent = j.answer || '(koi jawab nahi)'; }
    else if (j && j.error) { wait.textContent = 'Error: ' + j.error; }
    else { wait.textContent = 'Server abhi load ho raha hai ya band hai — 5-10 minute baad phir try karo. (Agar baar-baar ye aaye to mujhe bata dena.)'; }
  } catch (e) { wait.textContent = 'Server se connection nahi ho raha — 5-10 minute baad phir try karo.'; }
  send.disabled = false; q.focus();
}
</script></body></html>
"""


def ask_llama(prompt):
    payload = json.dumps({
        "model": "qwen2.5-7b-trial6",
        "messages": [
            {"role": "system", "content": "You are a helpful AI assistant. Give direct, complete and correct answers. When asked for code, output the full working code."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": MAX_TOKENS,
        "temperature": 0.7,
        "repetition_penalty": 1.1,
        "stream": False,
    }).encode()
    req = urllib.request.Request(
        LLAMA_URL + "/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=1800) as resp:
        data = json.loads(resp.read())
    ans = data["choices"][0]["message"]["content"]
    return ans.strip(), time.time() - t0


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[{time.strftime('%H:%M:%S')}] {fmt % args}", flush=True)

    def _send(self, code, body, ctype="application/json"):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _key_ok(self, key):
        return key and key == KEY

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send(200, json.dumps({"status": "ok"}))
            return
        if parsed.path in ("/", "/index.html"):
            qs = parse_qs(parsed.query)
            if not self._key_ok(qs.get("key", [""])[0]):
                self._send(403, "Galat key.", "text/plain")
                return
            page = PAGE.replace("7B Model se baat karo", TITLE).replace(
                "<title>7B Model Chat</title>", f"<title>{TITLE}</title>")
            self._send(200, page, "text/html; charset=utf-8")
            return
        self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        if urlparse(self.path).path != "/chat":
            self._send(404, json.dumps({"error": "not found"}))
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            self._send(400, json.dumps({"error": "bad json"}))
            return
        if not self._key_ok(body.get("key", "")):
            self._send(403, json.dumps({"error": "galat key"}))
            return
        prompt = (body.get("prompt") or "").strip()
        if not prompt:
            self._send(400, json.dumps({"error": "prompt khaali hai"}))
            return
        print(f"CHAT prompt: {prompt[:100]}", flush=True)
        try:
            ans, dt = ask_llama(prompt)
        except Exception as e:
            print(f"CHAT error: {e}", flush=True)
            self._send(500, json.dumps({"error": "model se jawab nahi mila, dobara try karo"}))
            return
        print(f"CHAT done in {dt:.1f}s", flush=True)
        self._send(200, json.dumps({"answer": ans, "seconds": round(dt, 1)}))


server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
print(f"PROXY-READY http://127.0.0.1:{PORT} -> {LLAMA_URL}", flush=True)
server.serve_forever()
