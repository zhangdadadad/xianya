# d:\LLM\Xiangya\cv-catch\ffmpeg_cat\services\movement_guidance.py
from typing import List

class MovementGuidance:
    def __init__(self, deadband=0.2, area_target=0.12, area_tolerance=0.04, alpha=0.6, hysteresis=0.05):
        self.deadband = float(deadband)
        self.area_target = float(area_target)
        self.area_tol = float(area_tolerance)
        self.alpha = float(alpha)
        self.hys = float(hysteresis)
        self._cx = None
        self._cy = None
        self._area = None
        self._in_center = False

    def update(self, frame, boxes) -> List[str]:
        if frame is None or not boxes:
            return []
        h, w = frame.shape[0], frame.shape[1]
        b = max(boxes, key=lambda bb: bb.w * bb.h)
        cx = (b.x + b.w / 2.0) / float(w)
        cy = (b.y + b.h / 2.0) / float(h)
        area = (b.w * b.h) / float(w * h)
        if self._cx is None:
            self._cx, self._cy, self._area = cx, cy, area
        else:
            self._cx = self.alpha * cx + (1 - self.alpha) * self._cx
            self._cy = self.alpha * cy + (1 - self.alpha) * self._cy
            self._area = self.alpha * area + (1 - self.alpha) * self._area
        ex = self._cx - 0.5
        ey = self._cy - 0.5
        msgs = []
        m_enter = self.deadband
        m_exit = max(0.0, self.deadband - self.hys)
        outside = abs(ex) > m_enter or abs(ey) > m_enter
        if not outside and (abs(ex) <= m_exit and abs(ey) <= m_exit):
            self._in_center = True
        else:
            self._in_center = False
            sx = abs(ex) - m_enter
            sy = abs(ey) - m_enter
            if ex < -m_enter:
                msgs.append(self._mag_msg("向右", sx))
            elif ex > m_enter:
                msgs.append(self._mag_msg("向左", sx))
            if ey < -m_enter:
                msgs.append(self._mag_msg("向下", sy))
            elif ey > m_enter:
                msgs.append(self._mag_msg("向上", sy))
        at = self._area - self.area_target
        if at < -self.area_tol:
            msgs.append("靠近一点")
        elif at > self.area_tol:
            msgs.append("后退一点")
        return [m for m in msgs if m]

    def _mag_msg(self, base: str, severity: float) -> str:
        if severity > 0.12:
            return base + "明显"
        if severity > 0.05:
            return base + "少许"
        return base + "一点"