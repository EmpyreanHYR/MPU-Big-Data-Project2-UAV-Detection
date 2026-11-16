#!/usr/bin/env python3
"""Bounded, loopback-only PinP2 H10 service for the PyQt client. No Torch/CPU fallback."""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import platform
import signal
import socket
import subprocess
import time
import threading

import numpy as np
from PIL import Image

from pinp2_postprocess import PinP2Postprocessor, load_policy
from detection_eval import prepare, sha


class H10Engine:
    def __init__(self, model_dir, lock_paths):
        if platform.system() != 'Linux' or platform.machine() != 'aarch64':
            raise RuntimeError('该服务只能在已授权 Raspberry Pi 5/H10 上运行；Mac 不加载模型')
        if 'Raspberry Pi 5' not in Path('/proc/device-tree/model').read_text():
            raise RuntimeError('需要 Raspberry Pi 5')
        import fcntl
        self.stack = ExitStack()
        try:
            if len(set(Path(p).resolve() for p in lock_paths)) < 2:
                raise ValueError('必须指定至少两个不同的现有共享硬件锁路径')
            for path in sorted(set(Path(p).resolve() for p in lock_paths)):
                handle = self.stack.enter_context(path.open('a'))
                try:
                    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    raise RuntimeError('H10 is busy: a shared hardware lock is held / H10 正由其他会话使用') from None
            if subprocess.run(['fuser', '/dev/hailo0'], capture_output=True, timeout=10).returncode != 1:
                raise RuntimeError('H10 设备被其他进程占用，未启动推理')
            policy = load_policy()
            meta = json.loads((model_dir / 'h10_metadata.json').read_text())
            hef = model_dir / 'model.hef'
            for key in ('model_id', 'family', 'weights_sha256'):
                if meta[key] != policy[key]:
                    raise ValueError('模型身份与部署策略不一致：' + key)
            if sha(hef) != meta['hef_sha256'] or meta['hef_sha256'] != policy['hef_sha256']:
                raise ValueError('HEF 哈希不匹配')
            identity = subprocess.check_output(['hailortcli', 'fw-control', 'identify'], text=True, timeout=10)
            if 'HAILO10H' not in identity:
                raise RuntimeError('实际设备不是 HAILO10H')
            from hailo_platform import VDevice, FormatType, HEF, __version__
            infos = HEF(str(hef)).get_output_vstream_infos()
            mapping, used = [], set()
            for _, channels, height, width in meta['output_shapes']:
                found = [x.name for x in infos if tuple(x.shape) == (height, width, channels) and x.name not in used]
                if len(found) != 1:
                    raise ValueError('无法唯一匹配原始检测头输出')
                mapping.append(found[0])
                used.add(found[0])
            if len(used) != len(infos) or len(used) != 8:
                raise ValueError('PinP2 需要八路已验证输出')
            device = self.stack.enter_context(VDevice())
            infer = device.create_infer_model(str(hef))
            self.device, self.infer = device, infer
            infer.set_batch_size(1)
            infer.input().set_format_type(FormatType.UINT8)
            if tuple(infer.input().shape) != (640, 640, 3):
                raise ValueError('输入必须为 640×640×3')
            for name in mapping:
                infer.output(name).set_format_type(FormatType.FLOAT32)
            self.configured = self.stack.enter_context(infer.configure())
            self.buffers = {name: np.empty(infer.output(name).shape, np.float32) for name in mapping}
            self.bindings = self.configured.create_bindings(output_buffers=self.buffers)
            self.mapping, self.meta = mapping, meta
            self.decoder = PinP2Postprocessor(policy)
            self.info = {'protocol': 'pinp2-demo-v1', 'backend': 'HAILO10H', 'runtime': __version__,
                         'H10_used': True, 'service_sha256': sha(__file__),
                         'model_id': meta['model_id'], 'weights_sha256': meta['weights_sha256'],
                         'hef_sha256': meta['hef_sha256'], 'policy': policy,
                         'confidence_floor': policy['confidence'], 'warmup_frames': 0}
        except BaseException:
            self.stack.close()
            raise

    def detect(self, image):
        started = time.perf_counter()
        x, geo = prepare(image)
        pixels = np.ascontiguousarray(np.rint(x[0].transpose(1, 2, 0) * 255).astype(np.uint8))
        self.bindings.input().set_buffer(pixels)
        self.configured.run([self.bindings], timeout=10000)
        raw = [np.asarray(self.bindings.output(name).get_buffer()).transpose(2, 0, 1)[None] for name in self.mapping]
        if not all(np.isfinite(v).all() for v in raw):
            raise ValueError('H10 输出含非有限数值')
        detections = self.decoder.decode(raw, self.meta, geo)
        return {'boxes_xyxy_score_class': detections.tolist(), 'image_size': list(image.size),
                'pipeline_ms': (time.perf_counter() - started) * 1000,
                'timing_scope': 'PIL preprocessing + H10 + original-coordinate NMS; excludes upload/decode/display/export',
                'postprocessing': self.decoder.receipt()}

    def close(self):
        self.stack.close()


