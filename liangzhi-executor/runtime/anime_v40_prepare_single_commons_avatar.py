#!/usr/bin/env python3
from pathlib import Path
import json, subprocess, requests, datetime, hashlib
BASE=Path.home()/"Library/Application Support/LiangZhiLocalExecutor"; R=BASE/"reports"; BAK=R/"backups"
SUM=R/"anime-v40-single-avatar-prep-summary.txt"; OUT=R/"anime-v40-single-avatar-prep.json"
PID="80840"; EXPECT_TMDB="4055060"; IMAGE_URL="https://commons.wikimedia.org/wiki/Special:FilePath/Adam%20Gibbs%20%2855163669246%29.jpg"

def finish(rep):
    OUT.write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    SUM.write_text("\n".join([
        "日漫 V4.0 单一头像写入准备",
        f"status: {rep.get('status')}",f"person_id: {PID}",f"live_name: {rep.get('live_name','')}",
        f"live_tmdb: {rep.get('live_tmdb','')}",f"primary_present: {rep.get('primary_present')}",
        f"image_bytes: {rep.get('image_bytes',0)}",f"image_sha256: {rep.get('image_sha256','')}",
        f"backup_written: {rep.get('backup_written',False)}",f"reason: {rep.get('reason','')}",
        "scope: write-prep-only","emby_changes: none","network_changes: none","series_changes: none"
    ])+"\n",encoding="utf-8"); print(SUM.read_text(encoding="utf-8"))
try:
    cfg=json.loads((BASE/"settings.json").read_text(encoding="utf-8")); server=cfg["emby_base"].rstrip("/")
    def js(expr):
        esc=expr.replace("\\","\\\\").replace('"','\\"')
        sc=('tell application "Google Chrome"\nrepeat with w in windows\nrepeat with t in tabs of w\nif (URL of t) contains "192.168.100.198:8096/web/" then\nreturn execute t javascript "'+esc+'"\nend if\nend repeat\nend repeat\nend tell')
        r=subprocess.run(["osascript","-e",sc],capture_output=True,text=True,timeout=15)
        if r.returncode: raise RuntimeError("chrome-token-read-failed")
        return r.stdout.strip()
    token=js("JSON.parse(localStorage.getItem('servercredentials3')).Servers[0].Users[0].AccessToken")
    h={"X-Emby-Token":token}
    p=requests.get(f"{server}/Items/{PID}",headers=h,timeout=10); p.raise_for_status(); person=p.json()
    ids={str(k).lower():str(v) for k,v in (person.get("ProviderIds") or {}).items() if v}
    live_tmdb=ids.get("tmdb","")
    primary_present=bool((person.get("ImageTags") or {}).get("Primary"))
    if live_tmdb!=EXPECT_TMDB: raise RuntimeError(f"tmdb-mismatch:{live_tmdb}")
    if primary_present: raise RuntimeError("primary-already-present")
    ir=requests.get(IMAGE_URL,timeout=30,allow_redirects=True,headers={"User-Agent":"LiangZhiNetwork/1.0"}); ir.raise_for_status(); data=ir.content
    ctype=(ir.headers.get("content-type") or "").lower()
    if not ctype.startswith("image/") or len(data)<10000: raise RuntimeError("invalid-image-payload")
    sha=hashlib.sha256(data).hexdigest(); BAK.mkdir(exist_ok=True)
    ts=datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    (BAK/f"anime-v40-person-{PID}-before-{ts}.json").write_text(json.dumps(person,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    img=BAK/f"anime-v40-person-{PID}-candidate-{ts}.jpg"; img.write_bytes(data)
    finish({"time":datetime.datetime.now().isoformat(),"status":"PASS","live_name":person.get("Name"),"live_tmdb":live_tmdb,"primary_present":primary_present,"image_bytes":len(data),"image_sha256":sha,"candidate_path":str(img),"backup_written":True})
except Exception as e:
    finish({"time":datetime.datetime.now().isoformat(),"status":"FAIL","reason":repr(e),"backup_written":False}); raise
