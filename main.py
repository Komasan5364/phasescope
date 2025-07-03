import sys
import time
import signal
import math
import numpy as np

import soundcard as sc

from PySide6.QtCore import Qt, QPointF, QLineF, QRectF
from PySide6.QtGui import QColor, QPen, QBrush, QLinearGradient, QPainterPath, QPainter, QPixmap, QImage
from PySide6.QtWidgets import QMainWindow, QApplication, QWidget, QVBoxLayout, QStackedLayout, QComboBox, QSlider, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsSimpleTextItem


SIZE = 320

device = None

def get_devices():
    dev = {i._id: i.name for i in sc.all_speakers()}
    dev |= {i._id: i.name for i in sc.all_microphones()}
    return dev

def set_device(name):
    global device
    ret = True
    if device:
        device.__exit__(..., ..., ...)
    if name:
        try:
            device = sc.get_microphone(id=name, include_loopback=True).recorder(samplerate=48000, channels=[0, 1], blocksize=128)
        except Exception:
            ret = False
            device = None
        if device:
            device.__enter__()
    else:
        device = None
    return ret

level = None

class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)

        self.setWindowTitle('phasescope')
        self.setFixedSize(SIZE, SIZE + 20)

        self.widget = MainView()
        self.setCentralWidget(self.widget)

        self.t0 = time.perf_counter()

        self.startTimer(1)

    def positionChanged(self, position):
        self.at = position / 1000
        self.atc = time.perf_counter()

    def timerEvent(self, event):
        t = time.perf_counter()

        if device:
            try:
                buf = device.record(128)
            except Exception as ex:
                print(ex)
                buf = np.zeros((0, 2))
        else:
            buf = np.zeros((0, 2))

        self.widget.scope.pushSample(buf, self.t0, t)
        self.widget.scope.updateImage(t)
        self.t0 = t

