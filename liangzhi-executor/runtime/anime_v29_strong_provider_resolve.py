#!/usr/bin/env python3
import json, pathlib, datetime, requests, time
BASE=pathlib.Path.home()/"Library/Application Support/LiangZhiLocalExecutor"
SRC=BASE/"reports"/"anime-v27-identity-audit.json"
OUT=BASE/"reports"/"anime-v29-strong-provider-resolve.json"
SUM=BASE/"reports"/"anime-v29-strong-provider-resolve-summary.txt"
if not SRC.exists():
    raise SystemExit("ERROR: missing anime-v27-identity-audit.json")
d=json.loads(SRC.read_text(encoding="utf-8"))
people=[]
for p in d.get("people",[]):
    ids=p.get("provider_ids") or {}
    norm={str(k).lower():str(v) for k,v in ids.items() if v}
    if norm.get("imdb") or norm.get("tmdb"):
        people.append({"person_id":str(p.get("person_id")),"name":p.get("name"),"provider_ids":norm,"has_primary":bool(p.get("has_primary")),"samples":p.get("samples",[])[:3]})

EP="https://query.wikidata.org/sparql"
HEAD={"User-Agent":"LiangZhiMetadataAudit/1.0 (read-only identity resolver)","Accept":"application/sparql-results+json"}

def chunks(xs,n=35):
    for i in range(0,len(xs),n): yield xs[i:i+n]

def query_prop(prop, ids):
    out={x:[] for x in ids}
    for part in chunks(sorted(set(ids))):
        vals=" ".join(json.dumps(x,ensure_ascii=False) for x in part)
        q=f'''SELECT ?item ?id ?zh ?en ?ja WHERE {{ VALUES ?id {{ {vals} }} ?item wdt:{prop} ?id. OPTIONAL {{ ?item rdfs:label ?zh FILTER(LANG(?zh)="zh" || LANG(?zh)="zh-hans" || LANG(?zh)="zh-cn") }} OPTIONAL {{ ?item rdfs:label ?en FILTER(LANG(?en)="en") }} OPTIONAL {{ ?item rdfs:label ?ja FILTER(LANG(?ja)="ja") }} }}'''
        r=requests.get(EP,params={"query":q,"format":"json"},headers=HEAD,timeout=60)
        r.raise_for_status()
        for b in r.json().get("results",{}).get("bindings",[]):
            ident=b["id"]["value"]
            row={"qid":b["item"]["value"].rsplit("/",1)[-1],"zh":b.get("zh",{}).get("value"),"en":b.get("en",{}).get("value"),"ja":b.get("ja",{}).get("value")}
            if row not in out.setdefault(ident,[]): out[ident].append(row)
        time.sleep(0.3)
    return out

imdb_ids=[p["provider_ids"]["imdb"] for p in people if p["provider_ids"].get("imdb")]
tmdb_ids=[p["provider_ids"]["tmdb"] for p in people if p["provider_ids"].get("tmdb")]
imdb_map=query_prop("P345",imdb_ids) if imdb_ids else {}
tmdb_map=query_prop("P4985",tmdb_ids) if tmdb_ids else {}

rows=[]; counts={"exact_with_zh":0,"exact_no_zh":0,"conflict":0,"no_match":0}
for p in people:
    ids=p["provider_ids"]
    a=imdb_map.get(ids.get("imdb"),[]) if ids.get("imdb") else []
    b=tmdb_map.get(ids.get("tmdb"),[]) if ids.get("tmdb") else []
    qids={x["qid"] for x in a+b}
    byqid={}
    for x in a+b:
        z=byqid.setdefault(x["qid"],{"qid":x["qid"],"zh":None,"en":None,"ja":None,"sources":[]})
        for k in ("zh","en","ja"):
            if x.get(k) and not z.get(k): z[k]=x[k]
    if ids.get("imdb"):
        for x in a: byqid[x["qid"]]["sources"].append("imdb")
    if ids.get("tmdb"):
        for x in b: byqid[x["qid"]]["sources"].append("tmdb")
    if len(qids)==1:
        c=byqid[next(iter(qids))]
        status="exact_with_zh" if c.get("zh") else "exact_no_zh"
        counts[status]+=1
        row={**p,"status":status,"candidate":c}
    elif len(qids)>1:
        counts["conflict"]+=1
        row={**p,"status":"conflict","candidates":list(byqid.values())}
    else:
        counts["no_match"]+=1
        row={**p,"status":"no_match"}
    rows.append(row)
rep={"time":datetime.datetime.now().isoformat(),"input_strong_people":len(people),**counts,"rows":rows}
OUT.write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
lines=["日漫 V2.9 强证据身份闭环（只读）",f"强证据输入: {len(people)}",f"唯一身份且有中文名: {counts['exact_with_zh']}",f"唯一身份但无中文名: {counts['exact_no_zh']}",f"Provider 冲突: {counts['conflict']}",f"Wikidata 无匹配: {counts['no_match']}"]
SUM.write_text("\n".join(lines)+"\n",encoding="utf-8")
print("\n".join(lines))
