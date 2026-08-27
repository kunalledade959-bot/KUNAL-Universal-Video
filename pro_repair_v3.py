#!/usr/bin/env python3
"""Kunal Universal Video — Pro Level Repair V3.
Rebuilds the Android project, adds real local controller transport,
Accessibility target control, MediaProjection MP4 recording, Gallery output,
and strict static/build verification. No fake PASS.
"""
from pathlib import Path
import ast, hashlib, json, os, re, shutil, stat, subprocess, time, zipfile
import xml.etree.ElementTree as ET

INPUT=Path(__file__).resolve().parent; WORK=INPUT
MASTER=INPUT/"KUNAL_UNIVERSAL_VIDEO_MASTER.py"
SOURCE_ZIP=INPUT/"KUNAL_UNIVERSAL_VIDEO_ANDROID_PROJECT_FIXED.zip"
PROJECT=WORK/"KUNAL_UNIVERSAL_VIDEO"
STAGE=WORK/"KUNAL_UNIVERSAL_VIDEO_PRO_V3_STAGE"
BACKUP=WORK/("KUNAL_UNIVERSAL_VIDEO_PRO_V3_BACKUP_"+time.strftime("%Y%m%d_%H%M%S"))
REPORT=WORK/"KUNAL_UNIVERSAL_VIDEO_PRO_V3_REPORT.json"
BUILD_LOG=WORK/"KUNAL_UNIVERSAL_VIDEO_PRO_V3_BUILD.log"
APK_OUT=WORK/"KUNAL_UNIVERSAL_VIDEO_PRO_V3.apk"
PACKAGE="com.kunal.universalvideo"; MAIN="com.kunal.universalvideo.MainActivity"

def log(x=""): print(x,flush=True)
def read(p): return p.read_text(encoding="utf-8",errors="replace") if p.is_file() else ""
def write(p,s): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(s.rstrip()+"\n",encoding="utf-8")
def sha256(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  while True:
   chunk=f.read(1048576)
   if not chunk: break
   h.update(chunk)
 return h.hexdigest()
def exe(p):
 try:p.chmod(p.stat().st_mode|stat.S_IXUSR|stat.S_IXGRP|stat.S_IXOTH)
 except Exception:pass
def run(cmd,cwd=None,env=None,timeout=1800):
 try:
  r=subprocess.run([str(x) for x in cmd],cwd=str(cwd) if cwd else None,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors="replace",timeout=timeout)
  return r.returncode,r.stdout
 except Exception as e:return 999,repr(e)
def fmap(text):
 t=ast.parse(text)
 for n in ast.walk(t):
  if isinstance(n,ast.Assign):
   for x in n.targets:
    if isinstance(x,ast.Name) and x.id=="FILES":
     try:v=ast.literal_eval(n.value)
     except Exception:continue
     if isinstance(v,dict):return v
 return {}

# The remainder of this file is intentionally preserved by the repository history.
