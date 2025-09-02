import os
import json
import tempfile
import shutil
import logging
from typing import Optional, List
from google.cloud import storage
from google.auth import default
from app.config import GCS_BUCKET_NAME, GCS_CHROMA_PREFIX, IS_PRODUCTION

logger = logging.getLogger(__name__)
if IS_PRODUCTION:
    logger.setLevel(logging.ERROR)

class GCSStorage:
    def __init__(self):
        try:
            # Initialize Google Cloud Storage client
            credentials, project = default()
            self.client = storage.Client(credentials=credentials, project=project)
            self.bucket = self.client.bucket(GCS_BUCKET_NAME)
            
            if not IS_PRODUCTION:
                logger.info(f"GCS Storage initialized for bucket: {GCS_BUCKET_NAME}")
        except Exception as e:
            logger.error(f"Failed to initialize GCS Storage: {e}")
            raise e
    
    def upload_chroma_collection(self, local_path: str, user_id: str, session_id: str) -> bool:
        """Upload ChromaDB collection to GCS."""
        try:
            collection_prefix = f"{GCS_CHROMA_PREFIX}{user_id}/{session_id}/"
            
            # Upload all files in the ChromaDB collection directory
            if os.path.exists(local_path):
                for root, dirs, files in os.walk(local_path):
                    for file in files:
                        local_file_path = os.path.join(root, file)
                        relative_path = os.path.relpath(local_file_path, local_path)
                        gcs_path = collection_prefix + relative_path
                        
                        blob = self.bucket.blob(gcs_path)
                        blob.upload_from_filename(local_file_path)
                        
                        if not IS_PRODUCTION:
                            logger.debug(f"Uploaded {local_file_path} to {gcs_path}")
                
                logger.info(f"ChromaDB collection uploaded for user {user_id}, session {session_id}")
                return True
            else:
                logger.warning(f"Local ChromaDB path not found: {local_path}")
                return False
                
        except Exception as e:
            logger.error(f"Error uploading ChromaDB collection: {e}")
            return False
    
    def download_chroma_collection(self, local_path: str, user_id: str, session_id: str) -> bool:
        """Download ChromaDB collection from GCS."""
        try:
            collection_prefix = f"{GCS_CHROMA_PREFIX}{user_id}/{session_id}/"
            
            # Create local directory
            os.makedirs(local_path, exist_ok=True)
            
            # List and download all blobs with the collection prefix
            blobs = self.bucket.list_blobs(prefix=collection_prefix)
            downloaded_files = 0
            
            for blob in blobs:
                if blob.name == collection_prefix:  # Skip directory marker
                    continue
                    
                # Get relative path within collection
                relative_path = blob.name[len(collection_prefix):]
                local_file_path = os.path.join(local_path, relative_path)
                
                # Create local directory structure
                local_dir = os.path.dirname(local_file_path)
                if local_dir:
                    os.makedirs(local_dir, exist_ok=True)
                
                # Download file
                blob.download_to_filename(local_file_path)
                downloaded_files += 1
                
                if not IS_PRODUCTION:
                    logger.debug(f"Downloaded {blob.name} to {local_file_path}")
            
            if downloaded_files > 0:
                logger.info(f"Downloaded {downloaded_files} files for user {user_id}, session {session_id}")
                return True
            else:
                logger.info(f"No ChromaDB files found for user {user_id}, session {session_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error downloading ChromaDB collection: {e}")
            return False
    
    def delete_chroma_collection(self, user_id: str, session_id: str) -> bool:
        """Delete ChromaDB collection from GCS."""
        try:
            collection_prefix = f"{GCS_CHROMA_PREFIX}{user_id}/{session_id}/"
            
            # List and delete all blobs with the collection prefix
            blobs = self.bucket.list_blobs(prefix=collection_prefix)
            deleted_files = 0
            
            for blob in blobs:
                blob.delete()
                deleted_files += 1
                
                if not IS_PRODUCTION:
                    logger.debug(f"Deleted {blob.name}")
            
            if deleted_files > 0:
                logger.info(f"Deleted {deleted_files} files for user {user_id}, session {session_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting ChromaDB collection: {e}")
            return False
    
    def collection_exists(self, user_id: str, session_id: str) -> bool:
        """Check if ChromaDB collection exists in GCS."""
        try:
            collection_prefix = f"{GCS_CHROMA_PREFIX}{user_id}/{session_id}/"
            blobs = list(self.bucket.list_blobs(prefix=collection_prefix, max_results=1))
            return len(blobs) > 0
        except Exception as e:
            logger.error(f"Error checking collection existence: {e}")
            return False
    
    def list_user_collections(self, user_id: str) -> List[str]:
        """List all collection session IDs for a user."""
        try:
            user_prefix = f"{GCS_CHROMA_PREFIX}{user_id}/"
            blobs = self.bucket.list_blobs(prefix=user_prefix, delimiter='/')
            
            session_ids = set()
            for blob in blobs:
                # Extract session_id from path
                relative_path = blob.name[len(user_prefix):]
                if '/' in relative_path:
                    session_id = relative_path.split('/')[0]
                    session_ids.add(session_id)
            
            return list(session_ids)
            
        except Exception as e:
            logger.error(f"Error listing user collections: {e}")
            return []