#!/usr/bin/env python3
from pathlib import Path
import json, collections, datetime
BASE=Path.home()/"Library/Application Support/LiangZhiLocalExecutor"; R=BASE/"reports"
SRC=R/"anime-v34-role-avatar-candidates.json"; OUT=R/"anime-v37-provider-avatar-plan.json"; SUM=R/"anime-v37-provider-avatar-plan-summary.txt"
def finish(rep):
 OUT.write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 SUM.write_text("\n".join(["日漫 V3.7 Provider 头像解析计划",f"status: {rep.get('status')}",f"candidate_people: {rep.get('candidate_people',0)}",f"tmdb_people: {rep.get('tmdb_people',0)}",f"tvdb_people: {rep.get('tvdb_people',0)}",f"imdb_people: {rep.get('imdb_people',0)}",f"other_provider_people: {rep.get('other_provider_people',0)}","scope: read-only-plan","emby_changes: none","network_changes: none","series_changes: none"])+"\n",encoding="utf-8")
 print(SUM.read_text(encoding="utf-8"))
try:
 d=json.loads(SRC.read_text(encoding="utf-8")); c=[x for x in d.get('items',[]) if x.get('bucket')=='avatar_provider_backed']
 rows=[]; counts=collections.Counter()
 for x in c:
  ids={str(k).lower():str(v) for k,v in (x.get('provider_ids') or {}).items() if v}
  kinds=[]
  for k in ('tmdb','tvdb','imdb'):
   if ids.get(k): kinds.append(k); counts[k]+=1
  if ids and not kinds: counts['other']+=1
  rows.append({'person_id':str(x.get('person_id') or ''),'name':x.get('name'),'provider_ids':ids,'resolvers':kinds or ['manual-provider-review']})
 finish({'time':datetime.datetime.now().isoformat(),'status':'PASS','candidate_people':len(c),'tmdb_people':counts['tmdb'],'tvdb_people':counts['tvdb'],'imdb_people':counts['imdb'],'other_provider_people':counts['other'],'rows':rows,'scope':'read-only-plan','emby_changes':'none','network_changes':'none','series_changes':'none'})
except Exception as e:
 finish({'time':datetime.datetime.now().isoformat(),'status':'FAIL','reason':repr(e),'candidate_people':0,'tmdb_people':0,'tvdb_people':0,'imdb_people':0,'other_provider_people':0,'rows':[]}); raise
