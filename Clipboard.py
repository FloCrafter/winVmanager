# -*- coding: utf-8 -*-
import sys
import os
import json
import threading
import winreg
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QListWidget,
    QListWidgetItem, QHBoxLayout, QDialog, QSpinBox, QKeySequenceEdit,
    QFormLayout, QDialogButtonBox, QAbstractItemView, QStyledItemDelegate, QStyle,
    QComboBox, QLineEdit, QCheckBox
)
from PyQt5.QtCore import Qt, QTimer, QObject, pyqtSignal, QPoint, QRect, QSize, QEvent
from PyQt5.QtGui import QKeySequence, QFontMetrics, QCursor, QColor, QBrush, QPen, QLinearGradient
import pyperclip
from pynput import keyboard, mouse

keyboard_controller = keyboard.Controller()

# =============================================================================
# 1. DESIGN UND STYLES
# =============================================================================
DARK_COLORS = { "window_bg": "#2b2b2b", "item_bg": "#3c3c3c", "item_hover_bg": "#505050", "border": "#444", "hover_border": "#6a6a6a", "text": "#f0f0f0", "button_bg": "#555", "button_hover_bg": "#666" }
LIGHT_COLORS = { "window_bg": "#ffffff", "item_bg": "#f0f0f0", "item_hover_bg": "#e0e0e0", "border": "#dcdcdc", "hover_border": "#c0c0c0", "text": "#1c1c1c", "button_bg": "#e1e1e1", "button_hover_bg": "#d1d1d1" }

def get_stylesheet(colors, font_size):
    return f"""
        QWidget {{ font-family: Segoe UI, sans-serif; font-size: {font_size}pt; color: {colors["text"]}; }}
        #MainWindow {{ background-color: {colors["window_bg"]}; border-radius: 10px; border: 1px solid {colors["border"]}; }}
        QDialog {{ background-color: {colors["window_bg"]}; }}
        QLineEdit, QSpinBox, QKeySequenceEdit, QComboBox {{ background-color: {colors["item_bg"]}; border: 1px solid {colors["border"]}; border-radius: 5px; padding: 5px; }}
        QListWidget {{ background-color: {colors["window_bg"]}; border: none; }}
        QPushButton {{ background-color: {colors["button_bg"]}; color: {colors["text"]}; border: none; padding: 8px 16px; border-radius: 5px; }}
        QPushButton:hover {{ background-color: {colors["button_hover_bg"]}; }}
        QDialogButtonBox QPushButton {{ min-width: 70px; }}
        QScrollBar:vertical {{ border: none; background: {colors["window_bg"]}; width: 10px; margin: 0; }}
        QScrollBar::handle:vertical {{ background: {colors["button_bg"]}; min-height: 20px; border-radius: 5px; }}
    """

class ClipboardItemDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent); self.ICON_SIZE = 24; self.ICON_PADDING = 8; self.ITEM_PADDING = 10; self.BORDER_RADIUS = 6; self.MAX_LINES = 3; self.colors = DARK_COLORS
    def set_theme_colors(self, colors): self.colors = colors
    def paint(self, painter, option, index):
        painter.save(); painter.setRenderHint(painter.Antialiasing); rect = option.rect.adjusted(1, 1, -1, -1)
        bg_color_str = self.colors["item_hover_bg"] if option.state & QStyle.State_MouseOver else self.colors["item_bg"]; bg_color = QColor(bg_color_str)
        if option.state & QStyle.State_MouseOver: painter.setPen(QPen(QColor(self.colors["hover_border"]), 1))
        else: painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(bg_color)); painter.drawRoundedRect(rect, self.BORDER_RADIUS, self.BORDER_RADIUS); text = index.data(Qt.DisplayRole); is_pinned = index.data(Qt.UserRole)
        icon_area_width = self.ICON_SIZE * 2 + self.ICON_PADDING; text_rect = QRect(rect.left() + self.ITEM_PADDING, rect.top() + self.ITEM_PADDING, rect.width() - icon_area_width - self.ITEM_PADDING * 2, rect.height() - self.ITEM_PADDING * 2)
        painter.setPen(QColor(self.colors["text"])); painter.drawText(text_rect, Qt.TextWordWrap, text); metrics = QFontMetrics(option.font); line_height = metrics.lineSpacing()
        total_text_height = metrics.boundingRect(text_rect, Qt.TextWordWrap, text).height()
        if total_text_height > self.MAX_LINES * line_height:
            gradient_height = int(line_height * 1.5); gradient_rect = QRect(int(text_rect.left()), int(rect.bottom() - gradient_height - self.ITEM_PADDING), int(text_rect.width()), int(gradient_height)); gradient = QLinearGradient(gradient_rect.topLeft(), gradient_rect.bottomLeft())
            gradient.setColorAt(0.0, QColor(bg_color.red(), bg_color.green(), bg_color.blue(), 0)); gradient.setColorAt(1.0, bg_color); painter.fillRect(gradient_rect, gradient)
        pin_icon = "📌" if is_pinned else "📍"; delete_icon = "🗑️"; pin_rect = QRect(rect.right() - self.ICON_SIZE * 2, rect.top(), self.ICON_SIZE, rect.height()); delete_rect = QRect(rect.right() - self.ICON_SIZE, rect.top(), self.ICON_SIZE, rect.height())
        painter.drawText(pin_rect, Qt.AlignCenter, pin_icon); painter.drawText(delete_rect, Qt.AlignCenter, delete_icon); painter.restore()
    def sizeHint(self, option, index):
        metrics = QFontMetrics(option.font); line_height = metrics.lineSpacing(); text = index.data(Qt.DisplayRole); width = option.rect.width() - self.ICON_SIZE * 2 - self.ICON_PADDING - self.ITEM_PADDING * 2
        text_rect = metrics.boundingRect(QRect(0, 0, width, 5000), Qt.TextWordWrap, text); calculated_lines = text_rect.height() / line_height; actual_lines = min(self.MAX_LINES, calculated_lines)
        height = int(actual_lines * line_height + self.ITEM_PADDING * 2); return QSize(option.rect.width(), max(50, height))

