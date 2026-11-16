#!/usr/bin/env python3
"""Launch an isolated, finite Pi H10 service, SSH tunnel and PyQt GUI from a private profile."""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import shlex
import socket
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from uav_detection.gui.core import Remote

FILES = ('scripts/deployment/serve_gui.py', 'scripts/deployment/pinp2_postprocess.py',
         'scripts/evaluation/detection_eval.py', 'scripts/evaluation/raw_head_decode.py',
         'configs/deployment/pinp2_h10.json')
# Input arrives over encrypted SSH stdin; no token is included in command arguments/files.
BOOTSTRAP = r'''
import base64,hashlib,json,os,pathlib,socket,subprocess,sys
p=json.load(sys.stdin)
root=pathlib.Path(p['remote_root'])/p['run_name']
assert root.parent.is_dir(), 'Remote project root does not exist'
root.mkdir(exist_ok=False)
for name,record in p['files'].items():
 path=pathlib.PurePosixPath(name)
 assert not path.is_absolute() and '..' not in path.parts
 content=base64.b64decode(record['content'],validate=True)
 assert hashlib.sha256(content).hexdigest()==record['sha256']
 target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(content)
with socket.socket() as sock:
 sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
args=['timeout','--signal=TERM','--kill-after=20s',str(p['seconds']+30)+'s',p.get('remote_python','python3'),'-u',str(root/'scripts/deployment/serve_gui.py'),'--model-dir',p['model_dir'],'--shared-lock',p['shared_lock'],'--additional-lock',p['additional_lock'],'--port',str(port),'--max-seconds',str(p['seconds'])]
env=dict(os.environ,PINP2_GUI_TOKEN=p['token'])
with (root/'service.log').open('wb') as log:
 child=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
start_ticks=pathlib.Path('/proc')/str(child.pid)/'stat'
receipt={'root':str(root),'pid':child.pid,'start_ticks':start_ticks.read_text().split()[21],'command':args,'port':port,'source_sha256':{k:v['sha256'] for k,v in p['files'].items()}}
(root/'launch.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt))
'''
CLEANUP = r'''
import json,os,pathlib,signal,sys,time
p=json.load(sys.stdin);root=pathlib.Path(p['root']);saved=json.loads((root/'launch.json').read_text())
assert saved['pid']==p['pid'] and saved['start_ticks']==p['start_ticks']
proc=pathlib.Path('/proc')/str(p['pid'])
if proc.exists():
 actual=(proc/'cmdline').read_bytes().decode().strip('\0').split('\0')
 if actual==p['command'] and (proc/'stat').read_text().split()[21]==p['start_ticks']:
  os.kill(p['pid'],signal.SIGTERM)
  until=time.monotonic()+23
  while proc.exists() and time.monotonic()<until:
   if (proc/'stat').read_text().split()[2]=='Z':break
   time.sleep(.1)
  if proc.exists() and (proc/'stat').read_text().split()[2]!='Z':raise RuntimeError('Owned guard has not exited; its timeout remains armed')
 elif actual:
  raise RuntimeError('PID identity changed; refusing to signal')
print(json.dumps({'status':'stopped_or_already_finished','root':str(root)}))
'''


