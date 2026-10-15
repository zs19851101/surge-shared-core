#!/usr/bin/env python3
import json, pathlib, subprocess, requests, re, collections, datetime, sys

BASE = pathlib.Path.home() / "Library/Application Support/LiangZhiLocalExecutor"
CFG = json.loads((BASE / "settings.json").read_text(encoding="utf-8"))
B = CFG["emby_base"].rstrip("/")
LIB = str(CFG["anime_library_id"])
OUT = BASE / "reports" / "anime-v27-identity-audit.json"
SUM = BASE / "reports" / "anime-v27-identity-audit-summary.txt"
LAT = re.compile(r"[A-Za-z]")
KANA = re.compile(r"[\u3040-\u30ff]")
HAN = re.compile(r"[\u3400-\u9fff]")

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

def fetch(types,limit):
    q=S.get(f"{B}/Users/{uid}/Items",params={"ParentId":LIB,"IncludeItemTypes":types,"Recursive":"true","Fields":"People,ProviderIds,ImageTags,ProductionYear,PremiereDate,OriginalTitle,SeriesId","Limit":limit},timeout=120)
    q.raise_for_status(); return q.json().get("Items",[])

def get(i):
    q=S.get(f"{B}/Users/{uid}/Items/{i}",params={"Fields":"ProviderIds,ImageTags,Overview"},timeout=30)
    q.raise_for_status(); return q.json()

series=fetch("Series",1000); seasons=fetch("Season",5000); episodes=fetch("Episode",30000)
foreign={}; refs=collections.defaultdict(list)
for obj in series+seasons+episodes:
    for p in obj.get("People") or []:
        if p.get("Type")!="Actor" or not p.get("Id"): continue
        name=(p.get("Name") or "").strip(); pid=str(p["Id"])
        if name and (LAT.search(name) or KANA.search(name)):
            foreign.setdefault(pid,{"person_id":pid,"name":name,"provider_ids":{},"has_primary":False,"samples":[]})
            if len(foreign[pid]["samples"])<5:
                foreign[pid]["samples"].append({"item":obj.get("Name"),"role":p.get("Role"),"series_id":obj.get("SeriesId")})

for pid in list(foreign):
    try:
        po=get(pid)
        foreign[pid]["provider_ids"]=po.get("ProviderIds") or {}
        foreign[pid]["has_primary"]=bool((po.get("ImageTags") or {}).get("Primary"))
    except Exception as e:
        foreign[pid]["fetch_error"]=repr(e)

provider_counts=collections.Counter()
for x in foreign.values():
    for k,v in x.get("provider_ids",{}).items():
        if v: provider_counts[k]+=1

rep={
    "time":datetime.datetime.now().isoformat(),
    "remaining_foreign_persons":len(foreign),
    "provider_coverage":dict(provider_counts),
    "with_any_provider":sum(1 for x in foreign.values() if any((x.get("provider_ids") or {}).values())),
    "with_primary":sum(1 for x in foreign.values() if x.get("has_primary")),
    "without_primary":sum(1 for x in foreign.values() if not x.get("has_primary")),
    "people":sorted(foreign.values(),key=lambda x:(x.get("name") or ""))
}
OUT.write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
lines=[
    "日漫 V2.7 外文姓名证据审计（只读）",
    f"剩余外文姓名人物: {rep['remaining_foreign_persons']}",
    f"有任意 ProviderId: {rep['with_any_provider']}",
    f"有头像: {rep['with_primary']}",
    f"无头像: {rep['without_primary']}",
    "Provider覆盖: "+json.dumps(rep['provider_coverage'],ensure_ascii=False,sort_keys=True),
]
SUM.write_text("\n".join(lines)+"\n",encoding="utf-8")
print("\n".join(lines))
sys.exit(0)
