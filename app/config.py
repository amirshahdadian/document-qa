import os
import logging
import warnings
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Suppress specific deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="langchain_community")

# Cloud Run Configuration
PORT = int(os.getenv("PORT", 8501))
IS_PRODUCTION = os.getenv("GAE_ENV", "").startswith("standard") or os.getenv("GOOGLE_CLOUD_PROJECT") is not None

# Configure logging based on environment - Set to WARNING to reduce noise
log_level = logging.WARNING if not IS_PRODUCTION else logging.ERROR
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Set specific loggers to higher levels to reduce noise
logging.getLogger('fsevents').setLevel(logging.ERROR)
logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
logging.getLogger('chromadb').setLevel(logging.WARNING)
logging.getLogger('langchain').setLevel(logging.WARNING)
logging.getLogger('streamlit').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Google API Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")

# Firebase Configuration
FIREBASE_CONFIG = {
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
    "projectId": os.getenv("FIREBASE_PROJECT_ID"),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.getenv("FIREBASE_APP_ID")
}

FIREBASE_SERVICE_ACCOUNT_KEY = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY")

# App Configuration
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
SUPPORTED_FILE_TYPES = ["pdf"]

# Model Configuration
AVAILABLE_MODELS = ["gemini-2.5-flash", "gemini-2.5-pro"]
DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_TEMPERATURE = 0.1

# Text Processing Configuration
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
TEXT_SEPARATORS = ["\n\n", "\n", " ", ""]

# Retrieval Configuration
DEFAULT_K_DOCS = 5
DEFAULT_FETCH_K = 10
SEARCH_TYPE = "mmr"  # Maximum Marginal Relevance

# ChromaDB Configuration - Use absolute path for better persistence
CHROMA_PERSIST_DIRECTORY = os.path.abspath("./chroma_db")
CHROMA_COLLECTION_PREFIX = "user_documents"

# Google Cloud Storage Configuration
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "your-app-chroma-db")  # Set this in your environment
GCS_CHROMA_PREFIX = "chroma_db/"  # Prefix for ChromaDB files in GCS

# Ensure GCS bucket name is properly configured
if not GCS_BUCKET_NAME:
    logger.warning("GCS_BUCKET_NAME not set, using default")
    GCS_BUCKET_NAME = "your-app-chroma-db"

# Cache validation result to avoid repeated calls
_config_validated = False

def validate_config():
    """Validate that all required configuration is present."""
    global _config_validated
    
    if _config_validated:
        return True
    
    required_vars = [
        "GOOGLE_API_KEY",
        "FIREBASE_API_KEY",
        "FIREBASE_AUTH_DOMAIN",
        "FIREBASE_PROJECT_ID",
        "FIREBASE_STORAGE_BUCKET",
        "FIREBASE_MESSAGING_SENDER_ID",
        "FIREBASE_APP_ID",
        "FIREBASE_SERVICE_ACCOUNT_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    _config_validated = True
    if not IS_PRODUCTION:
        logger.info("Configuration validated successfully")
    return True

# Validate GCS configuration in production
def validate_gcs_config():
    """Validate GCS configuration."""
    if IS_PRODUCTION:
        if not GCS_BUCKET_NAME:
            logger.error("GCS_BUCKET_NAME is required for production deployment")
            return False
        
        try:
            from google.cloud import storage
            from google.auth import default
            
            credentials, project = default()
            client = storage.Client(credentials=credentials, project=project)
            bucket = client.bucket(GCS_BUCKET_NAME)
            
            # Test bucket access
            bucket.exists()
            logger.info(f"GCS bucket '{GCS_BUCKET_NAME}' is accessible")
            return True
        except Exception as e:
            logger.error(f"GCS configuration validation failed: {e}")
            return False
    return True

# Create ChromaDB directory if it doesn't exist
os.makedirs(CHROMA_PERSIST_DIRECTORY, exist_ok=True)

# Only test API key in development and reduce output
if not IS_PRODUCTION:
    try:
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content("Hello")
        print("API key is working!")
    except Exception as e:
        print(f"API key error: {e}")