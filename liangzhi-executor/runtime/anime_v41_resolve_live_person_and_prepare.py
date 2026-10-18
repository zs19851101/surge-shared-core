#!/usr/bin/env python3
from pathlib import Path
import json, subprocess, requests, datetime, hashlib
BASE=Path.home()/"Library/Application Support/LiangZhiLocalExecutor"; R=BASE/"reports"; BAK=R/"backups"
SUM=R/"anime-v41-live-person-prep-summary.txt"; OUT=R/"anime-v41-live-person-prep.json"
EXPECT_TMDB="4055060"; IMAGE_URL="https://commons.wikimedia.org/wiki/Special:FilePath/Adam%20Gibbs%20%2855163669246%29.jpg"
def finish(rep):
 OUT.write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 SUM.write_text("\n".join(["日漫 V4.1 实时人物解析与写入准备",f"status: {rep.get('status')}",f"matched_count: {rep.get('matched_count',0)}",f"person_id: {rep.get('person_id','')}",f"live_name: {rep.get('live_name','')}",f"live_tmdb: {rep.get('live_tmdb','')}",f"primary_present: {rep.get('primary_present')}",f"image_bytes: {rep.get('image_bytes',0)}",f"image_sha256: {rep.get('image_sha256','')}",f"backup_written: {rep.get('backup_written',False)}",f"reason: {rep.get('reason','')}","scope: live-resolve-and-write-prep-only","emby_changes: none","network_changes: none","series_changes: none"])+"\n",encoding="utf-8"); print(SUM.read_text())
try:
 cfg=json.loads((BASE/"settings.json").read_text()); server=cfg["emby_base"].rstrip("/")
 def js(expr):
  esc=expr.replace("\\","\\\\").replace('"','\\"'); sc=('tell application "Google Chrome"\nrepeat with w in windows\nrepeat with t in tabs of w\nif (URL of t) contains "192.168.100.198:8096/web/" then\nreturn execute t javascript "'+esc+'"\nend if\nend repeat\nend repeat\nend tell'); r=subprocess.run(["osascript","-e",sc],capture_output=True,text=True,timeout=15)
  if r.returncode: raise RuntimeError("chrome-token-read-failed")
  return r.stdout.strip()
 token=js("JSON.parse(localStorage.getItem('servercredentials3')).Servers[0].Users[0].AccessToken"); h={"X-Emby-Token":token}
 q=requests.get(f"{server}/Items",params={"Recursive":"true","IncludeItemTypes":"Person","Fields":"ProviderIds,ImageTags","StartIndex":0,"Limit":10000},headers=h,timeout=30); q.raise_for_status(); items=q.json().get("Items") or []
 matches=[]
 for p in items:
  ids={str(k).lower():str(v) for k,v in (p.get("ProviderIds") or {}).items() if v}
  if ids.get("tmdb")==EXPECT_TMDB: matches.append(p)
 if len(matches)!=1: raise RuntimeError(f"tmdb-live-match-count:{len(matches)}")
 p=matches[0]; pid=str(p.get("Id")); primary=bool((p.get("ImageTags") or {}).get("Primary"))
 if primary: raise RuntimeError("primary-already-present")
 ir=requests.get(IMAGE_URL,timeout=30,allow_redirects=True,headers={"User-Agent":"LiangZhiNetwork/1.0"}); ir.raise_for_status(); data=ir.content; ctype=(ir.headers.get("content-type") or "").lower()
 if not ctype.startswith("image/") or len(data)<10000: raise RuntimeError("invalid-image-payload")
 sha=hashlib.sha256(data).hexdigest(); BAK.mkdir(exist_ok=True); ts=datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
 (BAK/f"anime-v41-person-{pid}-before-{ts}.json").write_text(json.dumps(p,ensure_ascii=False,indent=2)+"\n")
 img=BAK/f"anime-v41-person-{pid}-candidate-{ts}.jpg"; img.write_bytes(data)
 finish({"time":datetime.datetime.now().isoformat(),"status":"PASS","matched_count":1,"person_id":pid,"live_name":p.get("Name"),"live_tmdb":EXPECT_TMDB,"primary_present":False,"image_bytes":len(data),"image_sha256":sha,"candidate_path":str(img),"backup_written":True})
except Exception as e:
 finish({"time":datetime.datetime.now().isoformat(),"status":"FAIL","reason":repr(e),"backup_written":False}); raise
