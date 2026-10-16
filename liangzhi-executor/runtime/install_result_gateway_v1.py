#!/usr/bin/env python3
import json, os, pathlib, plistlib, shutil, subprocess, sys, time, urllib.request, datetime
BASE=pathlib.Path.home()/"Library/Application Support/LiangZhiLocalExecutor"
GW=BASE/"gateway"
REPORTS=BASE/"reports"
GW.mkdir(parents=True,exist_ok=True); REPORTS.mkdir(parents=True,exist_ok=True)
SERVER=GW/"result_gateway_server.py"
PLIST=pathlib.Path.home()/"Library/LaunchAgents/com.liangzhi.resultgateway.plist"
LOG=GW/"gateway.log"
ERR=GW/"gateway.err.log"
PORT=8765
server_code=r'''#!/usr/bin/env python3
import json, pathlib, os, time, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
BASE=pathlib.Path.home()/"Library/Application Support/LiangZhiLocalExecutor"
REPORTS=BASE/"reports"
STATE_CANDIDATES=[BASE/"state.json",BASE/"runner-state.json",BASE/"runner_state.json"]
ALLOWED_SUFFIXES=("-summary.txt","-guard-result.json")
MAX_BYTES=65536

def safe_file(name):
    if not name or "/" in name or "\\" in name: return None
    if not name.endswith(ALLOWED_SUFFIXES): return None
    p=(REPORTS/name).resolve()
    try: p.relative_to(REPORTS.resolve())
    except Exception: return None
    return p if p.is_file() else None

def runner_state():
    for p in STATE_CANDIDATES:
        if p.is_file():
            try: return json.loads(p.read_text(encoding="utf-8"))
            except Exception: pass
    return {"status":"unknown"}

class H(BaseHTTPRequestHandler):
    server_version="LiangZhiResultGateway/1.0"
    def sendj(self,obj,code=200):
        b=(json.dumps(obj,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
        self.send_response(code); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        u=urllib.parse.urlparse(self.path)
        if u.path=="/health":
            return self.sendj({"ok":True,"service":"liangzhi-result-gateway","version":1,"time":time.time()})
        if u.path=="/status":
            return self.sendj({"ok":True,"runner":runner_state()})
        if u.path=="/reports":
            rows=[]
            for p in sorted(REPORTS.glob("*"),key=lambda x:x.stat().st_mtime if x.is_file() else 0,reverse=True):
                if p.is_file() and p.name.endswith(ALLOWED_SUFFIXES):
                    st=p.stat(); rows.append({"name":p.name,"size":st.st_size,"mtime":st.st_mtime})
                    if len(rows)>=50: break
            return self.sendj({"ok":True,"reports":rows})
        if u.path=="/report":
            q=urllib.parse.parse_qs(u.query); name=(q.get("name") or [""])[0]; p=safe_file(name)
            if not p: return self.sendj({"ok":False,"error":"not_allowed_or_missing"},404)
            data=p.read_bytes()[:MAX_BYTES]
            try: text=data.decode("utf-8")
            except Exception: return self.sendj({"ok":False,"error":"decode_failed"},415)
            return self.sendj({"ok":True,"name":p.name,"content":text})
        return self.sendj({"ok":False,"error":"not_found"},404)
    def log_message(self,fmt,*args):
        pass

if __name__=="__main__":
    ThreadingHTTPServer(("127.0.0.1",8765),H).serve_forever()
'''
SERVER.write_text(server_code,encoding="utf-8"); os.chmod(SERVER,0o700)
py=shutil.which("python3") or "/usr/bin/python3"
plist={"Label":"com.liangzhi.resultgateway","ProgramArguments":[py,str(SERVER)],"RunAtLoad":True,"KeepAlive":True,"StandardOutPath":str(LOG),"StandardErrorPath":str(ERR),"ProcessType":"Background","ThrottleInterval":10}
PLIST.parent.mkdir(parents=True,exist_ok=True)
with open(PLIST,"wb") as f: plistlib.dump(plist,f)
uid=os.getuid(); domain=f"gui/{uid}"; service=f"{domain}/com.liangzhi.resultgateway"
subprocess.run(["launchctl","bootout",service],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
r=subprocess.run(["launchctl","bootstrap",domain,str(PLIST)],capture_output=True,text=True)
if r.returncode!=0 and "already bootstrapped" not in (r.stderr or "").lower():
    print("WARN bootstrap:",r.stderr.strip()[:300])
subprocess.run(["launchctl","kickstart","-k",service],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
health=None
for _ in range(12):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health",timeout=2) as resp:
            health=json.loads(resp.read().decode("utf-8")); break
    except Exception: time.sleep(0.5)
cf=shutil.which("cloudflared")
brew=shutil.which("brew")
summary={"time":datetime.datetime.now().isoformat(),"gateway_local_url":f"http://127.0.0.1:{PORT}","local_health":bool(health and health.get("ok")),"launchagent":str(PLIST),"cloudflared_installed":bool(cf),"cloudflared_path":cf,"brew_available":bool(brew),"external_exposure":False,"mode":"read-only allowlisted summaries only"}
(REPORTS/"result-gateway-setup-summary.txt").write_text("\n".join(["LiangZhi Result Gateway V1",f"local_health: {'PASS' if summary['local_health'] else 'FAIL'}",f"local_url: {summary['gateway_local_url']}",f"cloudflared_installed: {summary['cloudflared_installed']}",f"brew_available: {summary['brew_available']}","external_exposure: False","mode: read-only allowlisted summaries only"]) + "\n",encoding="utf-8")
(REPORTS/"result-gateway-setup-result.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("Result Gateway V1 local_health:","PASS" if summary["local_health"] else "FAIL")
print("cloudflared_installed:",summary["cloudflared_installed"])
print("external_exposure: False")
if not summary["local_health"]: sys.exit(2)
