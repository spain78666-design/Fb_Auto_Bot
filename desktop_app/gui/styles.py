"""
FB Auto Bot - QSS Dark Glassmorphic Design Tokens & Stylesheet
"""

GLASS_STYLESHEET = """
QMainWindow {
    background-color: #0b0f19;
}

QWidget {
    color: #e2e8f0;
    font-family: 'Segoe UI', 'SF Pro Display', -apple-system, Roboto, sans-serif;
    font-size: 13px;
}

/* Sidebar Styling */
QFrame#sidebarFrame {
    background-color: #111827;
    border-right: 1px solid rgba(255, 255, 255, 0.08);
}

QPushButton.navBtn {
    background-color: transparent;
    color: #94a3b8;
    text-align: left;
    padding: 10px 14px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    border: 1px solid transparent;
}

QPushButton.navBtn:hover {
    background-color: rgba(99, 102, 241, 0.12);
    color: #f8fafc;
    border: 1px solid rgba(99, 102, 241, 0.25);
}

QPushButton.navBtnActive {
    background-color: #4f46e5;
    color: #ffffff;
    border: 1px solid #6366f1;
    font-weight: 700;
}

/* Glassmorphic Content Panels */
QFrame.glassCard {
    background-color: rgba(17, 24, 39, 0.75);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 16px;
}

QLabel.pageTitle {
    font-size: 22px;
    font-weight: 700;
    color: #ffffff;
}

QLabel.pageSubtitle {
    font-size: 13px;
    color: #94a3b8;
}

QLabel.cardTitle {
    font-size: 15px;
    font-weight: 600;
    color: #f1f5f9;
}

/* Form Inputs */
QLineEdit, QTextEdit, QComboBox, QSpinBox {
    background-color: rgba(15, 23, 42, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 8px;
    color: #f8fafc;
    padding: 8px 12px;
    selection-background-color: #4f46e5;
}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #6366f1;
    background-color: #0f172a;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #1e293b;
    border: 1px solid rgba(255, 255, 255, 0.15);
    selection-background-color: #4f46e5;
    color: #f8fafc;
    border-radius: 6px;
}

/* Primary Action Buttons */
QPushButton.primaryBtn {
    background-color: #4f46e5;
    color: #ffffff;
    font-weight: 600;
    border: 1px solid #6366f1;
    border-radius: 8px;
    padding: 9px 18px;
}

QPushButton.primaryBtn:hover {
    background-color: #4338ca;
}

QPushButton.primaryBtn:pressed {
    background-color: #3730a3;
}

QPushButton.successBtn {
    background-color: #059669;
    color: #ffffff;
    font-weight: 700;
    border: 1px solid #10b981;
    border-radius: 8px;
    padding: 10px 22px;
    font-size: 14px;
}

QPushButton.successBtn:hover {
    background-color: #047857;
}

QPushButton.dangerBtn {
    background-color: #dc2626;
    color: #ffffff;
    font-weight: 600;
    border: 1px solid #ef4444;
    border-radius: 8px;
    padding: 10px 20px;
}

QPushButton.dangerBtn:hover {
    background-color: #b91c1c;
}

QPushButton.secondaryBtn {
    background-color: rgba(255, 255, 255, 0.06);
    color: #e2e8f0;
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 8px;
    padding: 8px 16px;
}

QPushButton.secondaryBtn:hover {
    background-color: rgba(255, 255, 255, 0.12);
}

/* Table Widget */
QTableWidget {
    background-color: rgba(15, 23, 42, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    gridline-color: rgba(255, 255, 255, 0.05);
}

QTableWidget::item {
    padding: 6px 10px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

QTableWidget::item:selected {
    background-color: rgba(99, 102, 241, 0.25);
    color: #ffffff;
}

QHeaderView::section {
    background-color: #1e293b;
    color: #cbd5e1;
    font-weight: 600;
    font-size: 12px;
    padding: 8px 10px;
    border: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

/* Checkboxes */
QCheckBox {
    color: #cbd5e1;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    background-color: rgba(15, 23, 42, 0.9);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 4px;
}

QCheckBox::indicator:checked {
    background-color: #4f46e5;
    border-color: #6366f1;
}

/* Terminal Console Box */
QTextEdit#consoleBox {
    background-color: #030712;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    color: #10b981;
    font-family: 'Consolas', 'Fira Code', monospace;
    font-size: 12px;
    line-height: 1.4;
    padding: 10px;
}

/* Progress Bar */
QProgressBar {
    background-color: #1e293b;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    text-align: center;
    color: #ffffff;
    font-size: 11px;
    font-weight: 600;
}

QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #10b981);
    border-radius: 5px;
}

/* Scrollbars */
QScrollBar:vertical {
    background: #0b0f19;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #334155;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #475569;
}
"""