# =============================================================================
# 2. HELFERKLASSEN
# =============================================================================
class SignalEmitter(QObject):
    hotkey_pressed = pyqtSignal(); global_mouse_press = pyqtSignal()

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent); self.setWindowTitle("Einstellungen"); self.layout = QFormLayout(self)
        self.history_limit = QSpinBox(); self.history_limit.setRange(1, 100)
        self.layout.addRow("Max. Einträge:", self.history_limit)
        self.hotkey_edit = QKeySequenceEdit(); self.layout.addRow("Hotkey:", self.hotkey_edit)
        self.theme_combo = QComboBox(); self.theme_combo.addItems(["System", "Hell", "Dunkel"]); self.layout.addRow("Theme:", self.theme_combo)
        self.font_size_spinbox = QSpinBox(); self.font_size_spinbox.setRange(8, 20); self.layout.addRow("Schriftgröße (pt):", self.font_size_spinbox)
        self.auto_paste_checkbox = QCheckBox("Nach Auswahl direkt einfügen (simuliert Strg+V)"); self.layout.addRow(self.auto_paste_checkbox)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept); self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def set_settings(self, settings):
        self.history_limit.setValue(settings.get("history_limit", 15))
        self.hotkey_edit.setKeySequence(QKeySequence(settings.get("hotkey", "meta+v").lower()))
        self.theme_combo.setCurrentText(settings.get("theme", "Hell"))
        self.auto_paste_checkbox.setChecked(settings.get("auto_paste", True))
        self.font_size_spinbox.setValue(settings.get("font_size", 10))

    def get_settings(self):
        return { "history_limit": self.history_limit.value(), "hotkey": self.hotkey_edit.keySequence().toString().lower(), "theme": self.theme_combo.currentText(), "auto_paste": self.auto_paste_checkbox.isChecked(), "font_size": self.font_size_spinbox.value() }

