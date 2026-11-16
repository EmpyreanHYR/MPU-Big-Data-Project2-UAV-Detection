"""Validated replay, image annotation, remote inference and auditable exports."""
from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import sys
import time
import http.client
import urllib.parse

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts' / 'evaluation'))
from detection_eval import ground_truth, match  # NumPy only; same matching as experiments

IMAGE_SUFFIXES = {'.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff', '.webp'}
VIDEO_SUFFIXES = {'.mp4', '.avi', '.mov', '.mkv', '.m4v'}
MAX_PIXELS = 24_000_000


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def safe_child(root, name):
    name = str(name).replace('\\', '/')
    part = PurePosixPath(name)
    if part.is_absolute() or '..' in part.parts or ':' in name or not name:
        raise ValueError(f'Unsafe relative path / 相对路径无效: {name}')
    root = Path(root).resolve()
    target = (root / name).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f'Path escapes the source folder / 路径超出素材目录: {name}')
    return target


def boxes_array(value):
    arr = np.asarray(value, dtype=np.float32)
    if arr.size == 0 and arr.shape in {(0,), (0, 6)}:
        return np.empty((0, 6), np.float32)
    if arr.ndim != 2 or arr.shape[1] != 6 or not np.isfinite(arr).all():
        raise ValueError('Expected finite N×6 detections [x1,y1,x2,y2,score,class] / 检测格式无效')
    if np.any(arr[:, 2:4] <= arr[:, :2]) or np.any(arr[:, :4] < 0):
        raise ValueError('Invalid box coordinates / 检测框坐标无效')
    if np.any((arr[:, 4] < 0) | (arr[:, 4] > 1)) or np.any(arr[:, 5] != 0):
        raise ValueError('Expected scores in [0,1], class 0 (UAV) / 分数或类别无效')
    return arr


def read_rgb(path):
    with Image.open(path) as im:
        if im.width * im.height > MAX_PIXELS:
            raise ValueError('Image exceeds 24 MP; resize first / 图片超过2400万像素')
        # Do not apply EXIF rotation: saved boxes refer to decoded pixel coordinates.
        return np.asarray(im.convert('RGB')).copy()


class Replay:
    """Read native deployment JSONL / NPZ without pickle or model inference."""

    def __init__(self, path):
        self.path = Path(path)
        self.records = {}
        if self.path.suffix.lower() == '.npz':
            with np.load(self.path, allow_pickle=False) as data:
                names = data['images']
                offsets = data['offsets']
                det = boxes_array(data['detections'])
                if names.ndim != 1 or names.dtype.kind not in 'US':
                    raise ValueError('images must be a 1D string array / 图片索引格式无效')
                if (offsets.ndim != 1 or offsets.dtype.kind not in 'iu'
                        or len(offsets) != len(names) + 1 or offsets[0] != 0
                        or offsets[-1] != len(det) or np.any(np.diff(offsets.astype(np.int64)) < 0)):
                    raise ValueError('NPZ offsets do not match detections / NPZ索引不一致')
                for i, name in enumerate(names):
                    self._add(str(name), det[offsets[i]:offsets[i + 1]])
        elif self.path.suffix.lower() == '.jsonl':
            for number, line in enumerate(self.path.read_text(encoding='utf-8').splitlines(), 1):
                if line.strip():
                    try:
                        row = json.loads(line)
                        self._add(row['image'], row['boxes_xyxy_score_class'])
                    except (KeyError, ValueError) as exc:
                        raise ValueError(f'JSONL 第 {number} 行：{exc}') from exc
        else:
            raise ValueError('Replay requires .npz or .jsonl / 回放文件格式不支持')
        if not self.records:
            raise ValueError('No image records found / 结果中无图片记录')
        self.metadata = {'model_id': 'Model source not provided / 未提供模型来源', 'mode': 'replay', 'confidence_floor': .25}
        sidecar = self.path.with_suffix('.meta.json')
        receipt = self.path.parent / 'completed.json'
        if sidecar.exists():
            self.metadata.update(json.loads(sidecar.read_text(encoding='utf-8')))
        elif receipt.exists():
            record = json.loads(receipt.read_text(encoding='utf-8'))
            self.metadata.update({key: record[key] for key in (
                'model_id', 'weights_sha256', 'hef_sha256', 'policy') if key in record})
            expected = record.get('detections_sha256') if self.path.name == 'detections.npz' else None
            if expected and digest(self.path) != expected:
                raise ValueError('Prediction SHA256 does not match receipt / 预测哈希不符')
            self.metadata['confidence_floor'] = record.get('policy', {}).get('confidence', .25)
        floor = self.metadata['confidence_floor']
        if not isinstance(floor, (float, int)) or not 0 <= floor <= 1:
            raise ValueError('Invalid confidence_floor / 保存阈值无效')
        self.metadata.update(mode='replay', prediction_sha256=digest(self.path))

    def _add(self, name, boxes):
        name = str(name).replace('\\', '/')
        safe_child(Path.cwd(), name)
        if name in self.records:
            raise ValueError(f'Duplicate image record / 重复图片: {name}')
        self.records[name] = boxes_array(boxes).copy()

    def detect(self, name, confidence):
        if confidence < self.metadata['confidence_floor'] - 1e-9:
            raise ValueError('Confidence is below the saved floor / 低于预测保存阈值')
        if name not in self.records:
            raise ValueError(f'Image missing in predictions / 缺少对应预测: {name}; missing predictions are not negative detections')
        boxes = self.records[name]
        return boxes[boxes[:, 4] >= confidence].copy()


