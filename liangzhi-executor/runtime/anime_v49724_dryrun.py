#!/usr/bin/env python3
import json, pathlib, subprocess, requests, datetime, sys

BASE=pathlib.Path.home()/"Library/Application Support/LiangZhiLocalExecutor"
R=BASE/"reports"
OUT=R/"anime-v49724-dryrun.json"
SUM=R/"anime-v49724-dryrun-summary.txt"
CFG=json.loads((BASE/"settings.json").read_text(encoding="utf-8"))
B=CFG["emby_base"].rstrip("/")
SERIES_ID="127761"
PERSON_ID="49724"
OLD_ROLE="Konno Erika (voice)"
NEW_ROLE="Konno Erika"
TARGETS=["127923","127927","127928","127936","127935","127930","127933","127941","127944","127932","127931","127934","127937","127929","127926","127924","127925","127938","127939","127946","127945","127942","127943","127940"]

def js(expr):
    esc=expr.replace("\\","\\\\").replace('"','\\"')
    sc=('tell application "Google Chrome"\nrepeat with w in windows\nrepeat with t in tabs of w\nif (URL of t) contains "192.168.100.198:8096/web/" then\nreturn execute t javascript "'+esc+'"\nend if\nend repeat\nend repeat\nend tell')
    r=subprocess.run(["osascript","-e",sc],capture_output=True,text=True,timeout=30)
    if r.returncode: raise RuntimeError("chrome-token-read-failed")
    return r.stdout.strip()

def finish(rep, code):
    R.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=[
        "49724 voice-cleanup dry-run",
        f"status: {rep.get('status')}",
        f"target_count: {rep.get('target_count',0)}",
        f"target_item_hits: {rep.get('target_item_hits',0)}",
        f"exact_old_role_hits: {rep.get('exact_old_role_hits',0)}",
        f"target_series_hits: {rep.get('target_series_hits',0)}",
        f"series_episode_count: {rep.get('series_episode_count',0)}",
        f"series_old_role_count: {rep.get('series_old_role_count',0)}",
        f"series_new_role_count: {rep.get('series_new_role_count',0)}",
        f"reason: {rep.get('reason','')}",
        "scope: read-only-dry-run",
        "emby_changes: none",
        "series_changes: none",
        "network_changes: none",
    ]
    SUM.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(SUM.read_text())
    sys.exit(code)

try:
    token=js("JSON.parse(localStorage.getItem('servercredentials3')).Servers[0].Users[0].AccessToken")
    S=requests.Session(); S.headers.update({"X-Emby-Token":token})
    details=[]; exact=0; series_hits=0; item_hits=0
    for iid in TARGETS:
        q=S.get(f"{B}/Items/{iid}",params={"Fields":"People,SeriesId,SeriesName"},timeout=20)
        q.raise_for_status(); x=q.json(); item_hits += 1
        if str(x.get("SeriesId") or "")==SERIES_ID: series_hits += 1
        matches=[]
        for p in x.get("People") or []:
            if str(p.get("Id") or "")==PERSON_ID:
                matches.append({"name":p.get("Name"),"role":p.get("Role"),"type":p.get("Type")})
                if str(p.get("Role") or "")==OLD_ROLE: exact += 1
        details.append({"item_id":iid,"series_id":str(x.get("SeriesId") or ""),"person_matches":matches})

    er=S.get(f"{B}/Items",params={"ParentId":SERIES_ID,"Recursive":"true","IncludeItemTypes":"Episode","Fields":"People,SeriesId","Limit":1000},timeout=60)
    er.raise_for_status(); eps=er.json().get("Items") or []
    old_count=0; new_count=0
    for e in eps:
        for p in e.get("People") or []:
            if str(p.get("Id") or "")==PERSON_ID:
                role=str(p.get("Role") or "")
                if role==OLD_ROLE: old_count += 1
                if role==NEW_ROLE: new_count += 1

    ok=(len(TARGETS)==24 and item_hits==24 and series_hits==24 and exact==24 and old_count==24 and new_count==24)
    rep={
        "time":datetime.datetime.now().isoformat(),
        "status":"PASS" if ok else "FAIL",
        "target_count":len(TARGETS),
        "target_item_hits":item_hits,
        "exact_old_role_hits":exact,
        "target_series_hits":series_hits,
        "series_episode_count":len(eps),
        "series_old_role_count":old_count,
        "series_new_role_count":new_count,
        "targets":details,
        "reason":"" if ok else "dry-run-count-mismatch"
    }
    finish(rep,0 if ok else 2)
except Exception as e:
    finish({"time":datetime.datetime.now().isoformat(),"status":"FAIL","reason":repr(e),"target_count":len(TARGETS)},2)
