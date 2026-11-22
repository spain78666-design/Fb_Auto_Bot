#!/usr/bin/env python3
"""
Brand-Logo Loading Overlay & Header Activity Spinner
Uses the application's actual FB Auto Bot logo for sleek animated loading feedback
across all pages, saves, additions, scans, and background workers.
"""

from __future__ import annotations

import math
import os
from typing import Callable, Optional

from PyQt5.QtCore import Qt, QTimer, QEvent, QRectF, QCoreApplication, QEventLoop
from PyQt5.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PyQt5.QtWidgets import QWidget


def _load_logo_pixmap(logo_path: Optional[str]) -> Optional[QPixmap]:
    if logo_path and os.path.isfile(logo_path):
        pm = QPixmap(logo_path)
        if not pm.isNull():
            return pm
    return None


class BrandLogoLoadingOverlay(QWidget):
    """
    Translucent cyber-glass loading overlay placed over `pages_stack`.
    Renders the FB Auto Bot logo inside a dual-orbit glowing animated ring
    plus status title, subtitle, and completion checkmark transition.
    """

    def __init__(self, parent: Optional[QWidget] = None, logo_path: Optional[str] = None):
        super().__init__(parent)
        self.setObjectName("brandLogoLoadingOverlay")
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setFocusPolicy(Qt.NoFocus)

        self._logo_path = logo_path
        self._logo_pixmap: Optional[QPixmap] = _load_logo_pixmap(logo_path)
        self._scaled_logo_cache: Optional[QPixmap] = None
        self._scaled_logo_px = 0

        self._title = "Working..."
        self._subtitle = "Please wait while FB Auto Bot processes your request"
        self._done_text = "Completed!"
        self._is_done = False
        self._active = False
        self._angle = 0.0
        self._counter_angle = 0.0
        self._pulse_phase = 0.0
        self._dot_tick = 0
        self._token = 0
        self._after_done_cb: Optional[Callable[[], None]] = None

        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(20)  # ~50 FPS smooth orbital rotation
        self._anim_timer.timeout.connect(self._on_anim_tick)

        self._auto_timer = QTimer(self)
        self._auto_timer.setSingleShot(True)
        self._auto_timer.timeout.connect(self._on_auto_finish_timeout)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._on_hide_timeout)

        if parent is not None:
            parent.installEventFilter(self)
            self.sync_geometry()

        self.hide()

    def set_logo_path(self, logo_path: Optional[str]):
        self._logo_path = logo_path
        self._logo_pixmap = _load_logo_pixmap(logo_path)
        self._scaled_logo_cache = None
        self._scaled_logo_px = 0

    def sync_geometry(self):
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(0, 0, max(1, parent.width()), max(1, parent.height()))

    def eventFilter(self, obj, event):
        if obj is self.parentWidget() and event.type() in (QEvent.Resize, QEvent.Show):
            self.sync_geometry()
            if self.isVisible():
                self.raise_()
        return super().eventFilter(obj, event)

    def _get_logo_for_size(self, target_px: int) -> Optional[QPixmap]:
        if self._logo_pixmap is None or self._logo_pixmap.isNull():
            return None
        if self._scaled_logo_cache is not None and self._scaled_logo_px == target_px:
            return self._scaled_logo_cache
        self._scaled_logo_px = target_px
        self._scaled_logo_cache = self._logo_pixmap.scaled(
            target_px, target_px, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        return self._scaled_logo_cache

    def start_loader(
        self,
        title: str,
        subtitle: str = "FB Auto Bot is processing...",
        duration_ms: int = 750,
        done_text: Optional[str] = None,
        auto_finish: bool = True,
        after_done: Optional[Callable[[], None]] = None,
        flush_paint: bool = True,
    ) -> int:
        self._token += 1
        token = self._token

        self._auto_timer.stop()
        self._hide_timer.stop()

        self._title = str(title or "Processing...")
        self._subtitle = str(subtitle or "Please wait...")
        self._done_text = str(done_text) if done_text else "Completed!"
        self._is_done = False
        self._active = True
        self._after_done_cb = after_done

        self.sync_geometry()
        self.show()
        self.raise_()

        if not self._anim_timer.isActive():
            self._anim_timer.start()

        if flush_paint:
            self.repaint()
            try:
                QCoreApplication.processEvents(QEventLoop.ExcludeUserInputEvents, 15)
            except Exception:
                pass

        if auto_finish:
            hold = max(160, int(duration_ms))
            self._auto_timer.start(hold)

        return token

    def finish_loader(
        self,
        done_text: Optional[str] = None,
        hide_delay_ms: int = 320,
        token: Optional[int] = None,
    ):
        if token is not None and token != self._token:
            return
        if not self._active and not self.isVisible():
            return

        self._auto_timer.stop()
        self._is_done = True
        if done_text:
            self._done_text = str(done_text)
        self.update()

        delay = max(120, int(hide_delay_ms))
        self._hide_timer.start(delay)

    def hide_immediately(self, token: Optional[int] = None):
        if token is not None and token != self._token:
            return
        self._token += 1
        self._auto_timer.stop()
        self._hide_timer.stop()
        self._anim_timer.stop()
        self._active = False
        self._is_done = False
        self._after_done_cb = None
        self.hide()

    def _on_auto_finish_timeout(self):
        self.finish_loader(done_text=self._done_text, hide_delay_ms=300, token=self._token)

    def _on_hide_timeout(self):
        cb = self._after_done_cb
        self._anim_timer.stop()
        self._active = False
        self._is_done = False
        self._after_done_cb = None
        self.hide()
        if callable(cb):
            try:
                cb()
            except Exception:
                pass

    def _on_anim_tick(self):
        self._angle = (self._angle + 7.2) % 360.0
        self._counter_angle = (self._counter_angle - 4.0) % 360.0
        self._pulse_phase = (self._pulse_phase + 0.14) % (2.0 * math.pi)
        self._dot_tick = (self._dot_tick + 1) % 45
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        w = float(self.width())
        h = float(self.height())
        if w <= 2 or h <= 2:
            return

        # Subtle dark glass backdrop over current page
        painter.fillRect(self.rect(), QColor(6, 10, 20, 176))

        # Centered cyber-glass card
        card_w = min(360.0, max(250.0, w - 36.0))
        card_h = 216.0
        card_x = (w - card_w) / 2.0
        card_y = (h - card_h) / 2.0
        card_rect = QRectF(card_x, card_y, card_w, card_h)

        # Ambient outer drop-glow behind card
        glow_color = QColor(16, 185, 129, 44) if self._is_done else QColor(56, 189, 248, 38)
        painter.setPen(Qt.NoPen)
        painter.setBrush(glow_color)
        painter.drawRoundedRect(card_rect.adjusted(-6, -6, 6, 6), 24, 24)

        # Card surface
        card_grad = QRadialGradient(card_rect.center(), card_w * 0.72)
        card_grad.setColorAt(0.0, QColor(18, 28, 52, 246))
        card_grad.setColorAt(1.0, QColor(9, 14, 28, 248))
        painter.setBrush(QBrush(card_grad))
        border_col = QColor(16, 185, 129, 195) if self._is_done else QColor(56, 189, 248, 130)
        painter.setPen(QPen(border_col, 1.6))
        painter.drawRoundedRect(card_rect, 20, 20)

        # Center coordinates for the Bot Logo Orbital Spinner
        cx = w / 2.0
        cy = card_y + 76.0
        pulse = 0.5 + 0.5 * math.sin(self._pulse_phase)

        # Breathing radial aura behind logo
        aura_radius = 52.0 + pulse * 6.0
        aura = QRadialGradient(cx, cy, aura_radius)
        if self._is_done:
            aura.setColorAt(0.0, QColor(16, 185, 129, 105))
            aura.setColorAt(0.65, QColor(16, 185, 129, 32))
            aura.setColorAt(1.0, QColor(16, 185, 129, 0))
        else:
            aura.setColorAt(0.0, QColor(56, 189, 248, 95))
            aura.setColorAt(0.6, QColor(99, 102, 241, 40))
            aura.setColorAt(1.0, QColor(56, 189, 248, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(aura))
        painter.drawEllipse(QRectF(cx - aura_radius, cy - aura_radius, aura_radius * 2, aura_radius * 2))

        # Track circle (faint background orbit)
        outer_r = 42.0
        outer_rect = QRectF(cx - outer_r, cy - outer_r, outer_r * 2, outer_r * 2)
        painter.setPen(QPen(QColor(148, 163, 184, 34), 3.2))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(outer_rect)

        if self._is_done:
            # Completed emerald glow ring
            done_pen = QPen(QColor(16, 185, 129, 245), 3.8, Qt.SolidLine, Qt.RoundCap)
            painter.setPen(done_pen)
            painter.drawEllipse(outer_rect)
        else:
            # Outer primary rotating gradient arc
            conical = QConicalGradient(cx, cy, -self._angle)
            conical.setColorAt(0.00, QColor(56, 189, 248, 255))
            conical.setColorAt(0.28, QColor(129, 140, 248, 235))
            conical.setColorAt(0.55, QColor(52, 211, 153, 150))
            conical.setColorAt(0.82, QColor(56, 189, 248, 0))
            conical.setColorAt(1.00, QColor(56, 189, 248, 255))
            arc_pen = QPen(QBrush(conical), 3.8, Qt.SolidLine, Qt.RoundCap)
            painter.setPen(arc_pen)
            painter.drawArc(outer_rect, int(-self._angle * 16), 270 * 16)

            # Inner counter-rotating dashed ring
            inner_r = 35.0
            inner_rect = QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2)
            dash_pen = QPen(QColor(129, 140, 248, 115), 1.6, Qt.DashLine, Qt.RoundCap)
            painter.setPen(dash_pen)
            painter.drawArc(inner_rect, int(-self._counter_angle * 16), 210 * 16)

        # Dark circular medallion holding the actual Bot Logo
        med_r = 28.0
        med_rect = QRectF(cx - med_r, cy - med_r, med_r * 2, med_r * 2)
        painter.setPen(QPen(QColor(255, 255, 255, 26), 1.0))
        painter.setBrush(QColor(8, 13, 27, 245))
        painter.drawEllipse(med_rect)

        # Draw actual Bot Logo with gentle breathing zoom
        breath_scale = 1.0 if self._is_done else (0.94 + 0.09 * pulse)
        logo_draw_sz = 42.0 * breath_scale
        pm = self._get_logo_for_size(64)
        if pm is not None and not pm.isNull():
            painter.save()
            clip_path = QPainterPath()
            clip_path.addEllipse(med_rect.adjusted(2, 2, -2, -2))
            painter.setClipPath(clip_path)
            target_rect = QRectF(
                cx - logo_draw_sz / 2.0,
                cy - logo_draw_sz / 2.0,
                logo_draw_sz,
                logo_draw_sz,
            )
            painter.drawPixmap(target_rect, pm, QRectF(pm.rect()))
            painter.restore()
        else:
            painter.setPen(QColor("#38bdf8"))
            painter.setFont(QFont("Segoe UI", 18, QFont.Bold))
            painter.drawText(med_rect, Qt.AlignCenter, "⚡")

        # Small emerald checkmark pill on completion
        if self._is_done:
            badge_rect = QRectF(cx + 15.0, cy + 13.0, 20.0, 20.0)
            painter.setBrush(QColor("#10b981"))
            painter.setPen(QPen(QColor("#064e3b"), 1.5))
            painter.drawEllipse(badge_rect)
            painter.setPen(QColor("#ffffff"))
            painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
            painter.drawText(badge_rect, Qt.AlignCenter, "✓")

        # Title Text
        title_rect = QRectF(card_x + 18.0, card_y + 132.0, card_w - 36.0, 26.0)
        painter.setFont(QFont("Segoe UI", 11, QFont.Bold))
        if self._is_done:
            painter.setPen(QColor("#34d399"))
            painter.drawText(title_rect, Qt.AlignCenter, self._done_text)
        else:
            painter.setPen(QColor("#f8fafc"))
            painter.drawText(title_rect, Qt.AlignCenter, self._title)

        # Subtitle Text with animated dots while working
        sub_rect = QRectF(card_x + 18.0, card_y + 158.0, card_w - 36.0, 22.0)
        painter.setFont(QFont("Segoe UI", 9))
        if self._is_done:
            painter.setPen(QColor("#a7f3d0"))
            painter.drawText(sub_rect, Qt.AlignCenter, "Ready")
        else:
            dots = "." * ((self._dot_tick // 12) % 4)
            painter.setPen(QColor("#94a3b8"))
            clean_sub = self._subtitle.rstrip(".")
            painter.drawText(sub_rect, Qt.AlignCenter, f"{clean_sub}{dots}")

        # Bottom Neon Shimmer Capsule Bar
        bar_w = card_w - 56.0
        bar_h = 4.0
        bar_x = card_x + 28.0
        bar_y = card_y + card_h - 20.0
        bar_rect = QRectF(bar_x, bar_y, bar_w, bar_h)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(30, 41, 59, 200))
        painter.drawRoundedRect(bar_rect, 2.0, 2.0)

        if self._is_done:
            painter.setBrush(QColor("#10b981"))
            painter.drawRoundedRect(bar_rect, 2.0, 2.0)
        else:
            seg_w = bar_w * 0.36
            travel = (self._angle / 360.0)
            seg_x = bar_x + travel * (bar_w - seg_w)
            seg_rect = QRectF(seg_x, bar_y, seg_w, bar_h)
            painter.setBrush(QColor("#38bdf8"))
            painter.drawRoundedRect(seg_rect, 2.0, 2.0)


class HeaderLogoSpinner(QWidget):
    """
    Compact top-header activity badge featuring the animated FB Auto Bot logo
    plus a concise live status label while tasks/workers/actions are running.
    """

    def __init__(self, parent: Optional[QWidget] = None, logo_path: Optional[str] = None):
        super().__init__(parent)
        self._logo_pixmap = _load_logo_pixmap(logo_path)
        self._scaled_pm: Optional[QPixmap] = None
        self._busy = False
        self._status_text = "Ready"
        self._angle = 0.0

        self.setFixedHeight(30)
        self.setMinimumWidth(34)
        self.setMaximumWidth(240)
        self.setVisible(False)

        self._timer = QTimer(self)
        self._timer.setInterval(24)
        self._timer.timeout.connect(self._on_tick)

        self._auto_stop_timer = QTimer(self)
        self._auto_stop_timer.setSingleShot(True)
        self._auto_stop_timer.timeout.connect(lambda: self.set_busy(False))

    def set_logo_path(self, logo_path: Optional[str]):
        self._logo_pixmap = _load_logo_pixmap(logo_path)
        self._scaled_pm = None

    def set_busy(self, busy: bool, text: str = "Working...", duration_ms: int = 0):
        self._auto_stop_timer.stop()
        self._busy = bool(busy)
        if text:
            self._status_text = str(text)

        if self._busy:
            fm = self.fontMetrics()
            needed_w = min(240, max(96, 44 + fm.horizontalAdvance(self._status_text) + 16))
            self.setFixedWidth(needed_w)
            self.setVisible(True)
            if not self._timer.isActive():
                self._timer.start()
            if duration_ms > 0:
                self._auto_stop_timer.start(duration_ms)
        else:
            self._timer.stop()
            self.setVisible(False)
        self.update()

    def _on_tick(self):
        self._angle = (self._angle + 8.0) % 360.0
        self.update()

    def paintEvent(self, event):
        if not self._busy:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        rect = QRectF(0.5, 0.5, self.width() - 1.0, self.height() - 1.0)
        painter.setBrush(QColor(15, 23, 42, 210))
        painter.setPen(QPen(QColor(56, 189, 248, 110), 1.0))
        painter.drawRoundedRect(rect, 15.0, 15.0)

        # Mini animated logo ring on the left
        cx = 16.0
        cy = self.height() / 2.0
        ring_r = 10.5
        ring_rect = QRectF(cx - ring_r, cy - ring_r, ring_r * 2, ring_r * 2)

        painter.setPen(QPen(QColor(148, 163, 184, 40), 2.0))
        painter.drawEllipse(ring_rect)

        conical = QConicalGradient(cx, cy, -self._angle)
        conical.setColorAt(0.0, QColor("#38bdf8"))
        conical.setColorAt(0.45, QColor("#818cf8"))
        conical.setColorAt(0.85, QColor(56, 189, 248, 0))
        conical.setColorAt(1.0, QColor("#38bdf8"))
        painter.setPen(QPen(QBrush(conical), 2.2, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(ring_rect, int(-self._angle * 16), 250 * 16)

        if self._logo_pixmap is not None and not self._logo_pixmap.isNull():
            if self._scaled_pm is None:
                self._scaled_pm = self._logo_pixmap.scaled(
                    24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            logo_rect = QRectF(cx - 7.5, cy - 7.5, 15.0, 15.0)
            painter.save()
            clip = QPainterPath()
            clip.addEllipse(logo_rect)
            painter.setClipPath(clip)
            painter.drawPixmap(logo_rect, self._scaled_pm, QRectF(self._scaled_pm.rect()))
            painter.restore()
        else:
            painter.setPen(QColor("#38bdf8"))
            painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
            painter.drawText(ring_rect, Qt.AlignCenter, "⚡")

        # Status text
        text_rect = QRectF(31.0, 0.0, self.width() - 40.0, self.height())
        painter.setPen(QColor("#bae6fd"))
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self._status_text)
