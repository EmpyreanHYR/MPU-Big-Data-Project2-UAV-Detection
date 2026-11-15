#!/usr/bin/env python3
"""PinP2 image/folder H10 inference. Explicit NMS=0.4 by default; no CPU fallback."""
import argparse
import fcntl
import json
from pathlib import Path
import platform
import resource
import statistics
import subprocess
import time
import numpy as np
from PIL import Image
from pinp2_postprocess import DEFAULT_CONFIG, PinP2Postprocessor, load_policy
from detection_eval import prepare, sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model-dir', type=Path, required=True)
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument('--input', type=Path, help='One image or a directory of images')
    source.add_argument('--validation-data', type=Path, help='Frozen data root with validation_manifest.json')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--shared-lock', type=Path, required=True)
    p.add_argument('--additional-lock', type=Path, action='append', required=True)
    p.add_argument('--policy', type=Path, default=DEFAULT_CONFIG)
    p.add_argument('--save-ap-predictions', action='store_true', help='Additional0.001-floor processing outside pipeline timing')
    a = p.parse_args()
    assert platform.machine() == 'aarch64' and 'Raspberry Pi 5' in Path('/proc/device-tree/model').read_text()
    policy = load_policy(a.policy)
    meta = json.loads((a.model_dir / 'h10_metadata.json').read_text())
    hef = a.model_dir / 'model.hef'
    for key in ['model_id', 'family', 'weights_sha256']:
        assert meta[key] == policy[key], (key, 'model identity mismatch')
    assert sha(hef) == meta['hef_sha256'] == policy['hef_sha256']
    if a.validation_data:
        manifest_path = a.validation_data / 'validation_manifest.json'
        manifest = json.loads(manifest_path.read_text())
        rows = [(r['image'], a.validation_data / r['image']) for r in manifest['images']]
        for r in manifest['images']:
            assert sha(a.validation_data / r['image']) == r['image_sha256']
            assert sha(a.validation_data / r['label']) == r['label_sha256']
        manifest_sha = sha(manifest_path)
    else:
        files = [a.input] if a.input.is_file() else sorted(x for x in a.input.iterdir() if x.suffix.lower() in {'.jpg', '.jpeg', '.png', '.bmp'})
        rows = [(f.name, f) for f in files]
        manifest_sha = None
    assert rows and len({name for name, _ in rows}) == len(rows), 'Empty/ambiguous image source'
    locks = []
    for path in [a.shared_lock, *a.additional_lock]:
        handle = path.open('a')
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        locks.append(handle)
    assert subprocess.run(['fuser', '/dev/hailo0'], capture_output=True).returncode == 1, 'Device busy'
    from hailo_platform import VDevice, FormatType, HEF, __version__ as runtime_version
    identity = subprocess.check_output(['hailortcli', 'fw-control', 'identify'], text=True)
    assert 'HAILO10H' in identity
    a.output.mkdir(parents=True, exist_ok=False)
    (a.output / 'device_identity.txt').write_text(identity)
    (a.output / 'effective_policy.json').write_text(json.dumps(policy, indent=2) + '\n')
    mapping, used = [], set()
    infos = HEF(str(hef)).get_output_vstream_infos()
    for _, channels, height, width in meta['output_shapes']:
        found = [x.name for x in infos if tuple(x.shape) == (height, width, channels) and x.name not in used]
        assert len(found) == 1, 'Ambiguous output mapping'
        mapping.append(found[0]); used.add(found[0])
    assert len(used) == len(infos) == 8
    fixed_decoder = PinP2Postprocessor(policy)
    ap_decoder = PinP2Postprocessor(policy)
    fixed_predictions, ap_predictions, times, device_times = [], [], [], []

    def pixels(path):
        with Image.open(path) as im:
            x, geo = prepare(im)
        return np.ascontiguousarray(np.rint(x[0].transpose(1, 2, 0) * 255).astype(np.uint8)), geo

    before = subprocess.check_output(['vcgencmd', 'get_throttled'], text=True).strip()
    with VDevice() as dev:
        infer = dev.create_infer_model(str(hef)); infer.set_batch_size(1)
        infer.input().set_format_type(FormatType.UINT8)
        assert tuple(infer.input().shape) == (640, 640, 3)
        for name in mapping: infer.output(name).set_format_type(FormatType.FLOAT32)
        with infer.configure() as configured:
            buffers = {name: np.empty(infer.output(name).shape, dtype=np.float32) for name in mapping}
            bindings = configured.create_bindings(output_buffers=buffers)

            def run(x):
                bindings.input().set_buffer(x)
                configured.run([bindings], timeout=10000)
                return [np.asarray(bindings.output(name).get_buffer()).transpose(2, 0, 1)[None] for name in mapping]

            x, _ = pixels(rows[0][1])
            for _ in range(20): run(x)
            for index, (name, path) in enumerate(rows):
                start = time.perf_counter(); x, geo = pixels(path)
                tick = time.perf_counter(); raw = run(x)
                device_times.append((time.perf_counter() - tick) * 1000)
                assert all(np.isfinite(v).all() for v in raw)
                fixed = fixed_decoder.decode(raw, meta, geo)
                times.append((time.perf_counter() - start) * 1000)
                fixed_predictions.append(fixed.copy())
                if a.save_ap_predictions:
                    ap = ap_decoder.decode(raw, meta, geo, confidence=.001)
                    assert np.array_equal(ap[ap[:, 4] >= policy['confidence']], fixed)
                    ap_predictions.append(ap.copy())
                if (index + 1) % 50 == 0: print('PINP2_DEPLOYMENT', index + 1, '/', len(rows), flush=True)

    def save(name, predictions):
        np.savez_compressed(a.output / name, images=np.array([r[0] for r in rows]),
                            offsets=np.cumsum([0] + [len(x) for x in predictions]),
                            detections=np.concatenate(predictions))

    save('detections.npz', fixed_predictions)
    if a.save_ap_predictions: save('ap_detections.npz', ap_predictions)
    with (a.output / 'detections.jsonl').open('w') as f:
        for (name, _), det in zip(rows, fixed_predictions):
            f.write(json.dumps({'image': name, 'boxes_xyxy_score_class': det.tolist()}) + '\n')
    receipt = {'status': 'completed', 'H10_used': True, 'model_id': meta['model_id'],
               'weights_sha256': meta['weights_sha256'], 'hef_sha256': sha(hef),
               'runtime': runtime_version, 'policy': policy, 'policy_sha256': sha(a.policy),
               'worker_sha256': sha(__file__),
               'postprocessor_sha256': sha(Path(__file__).with_name('pinp2_postprocess.py')),
               'validation_manifest_sha256': manifest_sha, 'images': len(rows), 'warmups': 20,
               'postprocessing_fixed': fixed_decoder.receipt(),
               'postprocessing_AP': ap_decoder.receipt() if a.save_ap_predictions else None,
               'pipeline_mean_ms': statistics.mean(times), 'pipeline_p95_ms': float(np.percentile(times, 95)),
               'pipeline_FPS': 1000 / statistics.mean(times), 'pipeline_ms': times, 'device_ms': device_times,
               'peak_RSS_KiB': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
               'throttled_before': before,
               'throttled_after': subprocess.check_output(['vcgencmd', 'get_throttled'], text=True).strip(),
               'timing_scope': 'Image read/PIL preprocessing/H10 synchronous call/raw decode/coordinate restoration/explicit NMS; excludes warmups, AP-floor pass, recording and network',
               'detections_sha256': sha(a.output / 'detections.npz')}
    if a.save_ap_predictions: receipt['ap_detections_sha256'] = sha(a.output / 'ap_detections.npz')
    (a.output / 'completed.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('PINP2_DEPLOYMENT_COMPLETED', fixed_decoder.receipt(), flush=True)


if __name__ == '__main__':
    main()
