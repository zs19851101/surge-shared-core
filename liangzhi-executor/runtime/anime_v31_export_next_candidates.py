#!/usr/bin/env python3
from pathlib import Path
import json, sys
BASE=Path.home()/"Library/Application Support/LiangZhiLocalExecutor"
R=BASE/"reports"
SRC=R/"anime-v29-strong-provider-resolve.json"
OUT=R/"anime-v31-next-candidates.txt"
if not SRC.exists():
    OUT.write_text("status: FAIL\nreason: missing-v29-report\n",encoding="utf-8")
    raise SystemExit(2)
d=json.loads(SRC.read_text(encoding="utf-8"))
rows=d.get("results") or d.get("people") or []
exact_no_zh=[]
no_match=[]
for x in rows:
    st=str(x.get("status", ""))
    row={
        "person_id": x.get("person_id"),
        "name": x.get("name"),
        "provider_ids": x.get("provider_ids") or x.get("matched_provider_ids") or {},
        "status": st,
    }
    if st=="exact_no_zh": exact_no_zh.append(row)
    elif st=="no_match": no_match.append(row)
lines=["动漫-日漫 V3.1 下一批候选（只读脱敏）","status: PASS",f"exact_no_zh_count: {len(exact_no_zh)}",f"no_match_count: {len(no_match)}","","[exact_no_zh]"]
for r in exact_no_zh:
    ids=",".join(f"{k}={v}" for k,v in sorted((r['provider_ids'] or {}).items()) if v)
    lines.append(f"{r['person_id']}\t{r['name']}\t{ids}")
lines += ["","[no_match_first_20]"]
for r in no_match[:20]:
    ids=",".join(f"{k}={v}" for k,v in sorted((r['provider_ids'] or {}).items()) if v)
    lines.append(f"{r['person_id']}\t{r['name']}\t{ids}")
lines += ["","scope: read-only","series_changes: none","network_changes: none"]
OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
print("\n".join(lines[:6]))
