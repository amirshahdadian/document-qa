import os
import json
import base64
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, auth
from datetime import datetime
import logging
import requests
from pathlib import Path

logger = logging.getLogger(__name__)

class FirebaseAuth:
    def __init__(self):
        self.firebase_config = {
            "apiKey": os.getenv("FIREBASE_API_KEY"),
            "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
            "projectId": os.getenv("FIREBASE_PROJECT_ID"),
            "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
            "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
            "appId": os.getenv("FIREBASE_APP_ID")
        }
        
        # Initialize Firebase Admin SDK
        self._init_admin_sdk()
        
    def _init_admin_sdk(self):
        """Initialize Firebase Admin SDK for server-side operations"""
        if not firebase_admin._apps:
            try:
                # Try to use service account key from environment variable first
                service_account_key = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY")
                if service_account_key:
                    decoded_key = base64.b64decode(service_account_key)
                    service_account_info = json.loads(decoded_key)
                    cred = credentials.Certificate(service_account_info)
                    firebase_admin.initialize_app(cred)
                    logger.info("Firebase Admin SDK initialized successfully from environment variable")
                else:
                    # Fallback to service account file (for local development only)
                    service_account_path = "rag-pdf-demo-firebase-adminsdk-fbsvc-00f8eceba4.json"
                    if os.path.exists(service_account_path):
                        cred = credentials.Certificate(service_account_path)
                        firebase_admin.initialize_app(cred)
                        logger.info("Firebase Admin SDK initialized successfully from file")
                    else:
                        raise FileNotFoundError("No Firebase service account credentials found")
            except Exception as e:
                logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
                raise e
    
    def sign_in_with_email_and_password(self, email, password):
        """Sign in user with email and password using Firebase REST API"""
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
                logger.error(f"Login failed: {response.json()}")
                return None
        except Exception as e:
            logger.error(f"Login error: {e}")
            return None
    
    def create_user_with_email_and_password(self, email, password, display_name=None):
        """Create user with email and password using Firebase REST API"""
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
                
                # Update display name if provided
                if display_name:
                    self.update_profile(user_data['idToken'], display_name)
                
                return user_data
            else:
                logger.error(f"Registration failed: {response.json()}")
                return None
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return None
    
    def update_profile(self, id_token, display_name):
        """Update user profile"""
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
    
    def get_user_info(self, id_token):
        """Get user information"""
        try:
            url = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={self.firebase_config['apiKey']}"
            payload = {
                "idToken": id_token
            }
            response = requests.post(url, json=payload)
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except Exception as e:
            logger.error(f"Get user info error: {e}")
            return None
    
    def login(self, email, password):
        """Login user"""
        return self.sign_in_with_email_and_password(email, password)
    
    def register(self, email, password, display_name=None):
        """Register new user"""
        return self.create_user_with_email_and_password(email, password, display_name)
    
    def logout(self):
        """Logout user"""
        if 'user' in st.session_state:
            del st.session_state['user']
        if 'user_token' in st.session_state:
            del st.session_state['user_token']
    
    def save_chat_history(self, user_id, chat_history):
        """Save user's chat history to Firestore"""
        try:
            db = firestore.client()
            doc_ref = db.collection('users').document(user_id).collection('chat_sessions').document()
            
            # Convert chat history to a serializable format
            serializable_history = []
            for question, answer in chat_history:
                serializable_history.append({
                    'question': str(question),
                    'answer': str(answer),
                    'timestamp': datetime.now()
                })
            
            doc_ref.set({
                'chat_history': serializable_history,
                'session_timestamp': datetime.now(),
                'session_id': doc_ref.id,
                'message_count': len(serializable_history)
            })
            return doc_ref.id
        except Exception as e:
            logger.error(f"Failed to save chat history: {e}")
            return None
    
    def get_chat_history(self, user_id, limit=10):
        """Get user's chat history from Firestore"""
        try:
            db = firestore.client()
            docs = db.collection('users').document(user_id).collection('chat_sessions')\
                    .order_by('session_timestamp', direction=firestore.Query.DESCENDING)\
                    .limit(limit).stream()
            
            chat_sessions = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                # Convert back to tuple format for compatibility
                if 'chat_history' in data:
                    converted_history = [(msg['question'], msg['answer']) for msg in data['chat_history']]
                    data['chat_history'] = converted_history
                chat_sessions.append(data)
            
            return chat_sessions
        except Exception as e:
            logger.error(f"Failed to get chat history: {e}")
            return []
    
    def save_document_metadata(self, user_id, filename, file_size, chunks_count):
        """Save document metadata to Firestore"""
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
    
    def get_user_documents(self, user_id):
        """Get user's document history from Firestore"""
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

def main():
    # Initialize Firebase Auth
    firebase_auth = FirebaseAuth()
    
    # Authentication sidebar
    with st.sidebar:
        st.header("Authentication")
        
        if 'user' not in st.session_state:
            # Login/Register tabs
            tab1, tab2 = st.tabs(["Login", "Register"])
            
            with tab1:
                with st.form("login_form"):
                    email = st.text_input("Email")
                    password = st.text_input("Password", type="password")
                    if st.form_submit_button("Login"):
                        user_data = firebase_auth.login(email, password)
                        if user_data:
                            st.session_state.user = user_data
                            st.success("Logged in successfully!")
                            st.rerun()
            
            with tab2:
                with st.form("register_form"):
                    email = st.text_input("Email")
                    password = st.text_input("Password", type="password")
                    display_name = st.text_input("Display Name")
                    if st.form_submit_button("Register"):
                        user_data = firebase_auth.register(email, password, display_name)
                        if user_data:
                            st.session_state.user = user_data
                            st.success("Registered successfully!")
                            st.rerun()
        else:
            # User is logged in
            st.success(f"Welcome {st.session_state.user.get('email', 'User')}")
            if st.button("Logout"):
                firebase_auth.logout()
                st.rerun()
    
    # Only show main app if user is authenticated
    if 'user' in st.session_state:
        # ...existing main app code...
        pass
    else:
        st.warning("Please login to access the PDF Q&A system")

if __name__ == "__main__":
    main()