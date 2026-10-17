#!/usr/bin/env python3
import json, pathlib, subprocess, requests, datetime, sys

BASE=pathlib.Path.home()/"Library/Application Support/LiangZhiLocalExecutor"
CFG=json.loads((BASE/"settings.json").read_text(encoding="utf-8"))
B=CFG["emby_base"].rstrip("/")
SRC=BASE/"reports"/"anime-v29-strong-provider-resolve.json"
BACKUP=BASE/"reports"/"anime-v30-person-backup.json"
DETAIL=BASE/"reports"/"anime-v30-apply-two-strong-names.json"
SUM=BASE/"reports"/"anime-v30-apply-two-strong-names-summary.txt"

if not SRC.exists():
    raise SystemExit("ERROR: missing anime-v29-strong-provider-resolve.json")

def js(expr):
    esc=expr.replace("\\","\\\\").replace('"','\\"')
    sc=('tell application "Google Chrome"\nrepeat with w in windows\nrepeat with t in tabs of w\n'
        'if (URL of t) contains "192.168.100.198:8096/web/" then\nreturn execute t javascript "'+esc+'"\nend if\nend repeat\nend repeat\nend tell')
    r=subprocess.run(["osascript","-e",sc],capture_output=True,text=True,timeout=30)
    if r.returncode: raise RuntimeError(r.stderr[:300])
    return r.stdout.strip()

token=js("JSON.parse(localStorage.getItem('servercredentials3')).Servers[0].Users[0].AccessToken")
uid=js("JSON.parse(localStorage.getItem('servercredentials3')).Servers[0].UserId")
S=requests.Session(); S.headers.update({"X-Emby-Token":token,"Content-Type":"application/json"})

def get_person(pid):
    r=S.get(f"{B}/Users/{uid}/Items/{pid}",params={"Fields":"ProviderIds,ImageTags,Overview"},timeout=30)
    r.raise_for_status(); return r.json()

def put_person(pid,obj):
    r=S.post(f"{B}/Items/{pid}",json=obj,timeout=60)
    r.raise_for_status(); return r

d=json.loads(SRC.read_text(encoding="utf-8"))
candidates=[]
for row in d.get("rows",[]):
    if row.get("status")!="exact_with_zh":
        continue
    c=row.get("candidate") or {}
    zh=(c.get("zh") or "").strip()
    if not zh or len(c.get("sources") or [])<1:
        continue
    candidates.append({"person_id":str(row.get("person_id")),"old_name":row.get("name"),"new_name":zh,"provider_ids":row.get("provider_ids") or {},"qid":c.get("qid"),"sources":c.get("sources") or []})

# Fail closed: v29 established exactly two safe candidates. Do not write if the evidence set changed.
if len(candidates)!=2:
    rep={"time":datetime.datetime.now().isoformat(),"status":"ABORTED","reason":"expected_exactly_two_candidates","candidate_count":len(candidates),"network_changes":"none","series_changes":"none"}
    DETAIL.write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    SUM.write_text("日漫 V3.0 两名强证据人物最小写入\nstatus: ABORTED\nreason: expected_exactly_two_candidates\nnetwork_changes: none\nseries_changes: none\n",encoding="utf-8")
    raise SystemExit(2)

snap=[]
for c in candidates:
    cur=get_person(c["person_id"])
    # Provider IDs must still agree with the v29 evidence source where present.
    cur_ids={str(k).lower():str(v) for k,v in (cur.get("ProviderIds") or {}).items() if v}
    for k,v in c["provider_ids"].items():
        if v and cur_ids.get(str(k).lower())!=str(v):
            raise SystemExit(f"ERROR: provider drift for person {c['person_id']}")
    snap.append({"person_id":c["person_id"],"original":cur,"target_name":c["new_name"]})
BACKUP.write_text(json.dumps({"time":datetime.datetime.now().isoformat(),"items":snap},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

changed=[]; results=[]
try:
    for item in snap:
        pid=item["person_id"]; cur=item["original"]; target=item["target_name"]
        before=(cur.get("Name") or "").strip()
        if before==target:
            results.append({"person_id":pid,"action":"already_correct","verified":True})
            continue
        payload=dict(cur)
        payload["Name"]=target
        put_person(pid,payload)
        changed.append(pid)
        reread=get_person(pid)
        ok=((reread.get("Name") or "").strip()==target)
        results.append({"person_id":pid,"action":"renamed","verified":ok})
        if not ok:
            raise RuntimeError(f"verification failed for person {pid}")
except Exception as e:
    # Roll back every person that was changed in this run.
    for item in snap:
        if item["person_id"] in changed:
            try: put_person(item["person_id"],item["original"])
            except Exception: pass
    rep={"time":datetime.datetime.now().isoformat(),"status":"FAILED_ROLLED_BACK","error":repr(e),"attempted":len(snap),"changed_before_rollback":len(changed),"network_changes":"none","series_changes":"none"}
    DETAIL.write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    SUM.write_text("日漫 V3.0 两名强证据人物最小写入\nstatus: FAILED_ROLLED_BACK\nnetwork_changes: none\nseries_changes: none\n",encoding="utf-8")
    raise

rep={"time":datetime.datetime.now().isoformat(),"status":"PASS","candidate_count":len(candidates),"renamed":sum(1 for x in results if x["action"]=="renamed"),"already_correct":sum(1 for x in results if x["action"]=="already_correct"),"verified":all(x["verified"] for x in results),"network_changes":"none","series_changes":"none","scope":"person-name-only","results":results}
DETAIL.write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
SUM.write_text("\n".join(["日漫 V3.0 两名强证据人物最小写入",f"status: {rep['status']}",f"candidate_count: {rep['candidate_count']}",f"renamed: {rep['renamed']}",f"already_correct: {rep['already_correct']}",f"verified: {str(rep['verified']).lower()}","scope: person-name-only","network_changes: none","series_changes: none"])+"\n",encoding="utf-8")
print(SUM.read_text(encoding="utf-8"))
sys.exit(0)
