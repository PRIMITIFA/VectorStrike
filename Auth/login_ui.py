import os
import sys
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QObject, QPropertyAnimation, QEasingCurve, QPoint, QTimer, QRect
from PyQt5.QtGui import QIcon, QPixmap, QColor, QPalette, QFont, QCursor
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFrame, QStackedWidget,
    QGridLayout, QSpacerItem, QSizePolicy, QMessageBox, QCheckBox,
    QGraphicsOpacityEffect
)

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Auth.login_integration import LoginIntegration

# Color scheme
COLORS = {
    'background': '#121212',
    'surface': '#1E1E1E',
    'primary': '#BB86FC',
    'secondary': '#03DAC6',
    'error': '#CF6679',
    'on_background': '#FFFFFF',
    'on_surface': '#FFFFFF',
    'on_primary': '#000000',
    'on_secondary': '#000000',
    'on_error': '#000000',
    'discord': '#5865F2',
    'google': '#DB4437'
}

class LoginWindow(QMainWindow):
    login_successful = pyqtSignal(object)
    login_failed = pyqtSignal(str)

    def __init__(self, login_integration: 'LoginIntegration', parent=None):
        super().__init__(parent)
        self.login_integration = login_integration
        self.setWindowTitle("Vector Strike - Login")
        self.init_ui()

        # Connect signals from LoginIntegration
        self.login_integration.login_successful.connect(self.on_login_successful)
        self.login_integration.login_failed.connect(self.on_login_failed)

    def on_login_successful(self, user):
        self.login_successful.emit(user)
        self.close()

    def on_login_failed(self, error_message):
        self.show_error_message(error_message)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            delta = event.globalPos() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPos()

    def fade_in(self):
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(300)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.animation.start()

    def animate_stacked_widget_transition(self, index):
        # Save current widget position
        current_index = self.stacked_widget.currentIndex()
        next_widget = self.stacked_widget.widget(index)
        current_widget = self.stacked_widget.widget(current_index)
        
        # Set the next widget visible but transparent
        next_widget.setVisible(True)
        
        # Create animation for sliding effect
        direction = 1 if index > current_index else -1
        
        # Move next widget outside the view
        next_widget.setGeometry(direction * self.stacked_widget.width(), 0, 
                               self.stacked_widget.width(), self.stacked_widget.height())
        
        # Animation for current widget (slide out)
        current_anim = QPropertyAnimation(current_widget, b"pos")
        current_anim.setDuration(300)
        current_anim.setStartValue(QPoint(0, 0))
        current_anim.setEndValue(QPoint(-direction * self.stacked_widget.width(), 0))
        current_anim.setEasingCurve(QEasingCurve.InOutQuad)
        
        # Animation for next widget (slide in)
        next_anim = QPropertyAnimation(next_widget, b"pos")
        next_anim.setDuration(300)
        next_anim.setStartValue(QPoint(direction * self.stacked_widget.width(), 0))
        next_anim.setEndValue(QPoint(0, 0))
        next_anim.setEasingCurve(QEasingCurve.InOutQuad)
        
        # Start animations
        current_anim.start()
        next_anim.start()
        
        # Store animations to prevent garbage collection
        self.animations = [current_anim, next_anim]
        
        # Change the index after animation completes
        next_anim.finished.connect(lambda: self.stacked_widget.setCurrentIndex(index))

    def show_login(self):
        self.animate_stacked_widget_transition(0)

    def show_signup(self):
        self.animate_stacked_widget_transition(1)

    def show_reset_password(self):
        self.animate_stacked_widget_transition(2)

    def init_ui(self):
        self.setWindowTitle("VectorStrike - Login")
        self.setMinimumSize(450, 600)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        container = QWidget()
        container.setStyleSheet(f"""
            background-color: {COLORS['background']};
            border-radius: 15px;
        """)
        self.setCentralWidget(container)

        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        title_bar = self._create_title_bar()
        main_layout.addWidget(title_bar)

        right_panel = self._create_right_panel()
        main_layout.addWidget(right_panel)

    def _create_title_bar(self):
        title_bar = QWidget()
        title_bar.setFixedHeight(40)
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(10, 0, 10, 0)

        title = QLabel("VectorStrike - Login")
        title.setStyleSheet("color: white; font-size: 14px;")
        title_bar_layout.addWidget(title)
        
        title_bar_layout.addStretch()

        self.minimize_button = QPushButton("_")
        self.minimize_button.setFixedSize(30, 30)
        self.minimize_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #333333;
            }
        """)
        self.minimize_button.clicked.connect(self.showMinimized)
        title_bar_layout.addWidget(self.minimize_button)

        self.close_button = QPushButton("✕")
        self.close_button.setFixedSize(30, 30)
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #D32F2F;
            }
        """)
        self.close_button.clicked.connect(self.close)
        title_bar_layout.addWidget(self.close_button)

        return title_bar

    def _create_right_panel(self):
        right_panel = QWidget()
        right_panel.setStyleSheet(f"background-color: {COLORS['background']};")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setAlignment(Qt.AlignCenter)
        right_layout.setContentsMargins(50, 50, 50, 50)

        self.stacked_widget = QStackedWidget()
        right_layout.addWidget(self.stacked_widget)

        login_widget = self._create_login_form()
        register_widget = self._create_register_form()
        reset_widget = self._create_reset_password_form()

        self.stacked_widget.addWidget(login_widget)
        self.stacked_widget.addWidget(register_widget)
        self.stacked_widget.addWidget(reset_widget)

        return right_panel

    def _create_login_form(self):
        login_widget = QWidget()
        login_layout = QVBoxLayout(login_widget)
        login_layout.setSpacing(20)

        login_header = QLabel("Welcome Back")
        login_header.setStyleSheet(f"color: {COLORS['on_background']}; font-size: 24px; font-weight: bold;")
        login_header.setAlignment(Qt.AlignCenter)
        login_layout.addWidget(login_header)

        subtitle = QLabel("Sign in to continue to Vector Strike")
        subtitle.setStyleSheet(f"color: #AAAAAA; font-size: 14px;")
        subtitle.setAlignment(Qt.AlignCenter)
        login_layout.addWidget(subtitle)

        # Apply animations to form elements
        self._animate_form_elements(login_widget, [login_header, subtitle])

        email_label = QLabel("Email")
        email_label.setStyleSheet(f"color: {COLORS['on_background']}; font-size: 14px;")
        login_layout.addWidget(email_label)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter your email")
        self.email_input.setStyleSheet(self._get_line_edit_style())
        login_layout.addWidget(self.email_input)

        password_label = QLabel("Password")
        password_label.setStyleSheet(f"color: {COLORS['on_background']}; font-size: 14px;")
        login_layout.addWidget(password_label)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Password")
        self.password_input.setStyleSheet(self._get_line_edit_style())
        self.password_input.textChanged.connect(self.clear_error_message)
        login_layout.addWidget(self.password_input)

        # Apply animations to form input elements
        self._animate_form_elements(login_widget, [email_label, self.email_input, password_label, self.password_input], start_delay=100)

        remember_layout = QHBoxLayout()
        self.remember_me_checkbox = QCheckBox("Remember Me")
        self.remember_me_checkbox.setStyleSheet(self._get_checkbox_style())
        remember_layout.addWidget(self.remember_me_checkbox)

        forgot_password = QPushButton("Forgot Password?")
        forgot_password.setFlat(True)
        forgot_password.setCursor(QCursor(Qt.PointingHandCursor))
        forgot_password.setStyleSheet(self._get_link_style())
        forgot_password.clicked.connect(self.show_reset_password)
        remember_layout.addWidget(forgot_password)
        login_layout.addLayout(remember_layout)

        login_button = QPushButton("Sign In")
        login_button.setCursor(QCursor(Qt.PointingHandCursor))
        login_button.setStyleSheet(self._get_button_style('primary'))
        login_button.clicked.connect(self.login_with_email)
        login_button.clicked.connect(lambda: self.button_click_animation(login_button))
        login_layout.addWidget(login_button)

        # Apply animations to buttons
        self._animate_form_elements(login_widget, [self.remember_me_checkbox, forgot_password, login_button], start_delay=200)

        separator = self._create_separator()
        login_layout.addWidget(separator)

        oauth_layout = QHBoxLayout()
        google_button = self._create_oauth_button("Sign in with Google", "google", self.handle_google_login)
        discord_button = self._create_oauth_button("Sign in with Discord", "discord", self.handle_discord_login)
        oauth_layout.addWidget(google_button)
        oauth_layout.addWidget(discord_button)
        login_layout.addLayout(oauth_layout)

        # Apply animations to OAuth buttons
        self._animate_form_elements(login_widget, [google_button, discord_button], start_delay=300)

        spacer = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        login_layout.addItem(spacer)

        signup_layout = QHBoxLayout()
        signup_text = QLabel("Don't have an account?")
        signup_text.setStyleSheet(f"color: {COLORS['on_background']}; font-size: 14px;")
        signup_layout.addWidget(signup_text)

        signup_link = QPushButton("Sign Up")
        signup_link.setFlat(True)
        signup_link.setCursor(QCursor(Qt.PointingHandCursor))
        signup_link.setStyleSheet(self._get_link_style())
        signup_link.clicked.connect(self.show_signup)
        signup_layout.addWidget(signup_link)
        login_layout.addLayout(signup_layout)

        # Apply animations to signup elements
        self._animate_form_elements(login_widget, [signup_text, signup_link], start_delay=400)

        return login_widget

    def _animate_form_elements(self, parent, widgets, start_delay=0):
        for i, widget in enumerate(widgets):
            if widget is None or not hasattr(widget, 'setGraphicsEffect'):
                continue
                
            # Create opacity effect
            opacity_effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(opacity_effect)
            opacity_effect.setOpacity(0)
            
            # Create animation
            anim = QPropertyAnimation(opacity_effect, b"opacity")
            anim.setDuration(300)
            anim.setStartValue(0)
            anim.setEndValue(1)
            anim.setEasingCurve(QEasingCurve.InOutQuad)
            
            # Store animation to prevent garbage collection
            if not hasattr(parent, '_animations'):
                parent._animations = []
            parent._animations.append(anim)
            
            # Use QTimer for delay instead of setDelay
            delay = start_delay + i * 50  # Stagger the animations
            QTimer.singleShot(delay, anim.start)

    def _create_register_form(self):
        register_widget = QWidget()
        register_layout = QVBoxLayout(register_widget)
        register_layout.setSpacing(20)

        register_header = QLabel("Create Account")
        register_header.setStyleSheet(f"color: {COLORS['on_background']}; font-size: 24px; font-weight: bold;")
        register_header.setAlignment(Qt.AlignCenter)
        register_layout.addWidget(register_header)
        
        # Apply animations to header
        self._animate_form_elements(register_widget, [register_header])

        reg_email_label = QLabel("Email")
        reg_email_label.setStyleSheet(f"color: {COLORS['on_background']}; font-size: 14px;")
        register_layout.addWidget(reg_email_label)

        self.reg_email_input = QLineEdit()
        self.reg_email_input.setPlaceholderText("Enter your email")
        self.reg_email_input.setStyleSheet(self._get_line_edit_style())
        register_layout.addWidget(self.reg_email_input)

        reg_password_label = QLabel("Password")
        reg_password_label.setStyleSheet(f"color: {COLORS['on_background']}; font-size: 14px;")
        register_layout.addWidget(reg_password_label)

        self.reg_password_input = QLineEdit()
        self.reg_password_input.setPlaceholderText("Create a password")
        self.reg_password_input.setEchoMode(QLineEdit.Password)
        self.reg_password_input.setStyleSheet(self._get_line_edit_style())
        register_layout.addWidget(self.reg_password_input)

        confirm_password_label = QLabel("Confirm Password")
        confirm_password_label.setStyleSheet(f"color: {COLORS['on_background']}; font-size: 14px;")
        register_layout.addWidget(confirm_password_label)

        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setPlaceholderText("Confirm your password")
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        self.confirm_password_input.setStyleSheet(self._get_line_edit_style())
        register_layout.addWidget(self.confirm_password_input)
        
        # Apply animations to form input elements
        self._animate_form_elements(register_widget, [
            reg_email_label, self.reg_email_input, 
            reg_password_label, self.reg_password_input,
            confirm_password_label, self.confirm_password_input
        ], start_delay=100)

        self.terms_checkbox = QCheckBox("I agree to the Terms of Service and Privacy Policy")
        self.terms_checkbox.setStyleSheet(self._get_checkbox_style())
        register_layout.addWidget(self.terms_checkbox)

        register_button = QPushButton("Create Account")
        register_button.setCursor(QCursor(Qt.PointingHandCursor))
        register_button.setStyleSheet(self._get_button_style('primary'))
        register_button.clicked.connect(self.register)
        register_layout.addWidget(register_button)
        
        # Apply animations to checkbox and button
        self._animate_form_elements(register_widget, [self.terms_checkbox, register_button], start_delay=200)

        signin_layout = QHBoxLayout()
        signin_text = QLabel("Already have an account?")
        signin_text.setStyleSheet(f"color: {COLORS['on_background']}; font-size: 14px;")
        signin_layout.addWidget(signin_text)

        signin_link = QPushButton("Sign In")
        signin_link.setFlat(True)
        signin_link.setCursor(QCursor(Qt.PointingHandCursor))
        signin_link.setStyleSheet(self._get_link_style())
        signin_link.clicked.connect(self.show_login)
        signin_layout.addWidget(signin_link)
        register_layout.addLayout(signin_layout)
        
        # Apply animations to signin elements
        self._animate_form_elements(register_widget, [signin_text, signin_link], start_delay=300)

        return register_widget

    def _create_reset_password_form(self):
        reset_widget = QWidget()
        reset_layout = QVBoxLayout(reset_widget)
        reset_layout.setSpacing(20)

        reset_header = QLabel("Reset Password")
        reset_header.setStyleSheet(f"color: {COLORS['on_background']}; font-size: 24px; font-weight: bold;")
        reset_header.setAlignment(Qt.AlignCenter)
        reset_layout.addWidget(reset_header)

        reset_info = QLabel("Enter your email address and we'll send you a link to reset your password.")
        reset_info.setStyleSheet(f"color: {COLORS['on_background']}; font-size: 14px;")
        reset_info.setWordWrap(True)
        reset_layout.addWidget(reset_info)
        
        # Apply animations to header and info
        self._animate_form_elements(reset_widget, [reset_header, reset_info])

        reset_email_label = QLabel("Email")
        reset_email_label.setStyleSheet(f"color: {COLORS['on_background']}; font-size: 14px;")
        reset_layout.addWidget(reset_email_label)

        self.reset_email_input = QLineEdit()
        self.reset_email_input.setPlaceholderText("Enter your email")
        self.reset_email_input.setStyleSheet(self._get_line_edit_style())
        reset_layout.addWidget(self.reset_email_input)
        
        # Apply animations to email input
        self._animate_form_elements(reset_widget, [reset_email_label, self.reset_email_input], start_delay=100)

        reset_button = QPushButton("Send Reset Link")
        reset_button.setCursor(QCursor(Qt.PointingHandCursor))
        reset_button.setStyleSheet(self._get_button_style('primary'))
        reset_button.clicked.connect(self.reset_password)
        reset_layout.addWidget(reset_button)
        
        # Apply animations to button
        self._animate_form_elements(reset_widget, [reset_button], start_delay=200)

        back_layout = QHBoxLayout()
        back_link = QPushButton("Back to Sign In")
        back_link.setFlat(True)
        back_link.setCursor(QCursor(Qt.PointingHandCursor))
        back_link.setStyleSheet(self._get_link_style())
        back_link.clicked.connect(self.show_login)
        back_layout.addWidget(back_link)
        reset_layout.addLayout(back_layout)
        
        # Apply animations to back link
        self._animate_form_elements(reset_widget, [back_link], start_delay=300)

        return reset_widget

    def _create_separator(self):
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("color: #444; margin: 10px 0;")
        return separator

    def _create_oauth_button(self, text, provider, handler):
        button = QPushButton(text)
        button.setCursor(QCursor(Qt.PointingHandCursor))

        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "photos", "icons", f"{provider}_icon.png")
        if os.path.exists(icon_path):
            button.setIcon(QIcon(icon_path))
            button.setIconSize(QSize(24, 24))

        button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['on_background']};
                border: 1px solid {COLORS['surface']};
                padding: 10px;
                border-radius: 5px;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {COLORS['surface']};
            }}
        """)
        button.clicked.connect(handler)
        button.clicked.connect(lambda: self.button_click_animation(button))
        return button

    def _get_line_edit_style(self):
        return f"""
            QLineEdit {{
                background-color: {COLORS['surface']};
                color: {COLORS['on_surface']};
                border: 1px solid #333333;
                border-radius: 4px;
                padding: 10px;
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border: 1px solid {COLORS['primary']};
            }}
        """

    def _get_button_style(self, provider):
        base_style = f"""
            QPushButton {{
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
                text-align: center;
            }}
        """
        if provider == 'primary':
            return base_style + f"""
                QPushButton {{
                    background-color: {COLORS['primary']};
                    color: {COLORS['on_primary']};
                }}
                QPushButton:hover {{
                    background-color: {COLORS['primary']};
                }}
                QPushButton:pressed {{
                    background-color: {COLORS['primary']};
                }}
            """
        elif provider == 'secondary':
            return base_style + f"""
                QPushButton {{
                    background-color: {COLORS['secondary']};
                    color: {COLORS['on_secondary']};
                }}
                QPushButton:hover {{
                    background-color: {self._adjust_color(COLORS['secondary'], 15)};
                }}
                QPushButton:pressed {{
                    background-color: {self._adjust_color(COLORS['secondary'], -15)};
                }}
            """
        else:
            return base_style + f"""
                QPushButton {{
                    background-color: #1a1a1a;
                    color: {COLORS['on_background']};
                }}
                QPushButton:hover {{
                    background-color: #2a2a2a;
                }}
                QPushButton:pressed {{
                    background-color: #3a3a3a;
                }}
            """

    def _get_link_style(self):
        return f"""
            QPushButton {{
                color: {COLORS['primary']};
                background-color: transparent;
                border: none;
                font-size: 14px;
                text-decoration: none;
            }}
            QPushButton:hover {{
                color: {self._adjust_color(COLORS['primary'], 15)};
                text-decoration: underline;
            }}
            QPushButton:pressed {{
                color: {self._adjust_color(COLORS['primary'], -15)};
            }}
        """

    def _get_checkbox_style(self):
        return f"""
            QCheckBox {{
                color: {COLORS['on_background']};
                font-size: 14px;
                spacing: 5px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 3px;
                border: 1px solid #555;
                background-color: {COLORS['surface']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {COLORS['primary']};
                border: 1px solid {COLORS['primary']};
                image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' viewBox='0 0 24 24'%3E%3Cpath fill='%23000000' d='M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z'/%3E%3C/svg%3E");
            }}
            QCheckBox::indicator:hover {{
                border: 1px solid {COLORS['primary']};
            }}
        """

    def _adjust_color(self, color, amount):
        color = QColor(color)
        h, s, l, a = color.getHsl()
        l = max(0, min(255, l + amount))
        color.setHsl(h, s, l, a)
        return color.name()

    def handle_google_login(self):
        self.login_integration.login_with_provider("google")

    def handle_discord_login(self):
        self.login_integration.login_with_provider("discord")

    def clear_error_message(self):
        pass
    
    def show_login(self):
        self.stacked_widget.setCurrentIndex(0)
    
    def show_signup(self):
        self.stacked_widget.setCurrentIndex(1)
    
    def show_reset_password(self):
        self.stacked_widget.setCurrentIndex(2)
    
    def login_with_email(self):
        email = self.email_input.text()
        password = self.password_input.text()
        
        # Show loading animation
        self._show_loading_animation()
        
        # Simulate network delay for demo purposes
        QTimer.singleShot(1000, lambda: self._perform_login(email, password))
    
    def _perform_login(self, email, password):
        # Hide loading animation
        self._hide_loading_animation()

        # Continue with actual login logic
        if not email or not password:
            self.show_error_message("Please enter both email and password.")
            return

        self.login_integration.login_with_email(email, password)

    def show_error_message(self, message):
        QMessageBox.warning(self, "Login Error", message)

    def clear_error_message(self):
        # This method is called when password field changes
        pass
    
    def _show_loading_animation(self):
        # Create loading overlay if it doesn't exist
        if not hasattr(self, 'loading_overlay'):
            self.loading_overlay = QWidget(self)
            self.loading_overlay.setStyleSheet(f"background-color: rgba(0, 0, 0, 0.7); border-radius: 15px;")
            self.loading_overlay.setGeometry(self.rect())
            
            layout = QVBoxLayout(self.loading_overlay)
            layout.setAlignment(Qt.AlignCenter)
            
            loading_label = QLabel("Logging in...")
            loading_label.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
            loading_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(loading_label)
            
            # Create dots animation
            self.dots_label = QLabel("")
            self.dots_label.setStyleSheet("color: white; font-size: 24px;")
            self.dots_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(self.dots_label)
            
            # Setup dots animation timer
            self.dots_timer = QTimer(self)
            self.dots_timer.timeout.connect(self._update_dots)
            self.dots_count = 0
        
        # Show overlay and start animation
        self.loading_overlay.show()
        self.dots_timer.start(300)
    
    def _update_dots(self):
        dots = "." * ((self.dots_count % 3) + 1)
        self.dots_label.setText(dots)
        self.dots_count += 1
    
    def _hide_loading_animation(self):
        if hasattr(self, 'loading_overlay'):
            self.dots_timer.stop()
            self.loading_overlay.hide()

    def button_click_animation(self, button):
        # Create animation for button click effect
        anim = QPropertyAnimation(button, b"geometry")
        anim.setDuration(100)
        
        # Get current geometry
        current_geo = button.geometry()
        
        # Shrink slightly
        shrink_geo = QRect(
            current_geo.x() + 2, 
            current_geo.y() + 2, 
            current_geo.width() - 4, 
            current_geo.height() - 4
        )
        
        # Set keyframes
        anim.setKeyValueAt(0, current_geo)
        anim.setKeyValueAt(0.5, shrink_geo)
        anim.setKeyValueAt(1, current_geo)
        
        # Set easing curve
        anim.setEasingCurve(QEasingCurve.OutInQuad)
        
        # Start animation
        anim.start()

    def register(self):
        email = self.reg_email_input.text().strip()
        password = self.reg_password_input.text()
        confirm_password = self.confirm_password_input.text()

        # Validate input
        if not email or not password or not confirm_password:
            QMessageBox.warning(self, "Registration Error", "Please fill in all fields.")
            return

        if password != confirm_password:
            QMessageBox.warning(self, "Registration Error", "Passwords do not match.")
            return

        if not self.terms_checkbox.isChecked():
            QMessageBox.warning(self, "Registration Error", "You must agree to the Terms of Service and Privacy Policy.")
            return

        # Validate password strength
        if len(password) < 8:
            QMessageBox.warning(self, "Registration Error", "Password must be at least 8 characters long.")
            return

        # Attempt registration
        if self.login_integration.sign_up_with_email(email, password):
            QMessageBox.information(self, "Registration Successful", "Your account has been created successfully. You can now log in.")
            self.show_login()
        else:
            QMessageBox.warning(self, "Registration Error", "Failed to create account. Please try again.")

    def reset_password(self):
        email = self.reset_email_input.text().strip()

        # Validate input
        if not email:
            QMessageBox.warning(self, "Reset Error", "Please enter your email address.")
            return

        # Attempt password reset
        if self.login_integration.reset_password(email):
            QMessageBox.information(self, "Reset Email Sent", "If an account exists with this email, you will receive a password reset link.")
            self.show_login()
        else:
            QMessageBox.warning(self, "Reset Error", "Failed to send reset email. Please try again.")


def show_login_window():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    
    from Auth.login_integration import LoginIntegration
    login_integration = LoginIntegration()
    login_window = LoginWindow(login_integration)
    login_window.show()
    
    return app, login_window


if __name__ == "__main__":
    app, login_window = show_login_window()
    sys.exit(app.exec_())