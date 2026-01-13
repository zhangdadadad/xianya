#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from dataclasses import dataclass
from typing import List, Tuple, Dict

import cv2
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal


@dataclass
class FaceBox:
    x: int
    y: int
    w: int
    h: int
    score: float


class AnalysisService(QObject):
    """轻量人脸分析服务
    - 订阅 CameraManager 的帧更新
    - 使用 Haar 作为默认检测器（可通过配置升级为 YuNet/ONNX）
    - 输出每路的检测框与置信度，并提供抓拍触发建议
    """

    result_ready = pyqtSignal(int, list)  # stream_id, List[FaceBox]
    capture_suggested = pyqtSignal(int, object)  # stream_id, (frame, FaceBox)

    def __init__(self, config_getter):
        super().__init__()
        self._get = config_getter
        # 初始化检测器
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.detector = cv2.CascadeClassifier(cascade_path)
        # 每路触发与冷却
        self.last_seen: Dict[int, float] = {}
        self.cooldown_sec: float = float(self._get('analysis.cooldown_sec') or 2.0)
        self.min_face_size: int = int(self._get('analysis.min_face') or 64)
        self.trigger_frames: int = int(self._get('analysis.trigger_frames') or 6)
        self.center_margin: float = float(self._get('analysis.center_margin') or 0.2)
        self._seen_counter: Dict[int, int] = {}

    def on_frame(self, stream_id: int, frame: np.ndarray):
        try:
            # 转灰度并检测
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            faces = self.detector.detectMultiScale(
                gray,
                scaleFactor=1.2,
                minNeighbors=5,
                minSize=(self.min_face_size, self.min_face_size),
            )

            boxes: List[FaceBox] = []
            for (x, y, w, h) in faces:
                # 简单置信度估计：用面部尺寸与画面尺寸比值作为粗略分数
                score = min(0.99, (w * h) / float(frame.shape[0] * frame.shape[1]))
                boxes.append(FaceBox(x, y, w, h, score))

            self.result_ready.emit(stream_id, boxes)

            # 触发逻辑：持续检测到足够帧且冷却结束
            now = time.time()
            last = self.last_seen.get(stream_id, 0.0)
            cnt = self._seen_counter.get(stream_id, 0)
            if boxes:
                h, w = frame.shape[0], frame.shape[1]
                x0 = int(w * (0.5 - self.center_margin))
                x1 = int(w * (0.5 + self.center_margin))
                y0 = int(h * (0.5 - self.center_margin))
                y1 = int(h * (0.5 + self.center_margin))
                centered = [b for b in boxes if (b.x + b.w // 2) >= x0 and (b.x + b.w // 2) <= x1 and (b.y + b.h // 2) >= y0 and (b.y + b.h // 2) <= y1]
                if centered:
                    cnt += 1
                    self._seen_counter[stream_id] = cnt
                    if cnt >= self.trigger_frames and now - last >= self.cooldown_sec:
                        self.last_seen[stream_id] = now
                        best = sorted(centered, key=lambda b: b.w * b.h, reverse=True)[0]
                        self.capture_suggested.emit(stream_id, (frame.copy(), best))
                else:
                    self._seen_counter[stream_id] = 0
            else:
                self._seen_counter[stream_id] = 0
        except Exception:
            pass

