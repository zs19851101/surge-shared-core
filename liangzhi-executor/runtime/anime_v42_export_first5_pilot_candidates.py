#!/usr/bin/env python3
from pathlib import Path
import json, datetime

BASE=Path.home()/"Library/Application Support/LiangZhiLocalExecutor"
R=BASE/"reports"
OUT=R/"anime-v42-first5-pilot-candidates.json"
SUM=R/"anime-v42-first5-pilot-candidates-summary.txt"

def load(name):
    p=R/name
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))

def emit(rep):
    OUT.write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=["日漫 V4.2 首批 5 人联调候选导出",f"status: {rep.get('status')}"]
    for i,x in enumerate(rep.get('candidates',[]),1):
        lines += [
            f"[{i}] type: {x.get('type','')}",
            f"person_id: {x.get('person_id','')}",
            f"current_name: {x.get('current_name','')}",
            f"target_name: {x.get('target_name','')}",
            f"image_url: {x.get('image_url','')}",
            f"old_role: {x.get('old_role','')}",
            f"target_role: {x.get('target_role','')}",
            f"series_id: {x.get('series_id','')}",
            f"evidence: {x.get('evidence','')}",
        ]
    lines += [f"blocked_slots: {','.join(rep.get('blocked_slots',[]))}","scope: read-only-export","emby_changes: none","network_changes: none","series_changes: none"]
    SUM.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(SUM.read_text(encoding="utf-8"))

v29=load("anime-v29-strong-provider-resolve.json") or {}
v30b=load("anime-v30-person-backup.json") or {}
v38=load("anime-v38-wikidata-avatar-candidates.json") or {}
v41=load("anime-v41-live-person-prep.json") or {}
aud=load("anime-final-role-avatar-audit.json") or {}

cands=[]; blocked=[]

# name-only: use one exact provider->Wikidata Chinese-name candidate only if current live/baseline name differs.
name_rows=[]
for row in v29.get("rows",[]):
    if row.get("status")!="exact_with_zh":
        continue
    cand=row.get("candidate") or {}
    zh=(cand.get("zh") or "").strip(); old=(row.get("name") or "").strip()
    if zh and old and zh!=old:
        name_rows.append({"type":"name-only","person_id":str(row.get("person_id") or ""),"current_name":old,"target_name":zh,"image_url":"","evidence":"exact Provider ID -> unique Wikidata item -> zh label"})
if name_rows:
    cands.append(name_rows[0])
else:
    blocked.append("name-only")

# image-only: require V4.1 live resolution PASS for exact TMDB 4055060 and known Commons image.
if v41.get("status")=="PASS" and v41.get("person_id"):
    cands.append({"type":"image-only","person_id":str(v41.get("person_id")),"current_name":v41.get("live_name") or "","target_name":"","image_url":"https://commons.wikimedia.org/wiki/Special:FilePath/Adam%20Gibbs%20%2855163669246%29.jpg","evidence":"exact TMDB 4055060 -> unique live Emby Person; exact Wikidata P4985 -> Commons P18; Primary absent"})
else:
    blocked.append("image-only")

# name-image: only if an exact-with-image avatar row is also an exact Chinese-name v29 row for same TMDB/person and name differs.
by_pid_v29={str(r.get('person_id') or ''):r for r in v29.get('rows',[]) if r.get('status')=='exact_with_zh'}
combo=[]
for r in v38.get("rows",[]):
    if r.get("status")!="exact_with_image" or not (r.get("commons_images") or []):
        continue
    p=by_pid_v29.get(str(r.get("person_id") or ""))
    if not p: continue
    zh=((p.get("candidate") or {}).get("zh") or "").strip(); old=(p.get("name") or "").strip()
    if zh and old and zh!=old:
        combo.append({"type":"name-image","person_id":str(r.get("person_id") or ""),"current_name":old,"target_name":zh,"image_url":(r.get("commons_images") or [""])[0],"evidence":"same Person: exact provider->Wikidata zh label + exact TMDB->Wikidata P18"})
if combo:
    cands.append(combo[0])
else:
    blocked.append("name-image")

# voice-cleanup: only the deterministic known tail; verify it still appears in audit rows.
voice_rows=[]
for r in aud.get("rows",[]):
    if str(r.get("person_id") or "")=="49724" and str(r.get("series_id") or "")=="127761" and str(r.get("role") or "").strip()=="Konno Erika (voice)":
        voice_rows.append(r)
if voice_rows:
    cands.append({"type":"voice-cleanup","person_id":"49724","current_name":"雪野五月","target_name":"","image_url":"","old_role":"Konno Erika (voice)","target_role":"Konno Erika","series_id":"127761","evidence":f"exact old_role match in current audit rows: {len(voice_rows)}"})
else:
    blocked.append("voice-cleanup")

# no-op: select a V3.0 backed item whose original Name already equals target_name.
noop=[]
for it in v30b.get("items",[]):
    orig=it.get("original") or {}; target=(it.get("target_name") or "").strip(); cur=(orig.get("Name") or "").strip()
    if target and cur==target:
        noop.append({"type":"no-op","person_id":str(it.get("person_id") or orig.get("Id") or ""),"current_name":cur,"target_name":target,"image_url":"","evidence":"V3.0 backup: current name already equals exact provider/Wikidata target"})
if noop:
    cands.append(noop[0])
else:
    blocked.append("no-op")

status="PASS" if len(cands)==5 and not blocked else "PARTIAL"
emit({"time":datetime.datetime.now().isoformat(),"status":status,"candidates":cands,"blocked_slots":blocked,"scope":"read-only-export","emby_changes":"none","network_changes":"none","series_changes":"none"})
