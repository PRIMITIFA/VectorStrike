import os
import json
import keyring
import webbrowser
import uuid
import time
from supabase import create_client, Client
from cryptography.fernet import Fernet
from PyQt6.QtCore import QObject, pyqtSignal
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

import logging

logger = logging.getLogger(__name__)

class SupabaseService(QObject):
    # Signals
    auth_state_changed = pyqtSignal(dict)
    auth_error = pyqtSignal(str)
    
    def __init__(self, config):
        super().__init__()
        self.supabase_url = config['supabase_url']
        self.supabase_key = config['supabase_key']
        
        # Check if we're in demo mode
        self.demo_mode = (self.supabase_url == "https://demo.supabase.co" and 
                         self.supabase_key == "demo-anon-key")
        
        if self.demo_mode:
            logger.info("Running in DEMO MODE with mock authentication")
            self.client = None  # No actual Supabase client in demo mode
        else:
            try:
                self.client = create_client(self.supabase_url, self.supabase_key)
                logger.info("Successfully connected to Supabase")
            except Exception as e:
                logger.error(f"Error connecting to Supabase: {e}")
                logger.warning("Falling back to DEMO MODE with mock authentication")
                self.demo_mode = True
                self.client = None
            
        self.current_user = None
        self.current_session = None
        self.encryption_key = self._get_or_create_encryption_key()
        
        # Demo mode users (for testing)
        self.demo_users = {
            "demo@example.com": {
                "password": "password123",
                "user_id": str(uuid.uuid4()),
                "username": "demo_user",
                "role": "FREE"
            },
            "pro@example.com": {
                "password": "password123",
                "user_id": str(uuid.uuid4()),
                "username": "pro_user",
                "role": "PRO"
            }
        }
        
        # Try to restore session
        self._restore_session()
    
    def _get_or_create_encryption_key(self):
        """
        Get or create encryption key for secure storage
        """
        key = keyring.get_password("cs2_login_app", "encryption_key")
        if not key:
            key = Fernet.generate_key().decode()
            keyring.set_password("cs2_login_app", "encryption_key", key)
            logger.info("Created and saved new encryption key.")
        return key
    
    def _get_fernet(self):
        """
        Get Fernet encryption instance
        """
        return Fernet(self.encryption_key.encode())
    
    def _save_session(self, session, remember=False):
        """
        Save session data securely
        """
        if remember:
            # Encrypt session data
            fernet = self._get_fernet()
            session_data = json.dumps(session)
            encrypted_data = fernet.encrypt(session_data.encode()).decode()
            
            # Save to keyring
            keyring.set_password("cs2_login_app", "session", encrypted_data)
            logger.info("Saved session to keyring.")
    
    def _restore_session(self):
        """
        Restore previous session if available
        """
        try:
            # Get encrypted session from keyring
            encrypted_data = keyring.get_password("cs2_login_app", "session")
            if encrypted_data:
                # Decrypt session data
                fernet = self._get_fernet()
                session_data = fernet.decrypt(encrypted_data.encode()).decode()
                session = json.loads(session_data)
                logger.info("Restored session from keyring.")
                
                if self.demo_mode:
                    # For demo mode, extract user email from session token
                    # Demo tokens are in format "demo-token-{user_id}"
                    token = session.get("access_token", "")
                    
                    # Find the user with this token
                    user_email = None
                    for email, user_data in self.demo_users.items():
                        if f"demo-token-{user_data['user_id']}" == token:
                            user_email = email
                            break
                    
                    if user_email:
                        # Get demo user data
                        user_data = self.demo_users[user_email]
                        user_id = user_data["user_id"]
                        
                        # Create mock user
                        user = {
                            "id": user_id,
                            "email": user_email,
                            "user_metadata": {"username": user_data["username"]}
                        }
                        
                        self.current_user = user
                        self.current_session = session
                        
                        # Emit auth state changed signal
                        self.auth_state_changed.emit({
                            'user': self.current_user,
                            'session': self.current_session,
                            'role': user_data["role"]
                        })
                        logger.info(f"Demo user {user_email} session restored.")
                        
                        return True
                else:
                    # Set session in client
                    self.client.auth.set_session(session)
                    self.current_session = session
                    
                    # Get user from session
                    user_response = self.client.auth.get_user()
                    self.current_user = user_response.user
                    
                    # Emit auth state changed signal
                    self.auth_state_changed.emit({
                        'user': self.current_user,
                        'session': self.current_session
                    })
                    logger.info(f"User {self.current_user.email} session restored.")
                    
                    return True
        except Exception as e:
            logger.error(f"Error restoring session: {e}")
            self.clear_session()
        
        return False
    
    def clear_session(self):
        """
        Clear saved session
        """
        try:
            keyring.delete_password("cs2_login_app", "session")
            logger.info("Cleared session from keyring.")
        except:
            pass
        
        self.current_user = None
        self.current_session = None
    
    def _start_oauth_callback_server(self):
        if hasattr(self, 'callback_server_thread') and self.callback_server_thread.is_alive():
            logger.info("Callback server is already running.")
            return

        try:
            self.httpd = OAuthCallbackServer(("", 3000), self)
            self.callback_server_thread = threading.Thread(target=self.httpd.serve_forever)
            self.callback_server_thread.daemon = True
            self.callback_server_thread.start()
            logger.info("OAuth callback server started on port 3000.")
        except Exception as e:
            logger.error(f"Failed to start OAuth callback server: {e}")

    def _stop_oauth_callback_server(self):
        if hasattr(self, 'httpd'):
            logger.info("Shutting down OAuth callback server.")
            self.httpd.shutdown()
            self.httpd.server_close()

    def sign_up(self, email, password, username):
        """
        Register a new user
        """
        try:
            # Handle demo mode
            if self.demo_mode:
                # Check if email already exists
                if email in self.demo_users:
                    self.auth_error.emit("Email already registered")
                    logger.warning(f"Attempted to register existing demo email: {email}")
                    return
                
                # Create new demo user
                user_id = str(uuid.uuid4())
                self.demo_users[email] = {
                    "password": password,
                    "user_id": user_id,
                    "username": username,
                    "role": "FREE"
                }
                
                # Create mock user and session
                user = {
                    "id": user_id,
                    "email": email,
                    "user_metadata": {"username": username}
                }
                
                session = {
                    "access_token": f"demo-token-{user_id}",
                    "refresh_token": f"demo-refresh-{user_id}",
                    "expires_at": int(time.time()) + 3600
                }
                
                # Set current user and session
                self.current_user = user
                self.current_session = session
                
                # Emit auth state changed signal
                self.auth_state_changed.emit({
                    'user': self.current_user,
                    'session': self.current_session
                })
                logger.info(f"Successfully signed up demo user: {email}")
                
                return
            
            # Real Supabase implementation
            response = self.client.auth.sign_up({
                "email": email,
                "password": password
            })
            
            # Get user data
            user = response.user
            session = response.session
            
            if user and user.id:
                # Create profile in profiles table
                self.client.table('profiles').insert({
                    'id': user.id,
                    'username': username,
                    'role': 'FREE',
                    'created_at': 'now()'
                }).execute()
                
                # Set current user and session
                self.current_user = user
                self.current_session = session
                
                # Emit auth state changed signal
                self.auth_state_changed.emit({
                    'user': user,
                    'session': session
                })
                logger.info(f"Successfully signed up user: {email}")
                
                return True
            
            return False
        except Exception as e:
            error_msg = str(e)
            self.auth_error.emit(error_msg)
            logger.error(f"Error during sign up for {email}: {error_msg}")
            return False
    
    def sign_in_with_email(self, email, password, remember=False):
        """
        Sign in with email and password
        """
        try:
            # Handle demo mode
            if self.demo_mode:
                # Check if email exists and password matches
                if email not in self.demo_users:
                    self.auth_error.emit("Invalid email or password")
                    logger.warning(f"Failed sign in for non-existent demo user: {email}")
                    return False
                
                if self.demo_users[email]["password"] != password:
                    self.auth_error.emit("Invalid email or password")
                    logger.warning(f"Failed sign in with wrong password for demo user: {email}")
                    return False
                
                # Get demo user data
                user_data = self.demo_users[email]
                user_id = user_data["user_id"]
                
                # Create mock user and session
                user = {
                    "id": user_id,
                    "email": email,
                    "user_metadata": {"username": user_data["username"]}
                }
                
                session = {
                    "access_token": f"demo-token-{user_id}",
                    "refresh_token": f"demo-refresh-{user_id}",
                    "expires_at": int(time.time()) + 3600
                }
                
                # Set current user and session
                self.current_user = user
                self.current_session = session
                
                # Save session if remember is checked
                if remember:
                    self._save_session(session, remember)
                
                # Emit auth state changed signal
                self.auth_state_changed.emit({
                    'user': user,
                    'session': session,
                    'role': user_data["role"]
                })
                logger.info(f"Successfully signed in demo user: {email}")
                
                return True
            
            # Real Supabase implementation
            response = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            user = response.user
            session = response.session

            if user and session:
                self.current_user = user
                self.current_session = session
                if remember:
                    self._save_session(session, remember)
                
                self.auth_state_changed.emit({
                    'user': user,
                    'session': session
                })
                logger.info(f"Successfully signed in user: {email}")
                return True
            return False

        except Exception as e:
            error_msg = str(e)
            self.auth_error.emit(error_msg)
            logger.error(f"Error during sign in for {email}: {error_msg}")
            return False

    def sign_in_with_oauth(self, provider, use_browser=True):
        """
        Sign in with an OAuth provider
        """
        try:
            if self.demo_mode:
                # In demo mode, we can simulate a successful OAuth login
                # For simplicity, let's use the pro user for google
                if provider.lower() == 'google':
                    email = "pro@example.com"
                    user_data = self.demo_users[email]
                    user_id = user_data["user_id"]
                    
                    user = {
                        "id": user_id,
                        "email": email,
                        "user_metadata": {"username": user_data["username"]}
                    }
                    
                    session = {
                        "access_token": f"demo-token-{user_id}",
                        "refresh_token": f"demo-refresh-{user_id}",
                        "expires_at": int(time.time()) + 3600
                    }
                    
                    self.current_user = user
                    self.current_session = session
                    
                    self.auth_state_changed.emit({
                        'user': user,
                        'session': session,
                        'role': user_data["role"]
                    })
                    logger.info(f"Successfully simulated OAuth sign in for demo user: {email}")
                    return True
                else:
                    self.auth_error.emit(f"OAuth provider {provider} not supported in demo mode.")
                    return False

            # Real Supabase implementation
            self._start_oauth_callback_server()
            response = self.client.auth.sign_in_with_oauth({
                "provider": provider,
                "options": {
                    "redirect_to": "http://localhost:3000/callback"
                }
            })
            
            if use_browser and response.url:
                webbrowser.open(response.url)
                
            return True
        except Exception as e:
            error_msg = str(e)
            self.auth_error.emit(error_msg)
            logger.error(f"Error during OAuth sign in with {provider}: {error_msg}")
            self._stop_oauth_callback_server()
            return False

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Check if this is a direct callback with code in the URL
        if self.path.startswith('/callback') and 'code=' in self.path:
            # Extract the code from the URL
            query_params = self.path.split('?', 1)[1] if '?' in self.path else ''
            params = {k: v for k, v in [p.split('=') for p in query_params.split('&') if '=' in p]}
            code = params.get('code')
            
            if code:
                try:
                    # Exchange the authorization code for a session
                    auth_response = self.server.supabase_service.client.auth.exchange_code_for_session({
                        'auth_code': code
                    })
                    
                    if auth_response and auth_response.session:
                        self.server.supabase_service.current_user = auth_response.user
                        self.server.supabase_service.current_session = auth_response.session
                        
                        self.server.supabase_service.auth_state_changed.emit({
                            'user': self.server.supabase_service.current_user,
                            'session': self.server.supabase_service.current_session
                        })
                        
                        # Send a success response with a proper HTML page that shows authentication success
                        self.send_response(200)
                        self.send_header('Content-type', 'text/html')
                        self.end_headers()
                        success_html = b"""
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <title>VectorStrike Authentication</title>
                            <style>
                                body {
                                    font-family: Arial, sans-serif;
                                    background-color: #121212;
                                    color: #FFFFFF;
                                    text-align: center;
                                    padding-top: 100px;
                                }
                                h1 {
                                    color: #BB86FC;
                                }
                                .success-message {
                                    margin: 20px;
                                    padding: 20px;
                                    background-color: #1E1E1E;
                                    border-radius: 10px;
                                    display: inline-block;
                                }
                            </style>
                        </head>
                        <body>
                            <div class="success-message">
                                <h1>Authentication Successful!</h1>
                                <p>You have been successfully authenticated. You can close this window.</p>
                            </div>
                            <script>
                                // Close the window automatically after 3 seconds
                                setTimeout(() => window.close(), 3000);
                            </script>
                        </body>
                        </html>
                        """
                        self.wfile.write(success_html)
                        
                        # Schedule server shutdown after response is sent
                        threading.Timer(0.5, self.server.supabase_service._stop_oauth_callback_server).start()
                        return
                except Exception as e:
                    print(f"Error exchanging code for session: {str(e)}")
                    self.send_response(500)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(f"<h1>Authentication Error</h1><p>{str(e)}</p>".encode())
                    return
        
        # If not a direct callback or if there was an issue, serve the HTML page
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        html_content = b"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>VectorStrike Authentication</title>
            <script>
                function handleAuth() {
                    // Check for tokens in URL fragment (hash)
                    if (window.location.hash) {
                        const params = new URLSearchParams(window.location.hash.substring(1));
                        const accessToken = params.get('access_token');
                        const refreshToken = params.get('refresh_token');

                        if (accessToken && refreshToken) {
                            fetch('/token', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ access_token: accessToken, refresh_token: refreshToken })
                            }).then(response => {
                                if (response.ok) {
                                    document.body.innerHTML = "<h1>Authentication successful! You can close this window.</h1>";
                                    setTimeout(() => window.close(), 1000);
                                } else {
                                    document.body.innerHTML = "<h1>Authentication failed. Could not process tokens.</h1>";
                                }
                            });
                            return;
                        }
                    }
                    
                    // Check for authorization code in URL query parameters
                    const urlParams = new URLSearchParams(window.location.search);
                    const code = urlParams.get('code');
                    const error = urlParams.get('error');
                    const errorDescription = urlParams.get('error_description');

                    if (code) {
                        // Send the authorization code to the server
                        // Use relative URL to ensure it goes to the same server that served this page
                        fetch('/code', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ code: code })
                        }).then(response => {
                            if (response.ok) {
                                document.body.innerHTML = "<h1 style='color: #BB86FC;'>Authentication successful! You can close this window.</h1>";
                                setTimeout(() => window.close(), 3000);
                            } else {
                                document.body.innerHTML = "<h1>Authentication failed. Could not process authorization code.</h1>";
                            }
                        }).catch(error => {
                            console.error('Error:', error);
                            document.body.innerHTML = "<h1>Authentication failed. Error connecting to server.</h1><p>" + error + "</p>";
                        });
                        return;
                    }

                    if (error) {
                        document.body.innerHTML = `<h1>Authentication Error: ${error}</h1><p>${errorDescription}</p>`;
                        return;
                    }

                    document.body.innerHTML = "<h1>Authentication failed. No token or authorization code found.</h1>";
                }
            </script>
        </head>
        <body onload="handleAuth()">
            <h1>Processing authentication...</h1>
        </body>
        </html>
        """
        self.wfile.write(html_content)

    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)

            if self.path == '/token':
                access_token = data.get('access_token')
                refresh_token = data.get('refresh_token')

                if access_token and refresh_token:
                    self.server.supabase_service.client.auth.set_session(access_token, refresh_token)
                    
                    user_response = self.server.supabase_service.client.auth.get_user()
                    session = self.server.supabase_service.client.auth.get_session()

                    self.server.supabase_service.current_user = user_response.user
                    self.server.supabase_service.current_session = session
                    
                    self.server.supabase_service.auth_state_changed.emit({
                        'user': self.server.supabase_service.current_user,
                        'session': self.server.supabase_service.current_session
                    })
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'status': 'success'}).encode())
                    
                    # Schedule server shutdown after response is sent
                    threading.Timer(0.5, self.server.supabase_service._stop_oauth_callback_server).start()
                    return
            elif self.path == '/code':
                code = data.get('code')
                if code:
                    try:
                        # Exchange the authorization code for a session
                        auth_response = self.server.supabase_service.client.auth.exchange_code_for_session({
                            'auth_code': code
                        })
                        
                        if auth_response and auth_response.session:
                            self.server.supabase_service.current_user = auth_response.user
                            self.server.supabase_service.current_session = auth_response.session
                            
                            self.server.supabase_service.auth_state_changed.emit({
                                'user': self.server.supabase_service.current_user,
                                'session': self.server.supabase_service.current_session
                            })
                            
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.end_headers()
                            self.wfile.write(json.dumps({'status': 'success'}).encode())
                            
                            # Schedule server shutdown after response is sent
                            threading.Timer(0.5, self.server.supabase_service._stop_oauth_callback_server).start()
                            return
                    except Exception as e:
                        print(f"Error exchanging code for session: {str(e)}")
                        self.send_response(500)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({'status': 'error', 'message': str(e)}).encode())
                        return
            
            # If we get here, something went wrong
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'error', 'message': 'Invalid request'}).encode())
        except Exception as e:
            print(f"Error in POST handler: {str(e)}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'error', 'message': str(e)}).encode())

    def log_message(self, format, *args):
        return

class OAuthCallbackServer(HTTPServer):
    def __init__(self, server_address, supabase_service):
        self.supabase_service = supabase_service
        super().__init__(server_address, OAuthCallbackHandler)