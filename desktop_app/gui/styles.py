"""
FB Auto Bot - QSS Dark Glassmorphic Design Tokens & Stylesheet
"""

GLASS_STYLESHEET = """
QMainWindow, QWidget#centralWidget, QWidget#contentContainer, QStackedWidget#pagesStack,
QWidget.pageRoot, QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget {
    background-color: #070b14 !important;
}

QWidget {
    color: #e2e8f0;
    font-family: 'Segoe UI', 'SF Pro Display', -apple-system, Roboto, sans-serif;
    font-size: 13px;
}

QLabel {
    border: none;
    background: transparent;
}

/* ScrollAreas & Scrollbars */
QScrollArea {
    background-color: #070b14 !important;
    border: none !important;
}

QScrollArea > QWidget > QWidget {
    background-color: transparent !important;
}

QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 2px 0px 2px 0px;
}

QScrollBar::handle:vertical {
    background: rgba(148, 163, 184, 0.24);
    min-height: 28px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(99, 102, 241, 0.55);
}

QScrollBar:horizontal {
    background: transparent;
    height: 8px;
    margin: 0px 2px 0px 2px;
}

QScrollBar::handle:horizontal {
    background: rgba(148, 163, 184, 0.24);
    min-width: 28px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
    background: rgba(99, 102, 241, 0.55);
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
    border: none;
}

/* Top Header Bar */
QFrame#topHeaderBar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0b1120, stop:1 #0f172a);
    border: 1px solid rgba(148, 163, 184, 0.14);
    border-radius: 12px;
}

QFrame#topHeaderBar QLabel {
    color: #f8fafc;
}

/* Collapsible Sidebar Navigation */
QFrame#sidebarFrame {
    background-color: #0b101c;
    border-right: 1px solid rgba(148, 163, 184, 0.12);
}

QFrame#sidebarFrame QLabel {
    color: #f8fafc;
}

QPushButton#sidebarBrandBtn {
    background-color: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 12px;
    padding: 8px 10px;
    text-align: left;
}

QPushButton#sidebarBrandBtn:hover {
    background-color: rgba(99, 102, 241, 0.14);
    border: 1px solid rgba(99, 102, 241, 0.35);
}

QPushButton.navBtn {
    background-color: rgba(255, 255, 255, 0.025);
    color: #94a3b8;
    text-align: left;
    padding: 9px 12px;
    border-radius: 10px;
    font-size: 13px;
    font-weight: 600;
    border: 1px solid transparent;
    margin: 1px 0px;
}

QPushButton.navBtn:hover {
    background-color: rgba(99, 102, 241, 0.13);
    color: #f8fafc;
    border: 1px solid rgba(99, 102, 241, 0.28);
}

QPushButton.navBtn[active="true"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338ca, stop:1 #3b82f6);
    color: #ffffff;
    border: 1px solid rgba(129, 140, 248, 0.55);
    font-weight: 700;
}

QPushButton.navBtn[collapsed="true"] {
    text-align: center;
    padding: 9px 0px;
    font-size: 17px;
}

/* Bottom Sidebar Status + ABM CodeSpace Card */
QFrame#sidebarStatusBox {
    background-color: rgba(15, 23, 42, 0.72);
    border: 1px solid rgba(148, 163, 184, 0.14);
    border-radius: 12px;
}

QFrame#sidebarStatusDivider {
    background-color: rgba(148, 163, 184, 0.14);
    max-height: 1px;
    min-height: 1px;
    border: none;
}

/* Content Cards */
QFrame.glassCard {
    background-color: #0e1626;
    border: 1px solid #1e2d4a;
    border-radius: 14px;
    padding: 16px;
}

QFrame.glassCardHeader {
    border-bottom: 1px solid #1e2d4a;
    padding-bottom: 10px;
    margin-bottom: 14px;
}

/* Typography */
QLabel {
    color: #f1f5f9;
    font-weight: 600;
}

QLabel.pageTitle {
    font-size: 21px;
    font-weight: 800;
    color: #f8fafc;
    letter-spacing: -0.3px;
}

QLabel.pageSubtitle {
    font-size: 13px;
    color: #94a3b8;
    font-weight: 500;
}

QLabel.cardTitle {
    font-size: 15px;
    font-weight: 800;
    color: #f8fafc;
    letter-spacing: -0.2px;
}

/* Form Inputs & Sleek SpinBoxes */
QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #090e1a;
    border: 1.5px solid #1e2d4a;
    border-radius: 9px;
    color: #f8fafc;
    font-weight: 500;
    padding: 7px 11px;
    selection-background-color: #4f46e5;
    selection-color: #ffffff;
}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1.5px solid #6366f1;
    background-color: #0b1120;
}

QSpinBox, QDoubleSpinBox {
    padding-right: 26px;
}

QSpinBox::up-button, QDoubleSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 22px;
    background-color: rgba(30, 45, 74, 0.75);
    border-left: 1px solid #1e2d4a;
    border-bottom: 1px solid #1e2d4a;
    border-top-right-radius: 8px;
}

QSpinBox::down-button, QDoubleSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 22px;
    background-color: rgba(30, 45, 74, 0.75);
    border-left: 1px solid #1e2d4a;
    border-bottom-right-radius: 8px;
}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #4f46e5;
}

QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
    width: 0px;
    height: 0px;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid #cbd5e1;
}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
    width: 0px;
    height: 0px;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #cbd5e1;
}

QComboBox::drop-down {
    border: none;
    width: 26px;
}

QComboBox::down-arrow {
    width: 0px;
    height: 0px;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #94a3b8;
}

QComboBox QAbstractItemView {
    background-color: #0e1626;
    border: 1.5px solid #4f46e5;
    selection-background-color: #4f46e5;
    selection-color: #ffffff;
    color: #f8fafc;
    border-radius: 8px;
    padding: 4px;
}

/* Buttons */
QPushButton.primaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338ca, stop:1 #2563eb);
    color: #ffffff;
    font-weight: 700;
    border: 1px solid #4f46e5;
    border-radius: 10px;
    padding: 8px 18px;
}

QPushButton.primaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #3b82f6);
}

QPushButton.successBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #10b981);
    color: #ffffff;
    font-weight: 700;
    border: 1px solid #10b981;
    border-radius: 10px;
    padding: 9px 20px;
    font-size: 13px;
}

QPushButton.successBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #047857, stop:1 #059669);
}

QPushButton.dangerBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #b91c1c, stop:1 #dc2626);
    color: #ffffff;
    font-weight: 700;
    border: 1px solid #ef4444;
    border-radius: 10px;
    padding: 8px 18px;
}

QPushButton.dangerBtn:hover {
    background: #991b1b;
}

QPushButton.secondaryBtn {
    background-color: #182338;
    color: #e2e8f0;
    font-weight: 600;
    border: 1px solid #2b3b5c;
    border-radius: 10px;
    padding: 7px 15px;
}

QPushButton.secondaryBtn:hover {
    background-color: #21304d;
    border: 1px solid #4f46e5;
}

/* Tables */
QTableWidget {
    background-color: #090d16;
    color: #f8fafc;
    border: 1px solid #1e2d4a;
    border-radius: 11px;
    gridline-color: #162138;
}

QTableWidget::item {
    color: #f8fafc;
    padding: 7px 10px;
    border-bottom: 1px solid #162138;
    font-weight: 500;
}

QTableWidget::item:selected {
    background-color: rgba(79, 70, 229, 0.35);
    color: #ffffff;
}

QHeaderView::section {
    background-color: #0f172a;
    color: #38bdf8;
    font-weight: 700;
    font-size: 12px;
    padding: 8px 10px;
    border: none;
    border-bottom: 2px solid #0284c7;
}

/* Checkboxes */
QCheckBox {
    color: #cbd5e1;
    font-weight: 600;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 17px;
    height: 17px;
    background-color: #090d16;
    border: 1.5px solid #2d3f66;
    border-radius: 5px;
}

QCheckBox::indicator:hover {
    border-color: #6366f1;
}

QCheckBox::indicator:checked {
    background-color: #4f46e5;
    border-color: #6366f1;
}

/* Console Box */
QTextEdit#consoleBox {
    background-color: #080c15;
    border: 1px solid #1e2d4a;
    border-radius: 10px;
    color: #4ade80;
    font-family: 'Consolas', 'Cascadia Code', 'Menlo', monospace;
    font-size: 12px;
    padding: 10px;
}

/* Progress Bar */
QProgressBar {
    background-color: #090d16;
    border: 1px solid #1e2d4a;
    border-radius: 7px;
    text-align: center;
    color: #ffffff;
    font-size: 11px;
    font-weight: 800;
    height: 15px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #10b981);
    border-radius: 6px;
}

/* Dialogs & Alerts */
QDialog, QMessageBox, QInputDialog {
    background-color: #0f172a !important;
    color: #f8fafc !important;
    border: 1px solid rgba(255, 255, 255, 0.14);
}

QDialog QLabel, QMessageBox QLabel, QInputDialog QLabel {
    color: #f8fafc !important;
    font-size: 13px;
}

QDialog QPushButton, QMessageBox QPushButton, QInputDialog QPushButton {
    background-color: #4f46e5;
    color: #ffffff;
    border-radius: 8px;
    padding: 7px 18px;
    font-weight: 600;
    border: 1px solid rgba(255, 255, 255, 0.16);
}

QDialog QPushButton:hover, QMessageBox QPushButton:hover, QInputDialog QPushButton:hover {
    background-color: #4338ca;
}

QDialog QLineEdit, QInputDialog QLineEdit {
    background-color: #090d16;
    color: #f8fafc;
    border: 1px solid #6366f1;
    border-radius: 8px;
    padding: 8px 12px;
}
"""
