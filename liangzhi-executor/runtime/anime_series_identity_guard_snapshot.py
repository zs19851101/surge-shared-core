#!/usr/bin/env python3
import json, pathlib, subprocess, requests, datetime, sys

BASE=pathlib.Path.home()/"Library/Application Support/LiangZhiLocalExecutor"
CFG=json.loads((BASE/"settings.json").read_text(encoding="utf-8"))
B=CFG["emby_base"].rstrip("/")
LIB=str(CFG["anime_library_id"])
OUT=BASE/"reports"/"anime-series-identity-baseline.json"

def js(expr):
    esc=expr.replace("\\","\\\\").replace('"','\\"')
    sc=('tell application "Google Chrome"\nrepeat with w in windows\nrepeat with t in tabs of w\n'
        'if (URL of t) contains "192.168.100.198:8096/web/" then\nreturn execute t javascript "'+esc+'"\nend if\nend repeat\nend repeat\nend tell')
    r=subprocess.run(["osascript","-e",sc],capture_output=True,text=True,timeout=30)
    if r.returncode: raise RuntimeError(r.stderr[:300])
    return r.stdout.strip()

token=js("JSON.parse(localStorage.getItem('servercredentials3')).Servers[0].Users[0].AccessToken")
uid=js("JSON.parse(localStorage.getItem('servercredentials3')).Servers[0].UserId")
S=requests.Session(); S.headers.update({"X-Emby-Token":token})
q=S.get(f"{B}/Users/{uid}/Items",params={"ParentId":LIB,"IncludeItemTypes":"Series","Recursive":"true","Fields":"Overview,OriginalTitle,Path,ProviderIds,ProductionYear,PremiereDate,ParentId","Limit":1000},timeout=90)
q.raise_for_status()
items=q.json().get("Items",[])
protected={}
for x in items:
    protected[str(x["Id"])]= {
        "Name":x.get("Name"),
        "OriginalTitle":x.get("OriginalTitle"),
        "Overview":x.get("Overview"),
        "Path":x.get("Path"),
        "ProviderIds":x.get("ProviderIds") or {},
        "ProductionYear":x.get("ProductionYear"),
        "PremiereDate":x.get("PremiereDate"),
        "ParentId":x.get("ParentId")
    }
rep={"time":datetime.datetime.now().isoformat(),"series_count":len(protected),"protected_fields":["Name","OriginalTitle","Overview","Path","ProviderIds","ProductionYear","PremiereDate","ParentId"],"items":protected}
OUT.write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(f"Series identity baseline saved: {len(protected)}")
sys.exit(0)
