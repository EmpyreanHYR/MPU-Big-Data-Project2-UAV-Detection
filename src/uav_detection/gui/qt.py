"""Use PyQt6 on desktops, or the existing system PyQt5 on Raspberry Pi OS."""
try:
    from PyQt6.QtCore import Qt, QTimer, QUrl, QThread, pyqtSignal
    from PyQt6.QtGui import QColor, QDesktopServices, QImage, QKeySequence, QPixmap, QShortcut
    from PyQt6.QtWidgets import (
        QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout,
        QFrame, QGraphicsScene, QGraphicsView, QGroupBox, QHBoxLayout, QHeaderView,
        QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar,
        QPushButton, QScrollArea, QSpinBox, QSplitter, QTableWidget, QTableWidgetItem,
        QTabWidget, QTextBrowser, QVBoxLayout, QWidget,
    )
    BINDING = 'PyQt6'
except ModuleNotFoundError as exc:
    if exc.name != 'PyQt6':
        raise
    from PyQt5.QtCore import Qt, QTimer, QUrl, QThread, pyqtSignal
    from PyQt5.QtGui import QColor, QDesktopServices, QImage, QKeySequence, QPixmap
    from PyQt5.QtWidgets import (
        QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout,
        QFrame, QGraphicsScene, QGraphicsView, QGroupBox, QHBoxLayout, QHeaderView,
        QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar,
        QPushButton, QScrollArea, QSpinBox, QSplitter, QTableWidget, QTableWidgetItem,
        QTabWidget, QTextBrowser, QVBoxLayout, QWidget, QShortcut,
    )
    BINDING = 'PyQt5'
