#!/usr/bin/env python3
"""Fail if GUI dependencies/tests or a generated-fixture window smoke check fail."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(ROOT / 'src'))


def main():
    # Import before unittest so missing GUI dependencies cannot become a green skip.
    import cv2
    import numpy
    from PIL import Image
    from uav_detection.gui.qt import QApplication, QTimer
    from uav_detection.gui.app import MainWindow
    from prepare_gui_smoke_demo import prepare

    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests',
                    '-p', 'test_gui*.py', '-v'], cwd=ROOT, check=True)
    os.chdir(ROOT)
    with tempfile.TemporaryDirectory(prefix='pinp2-gui-') as tmp:
        config = prepare(Path(tmp) / 'fixture')
        config.update(display_fps=30, max_seconds=10)
        app = QApplication([])
        app.setStyle('Fusion')
        window = MainWindow(config)
        window.show()
        report = {}

        def completed(result):
            report.update(result)
            QTimer.singleShot(100, window.close)

        def start():
            window.start()
            if window.worker:
                window.worker.outcome.connect(completed)

        QTimer.singleShot(50, start)
        QTimer.singleShot(15000, window.close)
        app.exec()
        assert report.get('status') == 'completed', report
        assert report['frames'] == 12 and report['error'] is None, report
        summary = json.loads(Path(report['output'], 'summary.json').read_text())
        assert summary['raw_detections'] == 13 and summary['detections'] == 13
        assert summary['fixed_iou_0_5'] == {'TP': 12, 'FP': 1, 'FN': 0, 'GT': 12}, summary
        assert window.paint_records, 'No Qt viewport frames were painted'
        assert 'torch' not in sys.modules and 'hailo_platform' not in sys.modules
        print(json.dumps({'status': 'passed', 'fixture': 'synthetic, not model inference',
                          'source_root': str(ROOT), 'frames': 12,
                          'qt_platform': app.platformName(), 'model_loaded': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
