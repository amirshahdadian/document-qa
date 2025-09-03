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
    """Google Cloud Storage client for managing ChromaDB collections."""
    
    def __init__(self):
        try:
            # Use application default credentials for both Cloud Run and local development
            credentials, project = default()
            self.client = storage.Client(credentials=credentials, project=project)
            
            if not IS_PRODUCTION:
                logger.info(f"GCS initialized with project: {project}")
            
            self.bucket = self.client.bucket(GCS_BUCKET_NAME)
            
            # Verify bucket accessibility
            try:
                exists = self.bucket.exists()
                if exists:
                    if not IS_PRODUCTION:
                        logger.info(f"GCS Storage initialized for bucket: {GCS_BUCKET_NAME}")
                else:
                    logger.error(f"GCS bucket '{GCS_BUCKET_NAME}' does not exist")
                    if IS_PRODUCTION:
                        raise Exception(f"Bucket {GCS_BUCKET_NAME} not found")
            except Exception as e:
                logger.warning(f"GCS bucket access test failed: {e}")
                if IS_PRODUCTION:
                    raise e
                
        except Exception as e:
            logger.error(f"Failed to initialize GCS Storage: {e}")
            if IS_PRODUCTION:
                raise e
            else:
                logger.warning("GCS Storage initialization failed - storage features will be limited")
                self.client = None

    def upload_chroma_collection(self, local_path: str, user_id: str, session_id: str) -> bool:
        """Upload ChromaDB collection directory to GCS."""
        if not self.client:
            logger.warning("GCS client not available - skipping upload")
            return False
            
        try:
            collection_prefix = f"{GCS_CHROMA_PREFIX}{user_id}/{session_id}/"
            
            if os.path.exists(local_path):
                uploaded_files = 0
                for root, dirs, files in os.walk(local_path):
                    for file in files:
                        local_file_path = os.path.join(root, file)
                        relative_path = os.path.relpath(local_file_path, local_path)
                        gcs_path = collection_prefix + relative_path
                        
                        blob = self.bucket.blob(gcs_path)
                        blob.upload_from_filename(local_file_path)
                        uploaded_files += 1
                        
                        if not IS_PRODUCTION:
                            logger.debug(f"Uploaded {local_file_path} to {gcs_path}")
                
                if uploaded_files > 0:
                    logger.info(f"ChromaDB collection uploaded for user {user_id}, session {session_id} ({uploaded_files} files)")
                    return True
                else:
                    logger.warning(f"No files found to upload in {local_path}")
                    return False
            else:
                logger.warning(f"Local ChromaDB path not found: {local_path}")
                return False
                
        except Exception as e:
            logger.error(f"Error uploading ChromaDB collection: {e}")
            return False

    def download_chroma_collection(self, local_path: str, user_id: str, session_id: str) -> bool:
        """Download ChromaDB collection from GCS to local directory."""
        if not self.client:
            logger.warning("GCS client not available - skipping download")
            return False
            
        try:
            collection_prefix = f"{GCS_CHROMA_PREFIX}{user_id}/{session_id}/"
            os.makedirs(local_path, exist_ok=True)
            
            blobs = self.bucket.list_blobs(prefix=collection_prefix)
            downloaded_files = 0
            
            for blob in blobs:
                if blob.name == collection_prefix:
                    continue
                    
                relative_path = blob.name[len(collection_prefix):]
                local_file_path = os.path.join(local_path, relative_path)
                
                local_dir = os.path.dirname(local_file_path)
                if local_dir:
                    os.makedirs(local_dir, exist_ok=True)
                
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
        if not self.client:
            logger.warning("GCS client not available - skipping delete")
            return True
            
        try:
            collection_prefix = f"{GCS_CHROMA_PREFIX}{user_id}/{session_id}/"
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
        if not self.client:
            return False
            
        try:
            collection_prefix = f"{GCS_CHROMA_PREFIX}{user_id}/{session_id}/"
            blobs = list(self.bucket.list_blobs(prefix=collection_prefix, max_results=1))
            return len(blobs) > 0
        except Exception as e:
            logger.error(f"Error checking collection existence: {e}")
            return False

    def list_user_collections(self, user_id: str) -> List[str]:
        """List all collection session IDs for a user."""
        if not self.client:
            return []
            
        try:
            user_prefix = f"{GCS_CHROMA_PREFIX}{user_id}/"
            blobs = self.bucket.list_blobs(prefix=user_prefix, delimiter="/")
            
            session_ids = []
            for prefix in blobs.prefixes:
                session_id = prefix.replace(user_prefix, "").rstrip("/")
                if session_id:
                    session_ids.append(session_id)
            
            return session_ids
        except Exception as e:
            logger.error(f"Error listing user collections: {e}")
            return []