def annotate(rgb, boxes, gt=None, selected=-1, labels=True):
    image = Image.fromarray(rgb)
    draw = ImageDraw.Draw(image)
    width = max(1, round(min(image.size) / 400))
    if gt is not None:
        for box in gt:
            draw.rectangle(box.tolist(), outline='#ffbf47', width=width)
    for index, row in enumerate(boxes):
        color = '#ff6c7c' if index == selected else '#29e2bc'
        draw.rectangle(row[:4].tolist(), outline=color, width=width)
        if not labels:
            continue
        text = f'UAV {row[4]:.2f}'
        x, y = float(row[0]), max(0., float(row[1]) - 14)
        draw.rectangle((x, y, min(image.width, x + 65), y + 13), fill='#102c35')
        draw.text((x + 2, y), text, fill=color)
    return np.asarray(image).copy()


def read_gt(root, name, width, height):
    if not root:
        return None
    label = safe_child(root, str(PurePosixPath(name).with_suffix('.txt')))
    if not label.is_file():
        raise ValueError(f'Missing label / 缺少标注: {label.name} (negative images require an empty .txt)')
    gt = ground_truth(label, width, height)
    if not np.isfinite(gt).all() or np.any(gt[:, :2] < -1) or np.any(gt[:, 2:] > [width + 1, height + 1]):
        raise ValueError(f'Out-of-bounds label / 标注越界: {label.name}')
    return gt


def counts(boxes, gt):
    if gt is None:
        return None
    tp = int(match(boxes, gt)[:, 0].sum())
    return {'TP': tp, 'FP': len(boxes) - tp, 'FN': len(gt) - tp, 'GT': len(gt)}