# =============================================================================
# 3. HAUPTANWENDUNG
# =============================================================================
class ClipboardHistory(QWidget):
    def __init__(self):
        super().__init__(); self.setObjectName("MainWindow"); self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool); self.setAttribute(Qt.WA_TranslucentBackground)
        self.all_history_items = []; self.oldPos = self.pos(); self.clipboard_history = []; self.pinned_items = []; self.settings = self.load_settings()
        self.hotkey_listener = None; self.mouse_listener = None; self.emitter = SignalEmitter(); self.emitter.hotkey_pressed.connect(self.show_window)
        self.emitter.global_mouse_press.connect(self.check_if_click_is_outside); self.init_ui(); self.apply_theme(); self.load_history()
        self.last_clipboard_content = pyperclip.paste(); self.timer = QTimer(self); self.timer.timeout.connect(self.check_clipboard); self.timer.start(500)
        self.setup_hotkey_listener(); self.setup_mouse_listener()

    def on_global_click(self, x, y, button, pressed):
        if pressed and self.isVisible(): self.emitter.global_mouse_press.emit()
    def check_if_click_is_outside(self):
        if self.isVisible() and not self.geometry().contains(QCursor.pos()): self.hide()
    def init_ui(self):
        self.layout = QVBoxLayout(self); self.layout.setContentsMargins(1, 1, 1, 1); container = QWidget(); container.setObjectName("MainWindow")
        self.main_layout = QVBoxLayout(container); self.main_layout.setContentsMargins(10, 10, 10, 10); self.layout.addWidget(container)
        title_label = QLabel("Zwischenablage"); title_label.setStyleSheet("font-weight: bold; padding-bottom: 5px;")
        self.search_bar = QLineEdit(); self.search_bar.setPlaceholderText("Suchen..."); self.search_bar.textChanged.connect(self.filter_list)
        self.main_layout.addWidget(title_label); self.main_layout.addWidget(self.search_bar)
        self.list_widget = QListWidget(); self.list_widget.setSpacing(5); self.delegate = ClipboardItemDelegate(self.list_widget)
        self.list_widget.setItemDelegate(self.delegate); self.list_widget.setMouseTracking(True); self.list_widget.clicked.connect(self.on_item_clicked)
        self.list_widget.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel); self.main_layout.addWidget(self.list_widget)
        button_layout = QHBoxLayout(); self.delete_all_button = QPushButton("Alles löschen"); self.delete_all_button.clicked.connect(self.clear_history)
        button_layout.addWidget(self.delete_all_button); self.settings_button = QPushButton("Einstellungen"); self.settings_button.clicked.connect(self.open_settings)
        button_layout.addWidget(self.settings_button); self.main_layout.addLayout(button_layout)
    def on_item_clicked(self, index):
        item = self.list_widget.itemFromIndex(index);
        if not item: return
        text = item.text(); local_pos = self.list_widget.viewport().mapFromGlobal(QCursor.pos()); item_rect = self.list_widget.visualRect(index)
        pin_rect = QRect(item_rect.right() - self.delegate.ICON_SIZE * 2, item_rect.top(), self.delegate.ICON_SIZE, item_rect.height())
        delete_rect = QRect(item_rect.right() - self.delegate.ICON_SIZE, item_rect.top(), self.delegate.ICON_SIZE, item_rect.height())
        if pin_rect.contains(local_pos): self.toggle_pin(text); return 
        elif delete_rect.contains(local_pos): self.delete_item(text); return
        pyperclip.copy(text)
        if self.settings.get("auto_paste", False): self.hide(); QTimer.singleShot(100, self.perform_paste)
        else: self.hide()
    def perform_paste(self):
        with keyboard_controller.pressed(keyboard.Key.ctrl): keyboard_controller.press('v'); keyboard_controller.release('v')
    def mousePressEvent(self, event): self.oldPos = event.globalPos()
    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPos() - self.oldPos); self.move(self.x() + delta.x(), self.y() + delta.y()); self.oldPos = event.globalPos()
    def get_system_theme(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"); value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme"); winreg.CloseKey(key); return "Hell" if value == 1 else "Dunkel"
        except: return "Dunkel"
    def apply_theme(self):
        theme_choice = self.settings.get("theme", "System"); final_theme = theme_choice if theme_choice != "System" else self.get_system_theme()
        colors = LIGHT_COLORS if final_theme == "Hell" else DARK_COLORS; font_size = self.settings.get("font_size", 10)
        stylesheet = get_stylesheet(colors, font_size); self.delegate.set_theme_colors(colors)
        QApplication.instance().setStyleSheet(stylesheet); self.update_list_display()
    def get_appdata_path(self, filename):
        appdata = os.getenv('APPDATA') or os.path.expanduser('~'); app_dir = os.path.join(appdata, 'ClipboardHistory'); os.makedirs(app_dir, exist_ok=True); return os.path.join(app_dir, filename)
    
    # *** HIER WURDEN DIE STANDARD-EINSTELLUNGEN ANGEPASST ***
    def load_settings(self):
        try:
            with open(self.get_appdata_path('settings.json'), 'r', encoding='utf-8') as f: return json.load(f)
        except: 
            return {
                "history_limit": 15, 
                "hotkey": "meta+v", 
                "theme": "Hell", 
                "auto_paste": True, 
                "font_size": 10
            }

    def save_settings(self):
        with open(self.get_appdata_path('settings.json'), 'w', encoding='utf-8') as f: json.dump(self.settings, f, indent=4)
    def load_history(self):
        try:
            with open(self.get_appdata_path('history.json'), 'r', encoding='utf-8') as f: data = json.load(f)
            self.clipboard_history = data.get("history", []); self.pinned_items = data.get("pinned", [])
        except: self.clipboard_history, self.pinned_items = [], []
        self.update_list()
    def save_history(self):
        with open(self.get_appdata_path('history.json'), 'w', encoding='utf-8') as f: json.dump({"history": self.clipboard_history, "pinned": self.pinned_items}, f, indent=4)
    def format_hotkey_for_pynput(self, hotkey_str):
        hotkey_str = hotkey_str.lower().replace('meta', 'cmd').replace('win', 'cmd'); parts = hotkey_str.split('+')
        modifier_keys = ['ctrl', 'alt', 'shift', 'cmd']; formatted_parts = [f'<{p}>' if p in modifier_keys else p for p in parts]; return '+'.join(formatted_parts)
    def setup_hotkey_listener(self):
        if self.hotkey_listener and self.hotkey_listener.is_alive(): self.hotkey_listener.stop()
        hotkey_str = self.settings.get("hotkey", "meta+v");
        def on_activate(): self.emitter.hotkey_pressed.emit()
        try:
            pynput_hotkey_str = self.format_hotkey_for_pynput(hotkey_str); self.hotkey_listener = keyboard.GlobalHotKeys({pynput_hotkey_str: on_activate}); self.hotkey_listener.start()
            print(f"Hotkey '{hotkey_str}' (formatiert als '{pynput_hotkey_str}') ist aktiv.")
        except Exception as e: print(f"FEHLER beim Setzen des Hotkeys '{hotkey_str}'. Details: {e}")
    def setup_mouse_listener(self):
        if self.mouse_listener and self.mouse_listener.is_alive(): self.mouse_listener.stop()
        self.mouse_listener = mouse.Listener(on_click=self.on_global_click); self.mouse_listener.start(); print("Globaler Maus-Klick-Listener ist aktiv.")
    def check_clipboard(self):
        try:
            content = pyperclip.paste()
            if content and content != self.last_clipboard_content:
                self.last_clipboard_content = content;
                if content in self.clipboard_history: self.clipboard_history.remove(content)
                if content in self.pinned_items: return
                self.clipboard_history.insert(0, content); self.update_list(); self.save_history()
        except: pass
    def update_list(self):
        self.all_history_items = [(text, True) for text in self.pinned_items]; history_limit = self.settings.get("history_limit", 15)
        unpinned_history = [item for item in self.clipboard_history if item not in self.pinned_items]
        if history_limit > 0: unpinned_history = unpinned_history[:history_limit]
        self.all_history_items.extend([(text, False) for text in unpinned_history]); self.filter_list()
    def filter_list(self): self.update_list_display()
    def update_list_display(self):
        self.list_widget.clear(); search_text = self.search_bar.text().lower(); items_to_show = self.all_history_items
        if search_text: items_to_show = [item for item in self.all_history_items if search_text in item[0].lower()]
        for text, is_pinned in items_to_show:
            item = QListWidgetItem(text); item.setData(Qt.UserRole, is_pinned); self.list_widget.addItem(item)
    def toggle_pin(self, text):
        if text in self.pinned_items: self.pinned_items.remove(text); self.clipboard_history.insert(0, text)
        else:
            if text in self.clipboard_history: self.clipboard_history.remove(text)
            self.pinned_items.insert(0, text)
        self.save_history(); self.update_list()
    def delete_item(self, text):
        if text in self.clipboard_history: self.clipboard_history.remove(text)
        if text in self.pinned_items: self.pinned_items.remove(text)
        self.save_history(); self.update_list()
    def clear_history(self):
        self.clipboard_history.clear(); self.pinned_items.clear(); self.save_history(); self.update_list()
    def open_settings(self):
        dialog = SettingsDialog(self); dialog.set_settings(self.settings)
        if dialog.exec_(): self.settings = dialog.get_settings(); self.save_settings(); self.apply_theme(); self.setup_hotkey_listener()
    def show_window(self):
        if self.isVisible(): self.activateWindow(); return
        self.search_bar.clear(); self.update_list(); margin = 20; screen_geometry = QApplication.desktop().availableGeometry(self)
        self.show(); self.adjustSize(); x = screen_geometry.width() - self.width() - margin; y = screen_geometry.height() - self.height() - margin
        self.move(x, y); self.raise_(); self.activateWindow()
    def closeEvent(self, event):
        if self.hotkey_listener: self.hotkey_listener.stop()
        if self.mouse_listener: self.mouse_listener.stop()
        event.accept()

