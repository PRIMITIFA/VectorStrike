import os
import sys
import subprocess
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton, QMessageBox
from PyQt5.QtCore import Qt, QTimer

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from Auth.login_integration import initialize_login, require_authentication


class MainApplication(QMainWindow):
    """Example main application that requires authentication"""
    
    def __init__(self, user=None):
        super().__init__()
        self.user = user
        self.login_integration = initialize_login()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("VectorStrike - Main Application")
        self.setMinimumSize(800, 600)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        layout = QVBoxLayout(central_widget)
        layout.setAlignment(Qt.AlignCenter)
        
        # Welcome message
        welcome_label = QLabel(f"Welcome to VectorStrike!")
        welcome_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(welcome_label)
        
        # User info
        if self.user:
            if isinstance(self.user, dict):
                user_email = self.user.get('email', 'Unknown')
            else:
                # Handle Supabase user object
                user_email = getattr(self.user, 'email', 'Unknown')
                
            user_label = QLabel(f"Logged in as: {user_email}")
            user_label.setStyleSheet("font-size: 16px;")
            layout.addWidget(user_label)
        
        # Launch Cheats Button
        launch_button = QPushButton("Launch Cheats Menu")
        launch_button.setStyleSheet("""
            QPushButton {
                background-color: #03DAC6;
                color: #000000;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00B5A3;
            }
        """)
        launch_button.clicked.connect(self.launch_cheats)
        layout.addWidget(launch_button)
        
        # Logout button
        logout_button = QPushButton("Logout")
        logout_button.setStyleSheet("""
            QPushButton {
                background-color: #BB86FC;
                color: #000000;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #9E75D6;
            }
        """)
        logout_button.clicked.connect(self.logout)
        layout.addWidget(logout_button)
        
        # Auto-launch cheats if user is authenticated
        if self.user:
            self.launch_cheats()
    
    def launch_cheats(self):
        """Launch the VectorStrike cheats menu"""
        try:
            # Get the absolute path to VectorStrike_V1.py
            vectorstrike_path = os.path.join(project_root, "VectorStrike_V1.py")
            print(f"Launching cheats menu from: {vectorstrike_path}")
            
            # Launch the VectorStrike cheats menu directly without closing the window first
            # Use a direct command that's more likely to work on Windows
            cmd = f'"{sys.executable}" "{vectorstrike_path}"'
            print(f"Running command: {cmd}")
            
            # Start the process and don't wait for it to complete
            process = subprocess.Popen(
                cmd,
                shell=True,  # Use shell=True for Windows compatibility
                creationflags=subprocess.CREATE_NEW_CONSOLE  # Create a new console window
            )
            
            # Wait a moment to ensure the process starts before closing this window
            QApplication.processEvents()
            
            # Only close the main window after a short delay to ensure the process started
            QTimer.singleShot(1000, self.close)
            
        except Exception as e:
            print(f"Error launching cheats menu: {e}")
            # If there's an error, show a message box
            error_dialog = QMessageBox()
            error_dialog.setIcon(QMessageBox.Critical)
            error_dialog.setText("Error launching cheats menu")
            error_dialog.setInformativeText(str(e))
            error_dialog.setWindowTitle("Error")
            error_dialog.exec_()
    
    def logout(self):
        """Log out the current user and show login window"""
        if self.login_integration.logout():
            self.close()
            app, login_window = self.login_integration.show_login_window()
            login_window.login_successful.connect(self.on_login_successful)
            app.exec_()
    
    def on_login_successful(self, user):
        """Handle successful login"""
        print("Login successful in MainApplication, creating new instance")
        self.user = user
        
        # Create a new instance with the updated user
        main_app = MainApplication(user)
        main_app.show()
        
        # Close this window after showing the new one
        QTimer.singleShot(500, self.close)


@require_authentication
def start_application():
    """Start the main application with authentication"""
    app = QApplication.instance() or QApplication(sys.argv)
    login_integration = initialize_login()
    user = login_integration.get_current_user()
    
    main_app = MainApplication(user)
    main_app.show()
    
    return app.exec_()


if __name__ == "__main__":
    start_application()