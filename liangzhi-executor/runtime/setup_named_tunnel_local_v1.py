#!/usr/bin/env python3
import json, pathlib, subprocess, plistlib, time, os, sys
BASE=pathlib.Path.home()/"Library/Application Support/LiangZhiLocalExecutor"
BIN=BASE/"bin"/"cloudflared"
REPORTS=BASE/"reports"; REPORTS.mkdir(parents=True, exist_ok=True)
CFGDIR=BASE/"config"; CFGDIR.mkdir(parents=True, exist_ok=True)
OUT=REPORTS/"named-tunnel-local-summary.txt"
NAME="liangzhi-result-gateway"
if not BIN.exists():
    OUT.write_text("status: FAIL\nreason: cloudflared missing\nexternal_exposure: False\n",encoding="utf-8")
    raise SystemExit(2)
cert=pathlib.Path.home()/".cloudflared"/"cert.pem"
if not cert.exists():
    OUT.write_text("status: FAIL\nreason: cloudflare login certificate missing\nexternal_exposure: False\n",encoding="utf-8")
    raise SystemExit(2)

def run(args, check=True):
    p=subprocess.run([str(BIN),*args],capture_output=True,text=True,timeout=90)
    if check and p.returncode:
        raise RuntimeError((p.stderr or p.stdout)[-1200:])
    return p

# Reuse existing named tunnel when present; otherwise create one locally.
tunnel_id=None
p=run(["tunnel","list","--output","json"])
try:
    rows=json.loads(p.stdout or "[]")
except Exception:
    rows=[]
for r in rows:
    if r.get("name")==NAME and not r.get("deleted_at"):
        tunnel_id=str(r.get("id")); break
created=False
if not tunnel_id:
    p=run(["tunnel","create",NAME])
    created=True
    p2=run(["tunnel","list","--output","json"])
    rows=json.loads(p2.stdout or "[]")
    for r in rows:
        if r.get("name")==NAME and not r.get("deleted_at"):
            tunnel_id=str(r.get("id")); break
if not tunnel_id:
    OUT.write_text("status: FAIL\nreason: tunnel id unresolved\nexternal_exposure: False\n",encoding="utf-8")
    raise SystemExit(2)
cred=pathlib.Path.home()/".cloudflared"/(tunnel_id+".json")
if not cred.exists():
    OUT.write_text("status: FAIL\nreason: tunnel credential file missing\nexternal_exposure: False\n",encoding="utf-8")
    raise SystemExit(2)

config=CFGDIR/"cloudflared-result-gateway.yml"
config.write_text(
    f"tunnel: {tunnel_id}\n"
    f"credentials-file: {cred}\n"
    "ingress:\n"
    "  - service: http://127.0.0.1:8765\n"
    "  - service: http_status:404\n",
    encoding="utf-8"
)
os.chmod(config,0o600)

label="com.liangzhi.resultgateway.tunnel"
plist=pathlib.Path.home()/"Library"/"LaunchAgents"/(label+".plist")
plist.parent.mkdir(parents=True,exist_ok=True)
logdir=BASE/"logs"; logdir.mkdir(parents=True,exist_ok=True)
obj={
    "Label":label,
    "ProgramArguments":[str(BIN),"tunnel","--config",str(config),"run",tunnel_id],
    "RunAtLoad":True,
    "KeepAlive":True,
    "StandardOutPath":str(logdir/"cloudflared-result-gateway.out.log"),
    "StandardErrorPath":str(logdir/"cloudflared-result-gateway.err.log"),
    "ProcessType":"Background"
}
with plist.open("wb") as f: plistlib.dump(obj,f)
uid=os.getuid(); domain=f"gui/{uid}"
subprocess.run(["launchctl","bootout",domain,str(plist)],capture_output=True,text=True)
p=subprocess.run(["launchctl","bootstrap",domain,str(plist)],capture_output=True,text=True)
if p.returncode not in (0,):
    # If already loaded, kickstart is still enough.
    pass
subprocess.run(["launchctl","kickstart","-k",f"{domain}/{label}"],capture_output=True,text=True)
time.sleep(3)
# Verify local service is loaded. No DNS route/hostname is created in this task.
chk=subprocess.run(["launchctl","print",f"{domain}/{label}"],capture_output=True,text=True)
launchagent_ok=(chk.returncode==0)
lines=[
    "LiangZhi named tunnel local setup",
    "status: "+("PASS" if launchagent_ok else "FAIL"),
    f"tunnel_name: {NAME}",
    f"tunnel_created_now: {created}",
    f"launchagent_loaded: {launchagent_ok}",
    "origin: http://127.0.0.1:8765",
    "dns_route_created: False",
    "public_hostname_created: False",
    "external_exposure: False"
]
OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
print("\n".join(lines))
raise SystemExit(0 if launchagent_ok else 2)