# =============================================================================
# 4. ANWENDUNGSSTART
# =============================================================================
if __name__ == '__main__':
    app = QApplication(sys.argv)
    clipboard_app = ClipboardHistory()
    app.setQuitOnLastWindowClosed(False) 
    sys.exit(app.exec_())# -*- coding: utf-8 -*-
import sys
import os
import json
import threading
import winreg
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QListWidget,
    QListWidgetItem, QHBoxLayout, QDialog, QSpinBox, QKeySequenceEdit,
    QFormLayout, QDialogButtonBox, QAbstractItemView, QStyledItemDelegate, QStyle,
    QComboBox, QLineEdit, QCheckBox
)
from PyQt5.QtCore import Qt, QTimer, QObject, pyqtSignal, QPoint, QRect, QSize, QEvent
from PyQt5.QtGui import QKeySequence, QFontMetrics, QCursor, QColor, QBrush, QPen, QLinearGradient
import pyperclip
from pynput import keyboard, mouse

keyboard_controller = keyboard.Controller()

# =============================================================================
# 1. DESIGN UND STYLES
# =============================================================================
DARK_COLORS = { "window_bg": "#2b2b2b", "item_bg": "#3c3c3c", "item_hover_bg": "#505050", "border": "#444", "hover_border": "#6a6a6a", "text": "#f0f0f0", "button_bg": "#555", "button_hover_bg": "#666" }
LIGHT_COLORS = { "window_bg": "#ffffff", "item_bg": "#f0f0f0", "item_hover_bg": "#e0e0e0", "border": "#dcdcdc", "hover_border": "#c0c0c0", "text": "#1c1c1c", "button_bg": "#e1e1e1", "button_hover_bg": "#d1d1d1" }

