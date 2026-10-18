#!/usr/bin/env python3
from pathlib import Path
import json, collections
BASE=Path.home()/"Library/Application Support/LiangZhiLocalExecutor"
R=BASE/"reports"
AUD=R/"anime-final-role-avatar-audit.json"
AGG=R/"anime-final-role-avatar-aggregate.json"
OUT=R/"anime-v34-role-avatar-candidates.json"
SUM=R/"anime-v34-role-avatar-candidates-summary.txt"
if not AUD.exists() or not AGG.exists():
    SUM.write_text("日漫 V3.4 Role/头像候选分类\nstatus: FAIL\nreason: missing-audit-input\n",encoding="utf-8")
    raise SystemExit(2)
a=json.loads(AUD.read_text(encoding="utf-8"))
g=json.loads(AGG.read_text(encoding="utf-8"))
rows=a.get("rows",[])
by_person=collections.defaultdict(list)
for r in rows:
    pid=str(r.get("person_id") or "")
    if pid: by_person[pid].append(r)
items=[]
for p in g:
    pid=str(p.get("person_id") or "")
    prs=by_person.get(pid,[])
    flags=p.get("flags") or {}
    roles=sorted({str(x.get("role") or "").strip() for x in prs if str(x.get("role") or "").strip()})
    series_ids=sorted({str(x.get("series_id") or "") for x in prs if x.get("series_id")})
    item_types=collections.Counter(str(x.get("item_type") or x.get("type") or "") for x in prs)
    provider_ids=p.get("provider_ids") or {}
    bucket="review"
    if flags.get("missing_avatar") and provider_ids:
        bucket="avatar_provider_backed"
    if flags.get("empty_role") and len(roles)==1:
        bucket="single_role_empty_rows"
    if flags.get("empty_role") and len(roles)>1:
        bucket="multi_role_empty_rows"
    items.append({"person_id":pid,"name":p.get("name"),"bucket":bucket,"flags":flags,"roles":roles,"series_ids":series_ids,"provider_ids":provider_ids,"row_count":len(prs),"item_types":dict(item_types)})
counts=collections.Counter(x["bucket"] for x in items)
rep={"status":"PASS","total_people":len(items),"counts":dict(counts),"items":items,"scope":"read-only-classification","network_changes":"none","series_changes":"none"}
OUT.write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
SUM.write_text("\n".join(["日漫 V3.4 Role/头像候选分类","status: PASS",f"total_people: {len(items)}",f"avatar_provider_backed: {counts.get('avatar_provider_backed',0)}",f"single_role_empty_rows: {counts.get('single_role_empty_rows',0)}",f"multi_role_empty_rows: {counts.get('multi_role_empty_rows',0)}",f"review: {counts.get('review',0)}","scope: read-only-classification","network_changes: none","series_changes: none"])+"\n",encoding="utf-8")
print(SUM.read_text(encoding="utf-8"))
