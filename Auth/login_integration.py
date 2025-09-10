import os
import sys
import json
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QObject, pyqtSignal

from .supabase_client import SupabaseService

class LoginIntegration(QObject):
    """Integrates the login system with the main application"""
    
    login_successful = pyqtSignal(dict)
    login_failed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                              "configs", "auth_config.json")
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except Exception as e:
            print(f"Error loading auth config: {e}")
            config = {'supabase_url': 'https://demo.supabase.co', 'supabase_key': 'demo-anon-key'}
        
        self.supabase = SupabaseService(config)
        self.supabase.auth_state_changed.connect(self.on_authentication_changed)
        self.login_window = None

    def on_authentication_changed(self, auth_data):
        user = auth_data.get('user')
        if user:
            user_dict = {}
            if isinstance(user, dict):
                user_dict['id'] = user.get('id')
                user_dict['email'] = user.get('email')
                user_dict['user_metadata'] = user.get('user_metadata')
            else: # assume it's a User object
                user_dict['id'] = str(user.id) if hasattr(user, 'id') else None
                user_dict['email'] = user.email if hasattr(user, 'email') else None
                user_dict['user_metadata'] = user.user_metadata if hasattr(user, 'user_metadata') else None
            
            print("Authentication changed: User authenticated, emitting login_successful signal")
            self.login_successful.emit(user_dict)
            
            # Close the login window if it exists and is visible
            if self.login_window and hasattr(self.login_window, 'isVisible') and self.login_window.isVisible():
                print("Closing login window after authentication")
                self.login_window.close()
        else:
            self.login_failed.emit("Logged out")

    def check_authentication(self):
        return self.supabase.current_user is not None

    def login_with_provider(self, provider):
        """Initiates OAuth login with the specified provider."""
        try:
            self.supabase.sign_in_with_oauth(provider)
        except Exception as e:
            print(f"Error during {provider} login: {e}")
            self.login_failed.emit(str(e))

    def login_with_email(self, email, password):
        """Signs in a user with their email and password."""
        try:
            user = self.supabase.sign_in_with_email(email, password)
            if user:
                self.login_successful.emit(user)
            else:
                self.login_failed.emit("Invalid email or password.")
        except Exception as e:
            print(f"Error during email login: {e}")
            self.login_failed.emit(str(e))

    def sign_up_with_email(self, email, password):
        """Signs up a new user with email and password."""
        try:
            user = self.supabase.sign_up(email, password)
            if user:
                print("Sign up successful")
                return True
            return False
        except Exception as e:
            print(f"Error during sign up: {e}")
            return False

    def reset_password(self, email):
        """Sends a password reset email to the user."""
        try:
            self.supabase.reset_password_for_email(email)
            return True
        except Exception as e:
            print(f"Error sending password reset email: {e}")
            return False

    def check_authentication(self):
        return self.supabase.current_user is not None

    def show_login_window(self):
        from .login_ui import LoginWindow
        app = QApplication.instance()
        if not app:
            app = QApplication(sys.argv)
        
        self.login_window = LoginWindow(self)
        self.login_window.show()
        return app, self.login_window
    
    def logout(self):
        """Log out the current user
        
        Returns:
            bool: True if logout was successful, False otherwise
        """
        return self.supabase.sign_out()

    def get_current_user(self):
        return self.supabase.current_user


def initialize_login():
    """Initialize the login system
    
    Returns:
        LoginIntegration: The login integration instance
    """
    return LoginIntegration()


def require_authentication(callback):
    """Decorator to require authentication before executing a function
    
    Args:
        callback: The function to execute if authenticated
        
    Returns:
        function: Wrapped function that checks authentication
    """
    def wrapper(*args, **kwargs):
        login_integration = initialize_login()
        
        if login_integration.check_authentication():
            return callback(*args, **kwargs)
        else:
            app, login_window = login_integration.show_login_window()
            
            # Create a handler that will properly restart the application after login
            def on_login_success(user):
                print("Login successful, closing login window and starting main app")
                # Close the login window
                login_window.close()
                # Execute the callback function with the authenticated user
                return callback(*args, **kwargs)
            
            # Connect the signal to our handler
            login_integration.login_successful.connect(on_login_success)
            
            # Make sure the login window is shown
            login_window.show()
            
            return app.exec_()
    
    return wrapper