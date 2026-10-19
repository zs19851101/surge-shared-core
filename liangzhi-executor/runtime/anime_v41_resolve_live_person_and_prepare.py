#!/usr/bin/env python3
from pathlib import Path
import json, subprocess, requests, datetime, re

BASE=Path.home()/"Library/Application Support/LiangZhiLocalExecutor"
R=BASE/"reports"
SUM=R/"anime-v41-live-person-prep-summary.txt"
OUT=R/"anime-v41-live-person-prep.json"
BASELINE=R/"anime-series-identity-baseline.json"
EXPECT_TMDB="4055060"
ROLE_TARGETS={
 "seiya kanie":"Seiya Kanie",
 "shinichi izumi":"Shinichi Izumi",
 "shin ichi izumi":"Shinichi Izumi",
 "ryo":"Ryo",
 "ryou":"Ryo",
 "yuki anzai":"Yuki Anzai",
 "yuuki anzai":"Yuki Anzai",
 "koshi sugawara":"Koshi Sugawara",
 "koushi sugawara":"Koshi Sugawara",
}

def norm(s):
 s=str(s or '').lower().strip()
 s=re.sub(r'\([^)]*voice[^)]*\)','',s)
 s=re.sub(r'[^a-z0-9]+',' ',s)
 return ' '.join(s.split())

def finish(rep):
 R.mkdir(exist_ok=True)
 OUT.write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 lines=[
  "日漫 V4.1 live Person 身份桥解析",
  f"status: {rep.get('status')}",
  f"method: {rep.get('method','')}",
  f"person_id: {rep.get('person_id','')}",
  f"live_name: {rep.get('live_name','')}",
  f"series_id: {rep.get('series_id','')}",
  f"series_name: {rep.get('series_name','')}",
  f"role: {rep.get('role','')}",
  f"distinct_role_count: {rep.get('distinct_role_count',0)}",
  f"hit_count: {rep.get('hit_count',0)}",
  f"reason: {rep.get('reason','')}",
  "scope: read-only-live-identity-resolution",
  "emby_changes: none","network_changes: none","series_changes: none"
 ]
 SUM.write_text("\n".join(lines)+"\n",encoding="utf-8")
 print(SUM.read_text())