def get_stylesheet(colors, font_size):
    return f"""
        QWidget {{ font-family: Segoe UI, sans-serif; font-size: {font_size}pt; color: {colors["text"]}; }}
        #MainWindow {{ background-color: {colors["window_bg"]}; border-radius: 10px; border: 1px solid {colors["border"]}; }}
        QDialog {{ background-color: {colors["window_bg"]}; }}
        QLineEdit, QSpinBox, QKeySequenceEdit, QComboBox {{ background-color: {colors["item_bg"]}; border: 1px solid {colors["border"]}; border-radius: 5px; padding: 5px; }}
        QListWidget {{ background-color: {colors["window_bg"]}; border: none; }}
        QPushButton {{ background-color: {colors["button_bg"]}; color: {colors["text"]}; border: none; padding: 8px 16px; border-radius: 5px; }}
        QPushButton:hover {{ background-color: {colors["button_hover_bg"]}; }}
        QDialogButtonBox QPushButton {{ min-width: 70px; }}
        QScrollBar:vertical {{ border: none; background: {colors["window_bg"]}; width: 10px; margin: 0; }}
        QScrollBar::handle:vertical {{ background: {colors["button_bg"]}; min-height: 20px; border-radius: 5px; }}
    """

class ClipboardItemDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent); self.ICON_SIZE = 24; self.ICON_PADDING = 8; self.ITEM_PADDING = 10; self.BORDER_RADIUS = 6; self.MAX_LINES = 3; self.colors = DARK_COLORS
    def set_theme_colors(self, colors): self.colors = colors
    def paint(self, painter, option, index):
        painter.save(); painter.setRenderHint(painter.Antialiasing); rect = option.rect.adjusted(1, 1, -1, -1)
        bg_color_str = self.colors["item_hover_bg"] if option.state & QStyle.State_MouseOver else self.colors["item_bg"]; bg_color = QColor(bg_color_str)
        if option.state & QStyle.State_MouseOver: painter.setPen(QPen(QColor(self.colors["hover_border"]), 1))
        else: painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(bg_color)); painter.drawRoundedRect(rect, self.BORDER_RADIUS, self.BORDER_RADIUS); text = index.data(Qt.DisplayRole); is_pinned = index.data(Qt.UserRole)
        icon_area_width = self.ICON_SIZE * 2 + self.ICON_PADDING; text_rect = QRect(rect.left() + self.ITEM_PADDING, rect.top() + self.ITEM_PADDING, rect.width() - icon_area_width - self.ITEM_PADDING * 2, rect.height() - self.ITEM_PADDING * 2)
        painter.setPen(QColor(self.colors["text"])); painter.drawText(text_rect, Qt.TextWordWrap, text); metrics = QFontMetrics(option.font); line_height = metrics.lineSpacing()
        total_text_height = metrics.boundingRect(text_rect, Qt.TextWordWrap, text).height()
        if total_text_height > self.MAX_LINES * line_height:
            gradient_height = int(line_height * 1.5); gradient_rect = QRect(int(text_rect.left()), int(rect.bottom() - gradient_height - self.ITEM_PADDING), int(text_rect.width()), int(gradient_height)); gradient = QLinearGradient(gradient_rect.topLeft(), gradient_rect.bottomLeft())
            gradient.setColorAt(0.0, QColor(bg_color.red(), bg_color.green(), bg_color.blue(), 0)); gradient.setColorAt(1.0, bg_color); painter.fillRect(gradient_rect, gradient)
        pin_icon = "📌" if is_pinned else "📍"; delete_icon = "🗑️"; pin_rect = QRect(rect.right() - self.ICON_SIZE * 2, rect.top(), self.ICON_SIZE, rect.height()); delete_rect = QRect(rect.right() - self.ICON_SIZE, rect.top(), self.ICON_SIZE, rect.height())
        painter.drawText(pin_rect, Qt.AlignCenter, pin_icon); painter.drawText(delete_rect, Qt.AlignCenter, delete_icon); painter.restore()
    def sizeHint(self, option, index):
        metrics = QFontMetrics(option.font); line_height = metrics.lineSpacing(); text = index.data(Qt.DisplayRole); width = option.rect.width() - self.ICON_SIZE * 2 - self.ICON_PADDING - self.ITEM_PADDING * 2
        text_rect = metrics.boundingRect(QRect(0, 0, width, 5000), Qt.TextWordWrap, text); calculated_lines = text_rect.height() / line_height; actual_lines = min(self.MAX_LINES, calculated_lines)
        height = int(actual_lines * line_height + self.ITEM_PADDING * 2); return QSize(option.rect.width(), max(50, height))

