#!/usr/bin/env python3
from pathlib import Path
import json
BASE=Path.home()/"Library/Application Support/LiangZhiLocalExecutor"
R=BASE/"reports"
S=R/"anime-v30-apply-two-strong-names-summary.txt"
G=R/"anime-series-identity-guard-result.json"
O=R/"anime-seq20-verification-summary.txt"
if not S.exists() or not G.exists():
    O.write_text("status: FAIL\nreason: missing-seq20-report\n",encoding="utf-8")
    raise SystemExit(2)
s=S.read_text(encoding="utf-8",errors="replace")
g=json.loads(G.read_text(encoding="utf-8"))
summary_pass="status: PASS" in s
api_verified="verified: true" in s.lower()
guard_pass=g.get("status")=="PASS" and g.get("drift_count")==0
ok=summary_pass and api_verified and guard_pass
O.write_text("\n".join([
    "动漫-日漫 seq20 验收",
    "status: "+("PASS" if ok else "FAIL"),
    "seq20_summary_pass: "+str(summary_pass).lower(),
    "api_readback_verified: "+str(api_verified).lower(),
    "series_guard_pass: "+str(guard_pass).lower(),
    "drift_count: "+str(g.get("drift_count")),
    "data_plane_changes: none"
])+"\n",encoding="utf-8")
raise SystemExit(0 if ok else 2)
