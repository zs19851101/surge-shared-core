#!/usr/bin/env python3
from pathlib import Path
import json, collections
BASE=Path.home()/"Library/Application Support/LiangZhiLocalExecutor"
R=BASE/"reports"
AUD=R/"anime-final-role-avatar-audit.json"
AGG=R/"anime-final-role-avatar-aggregate.json"
OUT=R/"anime-v32-role-avatar-summary.txt"
if not AUD.exists() or not AGG.exists():
    OUT.write_text("日漫 V3.2 Role/头像审计汇总\nstatus: FAIL\nreason: missing-local-audit-input\n",encoding="utf-8")
    raise SystemExit(2)
a=json.loads(AUD.read_text(encoding="utf-8"))
g=json.loads(AGG.read_text(encoding="utf-8"))
rows=a.get("rows",[])
flag_counts=collections.Counter()
for r in rows:
    for f in r.get("flags",[]): flag_counts[f]+=1
people=len({str(r.get("person_id")) for r in rows if r.get("person_id")})
empty_people=sum(1 for x in g if (x.get("flags") or {}).get("empty_role"))
latin_people=sum(1 for x in g if (x.get("flags") or {}).get("latin_role"))
missing_people=sum(1 for x in g if (x.get("flags") or {}).get("missing_avatar"))
single=sum(1 for x in g if x.get("unique_roles")==1)
multi=sum(1 for x in g if (x.get("unique_roles") or 0)>1)
lines=[
"日漫 V3.2 Role/头像审计汇总",
"status: PASS",
f"issue_rows: {len(rows)}",
f"unique_problem_people: {people}",
f"empty_role_rows: {flag_counts.get('empty_role',0)}",
f"latin_role_rows: {flag_counts.get('latin_role',0)}",
f"missing_avatar_rows: {flag_counts.get('missing_avatar',0)}",
f"people_with_empty_role: {empty_people}",
f"people_with_latin_role: {latin_people}",
f"people_missing_avatar: {missing_people}",
f"single_role_people: {single}",
f"multi_role_people: {multi}",
"scope: read-only-summary",
"network_changes: none",
"series_changes: none",
]
OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
print(OUT.read_text(encoding="utf-8"))
