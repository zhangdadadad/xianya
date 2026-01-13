#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import threading
import queue
import time
import logging
from typing import Optional

import cv2
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal


logger = logging.getLogger(__name__)


class OpenCVStream(QObject):
    """OpenCV 摄像头采集流
    - 适用于数值索引（0/1/2/3）
    - 在 Windows 尝试 CAP_DSHOW 与 CAP_MSMF
    - 输出 RGB 帧，接口与 FFmpegStream 尽量对齐
    """

    frame_received = pyqtSignal(np.ndarray)
    error_occurred = pyqtSignal(str)

    def __init__(self, camera_url: str, stream_id: int):
        super().__init__()
        self.camera_url = camera_url
        self.stream_id = stream_id
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_running = False
        self.frame_queue: queue.Queue = queue.Queue(maxsize=30)
        self.thread: Optional[threading.Thread] = None
        self.on_frame_callback = None
        self.frame_count = 0

    def start_stream(self):
        try:
            if self.is_running:
                return
            index = self._parse_index(self.camera_url)
            if index is None:
                raise RuntimeError(f"摄像头索引无效: {self.camera_url}")
            # Windows 优先 DSHOW，再尝试 MSMF
            self.cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if not self.cap or not self.cap.isOpened():
                self.cap = cv2.VideoCapture(index, cv2.CAP_MSMF)
            if not self.cap or not self.cap.isOpened():
                raise RuntimeError(f"无法打开摄像头索引: {index}")

            # 应用分辨率设置（如有）
            w, h = 640, 480
            try:
                if hasattr(self, 'camera_config'):
                    res = self.camera_config.get('resolution') or '640x480'
                    if isinstance(res, str) and 'x' in res:
                        p = res.lower().split('x')
                        w = int(p[0]); h = int(p[1])
            except Exception:
                pass
            try:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
            except Exception:
                pass

            self.is_running = True
            self.thread = threading.Thread(target=self._read_loop, daemon=True)
            self.thread.start()
            logger.info(f"OpenCV摄像头 {self.stream_id} 已启动 (index={index})")
        except Exception as e:
            msg = f"摄像头 {self.stream_id} 启动失败(OpenCV): {e}"
            logger.error(msg)
            self.error_occurred.emit(msg)

    def _read_loop(self):
        try:
            while self.is_running and self.cap and self.cap.isOpened():
                ok, frame_bgr = self.cap.read()
                if not ok:
                    time.sleep(0.02)
                    continue
                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                self.frame_count += 1
                if not self.frame_queue.full():
                    self.frame_queue.put(frame_rgb)
                try:
                    if callable(self.on_frame_callback):
                        self.on_frame_callback(self.stream_id, frame_rgb)
                except Exception:
                    pass
                self.frame_received.emit(frame_rgb)
                time.sleep(0.001)
        except Exception as e:
            msg = f"摄像头 {self.stream_id} 读取失败(OpenCV): {e}"
            logger.error(msg)
            self.error_occurred.emit(msg)

    def stop_stream(self):
        self.is_running = False
        try:
            if self.cap:
                self.cap.release()
        except Exception:
            pass
        try:
            if self.thread:
                self.thread.join(timeout=2)
        except Exception:
            pass
        logger.info(f"OpenCV摄像头 {self.stream_id} 已停止")

    def get_frame(self) -> Optional[np.ndarray]:
        try:
            return self.frame_queue.get_nowait()
        except queue.Empty:
            return None

    @staticmethod
    def _parse_index(url: str) -> Optional[int]:
        try:
            return int(str(url).strip())
        except Exception:
            return None

