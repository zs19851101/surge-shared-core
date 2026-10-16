#!/usr/bin/env python3
import json, pathlib, platform, shutil, tarfile, zipfile, tempfile, os, stat, subprocess, requests

BASE=pathlib.Path.home()/"Library/Application Support/LiangZhiLocalExecutor"
BIN=BASE/"bin"; BIN.mkdir(parents=True,exist_ok=True)
OUT=BASE/"reports"/"cloudflared-install-summary.txt"
TARGET=BIN/"cloudflared"

arch=platform.machine().lower()
if arch in ("arm64","aarch64"):
    want=("darwin-arm64",)
elif arch in ("x86_64","amd64"):
    want=("darwin-amd64","darwin-x86_64")
else:
    OUT.write_text(f"status: FAIL\nreason: unsupported_arch\narch: {arch}\n",encoding="utf-8")
    raise SystemExit(2)

api="https://api.github.com/repos/cloudflare/cloudflared/releases/latest"
r=requests.get(api,headers={"Accept":"application/vnd.github+json","User-Agent":"LiangZhiCloudflaredInstaller/1.0"},timeout=30)
r.raise_for_status()
rel=r.json(); assets=rel.get("assets",[])
asset=None
for a in assets:
    n=(a.get("name") or "").lower()
    if any(x in n for x in want):
        asset=a; break
if not asset:
    OUT.write_text(f"status: FAIL\nreason: asset_not_found\narch: {arch}\nrelease: {rel.get('tag_name')}\n",encoding="utf-8")
    raise SystemExit(3)

url=asset["browser_download_url"]; name=asset["name"]
with tempfile.TemporaryDirectory() as td:
    tmp=pathlib.Path(td)/name
    with requests.get(url,stream=True,timeout=120,headers={"User-Agent":"LiangZhiCloudflaredInstaller/1.0"}) as rr:
        rr.raise_for_status()
        with open(tmp,"wb") as f:
            for chunk in rr.iter_content(chunk_size=1024*1024):
                if chunk: f.write(chunk)
    low=name.lower()
    extracted=None
    if low.endswith((".tgz",".tar.gz")):
        with tarfile.open(tmp,"r:gz") as t:
            t.extractall(td)
        for p in pathlib.Path(td).rglob("cloudflared"):
            if p.is_file(): extracted=p; break
    elif low.endswith(".zip"):
        with zipfile.ZipFile(tmp) as z: z.extractall(td)
        for p in pathlib.Path(td).rglob("cloudflared"):
            if p.is_file(): extracted=p; break
    else:
        extracted=tmp
    if not extracted or not extracted.exists():
        OUT.write_text(f"status: FAIL\nreason: extracted_binary_missing\nasset: {name}\n",encoding="utf-8")
        raise SystemExit(4)
    shutil.copy2(extracted,TARGET)

TARGET.chmod(TARGET.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
cp=subprocess.run([str(TARGET),"--version"],capture_output=True,text=True,timeout=20)
status="PASS" if cp.returncode==0 else "FAIL"
version=(cp.stdout or cp.stderr).strip().replace("\n"," ")
OUT.write_text("\n".join([
    "LiangZhi cloudflared local install",
    f"status: {status}",
    f"arch: {arch}",
    f"release: {rel.get('tag_name')}",
    f"asset: {name}",
    f"installed_path: {TARGET}",
    f"version: {version}",
    "external_exposure: False"
])+"\n",encoding="utf-8")
print(OUT.read_text(encoding="utf-8"),end="")
raise SystemExit(0 if status=="PASS" else 5)