class Remote:
    """One persistent connection per worker. Failed inference requests are not retried."""
    def __init__(self, url, token, timeout=45):
        parsed = urllib.parse.urlsplit(url)
        if (parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username
                or parsed.password or parsed.query or parsed.fragment):
            raise ValueError('Invalid service URL / 服务地址无效')
        if parsed.scheme == 'http' and parsed.hostname not in {'127.0.0.1', 'localhost', '::1'}:
            raise ValueError('HTTP requires a local SSH tunnel; use HTTPS for remote hosts / 请使用 SSH 隧道')
        if not token:
            raise ValueError('Access token required / 请填写服务令牌')
        self.url, self.token, self.timeout = url.rstrip('/'), token, timeout
        self.parsed = parsed
        self.connection = None
        self.last_response = 0.
        self.last_request_started = 0.
        self.last_transport = None

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def request(self, route, payload=None, content_type='image/png'):
        # Reconnect conservatively before the server's 30s idle timeout. Include the
        # entire previous round trip: a delayed response can hide an already idle peer.
        # Resume through a fresh connection,
        # before sending anything, without replaying a possibly processed POST.
        if self.connection is not None and (
                time.monotonic() - self.last_response >= 8
                or time.monotonic() - self.last_request_started >= 8):
            self.close()
        if self.connection is None:
            cls = http.client.HTTPSConnection if self.parsed.scheme == 'https' else http.client.HTTPConnection
            self.connection = cls(self.parsed.hostname, self.parsed.port, timeout=self.timeout)
        headers = {'Authorization': 'Bearer ' + self.token}
        if payload is not None:
            headers['Content-Type'] = content_type
        path = self.parsed.path.rstrip('/') + route
        try:
            self.last_request_started = time.monotonic()
            self.connection.request('GET' if payload is None else 'POST', path, body=payload, headers=headers)
            response = self.connection.getresponse()
            raw = response.read(2_000_001)
            status = response.status
            response.close()
            self.last_response = time.monotonic()
            if len(raw) > 2_000_000:
                raise ValueError('Response too large / 服务响应过大')
            if status != 200:
                raise RuntimeError(f'Service HTTP {status} / 服务错误：检查令牌、设备占用与服务日志')
            return json.loads(raw)
        except (OSError, http.client.HTTPException) as exc:
            self.close()
            raise RuntimeError(f'Service connection failed / 连接失败: {exc}') from None
        except Exception:
            self.close()
            raise

    def health(self):
        data = self.request('/health')
        if data.get('protocol') != 'pinp2-demo-v1' or data.get('backend') != 'HAILO10H':
            raise ValueError('Unexpected inference service / 推理设备或协议不匹配')
        return data

    def detect(self, rgb, *, encoded=None, content_type=None, transport='png'):
        if encoded is None:
            buf = io.BytesIO()
            if transport == 'jpeg':
                Image.fromarray(rgb).save(buf, format='JPEG', quality=95, subsampling=0)
                content_type = 'image/jpeg'
            else:
                Image.fromarray(rgb).save(buf, format='PNG')
                content_type = 'image/png'
            encoded = buf.getvalue()
            transport_name = 'jpeg_quality95' if transport == 'jpeg' else 'png_lossless'
        else:
            transport_name = 'original_' + str(content_type)
        if len(encoded) > 16_000_000:
            raise ValueError('Encoded image exceeds 16 MB / 图片超过服务上限')
        started = time.perf_counter()
        data = self.request('/detect', encoded, content_type or 'image/png')
        if data.get('image_size') != [rgb.shape[1], rgb.shape[0]]:
            raise ValueError('Response image size mismatch / 服务返回尺寸不符')
        boxes = boxes_array(data['boxes_xyxy_score_class'])
        if len(boxes) and np.any(boxes[:, 2:4] > [rgb.shape[1], rgb.shape[0]]):
            raise ValueError('Out-of-bounds response boxes / 服务返回检测框越界')
        server_ms = float(data['pipeline_ms'])
        if not np.isfinite(server_ms) or server_ms < 0:
            raise ValueError('Invalid server timing / 服务耗时无效')
        self.last_transport = {'encoding': transport_name, 'bytes': len(encoded)}
        return boxes, (time.perf_counter() - started) * 1000, server_ms


