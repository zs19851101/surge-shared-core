#!/usr/bin/env python3
import json, pathlib, subprocess, plistlib, time, os, traceback
BASE=pathlib.Path.home()/"Library/Application Support/LiangZhiLocalExecutor"
BIN=BASE/"bin"/"cloudflared"
REPORTS=BASE/"reports"; REPORTS.mkdir(parents=True, exist_ok=True)
CFGDIR=BASE/"config"; CFGDIR.mkdir(parents=True, exist_ok=True)
OUT=REPORTS/"named-tunnel-local-summary.txt"
NAME="liangzhi-result-gateway"

def fail(reason, detail=""):
    lines=["LiangZhi named tunnel local setup","status: FAIL",f"reason: {reason}"]
    if detail:
        lines.append("detail: "+detail.replace("\n"," | ")[-1800:])
    lines += ["dns_route_created: False","public_hostname_created: False","external_exposure: False"]
    OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines))
    raise SystemExit(2)

def run(args, check=True, timeout=90):
    p=subprocess.run([str(BIN),*args],capture_output=True,text=True,timeout=timeout)
    if check and p.returncode:
        fail("cloudflared command failed", "args="+" ".join(args)+"; rc="+str(p.returncode)+"; "+((p.stderr or p.stdout) or ""))
    return p

try:
    if not BIN.exists(): fail("cloudflared missing")
    cert=pathlib.Path.home()/".cloudflared"/"cert.pem"
    if not cert.exists(): fail("cloudflare login certificate missing")

    tunnel_id=None
    p=run(["tunnel","list","--output","json"])
    try: rows=json.loads(p.stdout or "[]")
    except Exception as e: fail("cannot parse tunnel list",repr(e)+"; stdout="+(p.stdout or "")[-1000:])
    for r in rows:
        if r.get("name")==NAME and not r.get("deleted_at"):
            tunnel_id=str(r.get("id")); break
    created=False
    if not tunnel_id:
        run(["tunnel","create",NAME])
        created=True
        p2=run(["tunnel","list","--output","json"])
        try: rows=json.loads(p2.stdout or "[]")
        except Exception as e: fail("cannot parse tunnel list after create",repr(e)+"; stdout="+(p2.stdout or "")[-1000:])
        for r in rows:
            if r.get("name")==NAME and not r.get("deleted_at"):
                tunnel_id=str(r.get("id")); break
    if not tunnel_id: fail("tunnel id unresolved")

    cred=pathlib.Path.home()/".cloudflared"/(tunnel_id+".json")
    if not cred.exists(): fail("tunnel credential file missing")

    config=CFGDIR/"cloudflared-result-gateway.yml"
    config.write_text(f"tunnel: {tunnel_id}\ncredentials-file: {cred}\ningress:\n  - service: http://127.0.0.1:8765\n  - service: http_status:404\n",encoding="utf-8")
    os.chmod(config,0o600)

    label="com.liangzhi.resultgateway.tunnel"
    plist=pathlib.Path.home()/"Library"/"LaunchAgents"/(label+".plist")
    plist.parent.mkdir(parents=True,exist_ok=True)
    logdir=BASE/"logs"; logdir.mkdir(parents=True,exist_ok=True)
    obj={"Label":label,"ProgramArguments":[str(BIN),"tunnel","--config",str(config),"run",tunnel_id],"RunAtLoad":True,"KeepAlive":True,"StandardOutPath":str(logdir/"cloudflared-result-gateway.out.log"),"StandardErrorPath":str(logdir/"cloudflared-result-gateway.err.log"),"ProcessType":"Background"}
    with plist.open("wb") as f: plistlib.dump(obj,f)
    uid=os.getuid(); domain=f"gui/{uid}"
    subprocess.run(["launchctl","bootout",domain,str(plist)],capture_output=True,text=True)
    p=subprocess.run(["launchctl","bootstrap",domain,str(plist)],capture_output=True,text=True)
    if p.returncode not in (0,):
        # Continue to print state; kickstart may still recover if already loaded.
        pass
    subprocess.run(["launchctl","kickstart","-k",f"{domain}/{label}"],capture_output=True,text=True)
    time.sleep(3)
    chk=subprocess.run(["launchctl","print",f"{domain}/{label}"],capture_output=True,text=True)
    launchagent_ok=(chk.returncode==0)
    if not launchagent_ok: fail("launchagent not loaded",(chk.stderr or chk.stdout or ""))

    lines=["LiangZhi named tunnel local setup","status: PASS",f"tunnel_name: {NAME}",f"tunnel_created_now: {created}","launchagent_loaded: True","origin: http://127.0.0.1:8765","dns_route_created: False","public_hostname_created: False","external_exposure: False"]
    OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines))
except SystemExit:
    raise
except Exception:
    fail("unexpected exception",traceback.format_exc())
