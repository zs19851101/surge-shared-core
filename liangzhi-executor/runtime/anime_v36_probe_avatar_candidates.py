#!/usr/bin/env python3
from pathlib import Path
import json, subprocess, requests, datetime
BASE=Path.home()/"Library/Application Support/LiangZhiLocalExecutor"
R=BASE/"reports"
SRC=R/"anime-v34-role-avatar-candidates.json"
OUT=R/"anime-v36-avatar-probe.json"
SUM=R/"anime-v36-avatar-probe-summary.txt"
try:
    if not SRC.exists(): raise RuntimeError("missing-v34-candidates")
    cfg=json.loads((BASE/"settings.json").read_text(encoding="utf-8")); B=cfg["emby_base"].rstrip("/")
    def js(expr):
        esc=expr.replace("\\","\\\\").replace('"','\\"')
        sc=('tell application "Google Chrome"\nrepeat with w in windows\nrepeat with t in tabs of w\nif (URL of t) contains "192.168.100.198:8096/web/" then\nreturn execute t javascript "'+esc+'"\nend if\nend repeat\nend repeat\nend tell')
        r=subprocess.run(["osascript","-e",sc],capture_output=True,text=True,timeout=30)
        if r.returncode: raise RuntimeError("chrome-token-read-failed")
        return r.stdout.strip()
    token=js("JSON.parse(localStorage.getItem('servercredentials3')).Servers[0].Users[0].AccessToken")
    S=requests.Session(); S.headers.update({"X-Emby-Token":token})
    d=json.loads(SRC.read_text(encoding="utf-8"))
    cands=[x for x in d.get("items",[]) if x.get("bucket")=="avatar_provider_backed"]
    rows=[]; with_remote=0; exact_one=0; errors=0
    for x in cands:
        pid=str(x.get("person_id") or "")
        try:
            r=S.get(f"{B}/Items/{pid}/RemoteImages",params={"Type":"Primary","StartIndex":0,"Limit":10},timeout=30)
            r.raise_for_status(); j=r.json(); imgs=j.get("Images") or []
            clean=[{"provider":i.get("ProviderName"),"type":i.get("Type"),"width":i.get("Width"),"height":i.get("Height")} for i in imgs]
            if clean: with_remote+=1
            if len(clean)==1: exact_one+=1
            rows.append({"person_id":pid,"name":x.get("name"),"provider_ids":x.get("provider_ids") or {},"remote_count":len(clean),"remote":clean})
        except Exception as e:
            errors+=1; rows.append({"person_id":pid,"name":x.get("name"),"error":type(e).__name__})
    rep={"time":datetime.datetime.now().isoformat(),"status":"PASS" if not errors else "PARTIAL","candidate_people":len(cands),"with_remote_primary":with_remote,"exactly_one_remote_primary":exact_one,"errors":errors,"rows":rows,"scope":"read-only-avatar-probe","emby_changes":"none","network_changes":"none","series_changes":"none"}
    OUT.write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    SUM.write_text("\n".join(["日漫 V3.6 缺头像可执行性探针",f"status: {rep['status']}",f"candidate_people: {len(cands)}",f"with_remote_primary: {with_remote}",f"exactly_one_remote_primary: {exact_one}",f"errors: {errors}","scope: read-only-avatar-probe","emby_changes: none","network_changes: none","series_changes: none"])+"\n",encoding="utf-8")
except Exception as e:
    SUM.write_text("日漫 V3.6 缺头像可执行性探针\nstatus: FAIL\nreason: "+type(e).__name__+"\nemby_changes: none\nnetwork_changes: none\nseries_changes: none\n",encoding="utf-8")
    raise
print(SUM.read_text(encoding="utf-8"))