try:
 cfg=json.loads((BASE/"settings.json").read_text())
 server=cfg["emby_base"].rstrip("/")
 def js(expr):
  esc=expr.replace("\\","\\\\").replace('"','\\"')
  sc=('tell application "Google Chrome"\nrepeat with w in windows\nrepeat with t in tabs of w\nif (URL of t) contains "192.168.100.198:8096/web/" then\nreturn execute t javascript "'+esc+'"\nend if\nend repeat\nend repeat\nend tell')
  r=subprocess.run(["osascript","-e",sc],capture_output=True,text=True,timeout=15)
  if r.returncode: raise RuntimeError("chrome-token-read-failed")
  return r.stdout.strip()
 token=js("JSON.parse(localStorage.getItem('servercredentials3')).Servers[0].Users[0].AccessToken")
 h={"X-Emby-Token":token}

 # 1) Exact provider identity first.
 q=requests.get(f"{server}/Items",params={"Recursive":"true","IncludeItemTypes":"Person","Fields":"ProviderIds,ImageTags","StartIndex":0,"Limit":10000},headers=h,timeout=30)
 q.raise_for_status(); people=q.json().get("Items") or []
 exact=[]
 for p in people:
  ids={str(k).lower():str(v) for k,v in (p.get("ProviderIds") or {}).items() if v}
  if ids.get("tmdb")==EXPECT_TMDB: exact.append(p)
 if len(exact)==1:
  p=exact[0]
  finish({"time":datetime.datetime.now().isoformat(),"status":"PASS","method":"exact-tmdb","person_id":str(p.get("Id")),"live_name":p.get("Name"),"distinct_role_count":0,"hit_count":0})
  raise SystemExit(0)

 # 2) Scan ONLY the protected anime Series baseline (100 Series), not the whole server.
 baseline=json.loads(BASELINE.read_text(encoding="utf-8"))
 series_map=baseline.get("items") or {}
 by_pid={}
 scanned=0
 for sid,meta in series_map.items():
  rr=requests.get(f"{server}/Items",params={"ParentId":sid,"Recursive":"true","IncludeItemTypes":"Episode","Fields":"People,SeriesId,SeriesName","Limit":2000},headers=h,timeout=30)
  rr.raise_for_status(); eps=rr.json().get("Items") or []
  scanned += 1
  for e in eps:
   for pp in e.get("People") or []:
    pid=str(pp.get("Id") or '')
    if not pid: continue
    name=str(pp.get("Name") or '')
    role=str(pp.get("Role") or '')
    nrole=norm(role)
    name_exact=(norm(name)=="adam gibbs")
    role_exact=nrole in ROLE_TARGETS
    if not (name_exact or role_exact): continue
    ent=by_pid.setdefault(pid,{"person_id":pid,"live_name":name,"name_exact":False,"roles":set(),"series":set(),"evidence":[]})
    ent["name_exact"] = ent["name_exact"] or name_exact
    if role_exact: ent["roles"].add(ROLE_TARGETS[nrole])
    ent["series"].add(str(e.get("SeriesId") or sid))
    ent["evidence"].append({"series_id":str(e.get("SeriesId") or sid),"series_name":e.get("SeriesName") or meta.get("Name"),"episode_id":str(e.get("Id") or ''),"episode_name":e.get("Name"),"person_id":pid,"person_name":name,"role":role,"name_exact":name_exact,"role_exact":role_exact})

 ranked=[]
 for x in by_pid.values():
  x["roles"]=sorted(x["roles"]); x["series"]=sorted(x["series"])
  x["distinct_role_count"]=len(x["roles"]); x["hit_count"]=len(x["evidence"])
  ranked.append(x)
 ranked.sort(key=lambda x:(1 if x["name_exact"] else 0,x["distinct_role_count"],len(x["series"]),x["hit_count"]),reverse=True)

 # Prefer exact live display name if unique; otherwise require one uniquely top role candidate with >=2 distinct known roles.
 name_hits=[x for x in ranked if x["name_exact"]]
 if len(name_hits)==1:
  best=name_hits[0]; first=best["evidence"][0]
  finish({"time":datetime.datetime.now().isoformat(),"status":"PASS","method":"anime-baseline-name-exact","person_id":best["person_id"],"live_name":best["live_name"],"series_id":first["series_id"],"series_name":first["series_name"],"role":first["role"],"distinct_role_count":best["distinct_role_count"],"hit_count":best["hit_count"],"evidence":best["evidence"],"scanned_series_count":scanned,"provider_exact_count":len(exact)})
  raise SystemExit(0)

 if ranked:
  best=ranked[0]
  second=ranked[1] if len(ranked)>1 else None
  unique_top=(second is None or (best["distinct_role_count"],len(best["series"]),best["hit_count"]) > (second["distinct_role_count"],len(second["series"]),second["hit_count"]))
  if best["distinct_role_count"]>=2 and unique_top:
   first=best["evidence"][0]
   finish({"time":datetime.datetime.now().isoformat(),"status":"PASS","method":"anime-baseline-role-intersection","person_id":best["person_id"],"live_name":best["live_name"],"series_id":first["series_id"],"series_name":first["series_name"],"role":first["role"],"distinct_role_count":best["distinct_role_count"],"hit_count":best["hit_count"],"evidence":best["evidence"],"candidates":ranked[:10],"scanned_series_count":scanned,"provider_exact_count":len(exact)})
   raise SystemExit(0)

 finish({"time":datetime.datetime.now().isoformat(),"status":"PARTIAL","method":"anime-baseline-role-scan","reason":"no-unique-strong-live-person","distinct_role_count":ranked[0]["distinct_role_count"] if ranked else 0,"hit_count":ranked[0]["hit_count"] if ranked else 0,"candidates":ranked[:20],"scanned_series_count":scanned,"provider_exact_count":len(exact)})
 raise RuntimeError("no-unique-strong-live-person")
except SystemExit:
 raise
except Exception as e:
 if not OUT.exists() or OUT.stat().st_mtime < datetime.datetime.now().timestamp()-5:
  finish({"time":datetime.datetime.now().isoformat(),"status":"FAIL","reason":repr(e)})
 raise
