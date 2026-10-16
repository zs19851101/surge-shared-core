#!/usr/bin/env python3
import json, pathlib, subprocess, requests, datetime, sys
BASE=pathlib.Path.home()/"Library/Application Support/LiangZhiLocalExecutor"
CFG=json.loads((BASE/"settings.json").read_text(encoding="utf-8"))
B=CFG["emby_base"].rstrip("/"); LIB=str(CFG["anime_library_id"])
BASELINE=BASE/"reports"/"anime-series-identity-baseline.json"
OUT=BASE/"reports"/"anime-series-identity-guard-result.json"
PROTECTED=["Name","OriginalTitle","Overview","Path","ProviderIds","ProductionYear","PremiereDate","ParentId"]
if not BASELINE.exists(): print("ERROR: missing identity baseline"); sys.exit(2)
baseline=json.loads(BASELINE.read_text(encoding="utf-8")); expected=baseline.get("items",{})
def js(expr):
    esc=expr.replace("\\","\\\\").replace('"','\\"')
    sc=('tell application "Google Chrome"\nrepeat with w in windows\nrepeat with t in tabs of w\nif (URL of t) contains "192.168.100.198:8096/web/" then\nreturn execute t javascript "'+esc+'"\nend if\nend repeat\nend repeat\nend tell')
    r=subprocess.run(["osascript","-e",sc],capture_output=True,text=True,timeout=30)
    if r.returncode: raise RuntimeError(r.stderr[:300])
    return r.stdout.strip()
token=js("JSON.parse(localStorage.getItem('servercredentials3')).Servers[0].Users[0].AccessToken")
uid=js("JSON.parse(localStorage.getItem('servercredentials3')).Servers[0].UserId")
S=requests.Session(); S.headers.update({"X-Emby-Token":token})
q=S.get(f"{B}/Users/{uid}/Items",params={"ParentId":LIB,"IncludeItemTypes":"Series","Recursive":"true","Fields":"Overview,OriginalTitle,Path,ProviderIds,ProductionYear,PremiereDate,ParentId","Limit":1000},timeout=90)
q.raise_for_status(); current={str(x["Id"]):x for x in q.json().get("Items",[])}
def norm(v): return dict(sorted(v.items())) if isinstance(v,dict) else v
drift=[]
for sid,old in expected.items():
    cur=current.get(sid)
    if cur is None:
        drift.append({"id":sid,"fields":["Id"]}); continue
    fields=[f for f in PROTECTED if norm(cur.get(f))!=norm(old.get(f))]
    if fields: drift.append({"id":sid,"fields":fields})
rep={"time":datetime.datetime.now().isoformat(),"baseline_series_count":len(expected),"drift_count":len(drift),"drift":drift,"status":"PASS" if not drift else "FAIL"}
OUT.write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("Series identity guard:",rep["status"]); print("drift_count:",len(drift))
if drift:
    for x in drift[:20]: print(x["id"],",".join(x["fields"]))
sys.exit(0 if not drift else 2)
