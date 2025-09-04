# Italian Student Document Q&A Assistant

![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)
![Framework](https://img.shields.io/badge/framework-Streamlit-red.svg)
![AI Model](https://img.shields.io/badge/AI-Google_Gemini-orange.svg)
![Vector DB](https://img.shields.io/badge/Vector_DB-ChromaDB-green.svg)
![Cloud](https://img.shields.io/badge/Cloud-Google_Cloud_Platform-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

A production-ready, AI-powered assistant designed to help international students navigate Italian bureaucratic documents. This application leverages a Retrieval-Augmented Generation (RAG) pipeline to answer questions about PDFs such as university announcements (*bandi*), regulations, and contracts. Built with modern AI tools for accurate, multilingual responses.

---

## ✨ Key Features

- **Multilingual Support**: Handles both English and Italian queries seamlessly.
- **Document Upload & Processing**: Secure PDF parsing with intelligent chunking for optimal retrieval.
- **Advanced RAG Pipeline**: Combines Google Gemini embeddings, ChromaDB vector storage, and semantic search for high-accuracy answers.
- **Real-Time Q&A**: Interactive chat interface with source document references.
- **Cloud-Native Deployment**: Scalable deployment on Google Cloud Run with persistent storage via GCS.
- **Authentication**: Secure user sessions with Firebase Authentication and Google OAuth.
- **Evaluation Framework**: Comprehensive AI quality testing using semantic similarity and domain-specific datasets.
- **Production-Ready**: Containerized with Docker, includes logging, error handling, and monitoring.

---

## 🏗️ System Architecture

The application follows a modular, scalable architecture optimized for production deployment.

```
User ↔ [Streamlit UI] ↔ [Firebase Auth]
         │
         └─> [Application Backend (app/main.py)]
               │
               ├─> [PDF Processing (app/pdf_processing.py)]
               │
               └─> [QA Pipeline (app/qa_pipeline.py)] ──┬──> [Google Gemini (Embeddings & LLM)]
                                                       │
                                                       ├─> [ChromaDB (Local Vector Store)]
                                                       │
                                                       └─> [GCS Storage (app/gcs_storage.py)] ↔ [Google Cloud Storage]
               │
               └─> [Auth Service (app/auth.py)] ↔ [Google Firestore (Chat History)]
```

1. **Frontend**: User-friendly interface built with **Streamlit** for document upload and Q&A.
2. **Authentication**: **Firebase Authentication** manages Google OAuth, user sessions, and metadata storage in **Firestore**.
3. **Backend Logic**: Core application logic in `app/main.py` orchestrates the workflow from upload to response.
4. **RAG Pipeline**:
   - **LangChain** orchestrates the entire pipeline.
   - **PyPDF** parses and chunks text from uploaded documents.
   - **Google Gemini** generates embeddings and synthesizes answers.
   - **ChromaDB** serves as the high-performance local vector database.
5. **Persistence**:
   - **Google Cloud Storage (GCS)** provides durable storage for ChromaDB collections, enabling stateful sessions in a stateless environment.
   - **Firestore** stores user metadata and chat history.
6. **Deployment**: Containerized with **Docker** and deployed as a serverless application on **Google Cloud Run**.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.9+
- **Frontend**: Streamlit
- **AI/ML**: LangChain, Google Gemini (Embeddings & LLM)
- **Vector Database**: ChromaDB
- **Cloud Platform**: Google Cloud Platform (Cloud Run, GCS, Firebase)
- **Authentication**: Firebase Authentication, Google OAuth 2.0
- **Containerization**: Docker
- **Evaluation**: Sentence Transformers, Scikit-learn (for semantic similarity)
- **Other**: PyPDF2, Dotenv

---

## ⚙️ Local Setup and Installation

### Prerequisites

- Python 3.9+
- Git
- Google Cloud SDK (`gcloud`) for deployment (optional)
- A Google Cloud Project with enabled APIs (Gemini, GCS, Firestore)

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd document-qa
```

### 2. Set Up Environment Variables

Create a `.env` file by copying the example:

```bash
cp .env.example .env
```

Edit `.env` and fill in your credentials:
- `GOOGLE_API_KEY`: Your Google Gemini API key.
- `FIREBASE_PROJECT_ID`: Your Firebase project ID.
- `GCS_BUCKET_NAME`: Your GCS bucket name.
- Other Firebase/Firestore credentials.

**Note**: Never commit `.env` to version control. Use `.env.example` as a template.

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

For evaluation features, ensure these are installed:
```bash
pip install sentence-transformers scikit-learn
```

### 4. Run the Application

```bash
streamlit run app.py
```

The app will be available at `http://localhost:8501`.

### Troubleshooting

- **API Key Issues**: Ensure `GOOGLE_API_KEY` is set and valid.
- **Firebase Auth**: Verify Firebase project settings and Firestore rules.
- **Port Conflicts**: If 8501 is in use, run `streamlit run app.py --server.port 8502`.

---

## ☁️ Deployment

Deploy to Google Cloud Run for production scalability.

### Prerequisites

1. Authenticate with Google Cloud:
   ```bash
   gcloud auth login
   gcloud auth application-default login
   ```
2. Set your project ID:
   ```bash
   gcloud config set project your-gcp-project-id
   ```
3. Enable required services: Cloud Build, Cloud Run, GCS, Firestore, Gemini API.

### Run the Deployment Script

The script builds the Docker image and deploys to Cloud Run:

```bash
./deploy.sh
```

This sets up environment variables, builds the container, and provides the public URL.

### Manual Deployment

If needed, build and deploy manually:

```bash
# Build Docker image
docker build -t document-qa .

# Run locally for testing
docker run -p 8501:8501 --env-file .env document-qa

# Deploy to Cloud Run
gcloud run deploy document-qa --source . --platform managed --region us-central1 --allow-unauthenticated
```

---

## 🧪 Testing and Evaluation

This project uses a comprehensive testing strategy for both code quality and AI performance.

### Unit and Integration Tests

Validate core logic, input handling, and component interactions:

```bash
python run_tests.py
```

### AI Quality Evaluation

The most critical test for the RAG system uses a custom, domain-specific dataset in `evaluation/italian_student_qa_test_set.json`. It measures real-world performance with:

- **Semantic Similarity**: Advanced NLP evaluation using Sentence Transformers to compare AI answers against ground-truth responses.
- **Multilingual Support**: Separate scoring for English and Italian queries.
- **Accuracy & Completeness Metrics**: Evaluates both correctness and response quality.
- **Real Document Processing**: Tests against actual Italian university PDFs.

To run the enhanced evaluation:

```bash
python evaluation/run_evaluation.py
```

**Key Improvements**:
- Uses `paraphrase-multilingual-mpnet-base-v2` for better semantic understanding.
- Handles paraphrases, synonyms, and multilingual variations.
- Provides detailed per-question feedback and overall performance metrics.
- Threshold-based pass/fail with configurable accuracy goals (default: 75%).

This evaluation framework proves the system's effectiveness beyond generic benchmarks, making it a strong academic contribution.

---

## 📁 Project Structure

```
├── .dockerignore              # Docker ignore rules
├── .env                       # Environment variables (not committed)
├── .env.example               # Environment template
├── .gitignore                 # Git ignore rules
├── app.py                     # Main Streamlit entry point
├── deploy.sh                  # Automated deployment script
├── Dockerfile                 # Container definition
├── LICENCE                    # MIT License
├── README.md                  # This file
├── requirements.txt           # Python dependencies
├── run_tests.py               # Unit/integration test runner
├── .streamlit/
│   └── config.toml            # Streamlit configuration
├── app/                       # Core application source code
│   ├── __init__.py
│   ├── auth.py                # Firebase auth and Firestore logic
│   ├── config.py              # Configuration and environment variables
│   ├── gcs_storage.py         # Google Cloud Storage interaction
│   ├── main.py                # Main application UI and workflow
│   ├── pdf_processing.py      # PDF parsing and chunking
│   ├── qa_pipeline.py         # RAG pipeline orchestration
│   ├── utils.py               # Utility functions
│   └── __pycache__/           # Python cache (ignored)
├── evaluation/                # AI evaluation framework
│   ├── evaluation_results.json # Evaluation output
│   ├── italian_student_qa_test_set.json # Test dataset
│   └── run_evaluation.py      # Enhanced evaluation script
└── tests/                     # Unit and integration tests
```

---

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/your-feature`.
3. Make changes and add tests.
4. Run tests: `python run_tests.py` and `python evaluation/run_evaluation.py`.
5. Commit changes: `git commit -m "Add your feature"`.
6. Push to your fork and submit a pull request.

### Guidelines

- Follow PEP 8 for Python code.
- Add docstrings and type hints.
- Update tests for new features.
- Ensure evaluation accuracy remains above 75%.

---

## 📄 License

This project is licensed under the MIT License. See the `LICENCE` file for details.

---

## 👤 Authors

- **Amir Shahdadian**
- **Mahtab Taheri**
- **Mohammad Ali Yazdani**

---

## 📞 Support

For questions or issues:
- Open an issue on GitHub.
- Check the troubleshooting section above.
- Review the evaluation results for AI-related concerns.

---

*Last updated: 2025*
