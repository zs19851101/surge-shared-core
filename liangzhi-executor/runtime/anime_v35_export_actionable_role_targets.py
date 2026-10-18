#!/usr/bin/env python3
from pathlib import Path
import json, collections
BASE=Path.home()/"Library/Application Support/LiangZhiLocalExecutor"
R=BASE/"reports"
AUD=R/"anime-final-role-avatar-audit.json"
OUT=R/"anime-v35-actionable-role-targets.json"
SUM=R/"anime-v35-actionable-role-targets-summary.txt"
try:
    a=json.loads(AUD.read_text(encoding="utf-8"))
    rows=a.get("rows",[])
    known=collections.defaultdict(set)
    for x in rows:
        pid=str(x.get("person_id") or "")
        sid=str(x.get("series_id") or "")
        role=str(x.get("role") or "").strip()
        if pid and sid and role:
            known[(pid,sid)].add(role)
    targets=[]
    for x in rows:
        pid=str(x.get("person_id") or "")
        sid=str(x.get("series_id") or "")
        role=str(x.get("role") or "").strip()
        typ=str(x.get("item_type") or x.get("type") or "")
        roles=known.get((pid,sid),set())
        iid=x.get("item_id") or x.get("id")
        if typ=="Episode" and iid and pid and sid and not role and len(roles)==1:
            targets.append({"item_id":str(iid),"series_id":sid,"person_id":pid,"name":x.get("name"),"target_role":next(iter(roles))})
    uniq={}
    for t in targets:
        uniq[(t["item_id"],t["person_id"],t["target_role"])]=t
    vals=list(uniq.values())
    rep={"status":"PASS","target_rows":len(vals),"target_people":len({x['person_id'] for x in vals}),"target_series":len({x['series_id'] for x in vals}),"targets":vals,"evidence":"same-person-same-series-single-known-role","scope":"read-only-export","network_changes":"none","series_changes":"none"}
    OUT.write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    SUM.write_text("\n".join(["日漫 V3.5 可执行空 Role 目标","status: PASS",f"target_rows: {rep['target_rows']}",f"target_people: {rep['target_people']}",f"target_series: {rep['target_series']}","evidence: same-person-same-series-single-known-role","scope: read-only-export","network_changes: none","series_changes: none"])+"\n",encoding="utf-8")
except Exception as e:
    SUM.write_text("日漫 V3.5 可执行空 Role 目标\nstatus: FAIL\nreason: "+type(e).__name__+"\nscope: read-only-export\nnetwork_changes: none\nseries_changes: none\n",encoding="utf-8")
    raise
print(SUM.read_text(encoding="utf-8"))