class BoundedHTTPServer(ThreadingHTTPServer):
    """Keep-alive clients, at most four connections; device calls remain serialized."""
    daemon_threads = False
    block_on_close = True

    def __init__(self, *args, **kwargs):
        self.slots = threading.BoundedSemaphore(4)
        self.stopping = False
        self.deadline = float('inf')
        super().__init__(*args, **kwargs)

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()


def handler_factory(engine, token):
    inference_lock = threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def setup(self):
            super().setup()
            self.connection.settimeout(30)
            self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        def log_message(self, fmt, *args):
            # Request URLs and headers are deliberately not logged.
            pass

        def log_error(self, fmt, *args):
            # Preserve event types for diagnostics without logging URLs or headers.
            print('HTTP transport error:', fmt, flush=True)

        def send_json(self, status, payload):
            body = json.dumps(payload, allow_nan=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Keep-Alive', 'timeout=30')
            self.end_headers()
            self.wfile.write(body)

        def authorized(self):
            if getattr(self.server, 'stopping', False) or time.monotonic() >= getattr(self.server, 'deadline', float('inf')):
                self.close_connection = True
                self.send_json(503, {'error': 'service_ending'})
                return False
            supplied = self.headers.get('Authorization', '')
            if not hmac.compare_digest(supplied.encode(), ('Bearer ' + token).encode()):
                self.close_connection = True
                self.send_json(401, {'error': 'unauthorized'})
                return False
            return True

        def do_GET(self):
            if not self.authorized():
                return
            info = dict(engine.info)
            if hasattr(engine, 'decoder'):
                info['postprocessing'] = engine.decoder.receipt()
            self.send_json(200, info) if self.path == '/health' else self.send_json(404, {'error': 'not_found'})

        def do_POST(self):
            if not self.authorized():
                return
            if self.path != '/detect':
                self.close_connection = True
                self.send_json(404, {'error': 'not_found'})
                return
            try:
                if self.headers.get('Transfer-Encoding'):
                    raise ValueError('chunked_not_supported')
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 16_000_000:
                    self.close_connection = True
                    self.send_json(413, {'error': 'image_too_large_or_empty'})
                    return
                content_type = self.headers.get('Content-Type')
                if content_type not in {'image/png', 'image/jpeg'}:
                    self.close_connection = True
                    self.send_json(415, {'error': 'expected_png_or_jpeg'})
                    return
                data = self.rfile.read(size)
                if len(data) != size:
                    raise ValueError('incomplete_image')
                with Image.open(io.BytesIO(data)) as image:
                    expected_format = 'PNG' if content_type == 'image/png' else 'JPEG'
                    if image.format != expected_format or image.width * image.height > 24_000_000:
                        raise ValueError('invalid_image')
                    rgb = image.convert('RGB')
            except (ValueError, OSError, Image.DecompressionBombError) as exc:
                print('Image request rejected:', type(exc).__name__, flush=True)
                self.close_connection = True
                self.send_json(400, {'error': 'invalid_image'})
                return
            if not inference_lock.acquire(blocking=False):
                self.send_json(409, {'error': 'device_busy'})
                return
            try:
                try:
                    result = engine.detect(rgb)
                except Exception as exc:
                    print('H10 inference failed:', type(exc).__name__, flush=True)
                    self.send_json(503, {'error': 'inference_failed'})
                    return
            finally:
                inference_lock.release()
            try:
                self.send_json(200, result)
            except (BrokenPipeError, ConnectionResetError, socket.timeout):
                pass
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-dir', type=Path, required=True)
    parser.add_argument('--shared-lock', type=Path, required=True)
    parser.add_argument('--additional-lock', type=Path, action='append', required=True)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--max-seconds', type=int, default=1800)
    args = parser.parse_args()
    token = os.environ.get('PINP2_GUI_TOKEN', '')
    if len(token) < 32:
        parser.error('PINP2_GUI_TOKEN 必须至少 32 字符；不要把令牌放入命令行参数')
    if not 1 <= args.port <= 65535 or not 1 <= args.max_seconds <= 7200:
        parser.error('端口／时长无效（运行上限 7200 秒）')
    running = True
    def stop(signum, frame):
        nonlocal running
        running = False
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        engine = H10Engine(args.model_dir, [args.shared_lock, *args.additional_lock])
    except Exception as exc:
        parser.exit(1, f'H10 startup failed / H10 启动失败: {exc}\n')
    try:
        with BoundedHTTPServer(('127.0.0.1', args.port), handler_factory(engine, token)) as server:
            server.timeout = .5
            deadline = time.monotonic() + args.max_seconds
            server.deadline = deadline
            print(f'PinP2 H10 ready at loopback port {args.port}; max {args.max_seconds}s; no CPU fallback', flush=True)
            while running and time.monotonic() < deadline:
                server.handle_request()
            server.stopping = True
    finally:
        engine.close()


if __name__ == '__main__':
    main()
