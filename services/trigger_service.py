# d:\LLM\Xiangya\cv-catch\ffmpeg_cat\services\trigger_service.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from PyQt5.QtCore import QObject, pyqtSignal, QEvent, Qt
from PyQt5.QtWidgets import QApplication

class TriggerService(QObject):
    triggered = pyqtSignal(str)
    identified = pyqtSignal(str)
    def __init__(self):
        super().__init__()
        self._provider = None
    def set_provider(self, provider: QObject):
        self._provider = provider
        try:
            self._provider.triggered.connect(self.triggered.emit)
        except Exception:
            pass
        try:
            self._provider.identified.connect(self.identified.emit)
        except Exception:
            pass
    def start(self):
        if self._provider and hasattr(self._provider, 'start'):
            self._provider.start()
    def stop(self):
        if self._provider and hasattr(self._provider, 'stop'):
            self._provider.stop()

class BaseTriggerProvider(QObject):
    triggered = pyqtSignal(str)
    identified = pyqtSignal(str)
    def start(self):
        pass
    def stop(self):
        pass

class KeyboardTriggerProvider(BaseTriggerProvider):
    def __init__(self):
        super().__init__()
        self._installed = False
        self._buffer = []
    def start(self):
        app = QApplication.instance()
        if app and not self._installed:
            app.installEventFilter(self)
            self._installed = True
    def stop(self):
        app = QApplication.instance()
        if app and self._installed:
            app.removeEventFilter(self)
            self._installed = False
        self._buffer = []
    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            k = event.key()
            if k == Qt.Key_Space:
                # 空格键触发拍照信号
                self.triggered.emit("SPACE")
                return True
            # 收集扫码枪键盘输入：字母/数字 + 回车
            if (Qt.Key_0 <= k <= Qt.Key_9) or (Qt.Key_A <= k <= Qt.Key_Z):
                ch = chr(k)
                # Qt 的字母键码为大写字母，统一转成大写
                self._buffer.append(ch)
                return True
            if k in (Qt.Key_Return, Qt.Key_Enter):
                code = ''.join(self._buffer).strip()
                self._buffer = []
                if code:
                    self.identified.emit(code)
                return True
            if k == Qt.Key_Backspace and self._buffer:
                self._buffer.pop()
                return True
        return False
    def _make_timestamp_id(self) -> str:
        import time
        return time.strftime('%Y%m%d%H%M%S')