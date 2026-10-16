#!/usr/bin/env python3
import json, pathlib, datetime, sys
BASE=pathlib.Path.home()/"Library/Application Support/LiangZhiLocalExecutor"
SRC=BASE/"reports"/"anime-v27-identity-audit.json"
OUT=BASE/"reports"/"anime-v28-evidence-plan.json"
SUM=BASE/"reports"/"anime-v28-evidence-plan-summary.txt"
if not SRC.exists():
 print("ERROR: missing V2.7 audit"); sys.exit(2)
d=json.loads(SRC.read_text(encoding="utf-8"))
strong=[]; medium=[]; weak=[]
for p in d.get("people",[]):
 ids=p.get("provider_ids") or {}
 keys={str(k).lower() for k,v in ids.items() if v}
 row={"person_id":p.get("person_id"),"name":p.get("name"),"provider_keys":sorted(keys),"has_primary":bool(p.get("has_primary")),"samples":p.get("samples",[])[:3]}
 if "tmdb" in keys or "imdb" in keys:
  strong.append(row)
 elif keys:
  medium.append(row)
 else:
  weak.append(row)
rep={"time":datetime.datetime.now().isoformat(),"remaining_foreign_persons":d.get("remaining_foreign_persons",0),"strong_exact_provider":len(strong),"medium_other_provider":len(medium),"weak_no_provider":len(weak),"strong":strong,"medium":medium,"weak":weak}
OUT.write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
lines=["日漫 V2.8 身份证据分层（只读）",f"剩余外文姓名人物: {rep['remaining_foreign_persons']}",f"强证据(TMDB/IMDb): {len(strong)}",f"中证据(其他Provider): {len(medium)}",f"弱证据(无Provider): {len(weak)}"]
SUM.write_text("\n".join(lines)+"\n",encoding="utf-8")
print("\n".join(lines))