# =============================================================================
# 2. HELFERKLASSEN
# =============================================================================
class SignalEmitter(QObject):
    hotkey_pressed = pyqtSignal(); global_mouse_press = pyqtSignal()

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent); self.setWindowTitle("Einstellungen"); self.layout = QFormLayout(self)
        self.history_limit = QSpinBox(); self.history_limit.setRange(1, 100)
        self.layout.addRow("Max. Einträge:", self.history_limit)
        self.hotkey_edit = QKeySequenceEdit(); self.layout.addRow("Hotkey:", self.hotkey_edit)
        self.theme_combo = QComboBox(); self.theme_combo.addItems(["System", "Hell", "Dunkel"]); self.layout.addRow("Theme:", self.theme_combo)
        self.font_size_spinbox = QSpinBox(); self.font_size_spinbox.setRange(8, 20); self.layout.addRow("Schriftgröße (pt):", self.font_size_spinbox)
        self.auto_paste_checkbox = QCheckBox("Nach Auswahl direkt einfügen (simuliert Strg+V)"); self.layout.addRow(self.auto_paste_checkbox)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept); self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def set_settings(self, settings):
        self.history_limit.setValue(settings.get("history_limit", 15))
        self.hotkey_edit.setKeySequence(QKeySequence(settings.get("hotkey", "meta+v").lower()))
        self.theme_combo.setCurrentText(settings.get("theme", "Hell"))
        self.auto_paste_checkbox.setChecked(settings.get("auto_paste", True))
        self.font_size_spinbox.setValue(settings.get("font_size", 10))

    def get_settings(self):
        return { "history_limit": self.history_limit.value(), "hotkey": self.hotkey_edit.keySequence().toString().lower(), "theme": self.theme_combo.currentText(), "auto_paste": self.auto_paste_checkbox.isChecked(), "font_size": self.font_size_spinbox.value() }

