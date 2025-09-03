import os
import json
import base64
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, auth
from datetime import datetime
import logging
import requests
from typing import Optional, Dict, Any, List
from app.config import FIREBASE_CONFIG, FIREBASE_SERVICE_ACCOUNT_KEY, GOOGLE_OAUTH_CLIENT_ID, IS_PRODUCTION
import urllib.parse

logger = logging.getLogger(__name__)
if IS_PRODUCTION:
    logger.setLevel(logging.ERROR)

class AuthService:
    """
    Firebase authentication and data management service.
    Handles user authentication, chat history, and document metadata storage.
    """
    
    def __init__(self):
        self.firebase_config = FIREBASE_CONFIG
        self._init_admin_sdk()
    
    def _get_redirect_uri(self) -> str:
        """Determine the appropriate OAuth redirect URI based on environment."""
        if IS_PRODUCTION:
            service_url = os.getenv("CLOUD_RUN_SERVICE_URL")
            if service_url:
                logger.info(f"Using Cloud Run service URL: {service_url}")
                return service_url
            else:
                fallback_url = "https://document-qa-876776881787.europe-west1.run.app"
                logger.info(f"Using hardcoded production URL: {fallback_url}")
                return fallback_url
        else:
            dev_uri = "http://localhost:8501"
            logger.debug(f"Using local redirect URI: {dev_uri}")
            return dev_uri
        
    def _init_admin_sdk(self):
        """Initialize Firebase Admin SDK with service account credentials."""
        try: 
            firebase_admin.get_app()
            logger.info("Firebase Admin SDK already initialized")
            return
        except ValueError:
            pass

        try:
            if FIREBASE_SERVICE_ACCOUNT_KEY:
                decoded_key = base64.b64decode(FIREBASE_SERVICE_ACCOUNT_KEY)
                service_account_info = json.loads(decoded_key)
                
                if 'private_key' in service_account_info:
                    private_key = service_account_info['private_key']
                    
                    # Normalize private key format
                    if '\\n' in private_key:
                        private_key = private_key.replace('\\n', '\n')
                    
                    private_key = private_key.strip()
                    
                    # Reconstruct malformed keys
                    if not private_key.startswith('-----BEGIN PRIVATE KEY-----'):
                        key_content = private_key.replace('-----BEGIN PRIVATE KEY-----', '').replace('-----END PRIVATE KEY-----', '').strip()
                        private_key = f"-----BEGIN PRIVATE KEY-----\n{key_content}\n-----END PRIVATE KEY-----"
                    
                    # Format single-line keys with proper line breaks
                    lines = private_key.split('\n')
                    if len(lines) == 1:
                        key_start = '-----BEGIN PRIVATE KEY-----'
                        key_end = '-----END PRIVATE KEY-----'
                        
                        if key_start in private_key and key_end in private_key:
                            start_idx = private_key.find(key_start) + len(key_start)
                            end_idx = private_key.find(key_end)
                            key_content = private_key[start_idx:end_idx].strip()
                            
                            formatted_lines = [key_start]
                            for i in range(0, len(key_content), 64):
                                formatted_lines.append(key_content[i:i+64])
                            formatted_lines.append(key_end)
                            
                            private_key = '\n'.join(formatted_lines)
                    
                    service_account_info['private_key'] = private_key
                    
                    # Validate key format
                    if not private_key.startswith('-----BEGIN PRIVATE KEY-----'):
                        logger.error("Private key does not start with correct header")
                        raise ValueError("Invalid private key format - missing header")
                    if not private_key.rstrip().endswith('-----END PRIVATE KEY-----'):
                        logger.error("Private key does not end with correct footer")
                        raise ValueError("Invalid private key format - missing footer")
                
                cred = credentials.Certificate(service_account_info)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized successfully")
            else:
                raise FileNotFoundError("No Firebase service account credentials found")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
            raise e
    
    def sign_in_with_email_and_password(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with email and password via Firebase REST API."""
        try:
            url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={self.firebase_config['apiKey']}"
            payload = {
                "email": email,
                "password": password,
                "returnSecureToken": True
            }
            response = requests.post(url, json=payload)
            
            if response.status_code == 200:
                return response.json()
            else:
                error_data = response.json()
                error_message = error_data.get('error', {}).get('message', 'Unknown error')
                logger.error(f"Login failed: {error_message}")
                return None
        except Exception as e:
            logger.error(f"Login error: {e}")
            return None
    
    def create_user_with_email_and_password(self, email: str, password: str, display_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Create new user account via Firebase REST API."""
        try:
            url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={self.firebase_config['apiKey']}"
            payload = {
                "email": email,
                "password": password,
                "returnSecureToken": True
            }
            response = requests.post(url, json=payload)
            
            if response.status_code == 200:
                user_data = response.json()
                
                if display_name:
                    self.update_profile(user_data['idToken'], display_name)
                
                return user_data
            else:
                error_data = response.json()
                error_message = error_data.get('error', {}).get('message', 'Unknown error')
                logger.error(f"Registration failed: {error_message}")
                return None
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return None
    
    def sign_in_with_google_oauth(self, google_access_token: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with Google OAuth token via Firebase REST API."""
        try:
            url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithIdp?key={self.firebase_config['apiKey']}"
            payload = {
                "requestUri": "http://localhost",
                "postBody": f"access_token={google_access_token}&providerId=google.com",
                "returnSecureToken": True,
                "returnIdpCredential": True
            }
            response = requests.post(url, json=payload)
            
            if response.status_code == 200:
                return response.json()
            else:
                error_data = response.json()
                error_message = error_data.get('error', {}).get('message', 'Unknown error')
                logger.error(f"Google login failed: {error_message}")
                return None
        except Exception as e:
            logger.error(f"Google login error: {e}")
            return None
    
    def get_google_oauth_url(self) -> str:
        """Generate Google OAuth authorization URL."""
        if not GOOGLE_OAUTH_CLIENT_ID:
            return ""
        
        redirect_uri = self._get_redirect_uri()
        base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        params = {
            "client_id": GOOGLE_OAUTH_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "state": "google_auth"
        }
        
        param_string = urllib.parse.urlencode(params)
        return f"{base_url}?{param_string}"
    
    def exchange_google_code_for_token(self, code: str) -> Optional[str]:
        """Exchange Google authorization code for access token."""
        try:
            from app.config import GOOGLE_OAUTH_CLIENT_SECRET
            
            redirect_uri = self._get_redirect_uri()
            url = "https://oauth2.googleapis.com/token"
            payload = {
                "client_id": GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri
            }
            
            logger.debug(f"TOKEN_EXCHANGE: Sending POST to {url} with payload: {payload}")
            
            response = requests.post(url, data=payload)
            
            logger.debug(f"TOKEN_EXCHANGE: Received response. Status: {response.status_code}, Body: {response.text}")
            
            if response.status_code == 200:
                token_data = response.json()
                return token_data.get("access_token")
            else:
                logger.error(f"TOKEN_EXCHANGE: Failed. Status: {response.status_code}, Response: {response.text}")
                return None
        except Exception as e:
            logger.critical(f"TOKEN_EXCHANGE: Unhandled exception: {e}", exc_info=True)
            return None
    
    def update_profile(self, id_token: str, display_name: str) -> bool:
        """Update user profile information."""
        try:
            url = f"https://identitytoolkit.googleapis.com/v1/accounts:update?key={self.firebase_config['apiKey']}"
            payload = {
                "idToken": id_token,
                "displayName": display_name,
                "returnSecureToken": True
            }
            response = requests.post(url, json=payload)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Profile update error: {e}")
            return False
    
    # Public API methods
    def login(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Public method for user login."""
        return self.sign_in_with_email_and_password(email, password)
    
    def register(self, email: str, password: str, display_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Public method for user registration."""
        return self.create_user_with_email_and_password(email, password, display_name)
    
    def login_with_google(self, google_access_token: str) -> Optional[Dict[str, Any]]:
        """Public method for Google OAuth login."""
        return self.sign_in_with_google_oauth(google_access_token)
    
    def logout(self) -> None:
        """Clear user session data."""
        keys_to_remove = ['user', 'user_token', 'chat_history', 'current_session_id', 'google_auth_code']
        for key in keys_to_remove:
            if key in st.session_state:
                del st.session_state[key]
    
    def delete_chat_session(self, user_id: str, session_id: str) -> bool:
        """Remove a specific chat session from Firestore."""
        try:
            db = firestore.client()
            doc_ref = db.collection('users').document(user_id).collection('chat_sessions').document(session_id)
            doc_ref.delete()
            return True
        except Exception as e:
            logger.error(f"Failed to delete chat session: {e}")
            return False
    
    def save_document_session(self, user_id: str, session_id: str, filename: str, file_size: int, chunks_count: int, file_hash: str) -> bool:
        """Associate document metadata with a chat session."""
        try:
            db = firestore.client()
            session_ref = db.collection('users').document(user_id).collection('chat_sessions').document(session_id)
            
            session_ref.update({
                'document_metadata': {
                    'filename': filename,
                    'file_size': file_size,
                    'chunks_count': chunks_count,
                    'file_hash': file_hash,
                    'has_embeddings': True,
                    'upload_timestamp': datetime.now()
                },
                'updated_at': datetime.now()
            })
            
            logger.info(f"Saved document session for user {user_id}, session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save document session: {e}")
            return False

    def get_session_document_info(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve document metadata for a specific session."""
        try:
            db = firestore.client()
            session_ref = db.collection('users').document(user_id).collection('chat_sessions').document(session_id)
            session_doc = session_ref.get()
            
            if session_doc.exists:
                session_data = session_doc.to_dict()
                return session_data.get('document_metadata')
            return None
        except Exception as e:
            logger.error(f"Failed to get session document info: {e}")
            return None

    def get_chat_history(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve chat history for a user from Firestore."""
        try:
            db = firestore.client()
            sessions_ref = db.collection('users').document(user_id).collection('chat_sessions')
            
            # Order by updated_at descending to get most recent first
            query = sessions_ref.order_by('updated_at', direction=firestore.Query.DESCENDING).limit(limit)
            docs = query.stream()
            
            chat_sessions = []
            for doc in docs:
                session_data = doc.to_dict()
                session_data['id'] = doc.id  # Add document ID
                chat_sessions.append(session_data)
            
            logger.info(f"Retrieved {len(chat_sessions)} chat sessions for user {user_id}")
            return chat_sessions
            
        except Exception as e:
            logger.error(f"Failed to get chat history for user {user_id}: {e}")
            return []