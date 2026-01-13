#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import sqlite3
import time
from typing import Optional, Tuple

import cv2
import numpy as np


class StorageService:
    """SQLite 存储服务
    - 初始化并维护监控数据库
    - 保存抓拍图片与结构化元数据
    """

    def __init__(self, base_dir: Optional[str] = None):
        import sys
        if base_dir is None:
            # 获取exe所在目录或脚本所在目录
            if getattr(sys, 'frozen', False):
                # 打包成exe后，使用exe所在目录
                base_dir = os.path.dirname(sys.executable)
            else:
                # 开发环境，使用脚本所在目录
                base_dir = os.path.join(os.path.dirname(__file__), '..')
        self.base_dir = os.path.abspath(base_dir)
        self.db_path = os.path.join(self.base_dir, 'monitoring.db')
        self.capture_dir = os.path.join(self.base_dir, 'captures')
        os.makedirs(self.capture_dir, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS persons (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT UNIQUE,
                  notes TEXT,
                  face_embedding BLOB
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS captures (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp DATETIME,
                  camera_name TEXT,
                  image_path TEXT,
                  person_id INTEGER,
                  detection_confidence REAL,
                  recognition_confidence REAL,
                  bounding_box TEXT,
                  FOREIGN KEY(person_id) REFERENCES persons(id)
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def save_capture(self,
                     camera_name: str,
                     frame: np.ndarray,
                     bbox: Optional[Tuple[int, int, int, int]] = None,
                     det_score: Optional[float] = None,
                     person_id: Optional[int] = None,
                     rec_score: Optional[float] = None,
                     session_id: Optional[str] = None) -> str:
        """保存抓拍图片与记录到数据库，返回图片相对路径"""
        ts_ms = int(time.time() * 1000)
        # 修改路径逻辑：所有摄像头的照片都保存在captures/二维码信息/文件夹下
        if session_id:
            subdir = os.path.join(self.capture_dir, str(session_id), camera_name)
        else:
            subdir = os.path.join(self.capture_dir, camera_name)
        os.makedirs(subdir, exist_ok=True)
        filename = f"{camera_name}_{ts_ms}.jpg"
        file_path = os.path.join(subdir, filename)
        
        # 添加调试信息
        print(f"[DEBUG] base_dir: {self.base_dir}")
        print(f"[DEBUG] capture_dir: {self.capture_dir}")
        print(f"[DEBUG] session_id: {session_id}")
        print(f"[DEBUG] subdir: {subdir}")
        print(f"[DEBUG] file_path: {file_path}")
        print(f"[DEBUG] frame shape: {frame.shape}")
        
        # 处理帧的格式，确保是BGR格式
        if len(frame.shape) == 3 and frame.shape[2] == 3:
            # 尝试检测当前格式并转换为BGR
            # FFmpeg通常返回BGR格式，但有时可能是RGB
            # 先尝试从RGB转换为BGR
            try:
                bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            except Exception:
                # 如果转换失败，说明已经是BGR格式，直接使用
                bgr = frame
        else:
            bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        # 保存图片
        success = cv2.imwrite(file_path, bgr)
        print(f"[DEBUG] cv2.imwrite result: {success}")
        if not success:
            print(f"[ERROR] Failed to save image to: {file_path}")
        
        rel_path = os.path.relpath(file_path, self.base_dir)
        bbox_json = None
        try:
            if bbox is not None:
                bx, by, bw, bh = bbox
                bbox_json = json.dumps({'x': int(bx), 'y': int(by), 'w': int(bw), 'h': int(bh)})
        except Exception:
            bbox_json = None

        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO captures(timestamp, camera_name, image_path, person_id,
                                     detection_confidence, recognition_confidence, bounding_box)
                VALUES(datetime('now'), ?, ?, ?, ?, ?, ?)
                """,
                (camera_name, rel_path, person_id, float(det_score or 0.0), float(rec_score or 0.0), bbox_json)
            )
            conn.commit()
        finally:
            conn.close()

        return rel_path
