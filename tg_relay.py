"""Telegram relay: phone <-> NASA tool (chay song song voi loader.py/NASA.py).

Phone gui link octo -> tool giai -> Link Goc gui ve phone, bam la mo.
Chi dung thu vien chuan (urllib) - khong can pip.

Setup 1 lan:
  1. Nhac @BotFather tren Telegram -> /newbot -> lay BOT_TOKEN.
  2. Nhac bot vua tao 1 tin bat ky, mo tren trinh duyet:
       https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
     lay so "id" trong "chat" (vd 123456789).
  3. Copy tg_settings.example.json -> tg_settings.json, dien token + chat id.
  4. Chay tool:  python loader.py --threads 2
     Chay relay (cua so terminal khac):  python tg_relay.py

Su dung tren phone:
  - Gui link http... -> bot tra loi "Da nhan, dang giai..." 
  - Xong: bot gui Link Goc ve -> bam la mo.
  - /ping : kiem tra tool co song khong.
"""
import json
import os
import time
import urllib.request
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
SETTINGS = os.path.join(HERE, "tg_settings.json")
BRIDGE = "http://127.0.0.1:8080"


def load_settings():
    try:
        with open(SETTINGS, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def tg_api(token, method, data=None):
    url = f"https://api.telegram.org/bot{token}/{method}"
    body = json.dumps(data or {}).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    except Exception as e:
        return {"ok": False, "error": str(e)[:100]}


def bridge_post(path, data):
    req = urllib.request.Request(BRIDGE + path,
                                 data=json.dumps(data).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    except Exception:
        return None


def bridge_get(path):
    try:
        with urllib.request.urlopen(BRIDGE + path, timeout=10) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    except Exception:
        return None


def send(token, chat_id, text):
    tg_api(token, "sendMessage", {"chat_id": chat_id, "text": text,
                                  "disable_web_page_preview": True})


HELP = ("Gui link octo (http...) de giai.\n"
        "Xong tool gui Link Goc ve day, bam la mo.\n"
        "/ping - kiem tra tool")


def main():
    st = load_settings()
    token = (st.get("bot_token") or "").strip()
    allowed = set(st.get("allowed_ids") or [])
    port = st.get("bridge_port") or 8080
    global BRIDGE
    BRIDGE = f"http://127.0.0.1:{port}"
    if not token or not allowed:
        print("Thieu bot_token/allowed_ids trong tg_settings.json "
              "(copy tu tg_settings.example.json).")
        return 1
    me = tg_api(token, "getMe")
    if not me.get("ok"):
        print(f"Token sai/khong mang: {me}")
        return 1
    print(f"Relay chay: bot @{me['result'].get('username')} -> bridge {BRIDGE}")
    offset = 0
    pending = set()
    while True:
        try:
            up = tg_api(token, "getUpdates",
                        {"offset": offset, "timeout": 20,
                         "allowed_updates": ["message"]})
            for u in (up.get("result") or []):
                offset = max(offset, int(u.get("update_id", 0)) + 1)
                msg = u.get("message") or {}
                chat = msg.get("chat") or {}
                cid = int(chat.get("id", 0) or 0)
                text = (msg.get("text") or "").strip()
                if cid not in allowed or not text:
                    continue
                if text.startswith("/ping"):
                    stt = bridge_get("/api/status")
                    send(token, cid, "Tool song." if stt else "Tool CHUA chay (mo NASA truoc).")
                elif text.startswith("/start") or text.startswith("/help"):
                    send(token, cid, HELP)
                elif text.lower().startswith("http://") or text.lower().startswith("https://"):
                    r = bridge_post("/api/tg_submit", {"url": text, "chat_id": cid})
                    if r and r.get("ok"):
                        pending.add(cid)
                        send(token, cid, "Da nhan link, dang giai... xong gui ve day.")
                    else:
                        send(token, cid, "Tool CHUA chay (mo NASA truoc roi gui lai).")
                else:
                    send(token, cid, HELP)
            for cid in list(pending):
                r = bridge_get(f"/api/tg_result?chat_id={cid}")
                if not r:
                    continue
                if r.get("empty"):
                    continue
                pending.discard(cid)
                res = r.get("result") or {}
                if res.get("ok") and res.get("link"):
                    send(token, cid, f"Link Goc:\n{res['link']}")
                else:
                    send(token, cid, f"Giai that bai: {res.get('err') or '?'}")
        except KeyboardInterrupt:
            print("\nRelay dung.")
            return 0
        except Exception as e:
            print(f"Relay loi (tu chay lai): {e}"[:120])
            time.sleep(3)


if __name__ == "__main__":
    raise SystemExit(main())
