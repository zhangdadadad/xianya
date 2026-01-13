#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import cv2
import numpy as np
import threading
import logging
from PyQt5.QtCore import QObject, pyqtSignal

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None
    logging.warning("pyttsx3库未安装，语音播报功能将不可用")

logger = logging.getLogger(__name__)


class QRCodeScanner(QObject):
    """二维码扫描服务"""
    qr_detected = pyqtSignal(str)  # 检测到二维码时发出信号，传递二维码内容

    def __init__(self):
        super().__init__()
        # 初始化二维码检测器
        self.detector = cv2.QRCodeDetector()
        # 初始化语音合成器
        self.tts_engine = None
        if pyttsx3:
            try:
                self.tts_engine = pyttsx3.init()
                # 设置语音属性
                self.tts_engine.setProperty('rate', 150)  # 语速
                self.tts_engine.setProperty('volume', 1.0)  # 音量
            except Exception as e:
                logging.error(f"初始化语音合成器失败: {str(e)}")
                self.tts_engine = None

    def scan_qr_code(self, frame: np.ndarray, camera_id: int) -> bool:
        """
        扫描二维码（优化版本）
        :param frame: 视频帧
        :param camera_id: 摄像头ID（只在主摄像头实现）
        :return: 是否检测到二维码
        """
        # 只在主摄像头（ID=0）实现二维码扫描
        if camera_id != 0:
            return False

        try:
            # 检测二维码
            data, vertices_array, binary_qrcode = self.detector.detectAndDecode(frame)

            if vertices_array is not None and data:
                logger.info(f"摄像头 {camera_id} 检测到二维码: {data}")
                self.qr_detected.emit(data)  # 发出二维码检测信号
                # 扫码成功后播放语音提示
                self._speak_success_message(data)
                return True

            return False

        except Exception as e:
            logger.error(f"二维码扫描错误: {str(e)}")
            return False

    def _speak_success_message(self, qr_data: str):
        """
        播放扫码成功的语音提示
        :param qr_data: 二维码内容
        """
        if not self.tts_engine:
            return

        def speak():
            try:
                self.tts_engine.say("扫码成功，准备拍照")
                # 可以选择是否播报二维码内容
                # self.tts_engine.say(f"二维码内容是：{qr_data}")
                self.tts_engine.runAndWait()
            except Exception as e:
                logger.error(f"语音播报失败: {str(e)}")

        # 在新线程中播放语音，避免阻塞主线程
        threading.Thread(target=speak, daemon=True).start()

    def draw_qr_code(self, frame: np.ndarray) -> np.ndarray:
        """
        在帧上绘制二维码检测结果
        :param frame: 视频帧
        :return: 绘制了二维码的视频帧
        """
        try:
            data, vertices_array, binary_qrcode = self.detector.detectAndDecode(frame)

            if vertices_array is not None and data:
                # 绘制二维码边框
                vertices = vertices_array.astype(int)
                for i in range(len(vertices[0])):
                    pt1 = tuple(vertices[0][i])
                    pt2 = tuple(vertices[0][(i + 1) % len(vertices[0])])
                    cv2.line(frame, pt1, pt2, (0, 255, 0), 2)

                # 绘制二维码内容
                cv2.putText(frame, data, (vertices[0][0][0], vertices[0][0][1] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            return frame

        except Exception as e:
            logger.error(f"绘制二维码错误: {str(e)}")
            return frame