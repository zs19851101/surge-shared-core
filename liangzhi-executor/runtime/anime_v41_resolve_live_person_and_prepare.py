#!/usr/bin/env python3
from pathlib import Path
import json, subprocess, requests, datetime, re

BASE=Path.home()/"Library/Application Support/LiangZhiLocalExecutor"
R=BASE/"reports"
SUM=R/"anime-v41-live-person-prep-summary.txt"
OUT=R/"anime-v41-live-person-prep.json"
EXPECT_TMDB="4055060"

TARGETS=[
 {"key":"amagi","terms":["甘城光辉游乐园","甘城辉煌乐园救世主","Amagi Brilliant Park","甘城ブリリアントパーク"],"roles":["Seiya Kanie"]},
 {"key":"parasyte","terms":["寄生兽","寄生獸","Parasyte","Kiseijuu","寄生獣"],"roles":["Shinichi Izumi","Shin'ichi Izumi"]},
 {"key":"7seeds","terms":["7SEEDS","7 Seeds"],"roles":["Ryo","Ryou"]},
 {"key":"devils-line","terms":["恶魔战线","惡魔戰線","Devils' Line","Devils Line"],"roles":["Yuki Anzai","Yuuki Anzai"]},
 {"key":"haikyuu","terms":["排球少年","Haikyuu","Haikyu"],"roles":["Koshi Sugawara","Koushi Sugawara"]},
]

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
  f"role: {rep.get('role','')}",
  f"distinct_work_count: {rep.get('distinct_work_count',0)}",
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

 # First try exact provider identity, but do not fail if stale.
 q=requests.get(f"{server}/Items",params={"Recursive":"true","IncludeItemTypes":"Person","Fields":"ProviderIds,ImageTags","StartIndex":0,"Limit":10000},headers=h,timeout=30)
 q.raise_for_status(); people=q.json().get("Items") or []
 exact=[]
 for p in people:
  ids={str(k).lower():str(v) for k,v in (p.get("ProviderIds") or {}).items() if v}
  if ids.get("tmdb")==EXPECT_TMDB: exact.append(p)
 if len(exact)==1:
  p=exact[0]
  finish({"time":datetime.datetime.now().isoformat(),"status":"PASS","method":"exact-tmdb","person_id":str(p.get("Id")),"live_name":p.get("Name"),"live_tmdb":EXPECT_TMDB,"distinct_work_count":0,"evidence":[]})
  raise SystemExit(0)

 # Stale-provider fallback: identify the same live Person by repeated known roles across known works.
 by_pid={}
 scanned_series=[]
 seen_series=set()
 for t in TARGETS:
  role_norms={norm(x) for x in t["roles"]}
  found=[]
  for term in t["terms"]:
   rr=requests.get(f"{server}/Items",params={"Recursive":"true","IncludeItemTypes":"Series","SearchTerm":term,"Fields":"OriginalTitle,ProviderIds","Limit":20},headers=h,timeout=20)
   rr.raise_for_status()
   for s in rr.json().get("Items") or []:
    sid=str(s.get("Id") or '')
    if sid and sid not in [x[0] for x in found]: found.append((sid,s.get("Name"),s.get("OriginalTitle")))
  for sid,sname,orig in found:
   if sid in seen_series: continue
   seen_series.add(sid)
   er=requests.get(f"{server}/Items",params={"ParentId":sid,"Recursive":"true","IncludeItemTypes":"Episode","Fields":"People,SeriesId,SeriesName","Limit":1000},headers=h,timeout=30)
   er.raise_for_status(); eps=er.json().get("Items") or []
   scanned_series.append({"target":t["key"],"series_id":sid,"name":sname,"original_title":orig,"episode_count":len(eps)})
   for e in eps:
    for pp in e.get("People") or []:
     role=str(pp.get("Role") or '')
     if norm(role) in role_norms:
      pid=str(pp.get("Id") or '')
      if not pid: continue
      ent=by_pid.setdefault(pid,{"person_id":pid,"live_name":pp.get("Name"),"works":{},"evidence":[]})
      ent["works"][t["key"]]=sid
      ent["evidence"].append({"target":t["key"],"series_id":sid,"series_name":sname,"episode_id":str(e.get("Id") or ''),"episode_name":e.get("Name"),"role":role})

 ranked=sorted(by_pid.values(),key=lambda x:(len(x["works"]),len(x["evidence"])),reverse=True)
 if not ranked:
  finish({"time":datetime.datetime.now().isoformat(),"status":"FAIL","method":"cross-series-role-intersection","reason":"no-role-candidates","scanned_series":scanned_series,"provider_exact_count":len(exact)})
  raise RuntimeError("no-role-candidates")
 best=ranked[0]; best_count=len(best["works"])
 tied=[x for x in ranked if len(x["works"])==best_count]
 if best_count<2 or len(tied)!=1:
  finish({"time":datetime.datetime.now().isoformat(),"status":"PARTIAL","method":"cross-series-role-intersection","reason":f"non-unique-or-weak:best_work_count={best_count},tied={len(tied)}","provider_exact_count":len(exact),"candidates":ranked[:10],"scanned_series":scanned_series})
  raise RuntimeError("non-unique-or-weak-cross-series-match")

 first=best["evidence"][0]
 finish({"time":datetime.datetime.now().isoformat(),"status":"PASS","method":"cross-series-role-intersection","person_id":best["person_id"],"live_name":best.get("live_name"),"series_id":first.get("series_id"),"role":first.get("role"),"distinct_work_count":best_count,"works":best["works"],"evidence":best["evidence"],"provider_exact_count":len(exact),"scanned_series":scanned_series})
except SystemExit:
 raise
except Exception as e:
 if not OUT.exists() or OUT.stat().st_mtime < datetime.datetime.now().timestamp()-5:
  finish({"time":datetime.datetime.now().isoformat(),"status":"FAIL","reason":repr(e)})
 raise