class ExportSession:
    """Stream results to disk: bounded memory, recoverable interrupted sessions."""
    def __init__(self, output, metadata, save_images=False):
        self.folder = Path(output)
        self.folder.mkdir(parents=True, exist_ok=False)
        self.metadata = dict(metadata)
        self.save_images = save_images
        self.frames = self.targets = 0
        self.raw_targets = self.timestamp_removed = 0
        self.metrics = {'TP': 0, 'FP': 0, 'FN': 0, 'GT': 0}
        self.labeled = 0
        self.latency_sum = 0.
        self.jsonl = self.csv_file = None
        self.raw_jsonl = None
        self._summary('running')
        try:
            self.jsonl = (self.folder / 'detections.jsonl').open('w', encoding='utf-8')
            self.raw_jsonl = (self.folder / 'raw_detections.jsonl').open('w', encoding='utf-8')
            self.csv_file = (self.folder / 'detections.csv').open('w', newline='', encoding='utf-8-sig')
            self.writer = csv.writer(self.csv_file)
            self.writer.writerow(['frame', 'image', 'x1', 'y1', 'x2', 'y2', 'confidence', 'class', 'client_ms', 'server_ms'])
            if save_images:
                (self.folder / 'annotated').mkdir()
        except Exception:
            self.close('failed')
            raise

    def append(self, packet):
        row = {'image': packet['name'], 'frame': packet['index'],
               'boxes_xyxy_score_class': packet['boxes'].tolist(),
               'client_ms': packet['client_ms'], 'server_ms': packet.get('server_ms'),
               'transport': packet.get('transport'),
               'counts': packet['counts']}
        row['timestamp_filter'] = packet.get('timestamp_filter', {'enabled': False, 'removed': 0})
        raw = packet.get('raw_boxes', packet['boxes'])
        self.raw_jsonl.write(json.dumps({'image': packet['name'], 'frame': packet['index'],
                                        'boxes_xyxy_score_class': raw.tolist()}, allow_nan=False) + '\n')
        self.jsonl.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')
        for box in packet['boxes']:
            # Prevent spreadsheet formula interpretation of untrusted filenames.
            name = packet['name']
            if name.startswith(('=', '+', '-', '@', '\t', '\r')):
                name = "'" + name
            self.writer.writerow([packet['index'], name, *box.tolist(), packet['client_ms'], packet.get('server_ms')])
        self.jsonl.flush()
        self.raw_jsonl.flush()
        self.csv_file.flush()
        if self.save_images:
            Image.fromarray(annotate(packet['rgb'], packet['boxes'], packet['gt'])).save(
                self.folder / 'annotated' / f'{packet["index"]:08d}.jpg', quality=95)
        self.frames += 1
        self.targets += len(packet['boxes'])
        self.raw_targets += len(raw)
        self.timestamp_removed += row['timestamp_filter'].get('removed', 0)
        self.latency_sum += packet['client_ms']
        if packet['counts'] is not None:
            self.labeled += 1
            for key, value in packet['counts'].items():
                self.metrics[key] += value

    def _summary(self, status, error=None):
        tp, fp, fn = (self.metrics[k] for k in ('TP', 'FP', 'FN'))
        fixed_metrics = {'precision': tp / (tp + fp) if tp + fp else None,
                         'recall': tp / (tp + fn) if tp + fn else None,
                         'f1': 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None}
        report = {**self.metadata, 'status': status, 'frames': self.frames, 'detections': self.targets,
                  'raw_detections': self.raw_targets, 'timestamp_removed': self.timestamp_removed,
                  'labeled_frames': self.labeled, 'fixed_iou_0_5': self.metrics if self.labeled else None,
                  'fixed_metrics': fixed_metrics if self.labeled else None,
                  'mean_client_ms': self.latency_sum / self.frames if self.frames else None,
                  'timing_scope': 'Replay lookup or remote request; excludes GUI painting, source decoding and export. Not hardware FPS.',
                  'error': error}
        temp = self.folder / 'summary.tmp'
        temp.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')
        temp.replace(self.folder / 'summary.json')
        sidecar = {**self.metadata, 'confidence_floor': self.metadata['confidence']}
        (self.folder / 'detections.meta.json').write_text(json.dumps(sidecar, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    def close(self, status, error=None):
        for handle in (self.jsonl, self.raw_jsonl, self.csv_file):
            if handle:
                handle.close()
        self._summary(status, error)
