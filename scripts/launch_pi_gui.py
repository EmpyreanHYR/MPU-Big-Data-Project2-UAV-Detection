#!/usr/bin/env python3
"""Deploy the GUI and a hash-cached video once; run on the Pi's existing desktop."""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time
import uuid
from run_live_gui import ROOT, ssh_base


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--profile', type=Path, default=ROOT/'outputs/gui_h10_profile.json')
    ap.add_argument('--video', type=Path)
    ap.add_argument('--rehearse-seconds', type=int, default=0)
    ap.add_argument('--prepare-only', action='store_true')
    args = ap.parse_args()
    if args.rehearse_seconds and not 10 <= args.rehearse_seconds <= 3600:
        ap.error('Rehearsal duration must be 10–3600 seconds')
    profile = json.loads(args.profile.read_text())
    ssh, host = ssh_base(profile)
    def call(code, payload, timeout=90):
        return subprocess.run([*ssh, host, 'python3 -c '+shlex.quote(code)], input=json.dumps(payload),
                              text=True, capture_output=True, timeout=timeout, check=True).stdout
    source = args.video or Path(profile.get('pi_gui_source', profile['gui_config']['source']))
    size = source.stat().st_size
    h = hashlib.sha256()
    with source.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    sha = h.hexdigest()
    cache = profile['remote_root']+'/gui-desktop-assets/'+sha+source.suffix.lower()
    cache_started = time.monotonic()
    exists = json.loads(call("import json,sys,pathlib,hashlib;p=json.load(sys.stdin);f=pathlib.Path(p['path']);print(json.dumps(f.is_file() and hashlib.sha256(f.read_bytes()).hexdigest()==p['sha']))", {'path':cache,'sha':sha}))
    if not exists:
        print('Caching video once on Pi / 首次缓存素材:', size, 'bytes', flush=True)
        code = "import sys,pathlib,hashlib,os;f=pathlib.Path(sys.argv[1]);f.parent.mkdir(parents=True,exist_ok=True);t=f.with_suffix('.'+sys.argv[3]+'.part');h=hashlib.sha256();s=t.open('xb');n=0\nwhile True:\n b=sys.stdin.buffer.read(1048576)\n if not b:break\n s.write(b);h.update(b);n+=len(b)\ns.close();assert h.hexdigest()==sys.argv[2];t.replace(f);print(n)"
        with source.open('rb') as stream:
            subprocess.run([*ssh,host,'python3 -c '+shlex.quote(code)+' '+shlex.quote(cache)+' '+sha+' '+uuid.uuid4().hex],stdin=stream,timeout=900,check=True)
    cache_seconds = time.monotonic()-cache_started
    run = 'gui-desktop-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-')+uuid.uuid4().hex[:6]
    remote = profile['remote_root']+'/'+run
    output = ROOT/'outputs/gui_desktop_connections'/run
    output.mkdir(parents=True)
    paths = [*ROOT.glob('src/uav_detection/gui/*.py'),ROOT/'src/uav_detection/__init__.py',ROOT/'scripts/run_pi_gui.py',ROOT/'scripts/run_gui.py',ROOT/'tests/test_gui.py']
    paths += [ROOT/p for p in ('scripts/deployment/serve_gui.py','scripts/deployment/pinp2_postprocess.py','scripts/evaluation/detection_eval.py','scripts/evaluation/raw_head_decode.py','configs/deployment/pinp2_h10.json')]
    config = {'backend':'local','kind':'video','source':cache,'labels':'','confidence':.25,'display_fps':30,
              'max_seconds':1800,'loop_video':True,'output_root':remote+'/results','save_images':False,'save_video':False,
              'timestamp_filter':bool(profile.get('timestamp_filter',False)),
              'timestamp_profiles':profile.get('timestamp_profiles',{}),
              'local_model_dir':profile['model_dir'],'local_locks':[profile['shared_lock'],profile['additional_lock']]}
    payload = {'root':remote,'files':{str(p.relative_to(ROOT)):base64.b64encode(p.read_bytes()).decode() for p in paths},'config':config,
               'source_name':source.name,'seconds':args.rehearse_seconds,'prepare':args.prepare_only,'python':profile.get('remote_python','python3')}
    boot = r'''
import base64,json,pathlib,sys,os,subprocess,shlex,hashlib
p=json.load(sys.stdin);r=pathlib.Path(p['root']);r.mkdir(exist_ok=False)
for n,v in p['files'].items():
 f=r/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(base64.b64decode(v))
cached=p['config']['source'];media=r/'media';media.mkdir();friendly=media/pathlib.Path(p['source_name']).name;friendly.symlink_to(cached);p['config']['source']=str(friendly)
(r/'config.json').write_text(json.dumps(p['config'],indent=2))
# Use the existing user's native desktop, never Xvfb/offscreen or a new service.
env=dict(os.environ,DISPLAY=':0',XDG_RUNTIME_DIR='/run/user/'+str(os.getuid()))
if pathlib.Path(env['XDG_RUNTIME_DIR'],'wayland-0').exists():
 env.update(WAYLAND_DISPLAY='wayland-0',QT_QPA_PLATFORM='wayland')
else:env['QT_QPA_PLATFORM']='xcb'
cmd=[p['python'],str(r/'scripts/run_pi_gui.py'),'--config',str(r/'config.json'),'--fullscreen']
launch=r/'launch-on-pi.sh'
local_cmd=['env']+[k+'='+env[k] for k in ('DISPLAY','XDG_RUNTIME_DIR','WAYLAND_DISPLAY','QT_QPA_PLATFORM') if k in env]+['timeout','--signal=TERM','--kill-after=20s','1860s']+cmd
launch.write_text('#!/bin/sh\ncd '+shlex.quote(str(r))+'\nexec '+shlex.join(local_cmd)+'\n');launch.chmod(0o755)
receipt={'root':str(r),'video_cached':cached,'recording_enabled':False,'source_sha256':{n:hashlib.sha256(base64.b64decode(v)).hexdigest() for n,v in p['files'].items()}}
if not p['prepare']:
 if p['seconds']:cmd+=['--rehearse-seconds',str(p['seconds'])]
 cmd=['timeout','--signal=TERM','--kill-after=20s',str((p['seconds'] or 1800)+60)+'s']+cmd
 with (r/'desktop.log').open('wb') as log:
  child=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
 receipt.update(pid=child.pid,start_ticks=pathlib.Path('/proc',str(child.pid),'stat').read_text().split()[21],command=cmd)
 (r/'launch.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt))
'''
    launch = json.loads(call(boot,payload))
    receipt={**launch,'local_source_sha256':sha,'video_upload_bytes':0 if exists else size,'rehearse_seconds':args.rehearse_seconds, 'cache_check_and_upload_seconds':cache_seconds}
    (output/'launch.json').write_text(json.dumps(receipt,indent=2))
    print('Pi desktop / 树莓派桌面:',remote,flush=True)
    print('Connection receipt / 连接记录:',output,flush=True)
    print('Recording disabled / 本次不录制视频',flush=True)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