class MainView(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self.main = QVBoxLayout()
        self.main.setContentsMargins(0, 0, 0, 0)
        self.main.setSpacing(0)

        self.level = LevelSlider()
        self.scope = PhasescopeView()
        self.dev = DeviceSelectionWidget()

        self.scope.setFixedSize(SIZE, SIZE)
        self.dev.setFixedHeight(20)


        self.vscope = QStackedLayout()

        self.vscope.addWidget(self.scope)
        self.vscope.addWidget(self.level)
        self.vscope.setStackingMode(QStackedLayout.StackingMode.StackAll)

        self.main.addLayout(self.vscope, 0)
        self.main.addWidget(self.dev)

        self.setLayout(self.main)

class DeviceSelectionWidget(QComboBox):
    def __init__(self):
        QComboBox.__init__(self)

        self.devs = get_devices()
        self.addItem('<Not active>')
        self.addItems(self.devs.values())

        default = sc.default_speaker()._id

        if default in self.devs and set_device(default):
            idx = list(self.devs.keys()).index(default) + 1
        else:
            idx = 0
        self.setCurrentIndex(idx)

        self.activated.connect(self.change)

    def change(self, index):
        if index != 0:
            name = list(self.devs.keys())[index - 1]
        else:
            name = None

        self.clear()
        self.devs = get_devices()
        self.addItem('<Not active>')
        self.addItems(self.devs.values())

        if index != 0:
            if name in self.devs and set_device(name):
                idx = list(self.devs.keys()).index(name) + 1
            else:
                idx = 0
            self.setCurrentIndex(idx)
        else:
            set_device(None)
            self.setCurrentIndex(0)

class LevelSlider(QSlider):
    def __init__(self):
        QSlider.__init__(self)

        self.setFixedSize(120, 20)

        self.setOrientation(Qt.Orientation.Horizontal)
        self.setRange(0, 9)
        self.setValue(0)

        self.setSingleStep(1)
        self.setPageStep(2)

        self.setTickInterval(1)
        self.setTickPosition(QSlider.TickPosition.TicksBelow)

        self.ss0 = """\
        QSlider::groove:horizontal {
            background: 2px solid;
            background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                stop: 0 #00ffff, stop: 0.11111 #008000, stop: 1 #00e000);
            height: 2px;
            border-radius: 1px;
            left: 10px;
            right: 10px;
        }

        QSlider::handle:horizontal {
            background: #00e0e0;
            width: 8px;
            margin: -4px -1px;
            border-radius: 4px;
            border: 1px solid #00e0e0;
        }

        QSlider::handle:horizontal:hover {
            background: #00ffff;
            border: 1px solid #00ffff;
        }

        QSlider::add-page:horizontal {
            background: #404040;
        }
        """

        self.ss1 = """\
        QSlider::groove:horizontal {
            background: 2px solid;
            background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                stop: 0 #00ffff, stop: 0.11111 #008000, stop: 1 #00e000);
            height: 2px;
            border-radius: 1px;
            left: 10px;
            right: 10px;
        }

        QSlider::handle:horizontal {
            background: #00c000;
            width: 8px;
            margin: -4px -1px;
            border-radius: 4px;
            border: 1px solid #00c000;
        }

        QSlider::handle:horizontal:hover {
            background: #00e000;
            border: 1px solid #00e000;
        }

        QSlider::add-page:horizontal {
            background: #404040;
        }
        """

        self.setStyleSheet(self.ss0)

        self.valueChanged.connect(self.change)

    def change(self, value):
        global level
        if value == 0:
            level = None
            self.setStyleSheet(self.ss0)
        else:
            level = (value - 1) * -3.
            self.setStyleSheet(self.ss1)


class PhasescopeView(QGraphicsView):
    def __init__(self):
        QGraphicsView.__init__(self)

        self.setRenderHints(QPainter.RenderHint.Antialiasing)

        self.pan = np.zeros((0,))
        self.corr = np.zeros((0,))
        self.samples = np.zeros((0, 2))
        self.times = np.zeros((0,))
        self.max_pluned = np.zeros((0,))
        self.times_pluned = np.zeros((0,))

        self.amp = -24.
        self.amp_goal = -24.
        self.t0 = time.perf_counter()

        scene = QGraphicsScene()
        scene.setSceneRect(-1, -1, 2, 2)

        pen = QPen()
        pen.setColor(QColor.fromRgb(64, 64, 64))
        pen.setWidthF(2.)
        brush = QBrush(Qt.BrushStyle.SolidPattern)
        brush.setColor(QColor.fromRgb(16, 16, 16))

        self.setBackgroundBrush(brush)

        path = QPainterPath()
        path.moveTo(QPointF(SIZE * -0.4, 0.))
        path.lineTo(QPointF(0., SIZE * -0.4))
        path.lineTo(QPointF(SIZE * 0.4, 0.))
        path.lineTo(QPointF(0., SIZE * 0.4))
        path.closeSubpath()
        scene.addPath(path, pen, brush)
        scene.addLine(QLineF(SIZE * -0.4, 0., SIZE * 0.4, 0.), pen)
        scene.addLine(QLineF(0., SIZE * -0.4, 0., SIZE * 0.4), pen)
        scene.addLine(QLineF(SIZE * -0.2, SIZE * -0.2, SIZE * 0.2, SIZE * 0.2), pen)
        scene.addLine(QLineF(SIZE * -0.2, SIZE * 0.2, SIZE * 0.2, SIZE * -0.2), pen)

        brush_text = QBrush(Qt.BrushStyle.SolidPattern)
        brush_text.setColor(QColor.fromRgb(64, 64, 64))
        self.item_level = QGraphicsSimpleTextItem('0.0 dB')
        self.item_level.setBrush(brush_text)
        self.item_level.setPos(QPointF(SIZE * -0.4, 0.))
        self.item_level.setRotation(45.)
        scene.addItem(self.item_level)

        self.item = QGraphicsPixmapItem()
        self.item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        self.item.setPos(-SIZE / 2, -SIZE / 2)

        grad = QLinearGradient(QPointF(0., SIZE * -0.4), QPointF(0, SIZE * 0.4))
        grad.setColorAt(0.5, QColor.fromRgb(0, 48, 0))
        grad.setColorAt(0.75, QColor.fromRgb(48, 48, 0))
        grad.setColorAt(1., QColor.fromRgb(48, 0, 0))
        scene.addRect(QRectF(SIZE * 0.44, SIZE * -0.4, SIZE * 0.02, SIZE * 0.8), pen, QBrush(grad))
        pen_none = QPen(Qt.PenStyle.NoPen)
        grad.setColorAt(0.5, QColor.fromRgb(0, 192, 0))
        grad.setColorAt(0.75, QColor.fromRgb(192, 192, 0))
        grad.setColorAt(1., QColor.fromRgb(192, 0, 0))
        self.item_corr = scene.addRect(QRectF(SIZE * 0.44, 0., SIZE * 0.02, 1.), pen_none, QBrush(grad))

        scene.addRect(QRectF(SIZE * -0.4, SIZE * 0.44, SIZE * 0.8, SIZE * 0.02), pen, brush)
        pen_main = QPen()
        pen_main.setColor(QColor.fromRgb(192, 192, 192))
        pen_main.setWidthF(2.)
        brush_main = QBrush(Qt.BrushStyle.SolidPattern)
        brush_main.setColor(QColor.fromRgb(128, 128, 128))
        self.item_pan_fill = scene.addRect(QRectF(0., SIZE * 0.44, 0., SIZE * 0.02), pen_none, brush_main)
        self.item_pan_edge = scene.addLine(QLineF(0., SIZE * 0.44, 0., SIZE * 0.46), pen_main)

        scene.addItem(self.item)

        self.setScene(scene)

    def pushSample(self, samps, t0, t):
        ns, nc = samps.shape
        l, r = samps[:, 0], samps[:, 1]
        x = (l - r) / 2.
        y = (l + r) / 2.
        pan = np.atan2(x, -y) / np.pi + 0.5
        pan -= np.floor(pan)
        pan = pan * 4. - 2.
        pan[pan < -1.] = -2. - pan[pan < -1.]
        pan[pan >  1.] =  2. - pan[pan >  1.]
        self.pan = np.concatenate([self.pan, pan], axis=0)
        self.corr = np.concatenate([self.corr, np.abs(1. - np.abs(np.atan2(x, y) / np.pi * 2.)) * 2. - 1.], axis=0)
        self.samples = np.concatenate([self.samples, samps], axis=0)
        self.times = np.concatenate([self.times, np.linspace(t0, t, ns, endpoint=False)], axis=0)
        self.max_pluned = np.concatenate([self.max_pluned, np.max(np.abs(samps), initial=0)[np.newaxis]], axis=0)
        self.times_pluned = np.concatenate([self.times_pluned, np.array(t)[np.newaxis]], axis=0)

    def updateImage(self, t):
        dt = t - self.t0
        self.t0 = t
        if abs(self.amp_goal - self.amp) < 0.01:
            self.amp = self.amp_goal
        else:
            cc = 1 - math.pow(1 - 0.99, dt)
            self.amp = self.amp * (1. - cc) + self.amp_goal * cc
        item_level_text = f'{self.amp:.1f} dB'
        if level is None:
            item_level_text += ' <adaptive>'
        self.item_level.setText(item_level_text)

        data = np.zeros((SIZE, SIZE))
        c = np.maximum(1.0 - (t - self.times) / 0.1, 0)
        l, r = self.samples[:, 0], self.samples[:, 1]
        x, y = (l - r) / 2., (l + r) / 2.
        indices = (np.clip((y / np.pow(2, self.amp / 6) * SIZE * 0.4 + SIZE / 2).astype(np.int16), 0, SIZE - 1), np.clip((x / np.pow(2, self.amp / 6) * SIZE * 0.4 + SIZE / 2).astype(np.int16), 0, SIZE - 1))
        np.add.at(data, indices, c * 0.5)
        cd = (t - self.times) <= 0.1
        self.pan = self.pan[cd]
        self.corr = self.corr[cd]
        self.samples = self.samples[cd]
        self.times = self.times[cd]
        img = np.full((SIZE, SIZE, 4), 255, dtype=np.uint8)
        img[:, :, 3] = np.minimum(data * 255, 255).astype(np.uint8)
        pixmap = QPixmap.fromImage(QImage(img.flatten().tobytes(), SIZE, SIZE, QImage.Format.Format_RGBA8888))
        self.item.setPixmap(pixmap)

        ci = (t - self.times) <= 0.1
        corr = np.average(self.corr[ci])
        self.item_corr.setRect(QRectF(SIZE * 0.44, 0., SIZE * 0.02, SIZE * -0.4 * corr))
        pan = np.average(self.pan[ci])
        self.item_pan_fill.setRect(QRectF(0., SIZE * 0.44, SIZE * 0.4 * pan, SIZE * 0.02))
        self.item_pan_edge.setLine(QLineF(SIZE * 0.4 * pan, SIZE * 0.44, SIZE * 0.4 * pan, SIZE * 0.46))
        self.update()

        ci = (t - self.times_pluned) <= 10.
        self.max_pluned = self.max_pluned[ci]
        self.times_pluned = self.times_pluned[ci]

        if level is None:
            if len(self.max_pluned) != 0:
                smax = np.log2(np.percentile(np.abs(self.max_pluned), 99.) / np.pow(2, self.amp_goal / 6))
            else:
                smax = np.full((1, ), -np.inf)
            if smax > 0:
                self.amp_goal += 6
                if self.amp_goal > 0: self.amp_goal = 0
            elif smax < -1:
                self.amp_goal -= 6
                if self.amp_goal < -24: self.amp_goal = -24
        else:
            self.amp_goal = level


def exit(signum, frame) -> None:
    sys.exit(signum)

def main():
    app = QApplication(sys.argv)

    signal.signal(signal.SIGTERM, exit)
    try:
        window = MainWindow()
        window.show()
        app.exec()
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        if device:
            device.__exit__(None, None, None)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        signal.signal(signal.SIGINT, signal.SIG_DFL)

if __name__ == "__main__":
    sys.exit(main())
