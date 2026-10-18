#!/usr/bin/env python3
from pathlib import Path
import json, datetime
BASE=Path.home()/"Library/Application Support/LiangZhiLocalExecutor"; R=BASE/"reports"
SRC=R/"anime-v38-wikidata-avatar-candidates.json"; OUT=R/"anime-v39-single-commons-avatar.json"; SUM=R/"anime-v39-single-commons-avatar-summary.txt"
def finish(rep):
    OUT.write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=["日漫 V3.9 单一 Commons 头像候选",f"status: {rep.get('status')}",f"candidate_count: {rep.get('candidate_count',0)}"]
    if rep.get('candidate_count')==1:
        c=rep['candidate']; lines += [f"person_id: {c.get('person_id')}",f"name: {c.get('name')}",f"tmdb_id: {c.get('tmdb_id')}",f"wikidata: {','.join(c.get('wikidata_items') or [])}",f"image: {(c.get('commons_images') or [''])[0]}"]
    lines += ["scope: read-only-export","emby_changes: none","network_changes: none","series_changes: none"]
    SUM.write_text("\n".join(lines)+"\n",encoding="utf-8"); print(SUM.read_text(encoding="utf-8"))
try:
    d=json.loads(SRC.read_text(encoding='utf-8')); rows=[x for x in d.get('rows',[]) if x.get('status')=='exact_with_image' and len(x.get('commons_images') or [])>=1]
    finish({'time':datetime.datetime.now().isoformat(),'status':'PASS' if len(rows)==1 else 'ABORTED','candidate_count':len(rows),'candidate':rows[0] if len(rows)==1 else None})
except Exception as e:
    finish({'time':datetime.datetime.now().isoformat(),'status':'FAIL','candidate_count':0,'reason':repr(e)}); raise
