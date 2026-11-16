#!/usr/bin/env python3
"""Run the Pi desktop GUI and optionally perform a bounded, unrecorded rehearsal."""
import argparse
import json
import os
from pathlib import Path
import platform
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--rehearse-seconds', type=int, default=0)
    parser.add_argument('--fullscreen', action='store_true')
    args = parser.parse_args()
    if platform.system() != 'Linux' or platform.machine() != 'aarch64':
        parser.error('Requires the existing Raspberry Pi desktop / 请在树莓派桌面运行')
    if args.rehearse_seconds and not 10 <= args.rehearse_seconds <= 3600:
        parser.error('Rehearsal duration must be 10–3600 seconds')
    from uav_detection.gui.qt import QApplication, QTimer
    from uav_detection.gui.app import MainWindow
    cfg = json.loads(args.config.read_text())
    cfg.update(save_video=False, save_images=False)
    if args.rehearse_seconds:
        cfg.update(loop_video=True, max_seconds=args.rehearse_seconds + 60)
    app = QApplication(sys.argv[:1])
    app.setStyle('Fusion')
    if app.platformName() in {'offscreen', 'minimal'}:
        raise RuntimeError('Native display required; offscreen is not a desktop rehearsal')
    window = MainWindow(cfg)
    window.showFullScreen() if args.fullscreen else window.showMaximized()
    if args.rehearse_seconds:
        report = {'status': 'starting', 'recording_enabled': False, 'samples': []}
        timer = QTimer()
        def sample():
            values = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
            temp = Path('/sys/class/thermal/thermal_zone0/temp')
            report['samples'].append({'monotonic': time.monotonic(), 'rss_kib': int(values['VmRSS'].split()[0]),
                                      'temperature_c': int(temp.read_text())/1000 if temp.exists() else None,
                                      'painted_frames': len(window.paint_records)})
        timer.timeout.connect(sample)
        timer.start(1000)
        sample()
        def finish(result):
            report.update(result)
            def save_and_close():
                report['display'] = window.display_receipt()
                report['torch_imported'] = 'torch' in sys.modules
                Path(cfg['output_root']).mkdir(parents=True, exist_ok=True)
                Path(cfg['output_root'], 'rehearsal.json').write_text(json.dumps(report, indent=2))
                window.grab().save(str(Path(cfg['output_root'])/'desktop_preview.png'))
                window.close()
            QTimer.singleShot(300, save_and_close)
        def start():
            window.start()
            if window.worker:
                window.worker.outcome.connect(finish)
                QTimer.singleShot(args.rehearse_seconds * 1000, window.stop)
        QTimer.singleShot(500, start)
    code = app.exec()
    if args.rehearse_seconds:
        return 0 if report.get('status') in {'stopped', 'time_limit'} and report.get('display', {}).get('painted_frames', 0) > 0 else 1
    return code


if __name__ == '__main__':
    raise SystemExit(main())
