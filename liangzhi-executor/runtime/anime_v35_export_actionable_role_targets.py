#!/usr/bin/env python3
from pathlib import Path
import json, collections
BASE=Path.home()/"Library/Application Support/LiangZhiLocalExecutor"
R=BASE/"reports"
AUD=R/"anime-final-role-avatar-audit.json"
OUT=R/"anime-v35-actionable-role-targets.json"
SUM=R/"anime-v35-actionable-role-targets-summary.txt"
a=json.loads(AUD.read_text(encoding="utf-8")); rows=a.get("rows",[])
known=collections.defaultdict(set)
for x in rows:
    pid=str(x.get("person_id") or ""); sid=str(x.get("series_id") or ""); role=str(x.get("role") or "").strip()
    if pid and sid and role: known[(pid,sid)].add(role)
targets=[]
for x in rows:
    pid=str(x.get("person_id") or ""); sid=str(x.get("series_id") or ""); role=str(x.get("role") or "").strip(); typ=str(x.get("item_type") or x.get("type") or "")
    roles=known.get((pid,sid),set())
    if typ=="Episode" and pid and sid and not role and len(roles)==1:
        targets.append({"item_id":x.get("item_id") or x.get("id"),"series_id":sid,"person_id":pid,"name":x.get("name"),"target_role":next(iter(roles))})
uniq={(str(t['item_id']),t['person_id'],t['target_role']):t for t in targets if t.get('item_id')}
vals=list(uniq.values())
OUT.write_text(json.dumps({"status":"PASS","targets":vals},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
SUM.write_text("\n".join(["日漫 V3.5 可执行空 Role 目标","status: PASS",f"target_rows: {len(vals)}",f"target_people: {len(set(x['person_id'] for x in vals))}",f"target_series: {len(set(x['series_id'] for x in vals))}","evidence: same-person-same-series-single-known-role","scope: read-only-export","network_changes: none","series_changes: none"])+"\n",encoding="utf-8")
print(SUM.read_text(encoding="utf-8"))
