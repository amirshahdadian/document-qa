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
from app.config import FIREBASE_CONFIG, FIREBASE_SERVICE_ACCOUNT_KEY, GOOGLE_OAUTH_CLIENT_ID
import urllib.parse

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self):
        self.firebase_config = FIREBASE_CONFIG
        self._init_admin_sdk()
    
    def _get_redirect_uri(self) -> str:
        """Get the current redirect URI based on the environment."""
        try:
            # In production (Cloud Run), use the actual service URL
            if os.getenv("GOOGLE_CLOUD_PROJECT"):
                # Try to get the actual Cloud Run service URL
                service_url = os.getenv("CLOUD_RUN_SERVICE_URL")
                if service_url:
                    return service_url
                # Fallback to constructing URL from project info
                project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
                region = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
                service_name = os.getenv("K_SERVICE", "document-qa")
                return f"https://{service_name}-{hash(project_id) % 1000000}.{region}.run.app"
            else:
                # Development mode
                return "http://localhost:8501"
        except:
            return "http://localhost:8501"
        
    def _init_admin_sdk(self):
        """Initialize Firebase Admin SDK for server-side operations."""
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
                cred = credentials.Certificate(service_account_info)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized successfully")
            else:
                raise FileNotFoundError("No Firebase service account credentials found")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
            raise e
    
    def sign_in_with_email_and_password(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Sign in user with email and password using Firebase REST API."""
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
        """Create user with email and password using Firebase REST API."""
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
        """Sign in with Google OAuth token using Firebase REST API."""
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
        """Generate Google OAuth URL for authentication."""
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
            
            # Check if we've already processed this code
            if 'processed_auth_codes' not in st.session_state:
                st.session_state.processed_auth_codes = set()
            
            if code in st.session_state.processed_auth_codes:
                logger.warning(f"Authorization code already processed: {code[:10]}...")
                return None
            
            redirect_uri = self._get_redirect_uri()
            url = "https://oauth2.googleapis.com/token"
            payload = {
                "client_id": GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri
            }
            
            logger.debug(f"Token exchange payload: {payload}")
            logger.debug(f"Redirect URI during token exchange: {redirect_uri}")
            
            response = requests.post(url, data=payload)
            logger.debug(f"Token exchange response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                token_data = response.json()
                # Mark this code as processed
                st.session_state.processed_auth_codes.add(code)
                return token_data.get("access_token")
            else:
                logger.error(f"Token exchange failed: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Token exchange error: {e}")
            return None
    
    def update_profile(self, id_token: str, display_name: str) -> bool:
        """Update user profile."""
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
    
    def login(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Login user."""
        return self.sign_in_with_email_and_password(email, password)
    
    def register(self, email: str, password: str, display_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Register new user."""
        return self.create_user_with_email_and_password(email, password, display_name)
    
    def login_with_google(self, google_access_token: str) -> Optional[Dict[str, Any]]:
        """Login with Google OAuth token."""
        return self.sign_in_with_google_oauth(google_access_token)
    
    def logout(self) -> None:
        """Logout user."""
        keys_to_remove = ['user', 'user_token', 'chat_history', 'current_session_id', 'google_auth_code']
        for key in keys_to_remove:
            if key in st.session_state:
                del st.session_state[key]
    
    def save_chat_history(self, user_id: str, chat_history: List[tuple]) -> Optional[str]:
        """Save user's chat history to Firestore."""
        try:
            db = firestore.client()
            doc_ref = db.collection('users').document(user_id).collection('chat_sessions').document()
            
            serializable_history = []
            for question, answer in chat_history:
                serializable_history.append({
                    'question': str(question),
                    'answer': str(answer),
                    'timestamp': datetime.now()
                })
            
            session_title = "New Session"
            if serializable_history:
                first_question = serializable_history[0]['question']
                session_title = first_question[:50] + "..." if len(first_question) > 50 else first_question
            
            doc_ref.set({
                'chat_history': serializable_history,
                'session_timestamp': datetime.now(),
                'session_id': doc_ref.id,
                'message_count': len(serializable_history),
                'session_title': session_title
            })
            logger.debug(f"Chat history saved for user {user_id}: {serializable_history}")
            return doc_ref.id
        except Exception as e:
            logger.error(f"Failed to save chat history: {e}")
            return None
    
    def get_chat_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's chat history from Firestore."""
        try:
            db = firestore.client()
            docs = db.collection('users').document(user_id).collection('chat_sessions')\
                    .order_by('session_timestamp', direction=firestore.Query.DESCENDING)\
                    .limit(limit)\
                    .stream()
            
            chat_sessions = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                chat_sessions.append(data)
            
            return chat_sessions
        except Exception as e:
            logger.error(f"Failed to get chat history: {e}")
            return []
    
    def save_document_metadata(self, user_id: str, filename: str, file_size: int, chunks_count: int) -> Optional[str]:
        """Save document metadata to Firestore."""
        try:
            db = firestore.client()
            doc_ref = db.collection('users').document(user_id).collection('documents').document()
            doc_ref.set({
                'filename': filename,
                'file_size': file_size,
                'chunks_count': chunks_count,
                'upload_timestamp': datetime.now(),
                'document_id': doc_ref.id
            })
            return doc_ref.id
        except Exception as e:
            logger.error(f"Failed to save document metadata: {e}")
            return None
    
    def get_user_documents(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's document history from Firestore."""
        try:
            db = firestore.client()
            docs = db.collection('users').document(user_id).collection('documents')\
                    .order_by('upload_timestamp', direction=firestore.Query.DESCENDING)\
                    .stream()
            
            documents = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                documents.append(data)
            
            return documents
        except Exception as e:
            logger.error(f"Failed to get user documents: {e}")
            return []
    
    def delete_chat_session(self, user_id: str, session_id: str) -> bool:
        """Delete a specific chat session."""
        try:
            db = firestore.client()
            doc_ref = db.collection('users').document(user_id).collection('chat_sessions').document(session_id)
            doc_ref.delete()
            return True
        except Exception as e:
            logger.error(f"Failed to delete chat session: {e}")
            return False