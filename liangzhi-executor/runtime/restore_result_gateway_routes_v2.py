#!/usr/bin/env python3
from pathlib import Path
import os, subprocess, time
BASE=Path.home()/"Library/Application Support/LiangZhiLocalExecutor"
CFG=BASE/"config"/"cloudflared-result-gateway.yml"
OUT=BASE/"reports"/"result-gateway-restore-summary.txt"
if not CFG.exists():
    OUT.write_text("status: FAIL\nreason: config-missing\n",encoding="utf-8")
    raise SystemExit(2)
text=CFG.read_text(encoding="utf-8")
lines=text.splitlines()
head=[]
for line in lines:
    if line.strip()=="ingress:": break
    head.append(line)
new="\n".join(head)+"\ningress:\n  - hostname: result.liangzhinet.com\n    path: ^/health$\n    service: http://127.0.0.1:8765\n  - hostname: result.liangzhinet.com\n    path: ^/reports$\n    service: http://127.0.0.1:8765\n  - hostname: result.liangzhinet.com\n    path: ^/report$\n    service: http://127.0.0.1:8765\n  - service: http_status:404\n"
CFG.write_text(new,encoding="utf-8")
os.chmod(CFG,0o600)
label=f"gui/{os.getuid()}/com.liangzhi.resultgateway.tunnel"
subprocess.run(["launchctl","kickstart","-k",label],capture_output=True,text=True)
time.sleep(5)
checks=[]
for u in ["http://127.0.0.1:8765/health","https://result.liangzhinet.com/health","https://result.liangzhinet.com/reports"]:
    r=subprocess.run(["/usr/bin/curl","-fsS","--max-time","20",u],capture_output=True,text=True)
    checks.append(r.returncode==0)
OUT.write_text("status: "+("PASS" if all(checks) else "FAIL")+"\nlocal_health: "+str(checks[0]).lower()+"\npublic_health: "+str(checks[1]).lower()+"\npublic_reports: "+str(checks[2]).lower()+"\ndata_plane_changes: none\n",encoding="utf-8")
raise SystemExit(0 if all(checks) else 2)
