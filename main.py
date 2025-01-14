import sys
import cv2
import mediapipe as mp
import numpy as np
import json
import os
import time
import datetime
import keyboard
import screen_brightness_control as sbc
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
import pyautogui
import threading
import sounddevice as sd
import soundfile as sf
import pygame
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from PIL import Image, ImageEnhance
import pickle

# MediaPipe modules
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# Modern UI components
class ModernButton(QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                border: none;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
            QPushButton:pressed {
                background-color: #219a52;
            }
        """)

class ModernSlider(QSlider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 8px;
                background: #cccccc;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #2ecc71;
                border: none;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
        """)

class ModernComboBox(QComboBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setStyleSheet("""
            QComboBox {
                border: 2px solid #2ecc71;
                border-radius: 5px;
                padding: 5px;
                background: white;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: url(assets/down-arrow.png);
                width: 12px;
                height: 12px;
            }
        """)

class ModernLabel(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                font-size: 14px;
            }
        """)

class CameraView(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMinimumSize(640, 480)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                background-color: #34495e;
                border-radius: 10px;
            }
        """)

class StatsWidget(QFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                padding: 10px;
            }
            QLabel {
                color: #2c3e50;
                font-size: 14px;
            }
        """)
        
        layout = QVBoxLayout(self)
        self.screenshot_label = ModernLabel("Screenshots: 0")
        self.uptime_label = ModernLabel("Uptime: 00:00:00")
        layout.addWidget(self.screenshot_label)
        layout.addWidget(self.uptime_label)

# Main application class
class GestureControlApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Clapathon")
        self.setGeometry(100, 100, 1200, 800)
        
        # Variables
        self.camera_active = False
        self.current_camera = 0
        self.available_cameras = []
        self.screenshot_count = 0
        self.start_time = time.time()
        self.last_clap_time = 0
        self.clap_threshold = 0.3
        self.last_gesture = None
        self.virtual_keyboard_active = False
        self.mouse_control_active = False
        self.exercise_mode_active = False
        self.current_profile = "default"
        self.current_theme = "light"
        
        # MediaPipe hand detection
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        
        # Volume control
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        self.volume = interface.QueryInterface(IAudioEndpointVolume)
        
        # Spotify API
        self.spotify = None
        self.init_spotify()
        
        # Pygame sound effects
        pygame.mixer.init()
        self.load_sound_effects()
        
        # Profile management
        self.profiles = self.load_profiles()
        
        # UI setup
        self.setup_ui()
        
        # Camera refresh timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        
        # Stats update timer
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(1000)
        
        # Scan cameras
        self.refresh_cameras()

    def init_spotify(self):
        try:
            self.spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(
                client_id="YOUR_CLIENT_ID",
                client_secret="YOUR_CLIENT_SECRET",
                redirect_uri="http://localhost:8888/callback",
                scope="user-modify-playback-state user-read-playback-state"
            ))
        except Exception as e:
            print(f"Could not connect to Spotify: {e}")

    def load_sound_effects(self):
        try:
            pygame.mixer.init()
            self.sounds = {}
            print("Sound system initialized (sound effects disabled)")
        except Exception as e:
            print(f"Could not initialize sound system: {e}")
            self.sounds = {}

    def load_profiles(self):
        try:
            with open('profiles.pkl', 'rb') as f:
                return pickle.load(f)
        except:
            return {'default': {
                'clap_threshold': 0.3,
                'gesture_sensitivity': 0.7,
                'shortcuts': {},
                'theme': 'light'
            }}

    def save_profiles(self):
        with open('profiles.pkl', 'wb') as f:
            pickle.dump(self.profiles, f)

    def setup_ui(self):
        # Main widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)
        
        # Left menu
        left_menu = QFrame()
        left_menu.setStyleSheet("""
            QFrame {
                background-color: #2c3e50;
                border-radius: 10px;
                margin: 10px;
                padding: 10px;
                max-width: 200px;
            }
        """)
        left_layout = QVBoxLayout(left_menu)
        
        # Camera control
        camera_group = QGroupBox("Camera Control")
        camera_group.setStyleSheet("QGroupBox { color: white; }")
        camera_layout = QVBoxLayout(camera_group)
        
        self.camera_combo = ModernComboBox()
        self.camera_combo.currentIndexChanged.connect(self.change_camera)
        
        self.camera_button = ModernButton("Start Camera")
        self.camera_button.clicked.connect(self.toggle_camera)
        
        camera_layout.addWidget(self.camera_combo)
        camera_layout.addWidget(self.camera_button)
        
        # Mode options
        modes_group = QGroupBox("Modes")
        modes_group.setStyleSheet("QGroupBox { color: white; }")
        modes_layout = QVBoxLayout(modes_group)
        
        self.keyboard_button = ModernButton("Virtual Keyboard")
        self.keyboard_button.clicked.connect(self.toggle_virtual_keyboard)
        
        self.mouse_button = ModernButton("Mouse Control")
        self.mouse_button.clicked.connect(self.toggle_mouse_control)
        
        self.exercise_button = ModernButton("Exercise Mode")
        self.exercise_button.clicked.connect(self.toggle_exercise_mode)
        
        modes_layout.addWidget(self.keyboard_button)
        modes_layout.addWidget(self.mouse_button)
        modes_layout.addWidget(self.exercise_button)
        
        # Profile selection
        profile_group = QGroupBox("Profile")
        profile_group.setStyleSheet("QGroupBox { color: white; }")
        profile_layout = QVBoxLayout(profile_group)
        
        self.profile_combo = ModernComboBox()
        self.profile_combo.addItems(self.profiles.keys())
        self.profile_combo.currentTextChanged.connect(self.change_profile)
        
        profile_layout.addWidget(self.profile_combo)
        
        # Add groups to left menu
        left_layout.addWidget(camera_group)
        left_layout.addWidget(modes_group)
        left_layout.addWidget(profile_group)
        left_layout.addStretch()
        
        # Main content area
        content_area = QFrame()
        content_area.setStyleSheet("""
            QFrame {
                background-color: #ecf0f1;
                border-radius: 10px;
                margin: 10px;
                padding: 10px;
            }
        """)
        content_layout = QVBoxLayout(content_area)
        
        # Camera view
        self.camera_view = CameraView()
        
        # Status bar
        status_bar = QFrame()
        status_bar.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                padding: 5px;
            }
        """)
        status_layout = QHBoxLayout(status_bar)
        
        self.camera_status = ModernLabel("Camera: Off")
        self.gesture_status = ModernLabel("Gesture: -")
        self.mode_status = ModernLabel("Mode: Normal")
        
        status_layout.addWidget(self.camera_status)
        status_layout.addWidget(self.gesture_status)
        status_layout.addWidget(self.mode_status)
        
        # Stats
        self.stats_widget = StatsWidget()
        
        # Add widgets to content area
        content_layout.addWidget(status_bar)
        content_layout.addWidget(self.camera_view)
        content_layout.addWidget(self.stats_widget)
        
        # Add left menu and content area to layout
        layout.addWidget(left_menu)
        layout.addWidget(content_area)

    def refresh_cameras(self):
        self.available_cameras = []
        self.camera_combo.clear()
        
        # Check camera count
        max_cameras = 10  # Check maximum 10 cameras
        for index in range(max_cameras):
            try:
                cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)  # Use DirectShow
                if cap.isOpened():
                    ret, _ = cap.read()
                    if ret:
                        self.available_cameras.append(index)
                        self.camera_combo.addItem(f"Camera {index}")
                cap.release()
            except Exception as e:
                print(f"Error checking camera {index}: {e}")
        
        if not self.available_cameras:
            print("No cameras found!")
            self.camera_combo.addItem("No camera")
        else:
            print(f"{len(self.available_cameras)} cameras found")

    def change_camera(self, index):
        if self.camera_active:
            self.toggle_camera()  # Turn off current camera
        self.current_camera = self.available_cameras[index]
        if self.camera_active:
            self.toggle_camera()  # Turn on new camera
        print(f"Camera {self.current_camera} selected")

    def toggle_camera(self):
        if not self.camera_active:
            try:
                self.cap = cv2.VideoCapture(self.current_camera, cv2.CAP_DSHOW)
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.cap.set(cv2.CAP_PROP_FPS, 30)
                
                if not self.cap.isOpened():
                    raise Exception("Could not open camera!")
                
                self.camera_active = True
                self.timer.start(30)
                self.camera_button.setText("Stop Camera")
                self.camera_status.setText("Camera: On")
                self.play_sound('gesture')
            except Exception as e:
                print(f"Error starting camera: {e}")
                self.show_feedback("Camera error!", "#c0392b")
                return
        else:
            try:
                self.timer.stop()
                if hasattr(self, 'cap'):
                    self.cap.release()
                self.camera_active = False
                self.camera_button.setText("Start Camera")
                self.camera_status.setText("Camera: Off")
                self.camera_view.clear()
                self.play_sound('gesture')
            except Exception as e:
                print(f"Error stopping camera: {e}")

    def update_frame(self):
        if not hasattr(self, 'cap') or not self.cap.isOpened():
            self.show_feedback("Camera connection lost!", "#c0392b")
            self.toggle_camera()  # Turn off camera
            return
            
        try:
            ret, frame = self.cap.read()
            if not ret or frame is None:
                raise Exception("Could not capture frame!")
                
            # Flip the frame
            frame = cv2.flip(frame, 1)
            
            # Hand detection
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb_frame)
            
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    # Draw landmarks
                    mp_drawing.draw_landmarks(
                        frame,
                        hand_landmarks,
                        mp_hands.HAND_CONNECTIONS,
                        mp_drawing_styles.get_default_hand_landmarks_style(),
                        mp_drawing_styles.get_default_hand_connections_style()
                    )
                    
                    # Gesture detection
                    if len(results.multi_hand_landmarks) == 2:
                        self.process_two_hand_gesture(results.multi_hand_landmarks)
                    else:
                        self.process_single_hand_gesture(hand_landmarks)
            
            # Active modes
            if self.virtual_keyboard_active:
                cv2.putText(frame, "Virtual Keyboard Active", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            if self.mouse_control_active:
                cv2.putText(frame, "Mouse Control Active", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            if self.exercise_mode_active:
                cv2.putText(frame, "Exercise Mode Active", (10, 90),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # Send frame to Qt label
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            qt_image = qt_image.rgbSwapped()
            self.camera_view.setPixmap(QPixmap.fromImage(qt_image).scaled(
                self.camera_view.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                
        except Exception as e:
            print(f"Error processing frame: {e}")
            self.show_feedback("Camera error!", "#c0392b")

    def process_two_hand_gesture(self, hand_landmarks):
        # Two hand gesture detection
        hand1 = hand_landmarks[0].landmark
        hand2 = hand_landmarks[1].landmark
        
        # Clap detection
        distance = ((hand1[9].x - hand2[9].x) ** 2 + 
                   (hand1[9].y - hand2[9].y) ** 2) ** 0.5
        
        if distance < self.clap_threshold:
            current_time = time.time()
            if current_time - self.last_clap_time > 1.0:
                self.take_screenshot()
                self.last_clap_time = current_time
        
        # Virtual keyboard control
        if self.virtual_keyboard_active:
            self.handle_virtual_keyboard(hand1, hand2)
        
        # Volume control
        self.handle_volume_control(hand1, hand2)

    def process_single_hand_gesture(self, hand_landmarks):
        # Single hand gesture detection
        landmarks = hand_landmarks.landmark
        
        # Mouse control
        if self.mouse_control_active:
            self.handle_mouse_control(landmarks)
        
        # Shortcut based on finger count
        finger_count = self.count_fingers(landmarks)
        self.handle_finger_shortcuts(finger_count)
        
        # Exercise mode controls
        if self.exercise_mode_active:
            self.handle_exercise_tracking(landmarks)

    def handle_virtual_keyboard(self, hand1, hand2):
        # Virtual keyboard control
        distance = ((hand1[8].x - hand2[8].x) ** 2 + 
                   (hand1[8].y - hand2[8].y) ** 2) ** 0.5
        
        if distance < 0.1:  # Fingers are close
            avg_y = (hand1[8].y + hand2[8].y) / 2
            avg_x = (hand1[8].x + hand2[8].x) / 2
            
            # Convert screen coordinates
            screen_x = int(avg_x * pyautogui.size().width)
            screen_y = int(avg_y * pyautogui.size().height)
            
            # Virtual key press
            key = self.get_virtual_key(screen_x, screen_y)
            if key:
                keyboard.press_and_release(key)
                self.play_sound('gesture')

    def handle_mouse_control(self, landmarks):
        # Mouse control
        screen_w, screen_h = pyautogui.size()
        index_x = int(landmarks[8].x * screen_w)
        index_y = int(landmarks[8].y * screen_h)
        
        # Move cursor
        pyautogui.moveTo(index_x, index_y, duration=0.1)
        
        # Click control
        if landmarks[4].y > landmarks[8].y:  # Thumb is above index finger
            pyautogui.click()
            self.play_sound('gesture')

    def handle_volume_control(self, hand1, hand2):
        # Volume control
        y_diff = abs(hand1[8].y - hand2[8].y)
        volume_level = 1 - min(y_diff, 0.5) * 2  # 0-1 range
        
        # Set system volume level
        self.volume.SetMasterVolumeLevelScalar(volume_level, None)

    def handle_finger_shortcuts(self, finger_count):
        # Shortcut based on finger count
        shortcuts = self.profiles[self.current_profile]['shortcuts']
        if str(finger_count) in shortcuts:
            command = shortcuts[str(finger_count)]
            if command.startswith('key:'):
                keyboard.press_and_release(command[4:])
            elif command.startswith('media:'):
                self.control_media(command[6:])
            self.play_sound('gesture')

    def handle_exercise_tracking(self, landmarks):
        # Exercise tracking
        wrist_y = landmarks[0].y
        shoulder_threshold = 0.3
        
        if wrist_y < shoulder_threshold:
            self.gesture_status.setText("Gesture: Raise Hand")
        else:
            self.gesture_status.setText("Gesture: Sit Up")

    def control_media(self, command):
        # Media control
        if self.spotify:
            try:
                if command == 'play':
                    self.spotify.start_playback()
                elif command == 'pause':
                    self.spotify.pause_playback()
                elif command == 'next':
                    self.spotify.next_track()
                elif command == 'previous':
                    self.spotify.previous_track()
            except Exception as e:
                print(f"Spotify control error: {e}")

    def take_screenshot(self):
        # Take screenshot
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshots/screenshot_{timestamp}.png"
        
        # Check directory
        os.makedirs("screenshots", exist_ok=True)
        
        # Take screenshot
        screen = pyautogui.screenshot()
        screen.save(filename)
        
        self.screenshot_count += 1
        self.stats_widget.screenshot_label.setText(f"Screenshots: {self.screenshot_count}")
        self.play_sound('screenshot')

    def update_stats(self):
        # Update stats
        uptime = int(time.time() - self.start_time)
        hours = uptime // 3600
        minutes = (uptime % 3600) // 60
        seconds = uptime % 60
        
        self.stats_widget.uptime_label.setText(
            f"Uptime: {hours:02d}:{minutes:02d}:{seconds:02d}")

    def toggle_virtual_keyboard(self):
        self.virtual_keyboard_active = not self.virtual_keyboard_active
        self.keyboard_button.setStyleSheet("""
            QPushButton {
                background-color: """ + ("#27ae60" if self.virtual_keyboard_active else "#2ecc71") + """;
                border: none;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
            }
        """)
        self.mode_status.setText(f"Mode: {'Virtual Keyboard' if self.virtual_keyboard_active else 'Normal'}")
        self.play_sound('gesture')

    def toggle_mouse_control(self):
        self.mouse_control_active = not self.mouse_control_active
        self.mouse_button.setStyleSheet("""
            QPushButton {
                background-color: """ + ("#27ae60" if self.mouse_control_active else "#2ecc71") + """;
                border: none;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
            }
        """)
        self.mode_status.setText(f"Mode: {'Mouse Control' if self.mouse_control_active else 'Normal'}")
        self.play_sound('gesture')

    def toggle_exercise_mode(self):
        self.exercise_mode_active = not self.exercise_mode_active
        self.exercise_button.setStyleSheet("""
            QPushButton {
                background-color: """ + ("#27ae60" if self.exercise_mode_active else "#2ecc71") + """;
                border: none;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
            }
        """)
        self.mode_status.setText(f"Mode: {'Exercise' if self.exercise_mode_active else 'Normal'}")
        self.play_sound('gesture')

    def change_profile(self, profile_name):
        self.current_profile = profile_name
        profile = self.profiles[profile_name]
        
        # Apply profile settings
        self.clap_threshold = profile['clap_threshold']
        self.hands = self.mp_hands.Hands(
            min_detection_confidence=profile['gesture_sensitivity']
        )
        
        # Apply theme
        self.apply_theme(profile['theme'])
        
        self.play_sound('gesture')

    def apply_theme(self, theme):
        self.current_theme = theme
        if theme == 'dark':
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #2c3e50;
                }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #ecf0f1;
                }
            """)

    def count_fingers(self, landmarks):
        # Calculate finger count
        fingers = 0
        finger_tips = [8, 12, 16, 20]  # Indices, middle, ring, and pinky finger tips
        
        # Thumb control
        if landmarks[4].x < landmarks[3].x:
            fingers += 1
        
        # Other fingers
        for tip in finger_tips:
            if landmarks[tip].y < landmarks[tip - 2].y:
                fingers += 1
                
        return fingers

    def get_virtual_key(self, x, y):
        # Virtual keyboard key map
        keyboard_layout = {
            (0, 0): 'a', (1, 0): 's', (2, 0): 'd', (3, 0): 'f',
            (0, 1): 'q', (1, 1): 'w', (2, 1): 'e', (3, 1): 'r',
            (0, 2): 'z', (1, 2): 'x', (2, 2): 'c', (3, 2): 'v'
        }
        
        # Divide screen into grid
        grid_x = x // (pyautogui.size().width // 4)
        grid_y = y // (pyautogui.size().height // 3)
        
        return keyboard_layout.get((grid_x, grid_y))

    def play_sound(self, sound_name):
        # Visual feedback instead of sound
        if sound_name == 'screenshot':
            self.show_feedback("Screenshot taken!", "#27ae60")
        elif sound_name == 'gesture':
            self.show_feedback("Gesture detected!", "#2980b9")
        elif sound_name == 'error':
            self.show_feedback("Error!", "#c0392b")

    def show_feedback(self, message, color):
        # Create temporary label
        feedback = QLabel(message, self)
        feedback.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
            }}
        """)
        feedback.adjustSize()
        
        # Place label in center of screen
        x = (self.width() - feedback.width()) // 2
        feedback.move(x, 20)
        feedback.show()
        
        # Remove after 2 seconds
        QTimer.singleShot(2000, feedback.deleteLater)

    def closeEvent(self, event):
        # Clean up before closing
        if self.camera_active:
            self.cap.release()
        self.save_profiles()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = GestureControlApp()
    window.show()
    sys.exit(app.exec_()) 