# =============================================================================
# 3. HAUPTANWENDUNG
# =============================================================================
class ClipboardHistory(QWidget):
    def __init__(self):
        super().__init__(); self.setObjectName("MainWindow"); self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool); self.setAttribute(Qt.WA_TranslucentBackground)
        self.all_history_items = []; self.oldPos = self.pos(); self.clipboard_history = []; self.pinned_items = []; self.settings = self.load_settings()
        self.hotkey_listener = None; self.mouse_listener = None; self.emitter = SignalEmitter(); self.emitter.hotkey_pressed.connect(self.show_window)
        self.emitter.global_mouse_press.connect(self.check_if_click_is_outside); self.init_ui(); self.apply_theme(); self.load_history()
        self.last_clipboard_content = pyperclip.paste(); self.timer = QTimer(self); self.timer.timeout.connect(self.check_clipboard); self.timer.start(500)
        self.setup_hotkey_listener(); self.setup_mouse_listener()

    def on_global_click(self, x, y, button, pressed):
        if pressed and self.isVisible(): self.emitter.global_mouse_press.emit()
    def check_if_click_is_outside(self):
        if self.isVisible() and not self.geometry().contains(QCursor.pos()): self.hide()
    def init_ui(self):
        self.layout = QVBoxLayout(self); self.layout.setContentsMargins(1, 1, 1, 1); container = QWidget(); container.setObjectName("MainWindow")
        self.main_layout = QVBoxLayout(container); self.main_layout.setContentsMargins(10, 10, 10, 10); self.layout.addWidget(container)
        title_label = QLabel("Zwischenablage"); title_label.setStyleSheet("font-weight: bold; padding-bottom: 5px;")
        self.search_bar = QLineEdit(); self.search_bar.setPlaceholderText("Suchen..."); self.search_bar.textChanged.connect(self.filter_list)
        self.main_layout.addWidget(title_label); self.main_layout.addWidget(self.search_bar)
        self.list_widget = QListWidget(); self.list_widget.setSpacing(5); self.delegate = ClipboardItemDelegate(self.list_widget)
        self.list_widget.setItemDelegate(self.delegate); self.list_widget.setMouseTracking(True); self.list_widget.clicked.connect(self.on_item_clicked)
        self.list_widget.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel); self.main_layout.addWidget(self.list_widget)
        button_layout = QHBoxLayout(); self.delete_all_button = QPushButton("Alles löschen"); self.delete_all_button.clicked.connect(self.clear_history)
        button_layout.addWidget(self.delete_all_button); self.settings_button = QPushButton("Einstellungen"); self.settings_button.clicked.connect(self.open_settings)
        button_layout.addWidget(self.settings_button); self.main_layout.addLayout(button_layout)
    def on_item_clicked(self, index):
        item = self.list_widget.itemFromIndex(index);
        if not item: return
        text = item.text(); local_pos = self.list_widget.viewport().mapFromGlobal(QCursor.pos()); item_rect = self.list_widget.visualRect(index)
        pin_rect = QRect(item_rect.right() - self.delegate.ICON_SIZE * 2, item_rect.top(), self.delegate.ICON_SIZE, item_rect.height())
        delete_rect = QRect(item_rect.right() - self.delegate.ICON_SIZE, item_rect.top(), self.delegate.ICON_SIZE, item_rect.height())
        if pin_rect.contains(local_pos): self.toggle_pin(text); return 
        elif delete_rect.contains(local_pos): self.delete_item(text); return
        pyperclip.copy(text)
        if self.settings.get("auto_paste", False): self.hide(); QTimer.singleShot(100, self.perform_paste)
        else: self.hide()
    def perform_paste(self):
        with keyboard_controller.pressed(keyboard.Key.ctrl): keyboard_controller.press('v'); keyboard_controller.release('v')
    def mousePressEvent(self, event): self.oldPos = event.globalPos()
    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPos() - self.oldPos); self.move(self.x() + delta.x(), self.y() + delta.y()); self.oldPos = event.globalPos()
    def get_system_theme(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"); value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme"); winreg.CloseKey(key); return "Hell" if value == 1 else "Dunkel"
        except: return "Dunkel"
    def apply_theme(self):
        theme_choice = self.settings.get("theme", "System"); final_theme = theme_choice if theme_choice != "System" else self.get_system_theme()
        colors = LIGHT_COLORS if final_theme == "Hell" else DARK_COLORS; font_size = self.settings.get("font_size", 10)
        stylesheet = get_stylesheet(colors, font_size); self.delegate.set_theme_colors(colors)
        QApplication.instance().setStyleSheet(stylesheet); self.update_list_display()
    def get_appdata_path(self, filename):
        appdata = os.getenv('APPDATA') or os.path.expanduser('~'); app_dir = os.path.join(appdata, 'ClipboardHistory'); os.makedirs(app_dir, exist_ok=True); return os.path.join(app_dir, filename)
    
    # *** HIER WURDEN DIE STANDARD-EINSTELLUNGEN ANGEPASST ***
    def load_settings(self):
        try:
            with open(self.get_appdata_path('settings.json'), 'r', encoding='utf-8') as f: return json.load(f)
        except: 
            return {
                "history_limit": 15, 
                "hotkey": "meta+v", 
                "theme": "Hell", 
                "auto_paste": True, 
                "font_size": 10
            }

    def save_settings(self):
        with open(self.get_appdata_path('settings.json'), 'w', encoding='utf-8') as f: json.dump(self.settings, f, indent=4)
    def load_history(self):
        try:
            with open(self.get_appdata_path('history.json'), 'r', encoding='utf-8') as f: data = json.load(f)
            self.clipboard_history = data.get("history", []); self.pinned_items = data.get("pinned", [])
        except: self.clipboard_history, self.pinned_items = [], []
        self.update_list()
    def save_history(self):
        with open(self.get_appdata_path('history.json'), 'w', encoding='utf-8') as f: json.dump({"history": self.clipboard_history, "pinned": self.pinned_items}, f, indent=4)
    def format_hotkey_for_pynput(self, hotkey_str):
        hotkey_str = hotkey_str.lower().replace('meta', 'cmd').replace('win', 'cmd'); parts = hotkey_str.split('+')
        modifier_keys = ['ctrl', 'alt', 'shift', 'cmd']; formatted_parts = [f'<{p}>' if p in modifier_keys else p for p in parts]; return '+'.join(formatted_parts)
    def setup_hotkey_listener(self):
        if self.hotkey_listener and self.hotkey_listener.is_alive(): self.hotkey_listener.stop()
        hotkey_str = self.settings.get("hotkey", "meta+v");
        def on_activate(): self.emitter.hotkey_pressed.emit()
        try:
            pynput_hotkey_str = self.format_hotkey_for_pynput(hotkey_str); self.hotkey_listener = keyboard.GlobalHotKeys({pynput_hotkey_str: on_activate}); self.hotkey_listener.start()
            print(f"Hotkey '{hotkey_str}' (formatiert als '{pynput_hotkey_str}') ist aktiv.")
        except Exception as e: print(f"FEHLER beim Setzen des Hotkeys '{hotkey_str}'. Details: {e}")
    def setup_mouse_listener(self):
        if self.mouse_listener and self.mouse_listener.is_alive(): self.mouse_listener.stop()
        self.mouse_listener = mouse.Listener(on_click=self.on_global_click); self.mouse_listener.start(); print("Globaler Maus-Klick-Listener ist aktiv.")
    def check_clipboard(self):
        try:
            content = pyperclip.paste()
            if content and content != self.last_clipboard_content:
                self.last_clipboard_content = content;
                if content in self.clipboard_history: self.clipboard_history.remove(content)
                if content in self.pinned_items: return
                self.clipboard_history.insert(0, content); self.update_list(); self.save_history()
        except: pass
    def update_list(self):
        self.all_history_items = [(text, True) for text in self.pinned_items]; history_limit = self.settings.get("history_limit", 15)
        unpinned_history = [item for item in self.clipboard_history if item not in self.pinned_items]
        if history_limit > 0: unpinned_history = unpinned_history[:history_limit]
        self.all_history_items.extend([(text, False) for text in unpinned_history]); self.filter_list()
    def filter_list(self): self.update_list_display()
    def update_list_display(self):
        self.list_widget.clear(); search_text = self.search_bar.text().lower(); items_to_show = self.all_history_items
        if search_text: items_to_show = [item for item in self.all_history_items if search_text in item[0].lower()]
        for text, is_pinned in items_to_show:
            item = QListWidgetItem(text); item.setData(Qt.UserRole, is_pinned); self.list_widget.addItem(item)
    def toggle_pin(self, text):
        if text in self.pinned_items: self.pinned_items.remove(text); self.clipboard_history.insert(0, text)
        else:
            if text in self.clipboard_history: self.clipboard_history.remove(text)
            self.pinned_items.insert(0, text)
        self.save_history(); self.update_list()
    def delete_item(self, text):
        if text in self.clipboard_history: self.clipboard_history.remove(text)
        if text in self.pinned_items: self.pinned_items.remove(text)
        self.save_history(); self.update_list()
    def clear_history(self):
        self.clipboard_history.clear(); self.pinned_items.clear(); self.save_history(); self.update_list()
    def open_settings(self):
        dialog = SettingsDialog(self); dialog.set_settings(self.settings)
        if dialog.exec_(): self.settings = dialog.get_settings(); self.save_settings(); self.apply_theme(); self.setup_hotkey_listener()
    def show_window(self):
        if self.isVisible(): self.activateWindow(); return
        self.search_bar.clear(); self.update_list(); margin = 20; screen_geometry = QApplication.desktop().availableGeometry(self)
        self.show(); self.adjustSize(); x = screen_geometry.width() - self.width() - margin; y = screen_geometry.height() - self.height() - margin
        self.move(x, y); self.raise_(); self.activateWindow()
    def closeEvent(self, event):
        if self.hotkey_listener: self.hotkey_listener.stop()
        if self.mouse_listener: self.mouse_listener.stop()
        event.accept()

# =============================================================================
# 4. ANWENDUNGSSTART
# =============================================================================
if __name__ == '__main__':
    app = QApplication(sys.argv)
    clipboard_app = ClipboardHistory()
    app.setQuitOnLastWindowClosed(False) 
    sys.exit(app.exec_())           