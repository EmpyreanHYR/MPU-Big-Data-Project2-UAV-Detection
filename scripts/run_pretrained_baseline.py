#!/usr/bin/env python3
"""One explicitly authorized COCO initialization control after all scratch jobs."""
import argparse
import csv
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False))
    tmp.replace(path)


def previous_ready(previous):
    state = json.loads((previous / 'status.json').read_text())
    if state['status'].startswith(('failed', 'stopped')):
        raise RuntimeError('Previous queue stopped; do not bypass it')
    if state['status'] != 'completed':
        return False
    expected = ['fasterrcnn_r50_fpn', 'pconv_sdloss_yolov8n_p2', 'msf_ghostnet_iii']
    if json.loads((previous / 'plan.json').read_text())['jobs'] != expected:
        raise RuntimeError('Unexpected predecessor plan')
    return all((previous / job / 'completed.json').is_file() and
               json.loads((previous / job / 'completed.json').read_text()).get('epochs') == 150
               for job in expected)


def settings(root):
    spec = json.loads((root / 'configs/experiments/four_source150/baseline.json').read_text())
    value = {k: v for k, v in spec.items() if k not in {'model', 'task', 'variant'}}
    value.update(pretrained=True, resume=False, split='val')
    if (value['epochs'], value['batch'], value['imgsz'], value['seed'], value['amp']) != (150, 32, 640, 42, False):
        raise RuntimeError('Unexpected baseline settings')
    return value


def train(args):
    sys.path.insert(0, str(args.config_root / 'src'))
    from uav_detection.training import require_training_host
    require_training_host()
    import torch
    torch.set_num_threads(1 if args.check else 8)
    from ultralytics.utils.torch_utils import init_seeds
    from uav_detection.architecture import UAVYOLO, UAVDetectionModel
    init_seeds(42, deterministic=True)
    origin = json.loads(args.weights.with_suffix('.json').read_text())
    if sha(args.weights) != origin['sha256']:
        raise RuntimeError('Official weight hash changed')
    detector = UAVYOLO(str(args.config_root / 'configs/models/yolo26n-baseline.yaml'), task='detect')
    # Native load transfers every compatible tensor, including neck and box heads.
    # The 80-class COCO classifiers are rebuilt for the one-class UAV task.
    detector.load(str(args.weights))
    detector.overrides['nms'] = False
    source = detector.ckpt['model'].float()
    if source.model[-1].nc != 80 or source.model[-1].reg_max != 1 or not hasattr(source.model[-1], 'one2one_cv2'):
        raise RuntimeError('Expected official COCO YOLO26 detection checkpoint')
    source_state = source.state_dict()
    rebuilt = UAVDetectionModel(detector.model.yaml, nc=1, verbose=False)
    rebuilt.load(detector.model)
    selected = [k for k, v in rebuilt.state_dict().items()
                if k in source_state and v.shape == source_state[k].shape and
                torch.equal(v, source_state[k])]
    if 'model.0.conv.weight' not in selected or not any(k.startswith('model.23.') for k in selected):
        raise RuntimeError('Pretrained initialization did not survive model reconstruction')
    args.output.mkdir(parents=True, exist_ok=False)
    value = settings(args.config_root)
    write(args.output / 'initialization.json', {
        'initialization': 'official COCO pretrained', 'weights': origin,
        'pretrained': True, 'resume': False, 'settings': value,
        'compatible_tensors_equal_to_source': len(selected),
        'compatible_source_keys': selected, 'test_used_for_selection': False,
        'manifest_sha256': sha(args.data / 'provenance/manifest_exported.csv'),
        'script_sha256': sha(__file__)})
    if args.check:
        value.update(epochs=1, batch=2, nbs=2, imgsz=128, workers=0,
                     device='cpu', plots=False, save_period=-1)
    detector.train(data=str(args.fixture if args.check else args.data / 'dataset.yaml'),
                   project=str(args.output), name='train', exist_ok=False, **value)
    rows = list(csv.DictReader((args.output / 'train/results.csv').open()))
    expected = 1 if args.check else 150
    if len(rows) != expected:
        raise RuntimeError('Incomplete epoch schedule')
    write(args.output / ('check_passed.json' if args.check else 'completed.json'),
          {'epochs': expected, 'status': 'completed', 'finished': time.time(),
           'cpu_fixture_only': args.check})


def supervise(args):
    sys.path.insert(0, str(args.config_root / 'scripts'))
    from run_serial_suite import validate_data
    args.output.mkdir(parents=True, exist_ok=False)
    lock = (args.output / '.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    check = json.loads(args.ready.read_text())
    if check['script_sha256'] != sha(__file__) or check['weights_sha256'] != sha(args.weights):
        raise RuntimeError('Checked code or weights changed')
    write(args.output / 'plan.json', {'jobs': ['baseline_coco_pretrained'],
          'settings': settings(args.config_root), 'after': 'all ten scratch jobs',
          'retry': False, 'fallback': False, 'max_job_seconds': 86400,
          'script_sha256': sha(__file__), 'readiness': check})
    write(args.output / 'status.json', {'status': 'waiting_previous_ten', 'pid': os.getpid()})
    while not previous_ready(args.previous):
        if (args.output / 'STOP').exists():
            write(args.output / 'status.json', {'status': 'stopped_while_waiting'})
            return
        time.sleep(30)
    with (args.config_root / '.serial-suite.lock').open('a') as shared:
        fcntl.flock(shared, fcntl.LOCK_EX)
        if not previous_ready(args.previous):
            raise RuntimeError('Previous queue state changed')
        validate_data(args.data)
        child = None
        def stop(signum, frame):
            if child is not None and child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
            raise SystemExit(128 + signum)
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        command = [sys.executable, '-u', __file__, '--worker', '--authorized',
                   '--config-root', str(args.config_root), '--previous', str(args.previous),
                   '--data', str(args.data), '--weights', str(args.weights),
                   '--output', str(args.output / 'baseline_coco_pretrained')]
        with (args.output / 'baseline_coco_pretrained.log').open('wb', buffering=0) as log:
            child = subprocess.Popen(command, cwd=args.config_root, stdout=log,
                     stderr=subprocess.STDOUT, start_new_session=True,
                     env=os.environ | {'YOLO_AUTOINSTALL': 'false', 'PYTHONUNBUFFERED': '1'})
            write(args.output / 'status.json', {'status': 'running', 'child_pid': child.pid,
                  'job': 'baseline_coco_pretrained', 'started': time.time()})
            try:
                result = child.wait(timeout=86400)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=90)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
                result = 124
        if result != 0 or not (args.output / 'baseline_coco_pretrained/completed.json').is_file():
            raise RuntimeError(f'Pretrained job failed: {result}')
        write(args.output / 'status.json', {'status': 'completed', 'finished': time.time()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ['config-root', 'previous', 'data', 'weights', 'output']:
        parser.add_argument('--' + flag, type=Path, required=True)
    parser.add_argument('--ready', type=Path)
    parser.add_argument('--fixture', type=Path)
    parser.add_argument('--worker', action='store_true')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--authorized', action='store_true')
    args = parser.parse_args()
    if not args.authorized:
        parser.error('Explicit authorization required')
    try:
        train(args) if args.worker or args.check else supervise(args)
    except Exception as error:
        if args.output.is_dir():
            write(args.output / 'status.json', {'status': 'failed', 'error': str(error)})
        raise
