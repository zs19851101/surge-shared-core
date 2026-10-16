#!/usr/bin/env python3
import pathlib, subprocess
BASE=pathlib.Path.home()/"Library/Application Support/LiangZhiLocalExecutor"
BIN=BASE/"bin"/"cloudflared"
OUT=BASE/"reports"/"named-tunnel-create-summary.txt"
p=subprocess.run([str(BIN),"tunnel","create","liangzhi-result-gateway"],capture_output=True,text=True,timeout=90)
text=((p.stdout or "")+"\n"+(p.stderr or "")).strip()
OUT.write_text("status: "+("PASS" if p.returncode==0 else "FAIL")+"\n"+text[-1200:]+"\nexternal_exposure: False\n",encoding="utf-8")
print(OUT.read_text(encoding="utf-8"))
raise SystemExit(p.returncode)
