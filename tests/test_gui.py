"""GUI/replay/HTTP contract tests. All live predictions are explicit test fixtures."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from http.server import HTTPServer

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts/deployment'))
try:
    import cv2
    import numpy as np
    from PIL import Image
    from uav_detection.gui.qt import QApplication
except ImportError as exc:
    raise unittest.SkipTest(f'Optional GUI dependencies not installed: {exc}')
from uav_detection.gui.core import (ExportSession, Remote, Replay, boxes_array, counts,
                                     digest, read_gt, safe_child)
from uav_detection.gui.worker import DetectionWorker
from uav_detection.gui.app import MainWindow, DataTable
from uav_detection.gui.qt import QUrl
from serve_gui import BoundedHTTPServer, H10Engine, handler_factory

TOKEN = 'test-fixture-token-not-a-secret-12345678'


class FixtureEngine:
    info = {'protocol': 'pinp2-demo-v1', 'backend': 'HAILO10H',
            'model_id': 'TEST_FIXTURE_NOT_A_REAL_MODEL', 'confidence_floor': .25,
            'policy': {'nms_iou': .4, 'confidence': .25}}

    def detect(self, image):
        return {'boxes_xyxy_score_class': [[1, 1, 5, 5, .9, 0]],
                'image_size': list(image.size), 'pipeline_ms': .5}


@contextlib.contextmanager
def service(engine=None):
    server = BoundedHTTPServer(('127.0.0.1', 0), handler_factory(engine or FixtureEngine(), TOKEN))
    thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}'
    finally:
        server.stopping = True
        server.shutdown()
        server.server_close()
        thread.join(2)


class GUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.images = self.root / 'images'
        self.images.mkdir()
        self.labels = self.root / 'labels'
        self.labels.mkdir()
        for i in range(3):
            Image.new('RGB', (64, 48), (i * 40, 90, 120)).save(self.images / f'{i}.png')
            (self.labels / f'{i}.txt').write_text('0 .25 .3333333 .15625 .2083333\n')
        self.predictions = self.root / 'detections.jsonl'
        self.predictions.write_text('\n'.join(json.dumps({'image': f'{i}.png',
            'boxes_xyxy_score_class': [[11, 11, 21, 21, .8, 0]]}) for i in range(3)))
        self.cfg = dict(backend='replay', kind='folder', source=str(self.images), predictions=str(self.predictions),
                        labels=str(self.labels), confidence=.25, display_fps=60, max_seconds=30,
                        save_images=False, save_video=False, output=str(self.root / 'run'),
                        camera=0, url='', token='')

    def spin(self, predicate, timeout=5):
        until = time.monotonic() + timeout
        while not predicate() and time.monotonic() < until:
            self.app.processEvents()
            time.sleep(.005)
        self.app.processEvents()
        self.assertTrue(predicate(), 'Qt operation timed out')

    def run_worker(self, config=None):
        worker = DetectionWorker(config or self.cfg)
        packets, outcomes = [], []
        def frame(packet):
            packets.append(packet)
            worker.acknowledge()
        worker.frame.connect(frame)
        worker.outcome.connect(outcomes.append)
        worker.start()
        self.spin(lambda: bool(outcomes))
        worker.wait(2000)
        self.app.processEvents()
        return outcomes[0], packets

    def test_replay_preserves_missing_vs_empty_and_floor(self):
        replay = Replay(self.predictions)
        self.assertEqual(len(replay.detect('0.png', .25)), 1)
        self.assertEqual(len(replay.detect('0.png', .9)), 0)
        with self.assertRaises(ValueError): replay.detect('absent.png', .25)
        with self.assertRaises(ValueError): replay.detect('0.png', .1)

    def test_duplicate_and_unsafe_names_rejected(self):
        for names in [('same', 'same'), ('../outside.png',), ('/outside.png',), ('C:\\a.png',)]:
            self.predictions.write_text('\n'.join(json.dumps({'image': name, 'boxes_xyxy_score_class': []}) for name in names))
            with self.assertRaises(ValueError): Replay(self.predictions)

    def test_symlink_escape_rejected(self):
        (self.images / 'link').symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError): safe_child(self.images, 'link/outside.png')

    def test_npz_offsets_and_empty_frame(self):
        path = self.root / 'pred.npz'
        np.savez(path, images=np.array(['a', 'b']), offsets=np.array([0, 0, 1]),
                 detections=np.array([[1, 1, 2, 2, .8, 0]]))
        self.assertEqual(Replay(path).detect('a', .25).shape, (0, 6))
        np.savez(path, images=np.array(['a', 'b']), offsets=np.array([0, 2, 1]),
                 detections=np.array([[1, 1, 2, 2, .8, 0]]))
        with self.assertRaises(ValueError): Replay(path)

    def test_npz_object_arrays_forbidden(self):
        path = self.root / 'bad.npz'
        np.savez(path, images=np.array(['a'], dtype=object), offsets=[0, 0], detections=np.empty((0, 6)))
        with self.assertRaises(ValueError): Replay(path)

    def test_invalid_boxes_rejected(self):
        for boxes in [[[0, 0, 0, 1, .5, 0]], [[0, 0, 2, 2, 1.1, 0]], [[0, 0, 2, 2, .5, 1]],
                      [[0, 0, 2, 2, float('nan'), 0]], [[0, 0, 2, 2, .5]]]:
            with self.assertRaises(ValueError): boxes_array(boxes)

    def test_counts_one_to_one_and_no_label(self):
        boxes = boxes_array([[1, 1, 5, 5, .9, 0], [1, 1, 5, 5, .8, 0]])
        self.assertIsNone(counts(boxes, None))
        self.assertEqual(counts(boxes, np.array([[1, 1, 5, 5]])), {'TP': 1, 'FP': 1, 'FN': 0, 'GT': 1})
        with self.assertRaises(ValueError): read_gt(self.labels, 'missing.png', 64, 48)

    def test_replay_full_export_and_readback(self):
        result, packets = self.run_worker()
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(len(packets), 3)
        summary = json.loads((self.root / 'run/summary.json').read_text())
        self.assertEqual(summary['fixed_iou_0_5'], {'TP': 3, 'FP': 0, 'FN': 0, 'GT': 3})
        self.assertEqual(len(Replay(self.root / 'run/detections.jsonl').records), 3)
        self.assertNotIn('token', summary)

    def test_missing_image_fails_before_output(self):
        (self.images / '1.png').unlink()
        result, _ = self.run_worker()
        self.assertEqual(result['status'], 'failed')
        self.assertFalse((self.root / 'run').exists())

    def test_corrupted_image_creates_partial_receipt(self):
        (self.images / '1.png').write_bytes(b'broken image')
        result, packets = self.run_worker()
        self.assertEqual(result['status'], 'failed')
        summary = json.loads((self.root / 'run/summary.json').read_text())
        self.assertEqual(summary['frames'], 1)
        self.assertEqual(summary['status'], 'failed')

    def test_hash_mismatch_detected(self):
        self.predictions.with_suffix('.meta.json').write_text(json.dumps({'image_hashes': {'0.png': 'wrong'}}))
        result, packets = self.run_worker()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(packets, [])

    def test_existing_output_never_overwritten(self):
        (self.root / 'run').mkdir()
        marker = self.root / 'run/keep.txt'
        marker.write_text('preserved')
        result, _ = self.run_worker()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(marker.read_text(), 'preserved')

    def test_image_and_video_exports(self):
        self.cfg.update(save_images=True, save_video=True)
        result, _ = self.run_worker()
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(len(list((self.root / 'run/annotated').glob('*.jpg'))), 3)
        cap = cv2.VideoCapture(str(self.root / 'run/annotated.avi'))
        try:
            self.assertEqual(int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), 3)
            self.assertTrue(cap.read()[0])
        finally:
            cap.release()

    def test_service_protocol_and_auth(self):
        with service() as url:
            remote = Remote(url, TOKEN)
            self.assertEqual(remote.health()['model_id'], 'TEST_FIXTURE_NOT_A_REAL_MODEL')
            boxes, latency, server = remote.detect(np.zeros((48, 64, 3), np.uint8))
            self.assertEqual(boxes.shape, (1, 6))
            self.assertGreater(latency, 0)
            self.assertEqual(server, .5)
            with self.assertRaises(RuntimeError): Remote(url, 'wrong').health()
            self.assertEqual(remote.health()['backend'], 'HAILO10H')
            remote.close()

    def test_mixed_image_sizes_do_not_overcount_failed_video_export(self):
        Image.new('RGB', (80, 48)).save(self.images / '1.png')
        self.cfg.update(save_video=True, labels='')
        result, _ = self.run_worker()
        summary = json.loads((self.root / 'run/summary.json').read_text())
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['frames'], 1)
        self.assertEqual(summary['frames'], 1)
        rows = (self.root / 'run/detections.jsonl').read_text().splitlines()
        self.assertEqual(len(rows), 1)

    def test_server_rejects_bad_png(self):
        with service() as url:
            with self.assertRaises(RuntimeError): Remote(url, TOKEN).request('/detect', b'not png')

    def test_remote_url_and_token_validation(self):
        for url in ['file:///tmp/a', 'http://user:pass@localhost:1234', 'http://192.0.2.1:8765', 'https://example.com/?secret=a']:
            with self.assertRaises(ValueError): Remote(url, TOKEN)
        with self.assertRaises(ValueError): Remote('http://localhost:8765', '')

    def test_service_connection_failure(self):
        # An invalid health route must fail, not silently switch to replay/CPU.
        with service() as url:
            self.cfg.update(backend='remote', url=url + '/invalid', token=TOKEN)
            result, _ = self.run_worker()
            self.assertEqual(result['status'], 'failed')

    def test_remote_folder_pipeline(self):
        with service() as url:
            self.cfg.update(backend='remote', url=url, token=TOKEN, labels='')
            result, packets = self.run_worker()
            self.assertEqual(result['status'], 'completed')
            self.assertEqual(len(packets), 3)
            self.assertEqual(packets[0]['server_ms'], .5)

    def test_remote_video_pipeline(self):
        video = self.root / 'input.avi'
        writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*'MJPG'), 25, (64, 48))
        self.assertTrue(writer.isOpened())
        for _ in range(4): writer.write(np.zeros((48, 64, 3), np.uint8))
        writer.release()
        with service() as url:
            self.cfg.update(backend='remote', kind='video', source=str(video), url=url, token=TOKEN, labels='')
            result, packets = self.run_worker()
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(len(packets), 4)

    def test_paused_worker_deadline(self):
        self.cfg['max_seconds'] = .15
        worker = DetectionWorker(self.cfg)
        results = []
        worker.ready.connect(lambda _: worker.pause(True))
        worker.frame.connect(lambda _: worker.acknowledge())
        worker.outcome.connect(results.append)
        worker.start()
        self.spin(lambda: bool(results))
        worker.wait(2000)
        self.assertEqual(results[0]['status'], 'time_limit')

    def test_window_pause_stop_restart_close(self):
        cfg = {**self.cfg, 'output_root': str(self.root / 'runs'), 'display_fps': .2}
        window = MainWindow(cfg)
        window.show()
        window.start()
        self.spin(lambda: window.last_packet is not None)
        window.toggle_pause()
        self.assertTrue(window.paused)
        self.assertFalse(window.controls.isEnabled())
        window.stop()
        self.spin(lambda: window.worker is None)
        self.assertTrue(window.controls.isEnabled())
        window.display_fps.setValue(60)
        window.start()
        self.spin(lambda: window.worker is None)
        self.assertEqual(window.last_packet['index'], 2)
        window.start()
        window.close()
        self.spin(lambda: window.worker is None)
        self.assertFalse(window.isVisible())

    def test_configuration_never_saves_token(self):
        window = MainWindow()
        window.token.setText(TOKEN)
        self.assertNotIn(TOKEN, json.dumps(window.configuration()))
        window.close()

    def test_persistent_connection_and_idle_resume(self):
        with service() as url:
            remote = Remote(url, TOKEN)
            remote.health()
            first_socket = remote.connection.sock
            remote.detect(np.zeros((48, 64, 3), np.uint8))
            self.assertIs(remote.connection.sock, first_socket)
            remote.last_response -= 9
            remote.detect(np.zeros((48, 64, 3), np.uint8))
            self.assertIsNot(remote.connection.sock, first_socket)
            remote.close()

    def test_concurrent_device_call_returns_busy_without_second_inference(self):
        class BlockingEngine(FixtureEngine):
            def __init__(self):
                self.entered = threading.Event()
                self.release = threading.Event()
                self.calls = 0
            def detect(self, image):
                self.calls += 1
                self.entered.set()
                self.release.wait(3)
                return super().detect(image)
        engine = BlockingEngine()
        with service(engine) as url:
            first, second = Remote(url, TOKEN), Remote(url, TOKEN)
            outcomes = []
            thread = threading.Thread(target=lambda: outcomes.append(first.detect(np.zeros((48,64,3),np.uint8))))
            thread.start()
            try:
                self.assertTrue(engine.entered.wait(2))
                with self.assertRaisesRegex(RuntimeError, 'HTTP 409'):
                    second.detect(np.zeros((48,64,3),np.uint8))
            finally:
                engine.release.set()
                thread.join(3)
                first.close()
                second.close()
            self.assertEqual(engine.calls, 1)
            self.assertEqual(len(outcomes), 1)

    def test_original_jpeg_and_lossy_transport_are_recorded(self):
        with service() as url:
            remote = Remote(url, TOKEN)
            rgb = np.zeros((48, 64, 3), np.uint8)
            buf = io.BytesIO()
            Image.fromarray(rgb).save(buf, format='JPEG')
            remote.detect(rgb, encoded=buf.getvalue(), content_type='image/jpeg')
            self.assertEqual(remote.last_transport['encoding'], 'original_image/jpeg')
            remote.detect(rgb, transport='jpeg')
            self.assertEqual(remote.last_transport['encoding'], 'jpeg_quality95')
            remote.close()

    def test_switch_to_video_resets_stale_labels_and_selects_live(self):
        window = MainWindow({**self.cfg, 'output_root': str(self.root / 'runs')})
        self.assertTrue(window.labels.text())
        window.kind.setCurrentIndex(window.kind.findData('video'))
        self.assertEqual(window.backend.currentData(), 'remote')
        self.assertFalse(window.labels.text())
        self.assertEqual(window.display_fps.value(), 30)
        window.labels.setText(str(self.labels))
        window.source.setText('another-video.avi')
        self.assertFalse(window.labels.text())
        self.assertIn('IR UAV Detection', window.windowTitle())
        window.close()

    def test_accessible_table_selection_sorting_and_escaping(self):
        table = DataTable(selectable=True, sortable=True)
        table.set_data(['Target', 'Score'], [['<img src="file:///private">', '10'], ['UAV 2', '2']])
        self.assertIn('<img src="file:///private">', table.toPlainText())
        self.assertNotIn('<img src=', table.toHtml())
        selected = []
        table.row_selected.connect(selected.append)
        table.activate_link(QUrl('row:1'))
        self.assertEqual(selected, [1])
        self.assertEqual(table.currentRow(), 1)
        table.activate_link(QUrl('sort:1'))
        self.assertEqual([r[1] for r in table.rows], ['2', '10'])
        table.activate_link(QUrl('sort:1'))
        self.assertEqual([r[1] for r in table.rows], ['10', '2'])
        table.activate_link(QUrl('https://example.invalid'))
        table.set_data(['Target'], [])
        self.assertEqual(table.currentRow(), -1)
        table.close()
        window = MainWindow({**self.cfg, 'output_root': str(self.root / 'runs')})
        window.finished_outcome({'output': None, 'frames': 9, 'status': 'stopped', 'error': None})
        self.assertEqual(window.metric_labels['frames'].text(), '9')
        window.close()

    def test_local_backend_uses_memory_without_http_or_encoding(self):
        class MemoryFixture:
            last_transport = {'encoding': 'rgb_in_memory', 'upload_bytes': 0}
            def __init__(self, *args): pass
            def health(self): return dict(FixtureEngine.info)
            def detect(self, rgb, **kwargs):
                assert kwargs.get('encoded') is None
                return np.array([[1, 1, 5, 5, .9, 0]]), 1., .5
            def close(self): pass
        self.cfg.update(backend='local', labels='')
        with patch('uav_detection.gui.local.LocalH10', MemoryFixture), patch('uav_detection.gui.worker.Remote', side_effect=AssertionError('HTTP must not run')):
            result, packets = self.run_worker()
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(len(packets), 3)
        self.assertEqual(packets[0]['transport']['upload_bytes'], 0)
        summary = json.loads((self.root/'run/summary.json').read_text())
        self.assertEqual(summary['frame_transport'], 'rgb_in_memory')
        self.assertFalse(summary['original_image_upload'])

    def test_loop_video_and_paint_receipt(self):
        video = self.root / 'loop.avi'
        writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*'MJPG'), 25, (64, 48))
        writer.write(np.zeros((48,64,3), np.uint8)); writer.release()
        with service() as url:
            self.cfg.update(backend='remote', kind='video', source=str(video), url=url, token=TOKEN,
                            labels='', loop_video=True, max_seconds=.15, display_fps=60)
            result, packets = self.run_worker()
        self.assertEqual(result['status'], 'time_limit')
        self.assertGreater(len(packets), 1)
        self.assertEqual(packets[-1]['total'], 0)
        window = MainWindow({**self.cfg, 'output_root': str(self.root/'runs')})
        window.show()
        window.show_frame(packets[0])
        self.spin(lambda: len(window.paint_records) > 0)
        before = len(window.paint_records)
        window.detected.viewport().update()
        self.app.processEvents()
        self.assertEqual(len(window.paint_records), before)
        self.assertEqual(window.display_receipt()['painted_frames'], 1)
        window.close()

    def test_mac_guard_before_hardware_or_model_import(self):
        if sys.platform != 'darwin':
            self.skipTest('Mac-only guard')
        with self.assertRaises(RuntimeError): H10Engine(self.root, [])
        from uav_detection.gui.local import LocalH10
        with self.assertRaises(RuntimeError): LocalH10(self.root, [])
        self.assertNotIn('hailo_platform', sys.modules)
        self.assertNotIn('torch', sys.modules)

    def test_timestamp_filter_requires_verified_source_and_size(self):
        from uav_detection.gui.timestamp_filter import TimestampFilter
        source = self.images / '0.png'
        profiles = {digest(source): {'size': [64, 48], 'region': [0, 0, 8, 8], 'coverage': .5}}
        boxes = boxes_array([[1, 1, 5, 5, .9, 0], [20, 20, 24, 24, .8, 0]])
        f = TimestampFilter(True, source, 'image', profiles)
        result, info = f.apply(boxes, 64, 48)
        np.testing.assert_array_equal(result, boxes[1:])
        self.assertEqual(info['removed'], 1)
        for disabled in [TimestampFilter(False, source, 'image', profiles),
                         TimestampFilter(True, self.images / '1.png', 'image', profiles),
                         TimestampFilter(True, source, 'camera', profiles)]:
            result, info = disabled.apply(boxes, 64, 48)
            np.testing.assert_array_equal(result, boxes)
            self.assertFalse(info['applied'])
        result, info = f.apply(boxes, 128, 96)
        np.testing.assert_array_equal(result, boxes)
        self.assertEqual(info['reason'], 'size_mismatch')

    def test_timestamp_filtered_export_preserves_raw_and_ground_truth(self):
        source = self.images / '0.png'
        cfg = {**self.cfg, 'kind': 'image', 'source': str(source), 'timestamp_filter': True,
               'timestamp_profiles': {digest(source): {'size': [64, 48], 'region': [10, 10, 22, 22]}}}
        result, packets = self.run_worker(cfg)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(len(packets[0]['boxes']), 0)
        self.assertEqual(len(packets[0]['raw_boxes']), 1)
        self.assertEqual(packets[0]['counts']['FN'], 1)
        raw = Replay(self.root / 'run/raw_detections.jsonl')
        np.testing.assert_array_equal(raw.detect('0.png', .25), Replay(self.predictions).detect('0.png', .25))
        summary = json.loads((self.root / 'run/summary.json').read_text())
        self.assertEqual((summary['raw_detections'], summary['detections'], summary['timestamp_removed']), (1, 0, 1))


if __name__ == '__main__':
    unittest.main()
