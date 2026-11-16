"""PinP2-YOLO experiment demonstration workstation (PyQt6)."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
from html import escape
import json
import os
import time
from collections import deque
from pathlib import Path
import sys
import uuid

import numpy as np
from PIL import Image
from .qt import (
    Qt, QTimer, QUrl, pyqtSignal, QColor, QDesktopServices, QImage, QKeySequence, QPixmap, QShortcut,
    QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout,
    QFrame, QGraphicsScene, QGraphicsView, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar,
    QPushButton, QScrollArea, QSpinBox, QSplitter,
    QTabWidget, QTextBrowser, QVBoxLayout, QWidget,
)

from .core import ROOT, annotate
from .worker import DetectionWorker

STYLE = '''
QWidget { background: #0c1420; color: #dce7f4; font-size: 13px; }
QLabel { background: transparent; }
QMainWindow, QScrollArea, QScrollArea > QWidget > QWidget { background: #0c1420; }
QLabel#title { font-size: 27px; font-weight: 700; color: #f1f7ff; }
QLabel#subtitle, QLabel#muted { color: #8b9eb5; }
QLabel#badge { background: #163d39; color: #58e4c1; border-radius: 10px; padding: 9px 15px; font-weight: 600; }
QFrame#card, QGroupBox { background: #111e2e; border: 1px solid #243448; border-radius: 10px; }
QGroupBox { margin-top: 14px; padding: 18px 10px 10px; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; color: #a6bcd3; }
QLabel#metric { font-size: 25px; font-weight: 600; color: #64e3c4; background: transparent; }
QPushButton { background: #1b2d43; border: 1px solid #31475f; border-radius: 6px; padding: 9px 13px; }
QPushButton:hover { background: #29435f; border-color: #55c6b6; }
QPushButton:disabled { color: #53677e; background: #142134; border-color: #213147; }
QPushButton#primary { background: #37d9b1; color: #082e2a; font-weight: 700; border: none; }
QPushButton#primary:disabled { background: #22453f; color: #718780; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox { background: #0c1725; border: 1px solid #30455e; border-radius: 5px; padding: 7px; selection-background-color: #246b67; }
QLineEdit:focus, QComboBox:focus { border-color: #45d4b9; }
QTabWidget::pane { border: 1px solid #263a50; border-radius: 5px; }
QTabBar::tab { padding: 9px 19px; background: #132135; color: #8ca4bd; }
QTabBar::tab:selected { background: #233c50; color: #6ee5ca; }
QTableWidget { background: #101c2b; alternate-background-color: #142337; border: none; gridline-color: #243548; }
QHeaderView::section { background: #1b2d43; color: #b8cce1; padding: 7px; border: none; }
QPlainTextEdit { border: none; background: #101c2b; color: #aac0d5; padding: 9px; }
QProgressBar { border: none; background: #1c2b3f; border-radius: 4px; height: 8px; text-align: center; }
QProgressBar::chunk { background: #39c7a7; border-radius: 4px; }
QCheckBox { spacing: 8px; background: transparent; }
QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #5c728b; border-radius: 3px; background: #0c1725; }
QCheckBox::indicator:checked { background: #39c7a7; border-color: #70f1d2; }
QSplitter::handle { background: #0c1420; }
QToolTip { color: #edf6ff; background: #24374b; border: 1px solid #4d657e; }
'''


class ImageView(QGraphicsView):
    painted = pyqtSignal(int, float)
    def __init__(self, placeholder):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.item = None
        self.frame_id = self.painted_id = None
        self.image_size = None
        self.auto_fit = True
        self.setMinimumSize(220, 190)
        self.setBackgroundBrush(QColor('#080f19'))
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        text = self.scene().addText(placeholder)
        text.setDefaultTextColor(QColor('#738ba5'))
        self.setToolTip('Scroll to zoom · Drag to pan · Double-click to fit / 缩放与平移')

    def set_rgb(self, rgb, frame_id=None):
        if frame_id is not None:
            self.frame_id = frame_id
        rgb = np.ascontiguousarray(rgb, dtype=np.uint8)
        height, width = rgb.shape[:2]
        qimage = QImage(rgb.data, width, height, rgb.strides[0], QImage.Format.Format_RGB888).copy()
        pixmap = QPixmap.fromImage(qimage)
        if self.item is None:
            self.scene().clear()
            self.item = self.scene().addPixmap(pixmap)
        else:
            self.item.setPixmap(pixmap)
        if self.image_size != (width, height):
            self.image_size = (width, height)
            self.scene().setSceneRect(0, 0, width, height)
            if self.auto_fit:
                self.fit()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.frame_id is not None and self.frame_id != self.painted_id:
            self.painted_id = self.frame_id
            self.painted.emit(self.frame_id, time.monotonic())

    def fit(self):
        self.auto_fit = True
        if self.item is not None:
            self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event):
        factor = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
        if .02 < self.transform().m11() * factor < 100:
            self.auto_fit = False
            self.scale(factor, factor)
        event.accept()

    def mouseDoubleClickEvent(self, event):
        self.fit()
        event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.auto_fit:
            self.fit()


class DataTable(QTextBrowser):
    """Selectable, sortable rich-text table without Cocoa's native item-view AX cache.

    Qt's synthesized row accessibility objects can crash under macOS AX scans.
    Render escaped data with internal links instead; preserve copy and keyboard access.
    """
    row_selected = pyqtSignal(int)

    def __init__(self, headers=(), selectable=False, sortable=False):
        super().__init__()
        self.headers, self.rows = list(headers), []
        self.selectable, self.sortable = selectable, sortable
        self.selected = -1
        self.sort_column, self.reverse = None, False
        self.setOpenLinks(False)
        self.setOpenExternalLinks(False)
        self.anchorClicked.connect(self.activate_link)
        self.render()

    def set_data(self, headers, rows):
        self.headers = list(headers)
        self.rows = [[str(v) for v in row] for row in rows]
        self.selected = -1
        self.sort_column, self.reverse = None, False
        self.render()

    def currentRow(self):
        return self.selected

    def selectRow(self, row):
        if 0 <= row < len(self.rows):
            self.selected = row
            self.render()
            self.row_selected.emit(row)

    def activate_link(self, url):
        try:
            command, raw = url.toString().split(':', 1)
            index = int(raw)
        except (ValueError, TypeError):
            return
        if command == 'row' and self.selectable:
            self.selectRow(index)
        elif command == 'sort' and self.sortable and 0 <= index < len(self.headers):
            self.reverse = not self.reverse if self.sort_column == index else False
            self.sort_column = index
            def key(row):
                value = row[index] if index < len(row) else ''
                try:
                    return (0, float(value))
                except ValueError:
                    return (1, value.casefold())
            self.rows.sort(key=key, reverse=self.reverse)
            self.render()

    def render(self):
        headers = []
        for i, value in enumerate(self.headers):
            label = escape(str(value))
            if self.sortable:
                label = f'<a href="sort:{i}">{label}</a>'
            headers.append(f'<th bgcolor="#1b2d43">{label}</th>')
        lines = ['<table width="100%" cellspacing="1" cellpadding="7"><tr>' + ''.join(headers) + '</tr>']
        for i, row in enumerate(self.rows):
            color = '#244b58' if i == self.selected else ('#142337' if i % 2 else '#101c2b')
            cells = []
            for j, value in enumerate(row):
                label = escape(value)
                if j == 0 and self.selectable:
                    label = f'<a href="row:{i}">{label}</a>'
                cells.append(f'<td bgcolor="{color}">{label}</td>')
            lines.append('<tr>' + ''.join(cells) + '</tr>')
        lines.append('</table>')
        self.setHtml('<style>body {color:#dce7f4;} a {color:#64e3c4;}</style>' + ''.join(lines))


class MainWindow(QMainWindow):
    def __init__(self, initial_config=None):
        super().__init__()
        self.worker = None
        self.last_packet = self.last_output = None
        self.paused = self.close_pending = False
        self.local_config = {}
        self.paint_records = []
        self._last_kind = None
        self._display_times = deque(maxlen=30)
        self.setWindowTitle('PinP2-YOLO · IR UAV Detection / 红外无人机检测')
        self.resize(1460, 950)
        self.setMinimumSize(1080, 760)
        self.setStyleSheet(STYLE)
        host = QWidget()
        self.setCentralWidget(host)
        outer = QVBoxLayout(host)
        outer.setContentsMargins(22, 18, 22, 16)
        heading = QHBoxLayout()
        title_col = QVBoxLayout()
        title = QLabel('PinP2-YOLO  /  IR UAV Detection')
        title.setObjectName('title')
        title_col.addWidget(title)
        subtitle = QLabel('EXPERIMENT WORKSTATION  ·  红外无人机检测  ·  MPU BIG DATA PROJECT')
        subtitle.setObjectName('subtitle')
        title_col.addWidget(subtitle)
        heading.addLayout(title_col, 1)
        self.badge = QLabel('Ready / 就绪 · Result replay')
        self.badge.setObjectName('badge')
        self.badge.setMinimumWidth(250)
        self.badge.setWordWrap(True)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        heading.addWidget(self.badge)
        outer.addLayout(heading)
        outer.addSpacing(10)
        body = QHBoxLayout()
        outer.addLayout(body, 1)
        self.controls = QWidget()
        controls_layout = QVBoxLayout(self.controls)
        controls_layout.setContentsMargins(0, 0, 10, 0)
        self.demo = QPushButton('Load real demo / 真实样例')
        self.demo.clicked.connect(self.load_demo)
        controls_layout.addWidget(self.demo)
        backend_group = QGroupBox('01  Engine / 检测引擎')
        form = QFormLayout(backend_group)
        self.backend = QComboBox()
        self.backend.addItem('Result replay / 历史回放', 'replay')
        self.backend.addItem('H10 live detection / 实时检测', 'remote')
        self.backend.addItem('H10 on this Pi / 本机加速', 'local')
        form.addRow(self.backend)
        self.predictions = QLineEdit()
        self.predictions.setPlaceholderText('detections.npz / .jsonl')
        self.prediction_row = self.file_row(self.predictions, 'Predictions / 预测', 'Predictions (*.npz *.jsonl)')
        form.addRow(self.prediction_row)
        self.url = QLineEdit('http://127.0.0.1:8765')
        self.url.setPlaceholderText('Service URL via SSH tunnel')
        self.token = QLineEdit(os.environ.get('PINP2_GUI_TOKEN', ''))
        self.token.setPlaceholderText('Access token / 令牌 · not saved')
        self.token.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow(self.url)
        form.addRow(self.token)
        self.policy = QLabel('Default: conf 0.25 · NMS IoU 0.40\nSaved predictions only / 仅回放已有结果')
        self.policy.setWordWrap(True)
        self.policy.setObjectName('muted')
        form.addRow(self.policy)
        controls_layout.addWidget(backend_group)
        source_group = QGroupBox('02  Input / 输入素材')
        source_form = QFormLayout(source_group)
        self.kind = QComboBox()
        for title, data in [('Image folder / 图片文件夹', 'folder'), ('Single image / 单张图片', 'image'), ('Video file / 视频文件', 'video'), ('Camera / 摄像头', 'camera')]:
            self.kind.addItem(title, data)
        source_form.addRow(self.kind)
        self.source = QLineEdit()
        self.source.setPlaceholderText('Image / video / source folder')
        source_form.addRow(self.file_row(self.source, 'Input / 素材', source=True))
        self.camera = QSpinBox()
        self.camera.setRange(0, 20)
        self.camera.setPrefix('Camera ID / 编号  ')
        source_form.addRow(self.camera)
        self.labels = QLineEdit()
        self.labels.setPlaceholderText('Optional YOLO labels / 可选标注')
        source_form.addRow(self.file_row(self.labels, 'Labels / 标注', directory=True))
        controls_layout.addWidget(source_group)
        settings_group = QGroupBox('03  Controls / Export / 演示导出')
        settings_form = QFormLayout(settings_group)
        settings_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.confidence = QDoubleSpinBox()
        self.confidence.setRange(.25, 1.)
        self.confidence.setSingleStep(.05)
        self.confidence.setValue(.25)
        self.confidence.setToolTip('Filters returned predictions; NMS follows the verified server policy. / 显示过滤，不改 NMS。')
        settings_form.addRow('Confidence ≥', self.confidence)
        self.timestamp_filter = QCheckBox('Timestamp filter / 时间区域过滤')
        self.timestamp_filter.setToolTip('Only verified media. Raw predictions are always saved. / 仅适用于已核验素材，保留原始检测结果。')
        settings_form.addRow(self.timestamp_filter)
        self.display_fps = QDoubleSpinBox()
        self.display_fps.setRange(.2, 60)
        self.display_fps.setValue(2)
        self.display_fps.setSuffix(' FPS')
        settings_form.addRow('Speed cap / 播放', self.display_fps)
        self.transport = QComboBox()
        self.transport.addItem('PNG lossless / 无损', 'png')
        self.transport.addItem('JPEG 95 / 有损加速', 'jpeg')
        self.transport.setToolTip('Video/camera frame encoding. JPEG changes pixels; original image files are uploaded unchanged. / 视频帧 JPEG 会改变像素，图片原文件直接上传。')
        settings_form.addRow('Transport / 传输', self.transport)
        self.transport_label = settings_form.labelForField(self.transport)
        self.max_minutes = QSpinBox()
        self.max_minutes.setRange(1, 120)
        self.max_minutes.setValue(30)
        self.max_minutes.setSuffix(' min')
        settings_form.addRow('Time limit / 时长上限', self.max_minutes)
        self.output = QLineEdit(str(ROOT / 'outputs' / 'gui'))
        settings_form.addRow(self.file_row(self.output, 'Output / 输出', directory=True))
        self.save_images = QCheckBox('Save annotated images / 标注图片')
        self.save_video = QCheckBox('Record video / 导出视频 (AVI, silent)')
        settings_form.addRow(self.save_images)
        settings_form.addRow(self.save_video)
        hint = QLabel('Auto-save JSONL, CSV & summary.\nPlayback / network latency is not a hardware FPS benchmark. / 非硬件测速')
        hint.setObjectName('muted')
        hint.setWordWrap(True)
        settings_form.addRow(hint)
        controls_layout.addWidget(settings_group)
        config_row = QHBoxLayout()
        for title, action in [('Save config / 保存', self.save_config), ('Load config / 加载', self.load_config)]:
            button = QPushButton(title)
            button.clicked.connect(action)
            config_row.addWidget(button)
        controls_layout.addLayout(config_row)
        controls_layout.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(self.controls)
        scroll.setMinimumWidth(345)
        scroll.setMaximumWidth(370)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body.addWidget(scroll)
        main = QVBoxLayout()
        body.addLayout(main, 1)
        metrics = QHBoxLayout()
        self.metric_labels = {}
        for key, name in [('frames', 'Frames / 已处理帧'), ('targets', 'Targets / 当前目标'), ('latency', 'Request / replay latency'), ('errors', 'TP / FP / FN · IoU 0.5')]:
            card = QFrame()
            card.setObjectName('card')
            layout = QVBoxLayout(card)
            caption = QLabel(name)
            caption.setObjectName('muted')
            layout.addWidget(caption)
            number = QLabel('—')
            number.setObjectName('metric')
            layout.addWidget(number)
            self.metric_labels[key] = number
            metrics.addWidget(card)
        main.addLayout(metrics)
        self.notice = QLabel('Replay / 历史回放 · Green: detections; amber: ground truth. Metrics require labels.')
        self.notice.setObjectName('muted')
        self.notice.setWordWrap(True)
        main.addWidget(self.notice)
        self.filter_notice = QLabel('Timestamp filter: OFF / 时间区域过滤关闭')
        self.timestamp_filter.toggled.connect(self.filter_selection_changed)
        self.source.textChanged.connect(self.filter_selection_changed)
        self.filter_notice.setObjectName('muted')
        main.addWidget(self.filter_notice)
        self.visual_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.original = ImageView('Original input / 等待素材')
        self.detected = ImageView('Detection overlay / 等待开始')
        for title, view in [('Original / 原始画面', self.original), ('Detections / 检测结果 · Scroll to zoom', self.detected)]:
            panel = QWidget()
            layout = QVBoxLayout(panel)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(QLabel(title))
            layout.addWidget(view)
            self.visual_splitter.addWidget(panel)
        main.addWidget(self.visual_splitter, 4)
        self.frame_name = QLabel('No image loaded / 尚未载入')
        self.frame_name.setObjectName('muted')
        main.addWidget(self.frame_name)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        main.addWidget(self.progress)
        actions = QHBoxLayout()
        self.start_button = QPushButton('▶  Start / 开始')
        self.start_button.setObjectName('primary')
        self.start_button.clicked.connect(self.start)
        self.pause_button = QPushButton('Pause / 暂停')
        self.pause_button.clicked.connect(self.toggle_pause)
        self.pause_button.setEnabled(False)
        self.stop_button = QPushButton('Stop / 停止')
        self.stop_button.clicked.connect(self.stop)
        self.stop_button.setEnabled(False)
        self.snapshot_button = QPushButton('Snapshot / 截图')
        self.snapshot_button.clicked.connect(self.snapshot)
        self.snapshot_button.setEnabled(False)
        self.output_button = QPushButton('Open results / 结果目录')
        self.output_button.clicked.connect(self.open_output)
        for button in [self.start_button, self.pause_button, self.stop_button, self.snapshot_button, self.output_button]:
            actions.addWidget(button)
        main.addLayout(actions)
        self.detected.painted.connect(self.frame_painted)
        self.loop_video = QCheckBox('Loop video / 循环演示')
        settings_form.addRow(self.loop_video)
        self.tabs = QTabWidget()
        details = QWidget()
        detail_layout = QHBoxLayout(details)
        self.table = DataTable(['Target', 'Score', 'x1', 'y1', 'x2', 'y2', 'Area px²'], selectable=True)
        self.table.row_selected.connect(lambda _: self.select_target())
        detail_layout.addWidget(self.table, 3)
        self.crop = ImageView('Select a target to inspect\n选择目标查看放大图')
        self.crop.setMinimumSize(180, 135)
        detail_layout.addWidget(self.crop, 1)
        self.tabs.addTab(details, 'Detections / 目标明细')
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(1000)
        self.tabs.addTab(self.log, 'Log / 运行日志')
        experiments = QWidget()
        exp_layout = QVBoxLayout(experiments)
        exp_bar = QHBoxLayout()
        self.experiment_files = QComboBox()
        for path in sorted((ROOT / 'docs/results').glob('*.csv')):
            self.experiment_files.addItem(path.stem, str(path))
        exp_bar.addWidget(self.experiment_files, 1)
        load_results = QPushButton('View table / 查看')
        load_results.clicked.connect(lambda: self.load_experiment(self.experiment_files.currentData()))
        exp_bar.addWidget(load_results)
        exp_layout.addLayout(exp_bar)
        exp_hint = QLabel('Historical experiments / 历史实验 · Original metrics and protocols; not this session. Click headers to sort.')
        exp_hint.setObjectName('muted')
        exp_layout.addWidget(exp_hint)
        self.experiment_table = DataTable(sortable=True)
        exp_layout.addWidget(self.experiment_table)
        self.tabs.addTab(experiments, 'Experiments / 实验对比')
        main.addWidget(self.tabs, 2)
        self.backend.currentIndexChanged.connect(self.backend_changed)
        self.kind.currentIndexChanged.connect(self.kind_changed)
        self.source.textChanged.connect(lambda _: self.labels.clear())
        self.backend_changed()
        self.kind_changed()
        self.statusBar().showMessage('Space: Pause / resume 暂停继续   ·   Esc: Stop 停止   ·   F11: Fullscreen 全屏')
        QShortcut(QKeySequence('Space'), self, activated=self.toggle_pause)
        QShortcut(QKeySequence('Escape'), self, activated=self.stop)
        QShortcut(QKeySequence('F11'), self, activated=self.toggle_fullscreen)
        if initial_config:
            self.apply_config(initial_config)
        else:
            demo = ROOT / 'outputs' / 'gui_demo' / 'demo.json'
            if demo.exists():
                self.apply_config(json.loads(demo.read_text(encoding='utf-8')))
        self.append_log('Client ready / 客户端就绪. Inference runs on the connected H10 device.')

    def file_row(self, field, label, filter_text='', directory=False, source=False):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        layout.addWidget(field, 1)
        button = QPushButton('…')
        button.setFixedWidth(36)
        button.setToolTip('Choose / 选择 ' + label)
        def choose():
            is_dir = directory or (source and self.kind.currentData() == 'folder')
            if is_dir:
                value = QFileDialog.getExistingDirectory(self, 'Choose / 选择 ' + label, field.text())
            else:
                value, _ = QFileDialog.getOpenFileName(self, 'Choose / 选择 ' + label, field.text(), filter_text or 'Media (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp *.mp4 *.avi *.mov *.mkv);;All files (*)')
            if value:
                field.setText(value)
        button.clicked.connect(choose)
        layout.addWidget(button)
        return widget

    def backend_changed(self):
        replay = self.backend.currentData() == 'replay'
        self.display_fps.setValue(2 if replay else 30)
        self.prediction_row.setVisible(replay)
        self.transport.setVisible(self.backend.currentData() == 'remote')
        self.transport_label.setVisible(self.backend.currentData() == 'remote')
        self.url.setVisible(self.backend.currentData() == 'remote')
        self.token.setVisible(self.backend.currentData() == 'remote')
        self.badge.setText('Ready / 就绪 · ' + ('Replay / 历史回放' if replay else 'H10 live / 实时检测'))
        self.notice.setText(('Replay / 历史回放' if replay else 'H10 live / 实时检测 · Frames are sent to the configured service') + ' · Green: detections 检测框; amber: ground truth 标注')
        self.policy.setText('Default: conf 0.25 · NMS IoU 0.40\n' + ('Saved predictions only / 仅回放已有结果' if replay else 'Connect and verify model identity on start. / 开始时验证设备与模型'))
        if self.backend.currentData() == 'local':
            self.policy.setText('Default: conf 0.25 · NMS IoU 0.40\nVerify local model identity on start / 开始时核验本机模型')
            self.badge.setText('Ready / 就绪 · H10 local / 本机')
            self.notice.setText('H10 local / 本机加速 · Video stays on this Pi / 素材不逐帧上传')
        self.kind_changed()

    def kind_changed(self):
        kind = self.kind.currentData()
        camera = kind == 'camera'
        if self._last_kind is not None and kind != self._last_kind:
            self.labels.clear()
        self._last_kind = kind
        if kind in {'video', 'camera'} and self.backend.currentData() == 'replay':
            self.backend.setCurrentIndex(self.backend.findData('remote'))
        self.camera.setVisible(camera)
        self.source.setEnabled(not camera)

    def filter_selection_changed(self, *unused):
        self.filter_notice.setText(
            'Timestamp filter: enabled · source verified on Start / 已启用，开始时核验素材'
            if self.timestamp_filter.isChecked() else 'Timestamp filter: OFF / 时间区域过滤关闭')

    def configuration(self):
        return {**self.local_config, 'loop_video': self.loop_video.isChecked(), 'backend': self.backend.currentData(), 'kind': self.kind.currentData(),
                'timestamp_filter': self.timestamp_filter.isChecked(),
                'predictions': self.predictions.text().strip(), 'source': self.source.text().strip(),
                'labels': self.labels.text().strip(), 'url': self.url.text().strip(),
                'camera': self.camera.value(), 'confidence': self.confidence.value(),
                'display_fps': self.display_fps.value(), 'max_seconds': self.max_minutes.value() * 60,
                'transport': self.transport.currentData(),
                'output_root': self.output.text().strip(), 'save_images': self.save_images.isChecked(),
                'save_video': self.save_video.isChecked()}

    def apply_config(self, cfg):
        self.local_config = {k: cfg[k] for k in ('local_model_dir', 'local_locks', 'timestamp_profiles') if k in cfg}
        self.timestamp_filter.setChecked(bool(cfg.get('timestamp_filter', False)))
        self.loop_video.setChecked(bool(cfg.get('loop_video', False)))
        for key in ('backend', 'kind', 'transport'):
            widget = getattr(self, key)
            index = widget.findData(cfg.get(key))
            if index >= 0:
                widget.setCurrentIndex(index)
        for key in ('predictions', 'source', 'labels', 'url'):
            if key in cfg:
                getattr(self, key).setText(str(cfg[key]))
        if 'output_root' in cfg:
            self.output.setText(str(cfg['output_root']))
        for key in ('camera', 'confidence', 'display_fps'):
            if key in cfg:
                getattr(self, key).setValue(cfg[key])
        if 'max_seconds' in cfg:
            self.max_minutes.setValue(max(1, int(cfg['max_seconds']) // 60))
        for key in ('save_images', 'save_video'):
            if key in cfg:
                getattr(self, key).setChecked(bool(cfg[key]))

    def load_demo(self):
        path = ROOT / 'outputs/gui_demo/demo.json'
        if not path.exists():
            QMessageBox.information(self, 'Prepare demo / 准备样例', 'Demo bundle missing. Run prepare_gui_demo.py as described in docs/GUI.md, or select your predictions and media. / 请先准备样例或选择素材。')
            return
        self.apply_config(json.loads(path.read_text(encoding='utf-8')))
        self.append_log('Loaded verified PinP2/H10 replay configuration. / 已载入真实回放配置。')

    def save_config(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Save configuration (token excluded) / 保存配置', str(ROOT / 'outputs' / 'gui-config.json'), 'JSON (*.json)')
        if path:
            try:
                Path(path).write_text(json.dumps(self.configuration(), ensure_ascii=False, indent=2), encoding='utf-8')
            except OSError as exc:
                QMessageBox.warning(self, 'Unable to save / 保存失败', str(exc))

    def load_config(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Load config / 加载', '', 'JSON (*.json)')
        if path:
            try:
                self.apply_config(json.loads(Path(path).read_text(encoding='utf-8')))
            except (OSError, ValueError, TypeError) as exc:
                QMessageBox.warning(self, 'Invalid configuration / 配置无效', str(exc))

    def start(self):
        if self.worker is not None:
            return
        cfg = self.configuration()
        if not cfg['output_root']:
            QMessageBox.warning(self, 'Output required / 缺少输出目录', 'Choose a results folder. / 请选择结果目录。')
            return
        if cfg['backend'] == 'replay' and cfg['kind'] in {'camera', 'video'}:
            QMessageBox.warning(self, 'Select engine / 选择引擎', 'Video and camera require the H10 live service. Replay supports images and folders. / 视频与摄像头需连接 H10。')
            return
        cfg['token'] = self.token.text().strip()
        cfg['output'] = str(Path(cfg.pop('output_root')).expanduser() / (datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:6]))
        self.last_packet = None
        self._display_times.clear()
        self.paint_records.clear()
        self.detected.frame_id = self.detected.painted_id = None
        self.snapshot_button.setEnabled(False)
        self.table.set_data(self.table.headers, [])
        self.progress.setRange(0, 0)
        self.paused = False
        self.pause_button.setText('Pause / 暂停')
        self.controls.setEnabled(False)
        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        for label in self.metric_labels.values():
            label.setText('—')
        self.badge.setText('Preparing / 正在准备…')
        self.worker = DetectionWorker(cfg, self)
        self.worker.frame.connect(self.show_frame)
        self.worker.message.connect(self.append_log)
        self.worker.ready.connect(self.backend_ready)
        self.worker.outcome.connect(self.finished_outcome)
        self.worker.finished.connect(self.thread_finished)
        self.worker.start()

    def backend_ready(self, metadata):
        mode = {'replay': 'Replay', 'remote': 'H10 live', 'local': 'H10 local / 本机'}.get(metadata['mode'], 'H10')
        self.badge.setText(mode + ' · Running / 运行中')
        self.append_log(f'Engine: {mode}; model: {metadata.get("model_id", "not provided")}; NMS: {metadata.get("policy", {}).get("nms_iou", "not provided")}')
        self.notice.setText(f'{mode} · {metadata.get("model_id", "model source not provided")}  |  Green: detections 检测框; amber: ground truth 标注')

    def show_frame(self, packet):
        try:
            display_fps = ((len(self._display_times) - 1) / (self._display_times[-1] - self._display_times[0])
                           if len(self._display_times) > 1 else 0.)
            self.last_packet = packet
            filtering = packet.get('timestamp_filter', {})
            if filtering.get('applied'):
                self.filter_notice.setText(f'Timestamp filter: ON · Removed {filtering["removed"]} · Raw results saved / 已过滤，原始结果保留')
            elif filtering.get('enabled'):
                self.filter_notice.setText('Timestamp filter: inactive for this source / 当前素材未匹配已核验区域，不过滤')
            else:
                self.filter_notice.setText('Timestamp filter: OFF / 时间区域过滤关闭 · Raw results saved / 原始结果保留')
            self.original.set_rgb(packet['rgb'])
            self.rendered = annotate(packet['rgb'], packet['boxes'], packet['gt'], selected=0)
            self.selected_target = 0
            self.detected.set_rgb(self.rendered, packet['index'])
            self.metric_labels['frames'].setText(str(packet['index'] + 1))
            self.metric_labels['targets'].setText(str(len(packet['boxes'])))
            self.metric_labels['latency'].setText(f'{packet["client_ms"]:.1f} ms')
            c = packet['counts']
            self.metric_labels['errors'].setText(f'{c["TP"]} / {c["FP"]} / {c["FN"]}' if c is not None else 'No labels / 无标注')
            self.frame_name.setText(f'{packet["name"]}   ·   {packet["rgb"].shape[1]} × {packet["rgb"].shape[0]}' +
                                    (f'   ·   H10 {packet["server_ms"]:.1f} ms · Display {display_fps:.1f} FPS'
                                     if packet['server_ms'] is not None else '   ·   Saved prediction replay'))
            self.progress.setRange(0, packet['total'] or 0)
            self.progress.setValue(packet['index'] + 1)
            rows = [[f'UAV {i + 1}', f'{box[4]:.3f}', *[f'{v:.1f}' for v in box[:4]],
                     f'{(box[2]-box[0])*(box[3]-box[1]):.1f}'] for i, box in enumerate(packet['boxes'])]
            self.table.set_data(self.table.headers, rows)
            self.crop.scene().clear()
            self.crop.item = None
            if len(packet['boxes']):
                self.table.selectRow(0)
            self.snapshot_button.setEnabled(True)
        except Exception as exc:
            self.append_log(f'Display failed / 显示失败: {exc}')
            self.stop()
        finally:
            if self.worker:
                self.worker.acknowledge()

    def select_target(self):
        row = self.table.currentRow()
        packet = self.last_packet
        if packet is None or not 0 <= row < len(packet['boxes']):
            return
        box = packet['boxes'][row]
        height, width = packet['rgb'].shape[:2]
        pad = max(25, int(max(box[2] - box[0], box[3] - box[1])))
        x1, y1 = max(0, int(box[0]) - pad), max(0, int(box[1]) - pad)
        x2, y2 = min(width, int(box[2]) + pad), min(height, int(box[3]) + pad)
        if row != self.selected_target:
            self.rendered = annotate(packet['rgb'], packet['boxes'], packet['gt'], selected=row)
            self.selected_target = row
            self.detected.set_rgb(self.rendered)
        self.crop.set_rgb(self.rendered[y1:y2, x1:x2])

    def frame_painted(self, index, stamp):
        self._display_times.append(stamp)
        self.paint_records.append([index, stamp])

    def display_receipt(self):
        stamps = np.array([r[1] for r in self.paint_records], dtype=float)
        gaps = np.diff(stamps)
        screen = self.screen()
        return {'painted_frames': len(stamps), 'frames': self.paint_records,
                'paint_fps': (len(stamps)-1)/(stamps[-1]-stamps[0]) if len(stamps)>1 else None,
                'p95_frame_gap_ms': float(np.percentile(gaps, 95)*1000) if len(gaps) else None,
                'max_frame_gap_ms': float(gaps.max()*1000) if len(gaps) else None,
                'qt_platform': QApplication.platformName(), 'window_visible': self.isVisible(),
                'screen_refresh_hz': screen.refreshRate() if screen else None,
                'scope': 'Unique detection frames after actual viewport paintEvent; not monitor scanout or capture FPS.'}

    def toggle_pause(self):
        if self.worker is None or not self.pause_button.isEnabled():
            return
        self.paused = not self.paused
        self._display_times.clear()
        self.worker.pause(self.paused)
        self.pause_button.setText('Resume / 继续' if self.paused else 'Pause / 暂停')
        self.badge.setText('Paused / 已暂停' if self.paused else 'Running / 运行中')

    def stop(self):
        if self.worker is not None:
            self.worker.stop()
            self.badge.setText('Stopping & saving / 正在停止…')
            self.stop_button.setEnabled(False)
            self.pause_button.setEnabled(False)

    def finished_outcome(self, result):
        self.last_output = result['output']
        if self.last_output:
            Path(self.last_output, 'display_metrics.json').write_text(json.dumps(self.display_receipt(), indent=2))
        # A stop may arrive after export but before the last queued display update.
        self.metric_labels['frames'].setText(str(result['frames']))
        labels = {'completed': 'Completed / 已完成', 'stopped': 'Stopped / 已停止', 'failed': 'Failed / 运行失败', 'time_limit': 'Time limit / 达到时限'}
        self.badge.setText(labels[result['status']] + f' · {result["frames"]} frames')
        self.append_log(self.badge.text())
        if result['error']:
            self.append_log(result['error'])
            self.tabs.setCurrentIndex(1)
        self.progress.setRange(0, max(1, result['frames']))
        self.progress.setValue(result['frames'])

    def thread_finished(self):
        self.worker.deleteLater()
        self.worker = None
        self.controls.setEnabled(True)
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        if self.close_pending:
            self.close()

    def snapshot(self):
        if self.last_packet is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, 'Save snapshot / 保存截图', str(Path(self.last_output or self.output.text()) / 'snapshot.png'), 'PNG (*.png)')
        if path:
            try:
                p = self.last_packet
                Image.fromarray(annotate(p['rgb'], p['boxes'], p['gt'])).save(path)
                self.append_log('Snapshot saved / 截图已保存: ' + path)
            except OSError as exc:
                QMessageBox.warning(self, 'Save failed / 保存失败', str(exc))

    def open_output(self):
        path = Path(self.last_output or self.output.text())
        if path.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve())))
        else:
            self.append_log('The results folder is created on the first run. / 首次运行时创建结果目录。')

    def load_experiment(self, path):
        if not path:
            return
        try:
            with Path(path).open(encoding='utf-8-sig', newline='') as stream:
                rows = list(csv.reader(stream))
            if not rows:
                raise ValueError('Empty results table / 空结果表')
            self.experiment_table.set_data(rows[0], rows[1:])
        except (OSError, ValueError) as exc:
            self.append_log('Cannot read experiment table / 读取失败: ' + str(exc))

    def append_log(self, text):
        self.log.appendPlainText(datetime.now().strftime('%H:%M:%S') + '  ' + text)

    def toggle_fullscreen(self):
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def closeEvent(self, event):
        if self.worker is not None:
            self.close_pending = True
            self.stop()
            event.ignore()
        else:
            event.accept()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, help='GUI configuration JSON (enter token in the interface)')
    args = parser.parse_args(argv)
    cfg = json.loads(args.config.read_text(encoding='utf-8')) if args.config else None
    app = QApplication(sys.argv[:1])
    app.setApplicationName('PinP2-YOLO Demo')
    app.setOrganizationName('MPU UAV Project')
    app.setStyle('Fusion')
    window = MainWindow(cfg)
    window.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
