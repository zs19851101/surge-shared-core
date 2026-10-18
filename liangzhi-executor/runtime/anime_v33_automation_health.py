#!/usr/bin/env python3
from pathlib import Path
import json, datetime, sys
BASE=Path.home()/"Library/Application Support/LiangZhiLocalExecutor"
R=BASE/"reports"
STATE=BASE/"control"/"poller-state.json"
V32=R/"anime-v32-role-avatar-summary.txt"
OUT=R/"anime-v33-automation-health-summary.txt"
state={}
if STATE.exists():
    try: state=json.loads(STATE.read_text(encoding="utf-8"))
    except Exception: state={}
v32=V32.read_text(encoding="utf-8",errors="replace") if V32.exists() else ""
last_seq=int(state.get("last_seq") or 0)
last_task=str(state.get("last_task") or "")
ok=(last_seq>=23 and "status: PASS" in v32)
lines=[
"良知 LocalExecutor / Result Bridge 自动链路健康探针",
f"status: {'PASS' if ok else 'FAIL'}",
f"last_seq: {last_seq}",
f"last_task: {last_task}",f"v32_present: {str(V32.exists()).lower()}",f"v32_pass: {str('status: PASS' in v32).lower()}","scope: read-only","emby_changes: none","network_changes: none","series_changes: none",f"time: {datetime.datetime.now().isoformat()}"
]
OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
print(OUT.read_text(encoding="utf-8"))
sys.exit(0 if ok else 2)
