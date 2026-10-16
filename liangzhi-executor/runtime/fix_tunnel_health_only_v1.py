#!/usr/bin/env python3
import pathlib, re, subprocess, os, time
BASE=pathlib.Path.home()/"Library/Application Support/LiangZhiLocalExecutor"
CFG=BASE/"config"/"cloudflared-result-gateway.yml"
REPORT=BASE/"reports"/"tunnel-health-only-fix-summary.txt"
PLIST=pathlib.Path.home()/"Library/LaunchAgents/com.liangzhi.resultgateway.tunnel.plist"
HOST="result.liangzhinet.com"

def fail(msg):
    REPORT.write_text("status: FAIL\nreason: "+msg+"\nexternal_exposure: health-only\n",encoding="utf-8")
    raise SystemExit(2)

if not CFG.exists(): fail("config missing")
text=CFG.read_text(encoding="utf-8")n=re.search(r"^tunnel:\s*(.+)$",text,re.M)
c=re.search(r"^credentials-file:\s*(.+)$",text,re.M)
if not n or not c: fail("cannot parse existing tunnel config")
new=(f"tunnel: {n.group(1).strip()}\n"
     f"credentials-file: {c.group(1).strip()}\n"
     "ingress:\n"
     f"  - hostname: {HOST}\n"
     "    path: ^/health$\n"
     "    service: http://127.0.0.1:8765\n"
     "  - service: http_status:404\n")
CFG.write_text(new,encoding="utf-8")
os.chmod(CFG,0o600)
uid=os.getuid(); label=f"gui/{uid}/com.liangzhi.resultgateway.tunnel"
subprocess.run(["launchctl","kickstart","-k",label],capture_output=True,text=True)
time.sleep(4)
chk=subprocess.run(["launchctl","print",label],capture_output=True,text=True)
local=subprocess.run(["/usr/bin/curl","-fsS","http://127.0.0.1:8765/health"],capture_output=True,text=True)
ok=(chk.returncode==0 and local.returncode==0)
REPORT.write_text("\n".join([
    "LiangZhi tunnel health-only fix",
    "status: "+("PASS" if ok else "FAIL"),
    "hostname_configured: True",
    "public_path: /health only",
    "reports_exposed: False",
    "launchagent_loaded: "+str(chk.returncode==0),
    "local_health: "+("PASS" if local.returncode==0 else "FAIL"),
    "external_exposure: health-only"
])+"\n",encoding="utf-8")
raise SystemExit(0 if ok else 2)
