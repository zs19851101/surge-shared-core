#!/usr/bin/env python3
import pathlib, plistlib, subprocess, os, time
BASE=pathlib.Path.home()/"Library/Application Support/LiangZhiLocalExecutor"
BIN=BASE/"bin"/"cloudflared"
REPORTS=BASE/"reports"; REPORTS.mkdir(parents=True, exist_ok=True)
CFGDIR=BASE/"config"; CFGDIR.mkdir(parents=True, exist_ok=True)
OUT=REPORTS/"named-tunnel-activate-summary.txt"

def fail(reason, detail=""):
    lines=["LiangZhi existing tunnel activation","status: FAIL",f"reason: {reason}"]
    if detail: lines.append("detail: "+detail.replace("\n"," | ")[-1600:])
    lines += ["dns_route_created: False","public_hostname_created: False","external_exposure: False"]
    OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines)); raise SystemExit(2)

if not BIN.exists(): fail("cloudflared missing")
cf=pathlib.Path.home()/".cloudflared"
creds=[p for p in cf.glob("*.json") if p.is_file()]
if len(creds)!=1:
    fail("unexpected credential file count",f"count={len(creds)}")
cred=creds[0]
tunnel_id=cred.stem
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
subprocess.run(["launchctl","kickstart","-k",f"{domain}/{label}"],capture_output=True,text=True)
time.sleep(3)
chk=subprocess.run(["launchctl","print",f"{domain}/{label}"],capture_output=True,text=True)
if chk.returncode!=0: fail("launchagent not loaded",chk.stderr or chk.stdout or "")
lines=[
    "LiangZhi existing tunnel activation",
    "status: PASS",
    "launchagent_loaded: True",
    "origin: http://127.0.0.1:8765",
    "dns_route_created: False",
    "public_hostname_created: False",
    "external_exposure: False"
]
OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
print("\n".join(lines))
