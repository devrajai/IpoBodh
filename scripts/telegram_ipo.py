#!/usr/bin/env python3
"""
TELEGRAM IPO — daily IPO Terminal digest.

Runs in the market-brain repo (uses its TG_TOKEN secret) and reads IPO data
from this repo (ArthaSaar, ipo/data/) via public raw URLs.

Recipients: TG_CHAT_ID_IPO secret if set (comma-separated list), else falls
back to TG_CHAT_ID. Put someone ONLY in TG_CHAT_ID_IPO -> they get only the
IPO digest. Put them ONLY in TG_CHAT_ID -> only market messages.
In both -> they get both.

Message (sent ~8:45 AM IST daily via .github/workflows/telegram-ipo.yml):
  - IPOs closing today / allotment & listing today
  - Currently open IPOs with GMP (unofficial) + subscription
  - IPOs opening in the next 5 days

Usage:
  python3 scripts/telegram_ipo.py          # send
  python3 scripts/telegram_ipo.py --dry    # print only
"""
import json
import os
import sys
import time
import datetime as dt
import re
from pathlib import Path
from urllib.request import Request, urlopen

RAW = "https://raw.githubusercontent.com/devrajai/ArthaSaar/main/ipo/data/"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
TIMEOUT = 25


def get_json(name):
    try:
        with urlopen(Request(RAW + name, headers={"User-Agent": UA}),
                     timeout=TIMEOUT) as r:
            return json.loads(r.read().decode())
    except Exception as e:  # noqa: BLE001
        print(f"WARN: could not load {name}: {e}")
        return None


def send(token, chat_id, text):
    for attempt in range(3):
        try:
            body = json.dumps({"chat_id": chat_id, "text": text,
                               "parse_mode": "HTML",
                               "disable_web_page_preview": True}).encode()
            req = Request("https://api.telegram.org/bot%s/sendMessage" % token,
                          data=body, headers={"Content-Type": "application/json",
                                              "User-Agent": UA})
            with urlopen(req, timeout=TIMEOUT) as r:
                ok = json.loads(r.read().decode()).get("ok")
            if ok:
                return True
        except Exception as e:  # noqa: BLE001
            print(f"WARN send attempt {attempt + 1} failed: {e}")
            time.sleep(3 * (attempt + 1))
    return False


def norm(name):
    return re.sub(r"limited|ltd|india|[^\w]", "", str(name or "").lower())


def d(s):
    """ISO date -> date or None"""
    if not s:
        return None
    try:
        return dt.date.fromisoformat(str(s)[:10])
    except Exception:  # noqa: BLE001
        return None


def main():
    dry = "--dry" in sys.argv
    ipos = get_json("ipos.json") or []
    notion = get_json("notion-data.json") or {}
    subs = get_json("subscriptions.json") or {}
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30))).date()

    # lookup maps
    nmap = {}
    for i in notion.get("ipos", []):
        nmap[norm(i.get("company"))] = i
    smap = {}
    for s in subs.get("data", []):
        smap[norm(s.get("name"))] = s

    def sub_of(name):
        s = smap.get(norm(name)) or {}
        t = s.get("total") or (nmap.get(norm(name)) or {}).get("subscription") or ""
        t = t.strip()
        return "" if t in ("\u2014", "-") else t

    def gmp_of(x):
        g = str(x.get("gmp") or "").strip()
        if not g or g in ("\u2014", "-"):
            return ""
        p = str(x.get("gmp_pct") or "").strip().rstrip("%")
        return g + (f" ({p}%)" if p and p not in ("\u2014", "-") else "")

    closing, listed_today, allot_today, open_now, opening_soon = [], [], [], [], []
    for x in ipos:
        if not isinstance(x, dict) or not x.get("name"):
            continue
        cd, ld, od = d(x.get("close_date")), d(x.get("listing_date")), d(x.get("open_date"))
        ad = d(x.get("allotment_date"))
        if x.get("status") == "open" and cd == today:
            closing.append(x)
        elif ld == today:
            listed_today.append(x)
        elif ad == today:
            allot_today.append(x)
        elif x.get("status") == "open":
            open_now.append(x)
        elif x.get("status") == "upcoming" and od and today <= od <= today + dt.timedelta(days=5):
            opening_soon.append(x)

    opening_soon.sort(key=lambda x: d(x.get("open_date")) or today)
    L = []

    def fmt(x, with_gmp=True):
        name = x.get("name", "")
        band = str(x.get("price_band") or "").strip()
        lot = str(x.get("lot_size") or "").strip()
        board = x.get("board") or ""
        tag = " SME" if str(board).lower() == "sme" else ""
        s = f"<b>{name}</b>{tag}"
        if band and band != "\u2014":
            s += f" • {band}"
        if lot and lot not in ("\u2014", ""):
            try:
                s += f" • lot {int(float(lot))}"
            except Exception:  # noqa: BLE001
                pass
        sub = sub_of(name)
        if sub:
            s += f" • sub {sub}"
        if with_gmp:
            g = gmp_of(x)
            if g:
                s += f" • GMP {g}*"
        return s

    if closing:
        L.append("🔴 <b>CLOSES TODAY (5 PM)</b>")
        for x in closing:
            L.append("• " + fmt(x))
        L.append("")
    if allot_today:
        L.append("🎫 <b>ALLOTMENT TODAY</b>")
        for x in allot_today:
            L.append("• " + fmt(x, with_gmp=False))
        L.append("")
    if listed_today:
        L.append("🚀 <b>LISTS TODAY</b>")
        for x in listed_today:
            L.append("• " + fmt(x, with_gmp=False))
        L.append("")
    if open_now:
        L.append("🟢 <b>OPEN NOW</b>")
        for x in open_now:
            cd = d(x.get("close_date"))
            ctail = f" • closes {cd.strftime('%d/%m')}" if cd else ""
            L.append("• " + fmt(x) + ctail)
        L.append("")
    if opening_soon:
        L.append("🕐 <b>OPENING SOON</b>")
        for x in opening_soon:
            od = d(x.get("open_date"))
            otail = f" • opens {od.strftime('%d/%m')}" if od else ""
            L.append("• " + fmt(x, with_gmp=False) + otail)
        L.append("")

    if not L:
        L = ["😊 No open or upcoming IPOs right now."]

    head = (f"📈 <b>IPO TERMINAL</b> — {today.strftime('%a %d %b %Y')}\n\n")
    foot = ("\n📊 Full terminal: https://arthasaar.vercel.app/ipo/"
            "\n<i>* GMP is unofficial market rate, not guaranteed</i>")
    text = head + "\n".join(L).rstrip() + foot

    # chunk at 3800 chars (telegram limit 4096)
    msgs, cur = [], ""
    for line in text.split("\n"):
        if len(cur) + len(line) + 1 > 3800:
            msgs.append(cur)
            cur = line
        else:
            cur = (cur + "\n" + line) if cur else line
    if cur:
        msgs.append(cur)

    if dry:
        for m in msgs:
            print(m)
        return

    token = os.environ.get("TG_TOKEN")
    # IPO recipients: TG_CHAT_ID_IPO if set (comma-separated), else TG_CHAT_ID.
    chats = [c.strip() for c in os.environ.get("TG_CHAT_ID_IPO",
             os.environ.get("TG_CHAT_ID", "")).split(",") if c.strip()]
    if not token or not chats:
        print("Missing TG_TOKEN / TG_CHAT_ID")
        sys.exit(1)
    ok = True
    for chat in chats:
        ok = all(send(token, chat, m) for m in msgs) and ok
    print("sent to %d chat(s)" % len(chats) if ok else "FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
