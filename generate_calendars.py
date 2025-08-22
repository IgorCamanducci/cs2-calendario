# -*- coding: utf-8 -*-
import re, json, uuid, time, sys
from datetime import datetime, timedelta, timezone
import requests
from bs4 import BeautifulSoup

CONFIG = "times.json"
OUTPUT = "cs2.ics"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/115.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache"
}
TZID = "America/Sao_Paulo"
HLTV = "https://www.hltv.org"

def now_local():
    return datetime.now().astimezone()

def ics_escape(s: str) -> str:
    return (s or "").replace("\\","\\\\").replace(";","\\;").replace(",","\\,").replace("\n","\\n")

def fold(line: str) -> str:
    if len(line) <= 74: return line
    out=[]; s=line
    while len(s)>74:
        out.append(s[:74]); s=" " + s[74:]
    out.append(s); return "\r\n".join(out)

def write_ics(events, updated):
    lines=[]
    lines.append("BEGIN:VCALENDAR")
    lines.append("PRODID:-//cs2-cal//Igor//BR")
    lines.append("VERSION:2.0")
    lines.append("CALSCALE:GREGORIAN")
    lines.append(f"X-WR-CALNAME:CS2 — Times BR")
    lines.append(f"X-WR-CALDESC:Atualizado: {updated.strftime('%Y-%m-%d %H:%M')} BRT")
    for ev in events:
        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{ev.get('uid', str(uuid.uuid4())+'@cs2')}")
        lines.append(f"DTSTAMP:{updated.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}")
        lines.append(f"DTSTART;TZID={TZID}:{ev['start'].strftime('%Y%m%dT%H%M%S')}")
        lines.append(f"DTEND;TZID={TZID}:{ev['end'].strftime('%Y%m%dT%H%M%S')}")
        if ev.get("summary"): lines.append(fold(f"SUMMARY:{ics_escape(ev['summary'])}"))
        if ev.get("description"): lines.append(fold(f"DESCRIPTION:{ics_escape(ev['description'])}"))
        lines.append("BEGIN:VALARM")
        lines.append("TRIGGER:-PT15M")
        lines.append("ACTION:DISPLAY")
        lines.append("DESCRIPTION:Lembrete de partida")
        lines.append("END:VALARM")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    content="\r\n".join(fold(l) for l in lines)+"\r\n"
    with open(OUTPUT,"w",encoding="utf-8",newline="\n") as f:
        f.write(content)

def http_get(url, tries=5, backoff=2.0):
    last_exc=None
    for i in range(tries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=25)
            if r.status_code == 200:
                return r.text
            last_exc = Exception(f"HTTP {r.status_code} for {url}")
        except Exception as e:
            last_exc = e
        time.sleep(backoff * (i+1))
    raise last_exc

def parse_upcoming(team_id: str):
    try:
        html = http_get(f"{HLTV}/matches?team={team_id}")
    except Exception:
        return []
    soup = BeautifulSoup(html, "lxml")
    events = []
    for a in soup.select('a[href^="/matches/"]'):
        ts = None
        tsel = a.select_one('[data-unix]') or a.find(attrs={"data-unix": True})
        if not tsel:
            up=a
            for _ in range(4):
                if hasattr(up, "find"):
                    tsel = up.find(attrs={"data-unix": True})
                    if tsel: break
                up = getattr(up, "parent", None)
        if tsel:
            try: ts = int(tsel.get("data-unix"))
            except: ts = None
        if not ts: 
            continue
        start = datetime.fromtimestamp(ts/1000, tz=timezone.utc).astimezone()
        tnames = [el.get_text(strip=True) for el in a.select('.matchTeamName, .matchTeam, .team') if el.get_text(strip=True)]
        if len(tnames) < 2:
            txt = a.get_text(" ", strip=True)
            m = re.search(r"(.+?)\s+vs\s+(.+?)\s", txt, re.I)
            if m: tnames=[m.group(1), m.group(2)]
        event_name = ""
        ev_el = a.select_one('.matchEventName, .event-name') or a.find(string=re.compile(r'(BLAST|ESL|IEM|CCT|Cup|Liga|League|Series)', re.I))
        if ev_el:
            event_name = getattr(ev_el, 'get_text', lambda **k: str(ev_el))().strip()
        summary = " vs ".join(tnames[:2]) if tnames else "Partida CS2"
        if event_name: summary += f" — {event_name}"
        events.append({
            "start": start,
            "end": start + timedelta(hours=2),
            "summary": summary,
            "description": f"Fonte: HLTV"
        })
    return events

def parse_results(team_id: str):
    try:
        html = http_get(f"{HLTV}/results?team={team_id}")
    except Exception:
        return []
    soup = BeautifulSoup(html, "lxml")
    events = []
    for a in soup.select('a[href^="/matches/"]'):
        ts = None
        tsel = a.select_one('[data-unix]') or a.find(attrs={"data-unix": True})
        if tsel:
            try: ts = int(tsel.get("data-unix"))
            except: ts = None
        tnames = [el.get_text(strip=True) for el in a.select('.team') if el.get_text(strip=True)]
        txt = a.get_text(" ", strip=True)
        m = re.search(r"(\d+)\s*-\s*(\d+)", txt)
        score = f"{m.group(1)}-{m.group(2)}" if m else ""
        match_name = " vs ".join(tnames[:2]) if len(tnames)>=2 else "Resultado CS2"
        evname = a.find(class_="event-name")
        event_name = evname.get_text(strip=True) if evname else ""
        summary = f"[Final] {match_name}"
        if score: summary += f" {score}"
        if event_name: summary += f" — {event_name}"
        if ts:
            start = datetime.fromtimestamp(ts/1000, tz=timezone.utc).astimezone()
        else:
            start = now_local() - timedelta(hours=1)
        events.append({
            "start": start,
            "end": start + timedelta(minutes=1),
            "summary": summary,
            "description": "Resultado recente"
        })
    return events

def main():
    try:
        with open(CONFIG,"r",encoding="utf-8") as f:
            cfg=json.load(f)
        teams = cfg.get("teams", [])
    except Exception:
        teams = []
    all_events = []
    for t in teams:
        tid = str(t.get("id","")).strip()
        if not tid: continue
        all_events.extend(parse_upcoming(tid))
        all_events.extend(parse_results(tid))
    if not all_events:
        t = now_local() + timedelta(minutes=2)
        all_events = [{
            "start": t, "end": t+timedelta(minutes=1),
            "summary": "[INFO] Calendário ativo — aguardando próximas partidas",
            "description": "Sem partidas confirmadas encontradas agora."
        }]
    all_events.sort(key=lambda e: e["start"])
    write_ics(all_events, now_local())

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        t = datetime.now().astimezone() + timedelta(minutes=2)
        write_ics([{
            "start": t, "end": t+timedelta(minutes=1),
            "summary": "[ERRO] Falha temporária na atualização — tente novamente",
            "description": str(e)[:140]
        }], datetime.now().astimezone())
        sys.exit(0)
