"""Background I/O with cooperative cancellation and one-frame GUI backpressure."""
from __future__ import annotations

from pathlib import Path
import threading
import time

import cv2
import numpy as np
from .qt import QThread, pyqtSignal

from .core import (ExportSession, IMAGE_SUFFIXES, Remote, Replay, annotate, counts, digest,
                   read_gt, read_rgb, safe_child)
from .timestamp_filter import TimestampFilter


class DetectionWorker(QThread):
    frame = pyqtSignal(object)
    message = pyqtSignal(str)
    ready = pyqtSignal(object)
    outcome = pyqtSignal(object)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = dict(config)
        self._stop = threading.Event()
        self._resume = threading.Event()
        self._resume.set()
        self._ack = threading.Event()
        self._ack.set()
        self.deadline = float('inf')

    def stop(self):
        self._stop.set()
        self._resume.set()
        self._ack.set()

    def pause(self, paused):
        self._resume.clear() if paused else self._resume.set()

    def acknowledge(self):
        self._ack.set()

    def checkpoint(self):
        while not self._stop.is_set():
            if time.monotonic() >= self.deadline:
                return False
            if self._resume.wait(.1):
                return True
        return False

    def run(self):
        cfg = self.config
        capture = writer = session = None
        remote = None
        status, error, processed = 'completed', None, 0
        try:
            replay = Replay(cfg['predictions']) if cfg['backend'] == 'replay' else None
            if cfg['backend'] == 'local':
                from .local import LocalH10
                remote = LocalH10(cfg.get('local_model_dir', ''), cfg.get('local_locks', []))
            else:
                remote = None if replay else Remote(cfg['url'], cfg.get('token', ''))
            metadata = dict(replay.metadata) if replay else remote.health()
            confidence = cfg['confidence']
            floor = metadata.get('confidence_floor', metadata.get('policy', {}).get('confidence', .25))
            if confidence < floor - 1e-9:
                raise ValueError(f'Confidence is below the saved/server floor / 低于保存阈值: {floor}')
            metadata.update(mode=cfg['backend'], confidence=confidence, source_kind=cfg['kind'],
                            frame_transport='rgb_in_memory' if cfg['backend'] == 'local' else cfg.get('transport', 'png'),
                            original_image_upload=cfg['backend'] == 'remote', display_fps_cap=cfg['display_fps'],
                            loop_video=bool(cfg.get('loop_video', False)))
            timestamp_filter = TimestampFilter(cfg.get('timestamp_filter', False), cfg.get('source'),
                                               cfg['kind'], cfg.get('timestamp_profiles', {}))
            metadata.update(timestamp_filter_enabled=timestamp_filter.enabled,
                            timestamp_filter_profile=timestamp_filter.profile,
                            timestamp_filter_status=timestamp_filter.reason,
                            raw_prediction_scope='Existing confidence/NMS output before timestamp filtering; unchanged boxes and scores')
            self.ready.emit(metadata)
            source = Path(cfg['source']) if cfg['kind'] != 'camera' else None
            files, total, source_fps = [], 0, cfg['display_fps']
            if cfg['kind'] in {'image', 'folder'}:
                if not source.exists():
                    raise ValueError('Input image/folder not found / 输入素材不存在')
                if replay:
                    if cfg['kind'] == 'folder':
                        files = [(name, safe_child(source, name)) for name in replay.records]
                    else:
                        names = [name for name in replay.records if Path(name).name == source.name]
                        if len(names) != 1:
                            raise ValueError('Image name missing or ambiguous; use folder replay / 图片名未匹配或重名')
                        files = [(names[0], source)]
                elif cfg['kind'] == 'image':
                    files = [(source.name, source)]
                else:
                    files = [(p.relative_to(source).as_posix(), p) for p in sorted(source.rglob('*'))
                             if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES]
                if not files:
                    raise ValueError('No supported images found / 未找到可处理图片')
                missing = next((name for name, path in files if not path.is_file()), None)
                if missing:
                    raise ValueError(f'Source folder does not match predictions / 素材路径不匹配: {missing}')
                total = len(files)
            else:
                if replay:
                    raise ValueError('Video/camera requires the H10 service / 视频与摄像头需要连接 H10')
                source_value = int(cfg['camera']) if cfg['kind'] == 'camera' else str(source)
                capture = cv2.VideoCapture(source_value)
                if not capture.isOpened():
                    raise ValueError('Cannot open video/camera; check file, device ID and permissions / 无法打开视频或摄像头')
                capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                measured_fps = capture.get(cv2.CAP_PROP_FPS)
                source_fps = measured_fps if np.isfinite(measured_fps) and 0 < measured_fps <= 240 else 25.
                total = max(0, int(capture.get(cv2.CAP_PROP_FRAME_COUNT))) if cfg['kind'] == 'video' else 0
            session = ExportSession(cfg['output'], metadata, cfg['save_images'])
            self.message.emit('Writing results / 结果写入: ' + str(session.folder))
            started = time.monotonic()
            self.deadline = started + cfg['max_seconds']
            cycle_frames = 0
            while self.checkpoint():
                if time.monotonic() - started >= cfg['max_seconds']:
                    status = 'time_limit'
                    self.message.emit('Time limit reached / 已到本次演示时限')
                    break
                tick = time.perf_counter()
                if files:
                    if processed == len(files):
                        break
                    name, path = files[processed]
                    expected = metadata.get('image_hashes', {}).get(name)
                    if expected and digest(path) != expected:
                        raise ValueError(f'Image hash mismatch / 图像哈希不符: {name}')
                    rgb = read_rgb(path)
                else:
                    ok, bgr = capture.read()
                    if not ok and cfg['kind'] == 'video' and cfg.get('loop_video') and processed > 0:
                        if total and cycle_frames < total:
                            raise RuntimeError('Video ended before its declared frame count / 视频提前结束')
                        capture.release()
                        capture = cv2.VideoCapture(source_value)
                        cycle_frames = 0
                        ok, bgr = capture.read()
                        if not ok:
                            raise RuntimeError('Cannot reopen video for looping / 循环视频重开失败')
                    if not ok:
                        if cfg['kind'] == 'camera' or processed == 0:
                            raise RuntimeError('Camera disconnected or video decode failed / 摄像头断开或视频解码失败')
                        if total and processed < total - 1:
                            raise RuntimeError(f'Video ended early / 视频提前结束: {processed}/{total} 帧')
                        break
                    cycle_frames += 1
                    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                    name = f'frames/{processed:08d}.png'
                gt = read_gt(cfg['labels'], name, rgb.shape[1], rgb.shape[0])
                expected_label = metadata.get('label_hashes', {}).get(name)
                if cfg['labels'] and expected_label:
                    label_path = safe_child(cfg['labels'], str(Path(name).with_suffix('.txt')))
                    if digest(label_path) != expected_label:
                        raise ValueError(f'Label hash mismatch / 标注哈希不符: {name}')
                inference_start = time.perf_counter()
                if replay:
                    boxes = replay.detect(name, confidence)
                    client_ms = (time.perf_counter() - inference_start) * 1000
                    server_ms = None
                else:
                    encoded, content_type = None, None
                    if cfg['backend'] == 'remote' and files and path.suffix.lower() in {'.jpg', '.jpeg', '.png'}:
                        encoded = path.read_bytes()
                        content_type = 'image/png' if path.suffix.lower() == '.png' else 'image/jpeg'
                    boxes, client_ms, server_ms = remote.detect(
                        rgb, encoded=encoded, content_type=content_type, transport=cfg.get('transport', 'png'))
                    boxes = boxes[boxes[:, 4] >= confidence]
                if len(boxes) and np.any(boxes[:, 2:4] > [rgb.shape[1], rgb.shape[0]]):
                    raise ValueError(f'Out-of-bounds boxes; check source alignment / 检测框越界: {name}')
                raw_boxes = boxes.copy()
                boxes, filter_info = timestamp_filter.apply(raw_boxes, rgb.shape[1], rgb.shape[0])
                packet = {'rgb': rgb, 'boxes': boxes, 'gt': gt, 'counts': counts(boxes, gt),
                          'raw_boxes': raw_boxes, 'timestamp_filter': filter_info,
                          'name': name, 'index': processed, 'total': 0 if cfg.get('loop_video') else total, 'client_ms': client_ms,
                          'server_ms': server_ms, 'mode': cfg['backend'],
                          'transport': remote.last_transport if remote else None}
                if cfg['save_video']:
                    rendered = annotate(rgb, boxes, gt)
                    if writer is None:
                        video_shape = (rgb.shape[1], rgb.shape[0])
                        video_fps = min(source_fps, cfg['display_fps'])
                        writer = cv2.VideoWriter(str(session.folder / 'annotated.avi'),
                                                 cv2.VideoWriter_fourcc(*'MJPG'), video_fps, video_shape)
                        if not writer.isOpened():
                            raise RuntimeError('Cannot create MJPG/AVI output; disable video export / 无法创建视频输出')
                    if (rgb.shape[1], rgb.shape[0]) != video_shape:
                        raise ValueError('Video export requires a fixed image size / 视频导出要求图片尺寸一致')
                    writer.write(cv2.cvtColor(rendered, cv2.COLOR_RGB2BGR))
                session.append(packet)
                processed += 1
                while not self._ack.wait(.1):
                    if self._stop.is_set():
                        break
                if self._stop.is_set():
                    break
                self._ack.clear()
                self.frame.emit(packet)
                # Cancellable pacing, including folder slideshows; never queue all frames.
                self._stop.wait(max(0., 1 / cfg['display_fps'] - (time.perf_counter() - tick)))
            if self._stop.is_set():
                status = 'stopped'
            elif time.monotonic() >= self.deadline:
                status = 'time_limit'
        except Exception as exc:
            status, error = 'failed', f'{type(exc).__name__}: {exc}'
            self.message.emit(error)
        finally:
            if remote is not None:
                remote.close()
            if capture is not None:
                capture.release()
            if writer is not None:
                writer.release()
            if session is not None:
                try:
                    session.close(status, error)
                except Exception as exc:
                    status, error = 'failed', f'Export finalization failed / 导出收尾失败: {exc}'
            self.outcome.emit({'status': status, 'error': error, 'frames': processed,
                               'output': str(session.folder) if session else None})
