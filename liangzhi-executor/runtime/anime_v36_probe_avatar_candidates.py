#!/usr/bin/env python3
from pathlib import Path
import json, subprocess, requests, datetime, concurrent.futures
BASE=Path.home()/"Library/Application Support/LiangZhiLocalExecutor"
R=BASE/"reports"; SRC=R/"anime-v34-role-avatar-candidates.json"; OUT=R/"anime-v36-avatar-probe.json"; SUM=R/"anime-v36-avatar-probe-summary.txt"
def finish(rep):
    OUT.write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    SUM.write_text("\n".join(["日漫 V3.6 缺头像可执行性探针",f"status: {rep.get('status')}",f"candidate_people: {rep.get('candidate_people',0)}",f"with_remote_primary: {rep.get('with_remote_primary',0)}",f"exactly_one_remote_primary: {rep.get('exactly_one_remote_primary',0)}",f"errors: {rep.get('errors',0)}","scope: read-only-avatar-probe","emby_changes: none","network_changes: none","series_changes: none"])+"\n",encoding="utf-8")
    print(SUM.read_text(encoding="utf-8"))
try:
    if not SRC.exists(): raise RuntimeError("missing-v34-candidates")
    cfg=json.loads((BASE/"settings.json").read_text(encoding="utf-8")); B=cfg["emby_base"].rstrip("/")
    def js(expr):
        esc=expr.replace("\\","\\\\").replace('"','\\"')
        sc=('tell application "Google Chrome"\nrepeat with w in windows\nrepeat with t in tabs of w\nif (URL of t) contains "192.168.100.198:8096/web/" then\nreturn execute t javascript "'+esc+'"\nend if\nend repeat\nend repeat\nend tell')
        r=subprocess.run(["osascript","-e",sc],capture_output=True,text=True,timeout=15)
        if r.returncode: raise RuntimeError("chrome-token-read-failed")
        return r.stdout.strip()
    token=js("JSON.parse(localStorage.getItem('servercredentials3')).Servers[0].Users[0].AccessToken")
    d=json.loads(SRC.read_text(encoding="utf-8")); cands=[x for x in d.get("items",[]) if x.get("bucket")=="avatar_provider_backed"]
    def probe(x):
        pid=str(x.get("person_id") or "")
        try:
            r=requests.get(f"{B}/Items/{pid}/RemoteImages",params={"Type":"Primary","StartIndex":0,"Limit":10},headers={"X-Emby-Token":token},timeout=8); r.raise_for_status(); imgs=(r.json().get("Images") or [])
            clean=[{"provider":i.get("ProviderName"),"type":i.get("Type"),"width":i.get("Width"),"height":i.get("Height")} for i in imgs]
            return {"person_id":pid,"name":x.get("name"),"provider_ids":x.get("provider_ids") or {},"remote_count":len(clean),"remote":clean}
        except Exception as e: return {"person_id":pid,"name":x.get("name"),"error":type(e).__name__}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex: rows=list(ex.map(probe,cands))
    errors=sum(1 for x in rows if x.get("error")); with_remote=sum(1 for x in rows if x.get("remote_count",0)>0); exact_one=sum(1 for x in rows if x.get("remote_count")==1)
    rep={"time":datetime.datetime.now().isoformat(),"status":"PASS" if not errors else "PARTIAL","candidate_people":len(cands),"with_remote_primary":with_remote,"exactly_one_remote_primary":exact_one,"errors":errors,"rows":rows,"scope":"read-only-avatar-probe","emby_changes":"none","network_changes":"none","series_changes":"none"}; finish(rep)
except Exception as e:
    finish({"time":datetime.datetime.now().isoformat(),"status":"FAIL","reason":type(e).__name__,"candidate_people":0,"with_remote_primary":0,"exactly_one_remote_primary":0,"errors":1,"rows":[],"scope":"read-only-avatar-probe","emby_changes":"none","network_changes":"none","series_changes":"none"})
    raise
