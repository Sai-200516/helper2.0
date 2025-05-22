import sys
import os
import ctypes
import threading
import time
import requests
import pystray
from PIL import Image
from pynput import keyboard
from pynput.keyboard import Controller
import pyperclip
import pytesseract
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QTextEdit, QLineEdit, QVBoxLayout, QWidget, QPushButton, QDialog, QLabel, QDialogButtonBox, QRadioButton, QCheckBox, QDesktopWidget
from PyQt5.QtCore import Qt, QEvent, QTimer, QPoint, QRect
from PyQt5.QtGui import QKeySequence, QPainter, QPen, QImage, QPixmap, QColor
from PyQt5.QtWidgets import QShortcut
from tenacity import retry, stop_after_attempt, wait_fixed
import uuid
import json
import hashlib
import random
import string

# macOS-specific imports (only import if on macOS)
if sys.platform == "darwin":
    from AppKit import NSWindow, NSWindowCollectionBehaviorNonParticipating
    from Foundation import NSValue
    import objc

# Disable logging for production
import logging
logging.getLogger().setLevel(logging.CRITICAL + 1)  # Disable all logging
logger = logging.getLogger(__name__)

# Configuration
SERVER_URL = os.getenv("HELPER_SERVER_URL", "Server_Url")
API_KEY = os.getenv("HELPER_API_KEY", "Helper_Api_Key")
CONFIG_FILE = "activation.json"
TRIAL_ACTIVATION_CODE = "Helper2.0_Trail"

class CaptureWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 50);")  # Semi-transparent black background
        self.start_point = None
        self.end_point = None
        self.is_drawing = False
        self.setGeometry(QDesktopWidget().screenGeometry())
        self.setMouseTracking(True)  # Enable mouse tracking for smoother updates
        self.apply_platform_specific_settings()
        # print("CaptureWindow initialized")  # Debugging (remove for production)

    def apply_platform_specific_settings(self):
        hwnd = self.winId().__int__()
        if sys.platform == "win32":
            DWMWA_CLOAK = 14
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_CLOAK, ctypes.byref(ctypes.c_bool(True)), ctypes.sizeof(ctypes.c_bool))
            WDA_EXCLUDEFROMCAPTURE = 0x00000011
            try:
                ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
            except:
                ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x00000001)
        elif sys.platform == "darwin":
            with objc.autorelease_pool():
                ns_window = objc.objc_object(c_void_p=hwnd)
                ns_window.setCollectionBehavior_(NSWindowCollectionBehaviorNonParticipating)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_point = event.pos()
            self.end_point = event.pos()
            self.is_drawing = True
            # print(f"Mouse pressed at {self.start_point}")  # Debugging
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_drawing:
            self.end_point = event.pos()
            # print(f"Mouse moved to {self.end_point}")  # Debugging
            self.update()
            self.repaint()  # Force immediate redraw

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.end_point = event.pos()
            self.is_drawing = False
            # print(f"Mouse released at {self.end_point}")  # Debugging
            self.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # Draw semi-transparent overlay
        painter.setBrush(QColor(0, 0, 0, 50))
        painter.setPen(Qt.NoPen)
        painter.drawRect(self.rect())
        # Draw selected rectangle if drawing
        if self.is_drawing and self.start_point and self.end_point:
            painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
            painter.setBrush(Qt.NoBrush)
            rect = QRect(self.start_point, self.end_point)
            painter.drawRect(rect)
        # print("Paint event triggered")  # Debugging
        painter.end()

    def get_captured_region(self):
        if self.start_point and self.end_point:
            x = min(self.start_point.x(), self.end_point.x())
            y = min(self.start_point.y(), self.end_point.y())
            width = abs(self.start_point.x() - self.end_point.x())
            height = abs(self.start_point.y() - self.end_point.y())
            # print(f"Captured region: x={x}, y={y}, w={width}, h={height}")  # Debugging
            return (x, y, width, height)
        return None

class ActivationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Activate SystemService")
        self.setFixedSize(300, 200)
        self.setWindowOpacity(0.8)
        layout = QVBoxLayout()

        self.trial_radio = QRadioButton("Try Trial (15 commands)")
        self.trial_radio.setChecked(True)
        layout.addWidget(self.trial_radio)

        self.premium_radio = QRadioButton("Enter Premium Registration Number")
        layout.addWidget(self.premium_radio)

        self.reg_no_input = QLineEdit()
        self.reg_no_input.setPlaceholderText("e.g., ABC123-XYZ789")
        self.reg_no_input.setEnabled(False)
        layout.addWidget(self.reg_no_input)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: red")
        layout.addWidget(self.error_label)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.setLayout(layout)

        self.trial_radio.toggled.connect(self.toggle_reg_no_input)
        self.premium_radio.toggled.connect(self.toggle_reg_no_input)

    def toggle_reg_no_input(self):
        self.reg_no_input.setEnabled(self.premium_radio.isChecked())

    def is_trial(self):
        return self.trial_radio.isChecked()

    def get_reg_no(self):
        return self.reg_no_input.text().strip()

class ChatWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.hotkey_listener = None
        self.activated = False
        self.reg_no = None
        self.mac_address = self.get_mac_address()
        self.random_hotkey = self.generate_random_hotkey()
        self.init_ui()
        self.setup_system_tray()
        self.setup_shortcut()
        self.apply_platform_specific_settings()
        if sys.platform == "win32":
            ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x00000080)
        if not self.activated:
            self.prompt_activation()

    def get_mac_address(self):
        mac = uuid.getnode()
        mac_str = ':'.join(('%012X' % mac)[i:i+2] for i in range(0, 12, 2))
        hashed_mac = hashlib.sha256(mac_str.encode()).hexdigest()
        return hashed_mac

    def load_activation_status(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.reg_no = data.get('reg_no')
                    self.activated = data.get('activated', False)
        except Exception:
            pass

    def save_activation_status(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump({'reg_no': self.reg_no, 'activated': self.activated}, f)
        except Exception:
            pass

    def prompt_activation(self):
        dialog = ActivationDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            if dialog.is_trial():
                self.activate_trial()
            else:
                reg_no = dialog.get_reg_no()
                if not reg_no:
                    self.chat_output.append("Error: Registration number cannot be empty")
                    return
                self.activate_premium(reg_no)
        else:
            self.chat_output.append("Error: Activation required to use the application")
            self.user_input.setEnabled(False)

    def activate_trial(self):
        try:
            headers = {"Content-Type": "application/json"}
            payload = {"activation_code": TRIAL_ACTIVATION_CODE, "mac_address": self.mac_address}
            response = requests.post(f"{SERVER_URL}/trial_activate", json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            self.reg_no = response.json().get("reg_no")
            self.activated = True
            self.save_activation_status()
            self.user_input.setEnabled(True)
            self.chat_output.append("Trial activation successful! You have 15 commands.")
        except requests.RequestException as e:
            self.chat_output.append(f"Trial activation failed: {str(e)}")
            self.user_input.setEnabled(False)

    def activate_premium(self, reg_no):
        try:
            headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
            payload = {"reg_no": reg_no, "mac_address": self.mac_address}
            response = requests.post(f"{SERVER_URL}/activate", json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            self.reg_no = reg_no
            self.activated = True
            self.save_activation_status()
            self.user_input.setEnabled(True)
            self.chat_output.append("Premium activation successful! You can now use the application.")
        except requests.RequestException as e:
            self.chat_output.append(f"Premium activation failed: {str(e)}")
            self.user_input.setEnabled(False)

    def generate_random_hotkey(self):
        random_letter = random.choice(string.ascii_lowercase)
        return f"<ctrl>+<shift>+{random_letter}"

    def init_ui(self):
        self.setWindowTitle("SystemService")
        self.setFixedSize(300, 400)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setWindowOpacity(0.8)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.chat_output = QTextEdit()
        self.chat_output.setReadOnly(True)
        layout.addWidget(self.chat_output)

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Type your question...")
        self.user_input.setFocusPolicy(Qt.StrongFocus)
        self.user_input.setStyleSheet("color: black; background: white; font-size: 14px;")
        self.user_input.returnPressed.connect(self.send_query)
        self.user_input.installEventFilter(self)
        layout.addWidget(self.user_input)

        self.auto_send_checkbox = QCheckBox("Auto-Send Copied/OCR Text")
        self.auto_send_checkbox.setChecked(False)
        layout.addWidget(self.auto_send_checkbox)

        ocr_button = QPushButton("Capture Image for OCR")
        ocr_button.clicked.connect(self.capture_ocr)
        layout.addWidget(ocr_button)

        copy_question_button = QPushButton("Copy Question")
        copy_question_button.clicked.connect(self.copy_question)
        layout.addWidget(copy_question_button)

        send_button = QPushButton("Send")
        send_button.clicked.connect(self.send_query)
        layout.addWidget(send_button)

        copy_response_button = QPushButton("Copy Response")
        copy_response_button.clicked.connect(self.copy_response)
        layout.addWidget(copy_response_button)

        paste_response_button = QPushButton("Paste Response")
        paste_response_button.clicked.connect(self.paste_response)
        layout.addWidget(paste_response_button)

        activate_button = QPushButton("Activate")
        activate_button.clicked.connect(self.prompt_activation)
        layout.addWidget(activate_button)

        minimize_button = QPushButton("Minimize")
        minimize_button.clicked.connect(self.minimize_window)
        layout.addWidget(minimize_button)

        shortcut = QShortcut(QKeySequence("Ctrl+Return"), self.user_input)
        shortcut.activated.connect(self.send_query)

        self.randomize_position()

        self.topmost_timer = QTimer(self)
        self.topmost_timer.timeout.connect(self.ensure_topmost)
        self.topmost_timer.start(1000)

        self.idle_timer = QTimer(self)
        self.idle_timer.timeout.connect(self.minimize_window)
        self.idle_timer.start(30000)

    def randomize_position(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = random.randint(0, screen.width() - 300)
        y = random.randint(0, screen.height() - 400)
        self.setGeometry(x, y, 300, 400)

    def minimize_window(self):
        self.showMinimized()

    def capture_ocr(self):
        try:
            self.hide()  # Hide main window during capture
            capture_window = CaptureWindow(self)
            if capture_window.exec_() == QDialog.Accepted:
                region = capture_window.get_captured_region()
                if region:
                    x, y, width, height = region
                    if width > 0 and height > 0:
                        # Capture screen region
                        screen = QApplication.primaryScreen()
                        screenshot = screen.grabWindow(0, x, y, width, height)
                        # Convert QPixmap to PIL Image
                        qimage = screenshot.toImage()
                        buffer = qimage.bits().asstring(qimage.width() * qimage.height() * 4)
                        image = Image.frombytes("RGBA", (qimage.width(), qimage.height()), buffer, "raw", "BGRA")
                        image = image.convert("RGB")
                        # Preprocess image for better OCR
                        image_np = np.array(image)
                        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
                        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
                        image = Image.fromarray(thresh)
                        # Perform OCR
                        text = pytesseract.image_to_string(image).strip()
                        if text:
                            self.user_input.setText(text)
                            self.chat_output.append("Text extracted from image")
                            if self.auto_send_checkbox.isChecked():
                                self.send_query()
                        else:
                            self.chat_output.append("Error: No text detected in image")
                    else:
                        self.chat_output.append("Error: Invalid capture region")
                else:
                    self.chat_output.append("Error: No region selected")
            self.showNormal()
            self.ensure_topmost()
        except Exception as e:
            self.chat_output.append(f"Error during OCR: {str(e)}")
            self.showNormal()

    def copy_question(self):
        try:
            question_text = pyperclip.paste().strip()
            if not question_text:
                self.chat_output.append("Error: Clipboard is empty")
                return
            self.user_input.setText(question_text)
            self.chat_output.append("Question copied from clipboard")
            if self.auto_send_checkbox.isChecked():
                self.send_query()
        except Exception as e:
            self.chat_output.append(f"Error copying question: {str(e)}")

    def copy_response(self):
        try:
            response_text = self.chat_output.toPlainText().split("Bot:")[-1].strip().split("(Time:")[0].strip()
            pyperclip.copy(response_text)
            self.chat_output.append("Response copied to clipboard")
        except Exception as e:
            self.chat_output.append(f"Error copying response: {str(e)}")

    def paste_response(self):
        try:
            response_text = self.chat_output.toPlainText().split("Bot:")[-1].strip().split("(Time:")[0].strip()
            keyboard = Controller()
            keyboard.type(response_text)
            self.chat_output.append("Response pasted via simulated typing")
        except Exception as e:
            self.chat_output.append(f"Error pasting response: {str(e)}")

    def apply_platform_specific_settings(self):
        hwnd = self.winId().__int__()
        if sys.platform == "win32":
            GWL_EXSTYLE = -20
            WS_EX_TOOLWINDOW = 0x00000080
            current_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, current_style | WS_EX_TOOLWINDOW)
            HWND_TOPMOST = -1
            SWP_NOSIZE = 0x0001
            SWP_NOMOVE = 0x0002
            ctypes.windll.user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE)
            DWMWA_CLOAK = 14
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_CLOAK, ctypes.byref(ctypes.c_bool(True)), ctypes.sizeof(ctypes.c_bool))
            WDA_EXCLUDEFROMCAPTURE = 0x00000011
            try:
                ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
            except:
                ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x00000001)
        elif sys.platform == "darwin":
            with objc.autorelease_pool():
                ns_window = objc.objc_object(c_void_p=hwnd)
                ns_window.setLevel_(NSWindow.Level.popUpMenu)
                ns_window.setCollectionBehavior_(NSWindowCollectionBehaviorNonParticipating)

    def ensure_topmost(self):
        if self.isVisible():
            hwnd = self.winId().__int__()
            if sys.platform == "win32":
                HWND_TOPMOST = -1
                SWP_NOSIZE = 0x0001
                SWP_NOMOVE = 0x0002
                ctypes.windll.user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE)
            elif sys.platform == "darwin":
                with objc.autorelease_pool():
                    ns_window = objc.objc_object(c_void_p=hwnd)
                    ns_window.setLevel_(NSWindow.Level.popUpMenu)
            self.raise_()
            self.activateWindow()

    def eventFilter(self, obj, event):
        if obj == self.user_input and event.type() == QEvent.KeyPress:
            self.idle_timer.start(30000)
        return super().eventFilter(obj, event)

    def showEvent(self, event):
        self.user_input.setFocus()
        self.ensure_topmost()
        self.idle_timer.start(30000)
        super().showEvent(event)

    def setup_system_tray(self):
        icon = Image.new("RGB", (64, 64), color="black")
        menu = pystray.Menu(
            pystray.MenuItem("Show", self.show_window),
            pystray.MenuItem("Quit", self.quit_app)
        )
        self.tray = pystray.Icon("SystemService", icon, menu=menu)
        self.tray_thread = threading.Thread(target=self.tray.run, daemon=True)
        self.tray_thread.start()

    def setup_shortcut(self):
        self.hotkey_listener = keyboard.GlobalHotKeys({
            self.random_hotkey: self.toggle_window,
            '<alt>+<shift>+g': self.toggle_window
        })
        self.hotkey_listener.start()

    def toggle_window(self):
        start_time = time.time()
        if self.isVisible():
            self.hide()
        else:
            self.showNormal()
            self.ensure_topmost()
            self.user_input.setFocus()
        self.idle_timer.start(30000)

    def show_window(self):
        self.showNormal()
        self.ensure_topmost()
        self.user_input.setFocus()

    def quit_app(self):
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        self.tray.stop()
        QApplication.quit()

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def send_request(self, query):
        if not self.activated:
            raise Exception("Application not activated")
        headers = {
            "X-API-Key": API_KEY,
            "X-Reg-No": self.reg_no,
            "X-MAC-Address": self.mac_address,
            "Content-Type": "application/json"
        }
        payload = {"query": query}
        response = requests.post(f"{SERVER_URL}/chat", json=payload, headers=headers, timeout=10)
        return response

    def send_query(self):
        if not self.activated:
            self.chat_output.append("Error: Please activate the application")
            return
        query = self.user_input.text().strip()
        if not query:
            self.chat_output.append("Error: Please enter a query")
            self.chat_output.ensureCursorVisible()
            return

        self.chat_output.append(f"You: {query}")
        self.chat_output.repaint()
        QApplication.processEvents()
        self.user_input.clear()

        start_time = time.time()
        try:
            response = self.send_request(query)
            response.raise_for_status()
            response_text = response.json().get("response", "Error: No response")
        except requests.Timeout:
            response_text = "Error: Server took too long to respond."
        except requests.ConnectionError:
            response_text = "Error: Could not connect to the server."
        except requests.HTTPError as e:
            error_msg = response.json().get("detail", str(e))
            response_text = f"Error: {error_msg}"
            if "Trial command limit of 15 reached" in error_msg or "Trial period has ended" in error_msg:
                self.activated = False
                self.save_activation_status()
                self.user_input.setEnabled(False)
                response_text += "\nPlease activate a premium subscription to continue."
        except requests.RequestException as e:
            response_text = f"Error: {str(e)}"
        except ValueError as e:
            response_text = f"Error: Invalid response format ({str(e)})"
        elapsed = time.time() - start_time

        self.chat_output.append(f"Bot: {response_text} (Time: {elapsed:.2f}s)")
        self.chat_output.repaint()
        QApplication.processEvents()
        self.chat_output.ensureCursorVisible()

def main():
    app = QApplication(sys.argv)
    window = ChatWindow()
    window.show()
    if window.activated:
        window.user_input.setFocus()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()