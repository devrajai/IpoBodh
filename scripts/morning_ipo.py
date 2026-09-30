#!/usr/bin/env python3
# morning_ipo.py - 9:15 AM IST: IPO digest + Pre-open breadth (EK message)
# Dev format (25/09): CLOSES TODAY / ALLOTMENT TODAY / LISTS TODAY / OPEN NOW /
# OPENING SOON + pre-open breadth. Data: ipo/data/ipo-data.json + data/preopen.json
import sys, os, datetime
sys.path.insert(0, 'scripts')
from tghelp import jload, send

now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
today = now.date()

IPOD = jload('ipo/data/ipo-data.json')
IPJ = jload('ipo/data/ipos.json')
PRE = jload('data/preopen.json')

# ipos.json lookup (allotment_date etc.)
BYNAME = {}
for it in (IPJ if isinstance(IPJ, list) else IPJ.get('data') or IPJ.get('ipos') or []):
    if isinstance(it, dict) and it.get('name'):
        BYNAME[it['name'].strip().lower()] = it

def pdate(s):
    s = str(s or '').strip()
    if not s or s.startswith('\u2014') or s == '-':
        return None
    for f in ('%d/%m/%y', '%d/%m/%Y', '%b %d, %Y', '%d %b %Y', '%Y-%m-%d', '%d-%m-%Y'):
        try:
            return datetime.datetime.strptime(s, f).date()
        except Exception:
            pass
    return None

def nm(x):
    n = str(x.get('name') or '?')
    for suf in (' (India) Limited', ' Limited', ' Ltd', ' Limited.'):
        if n.endswith(suf):
            n = n[:-len(suf)]
            break
    return n.strip()

def val(x, *keys):
    for k in keys:
        v = x.get(k)
        if v not in (None, '', '\u2014', '-'):
            return v
    return None

ipos = IPOD.get('ipos') or []
closes, allot, lists_, open_now, soon = [], [], [], [], []
for x in ipos:
    o = pdate(x.get('open'))
    c = pdate(x.get('close'))
    l = pdate(x.get('listing'))
    if c == today:
        closes.append(x)
    if l == today:
        lists_.append(x)
    else:
        jit = BYNAME.get(str(x.get('name') or '').strip().lower()) or {}
        ad = pdate(jit.get('allotment_date')) or pdate(jit.get('listing_date'))
        if ad == today:
            allot.append(x)
    if o and o <= today and (c is None or c >= today) and l != today:
        if c != today:
            open_now.append(x)
    if o and today < o <= today + datetime.timedelta(days=7) and x not in soon:
        soon.append(x)

def line(x, extra_open=False):
    parts = [nm(x)]
    lot = val(x, 'lot')
    sub = val(x, 'sub')
    gmp = val(x, 'gmp')
    if lot and lot != '\u2014':
        parts.append('lot %s' % lot)
    if sub and sub != '\u2014':
        parts.append('sub %s' % sub)
    if gmp and gmp not in ('\u2014',):
        parts.append('GMP %s*' % str(gmp).replace('\u20b9', ''))
    return '\u2022 ' + ' \u2022 '.join(parts)

L = []
L.append('\U0001F680 <b>ArthaSaar \u2014 IPO & Pre-open</b>')
L.append(now.strftime('%A, %d %b %Y'))
L.append('')

def sect(emo, title, arr):
    if not arr:
        return
    L.append('%s <b>%s</b>' % (emo, title))
    for x in arr[:6]:
        L.append(line(x))
    L.append('')

sect('\U0001F534', 'CLOSES TODAY (5 PM)', closes)
sect('\U0001F39F', 'ALLOTMENT TODAY', allot)
sect('\U0001F680', 'LISTS TODAY', lists_)
sect('\U0001F7E2', 'OPEN NOW', open_now)
if soon:
    L.append('\U0001F550 <b>OPENING SOON</b>')
    for x in soon[:6]:
        o = pdate(x.get('open'))
        ds = o.strftime('%d/%m') if o else '?'
        L.append('\u2022 %s \u2022 opens %s' % (nm(x), ds))
    L.append('')

gb = PRE.get('gainer_buckets') or {}
lb = PRE.get('loser_buckets') or {}
n = PRE.get('stocks')
if n or gb.get('up_ge_1pct') is not None:
    L.append('\u2600 <b>Pre-open (9:15 IST, %s stocks)</b>' % ('{:,}'.format(n) if n else 'NSE'))
    L.append('Breadth: %s up \u22651%% vs %s down \u22651%%' % (
        gb.get('up_ge_1pct', '-'), lb.get('down_ge_1pct', '-')))
    tg = (PRE.get('top20_gainers') or [])[:3]
    tl = (PRE.get('top20_losers') or [])[:3]
    if tg:
        L.append('\U0001F7E2 ' + ' \u2022 '.join(
            '%s %+.1f%%' % (g.get('symbol'), g.get('change_pct') or 0) for g in tg))
    if tl:
        L.append('\U0001F7E0 ' + ' \u2022 '.join(
            '%s %+.1f%%' % (g.get('symbol'), g.get('change_pct') or 0) for g in tl))
    L.append('')

L.append('*GMP unofficial hai - grey market se, verify karo. (ArthaSaar \U0001F60E)')
send('\n'.join(L))
