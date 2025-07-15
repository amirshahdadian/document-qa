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
from app.config import FIREBASE_CONFIG, FIREBASE_SERVICE_ACCOUNT_KEY

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self):
        self.firebase_config = FIREBASE_CONFIG
        self._init_admin_sdk()
        
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
    
    def logout(self) -> None:
        """Logout user."""
        keys_to_remove = ['user', 'user_token', 'chat_history', 'current_session_id']
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