def ssh_base(profile):
    host = profile['host']
    if not isinstance(host, str) or host.startswith('-') or any(c.isspace() for c in host):
        raise ValueError('Invalid SSH host')
    args = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
            '-o', 'ServerAliveInterval=15', '-o', 'ServerAliveCountMax=3']
    if profile.get('identity_file'):
        args += ['-i', str(Path(profile['identity_file']).expanduser())]
    return args, host


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, default=ROOT / 'outputs/gui_h10_profile.json')
    parser.add_argument('--check-only', action='store_true', help='Verify service identity and close, without opening the GUI')
    args = parser.parse_args()
    if not args.profile.is_file():
        parser.error('Private connection profile missing; see docs/GUI.md / 缺少本机连接配置')
    profile = json.loads(args.profile.read_text(encoding='utf-8'))
    seconds = int(profile.get('max_seconds', 1800))
    if not 60 <= seconds <= 7200:
        parser.error('max_seconds must be 60–7200')
    for key in ('remote_root', 'model_dir', 'shared_lock', 'additional_lock'):
        if not isinstance(profile.get(key), str) or not profile[key].startswith('/'):
            parser.error(f'{key} must be an absolute Pi path')
    ssh, host = ssh_base(profile)
    run_name = 'gui-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + uuid.uuid4().hex[:6]
    output = ROOT / 'outputs/gui_connections' / run_name
    output.mkdir(parents=True, exist_ok=False)
    token = secrets.token_urlsafe(32)
    payload = {k: profile[k] for k in ('remote_root', 'model_dir', 'shared_lock', 'additional_lock')}
    payload.update(run_name=run_name, seconds=seconds, token=token, files={})
    if profile.get('remote_python'):
        payload['remote_python'] = profile['remote_python']
    for name in FILES:
        content = (ROOT / name).read_bytes()
        payload['files'][name] = {'content': base64.b64encode(content).decode(), 'sha256': hashlib.sha256(content).hexdigest()}
    launch = tunnel = gui = remote = None
    exit_code = 1
    try:
        print('Connecting to the existing Pi / 正在连接树莓派…', flush=True)
        result = subprocess.run([*ssh, host, 'python3 -c ' + shlex.quote(BOOTSTRAP)],
                                input=json.dumps(payload), text=True, capture_output=True, timeout=90, check=True)
        launch = json.loads(result.stdout)
        (output / 'remote_launch.json').write_text(json.dumps(launch, indent=2))
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        with (output / 'tunnel.log').open('w') as log:
            tunnel = subprocess.Popen([*ssh, '-o', 'ExitOnForwardFailure=yes', '-N', '-L',
                f'127.0.0.1:{port}:127.0.0.1:{launch["port"]}', host], stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT)
        url = f'http://127.0.0.1:{port}'
        health = None
        for _ in range(20):
            if tunnel.poll() is not None:
                raise RuntimeError('SSH tunnel exited; inspect the private tunnel.log')
            try:
                remote = Remote(url, token, timeout=5)
                health = remote.health()
                break
            except (RuntimeError, OSError):
                time.sleep(.5)  # Startup health checks only; never retries inference.
            finally:
                if remote:
                    remote.close()
        if health is None:
            remote_log = subprocess.run([*ssh, host, 'tail -n 12 ' + shlex.quote(launch['root'] + '/service.log')],
                                        text=True, capture_output=True, timeout=20)
            raise RuntimeError('H10 service did not become ready / 服务未就绪:\n' + remote_log.stdout[-2500:])
        expected_service = payload['files']['scripts/deployment/serve_gui.py']['sha256']
        if health.get('service_sha256') != expected_service or health.get('H10_used') is not True:
            raise RuntimeError('Unexpected service build or hardware / 服务版本或硬件身份不符')
        (output / 'health.json').write_text(json.dumps(health, indent=2))
        print('H10 ready / 真机已连接:', health['model_id'], flush=True)
        if args.check_only:
            exit_code = 0
        else:
            config = dict(profile.get('gui_config', {}))
            config.setdefault('timestamp_filter', bool(profile.get('timestamp_filter', False)))
            config.setdefault('timestamp_profiles', profile.get('timestamp_profiles', {}))
            config.update(backend='remote', url=url, max_seconds=seconds)
            config.pop('token', None)
            config_path = output / 'gui_config.json'
            config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False))
            gui = subprocess.Popen([sys.executable, str(ROOT / 'scripts/run_gui.py'), '--config', str(config_path)],
                                   env=dict(os.environ, PINP2_GUI_TOKEN=token))
            exit_code = gui.wait()
    except subprocess.CalledProcessError as exc:
        print('SSH operation failed / SSH 操作失败:', (exc.stderr or str(exc.returncode))[-2500:], file=sys.stderr)
    except (Exception, KeyboardInterrupt) as exc:
        print('Connection ended / 连接结束:', str(exc), file=sys.stderr)
    finally:
        if remote:
            remote.close()
        if gui is not None and gui.poll() is None:
            gui.terminate()
            try: gui.wait(timeout=20)
            except subprocess.TimeoutExpired: gui.kill(); gui.wait()
        if launch is not None:
            try:
                stopped = subprocess.run([*ssh, host, 'python3 -c ' + shlex.quote(CLEANUP)],
                    input=json.dumps(launch), text=True, capture_output=True, timeout=50, check=True)
                (output / 'cleanup.json').write_text(stopped.stdout)
                print('Owned H10 session stopped / 本次 H10 服务已结束', flush=True)
            except Exception as exc:
                print('Cleanup could not be confirmed; the finite remote guard remains armed:', exc, file=sys.stderr)
                exit_code = 1
        if tunnel is not None:
            tunnel.terminate()
            try: tunnel.wait(timeout=5)
            except subprocess.TimeoutExpired: tunnel.kill(); tunnel.wait()
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
