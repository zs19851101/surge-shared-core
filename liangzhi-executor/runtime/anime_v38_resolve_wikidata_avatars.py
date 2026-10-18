#!/usr/bin/env python3
from pathlib import Path
import json, datetime, requests, time
BASE=Path.home()/"Library/Application Support/LiangZhiLocalExecutor"; R=BASE/"reports"
SRC=R/"anime-v37-provider-avatar-plan.json"; OUT=R/"anime-v38-wikidata-avatar-candidates.json"; SUM=R/"anime-v38-wikidata-avatar-candidates-summary.txt"

def finish(rep):
    OUT.write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    SUM.write_text("\n".join([
        "日漫 V3.8 Wikidata/Commons 头像候选",
        f"status: {rep.get('status')}",
        f"candidate_people: {rep.get('candidate_people',0)}",
        f"wikidata_exact_matches: {rep.get('wikidata_exact_matches',0)}",
        f"with_commons_image: {rep.get('with_commons_image',0)}",
        f"without_commons_image: {rep.get('without_commons_image',0)}",
        f"errors: {rep.get('errors',0)}",
        "evidence: exact TMDB person ID (P4985) -> Wikidata item -> P18 image",
        "scope: read-only-resolution",
        "emby_changes: none",
        "network_changes: none",
        "series_changes: none"
    ])+"\n",encoding="utf-8")
    print(SUM.read_text(encoding="utf-8"))

try:
    d=json.loads(SRC.read_text(encoding="utf-8"))
    rows=d.get("rows",[])
    ids=[]; meta={}
    for x in rows:
        t=(x.get("provider_ids") or {}).get("tmdb")
        if t:
            t=str(t); ids.append(t); meta[t]={"person_id":str(x.get("person_id") or ""),"name":x.get("name"),"provider_ids":x.get("provider_ids") or {}}
    ids=sorted(set(ids), key=lambda z:int(z) if z.isdigit() else z)
    vals=" ".join('"'+i.replace('"','')+'"' for i in ids)
    q=f'''SELECT ?tmdb ?item ?itemLabel ?image WHERE {{ VALUES ?tmdb {{ {vals} }} ?item wdt:P4985 ?tmdb. OPTIONAL {{ ?item wdt:P18 ?image. }} SERVICE wikibase:label {{ bd:serviceParam wikibase:language "ja,en,zh". }} }}'''
    s=requests.Session(); s.headers.update({"User-Agent":"LiangZhiNetwork/1.0 (read-only metadata audit)"})
    r=s.get("https://query.wikidata.org/sparql",params={"query":q,"format":"json"},timeout=90); r.raise_for_status(); js=r.json()
    found={}
    for b in js.get("results",{}).get("bindings",[]):
        t=b.get("tmdb",{}).get("value");
        if not t: continue
        rec=found.setdefault(t,{"items":[]})
        rec["items"].append({"wikidata":b.get("item",{}).get("value"),"label":b.get("itemLabel",{}).get("value"),"image":b.get("image",{}).get("value")})
    out=[]; exact=0; with_img=0; without=0
    for t in ids:
        arr=found.get(t,{}).get("items",[])
        # P4985 should be unique; require exactly one Wikidata item to stay fail-closed.
        unique_items={x.get("wikidata") for x in arr if x.get("wikidata")}
        imgs=sorted({x.get("image") for x in arr if x.get("image")})
        status="no_wikidata_match"
        if len(unique_items)==1:
            exact+=1
            status="exact_with_image" if len(imgs)>=1 else "exact_no_image"
            if imgs: with_img+=1
            else: without+=1
        elif len(unique_items)>1:
            status="ambiguous_wikidata_match"
        out.append({"tmdb_id":t,**meta[t],"status":status,"wikidata_items":sorted(unique_items),"commons_images":imgs})
    finish({"time":datetime.datetime.now().isoformat(),"status":"PASS","candidate_people":len(ids),"wikidata_exact_matches":exact,"with_commons_image":with_img,"without_commons_image":without,"errors":0,"rows":out,"scope":"read-only-resolution","emby_changes":"none","network_changes":"none","series_changes":"none"})
except Exception as e:
    finish({"time":datetime.datetime.now().isoformat(),"status":"FAIL","reason":repr(e),"candidate_people":0,"wikidata_exact_matches":0,"with_commons_image":0,"without_commons_image":0,"errors":1,"rows":[]})
    raise
