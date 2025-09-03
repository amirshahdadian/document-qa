# Italian Student Document Q&A Assistant

![Python Version](https://img.shields.io/badge/python-3.9-blue.svg)
![Framework](https://img.shields.io/badge/framework-Streamlit-red.svg)
![Platform](https://img.shields.io/badge/platform-Google_Cloud-orange.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

A production-ready, AI-powered assistant built to help international students navigate the complexities of Italian bureaucratic documents. This application uses a Retrieval-Augmented Generation (RAG) pipeline to answer questions about PDFs like university announcements (*bandi*), regulations, and contracts.

---

## 🚀 Live Demo

The application is deployed on Google Cloud Run and is accessible here:

**[https://document-qa-876776881787.europe-west1.run.app](https://document-qa-876776881787.europe-west1.run.app)**

---

## ✨ Key Features

-   **📄 PDF Document Processing**: Upload large, multi-page PDF documents for analysis.
-   **🤖 AI-Powered Q&A**: Ask complex questions about the document content in natural language (English or Italian) and receive precise, context-aware answers.
-   **🔐 Secure User Authentication**: Full Google OAuth 2.0 integration via Firebase Authentication ensures user data is secure and private.
-   **💬 Persistent Chat Sessions**: Chat history is saved and linked to user accounts. Users can load, continue, or delete past conversations.
-   **☁️ Cloud-Native Persistence**: Vector embeddings are backed up to Google Cloud Storage (GCS), ensuring session data persists across deployments and server instances.
-   **🔬 Custom Evaluation Framework**: Includes a domain-specific test suite to measure the AI's accuracy and completeness on real-world Italian student documents.

---

## 🏗️ System Architecture

The application is built on a modern, modular, and scalable architecture designed for production deployment.

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

1.  **Frontend**: A user-friendly interface built with **Streamlit**.
2.  **Authentication**: **Firebase Authentication** handles Google OAuth, user management, and session data storage in **Firestore**.
3.  **Backend Logic**: The core application logic orchestrates the user flow, from document upload to Q&A.
4.  **RAG Pipeline**:
    -   **LangChain** orchestrates the entire pipeline.
    -   **PyPDF** parses and chunks text from uploaded documents.
    -   **Google Gemini** generates text embeddings and synthesizes answers.
    -   **ChromaDB** serves as the high-performance local vector database.
5.  **Persistence**:
    -   **Google Cloud Storage (GCS)** provides durable, long-term storage for ChromaDB vector collections, enabling stateful sessions in a stateless environment.
    -   **Firestore** stores user metadata and chat history.
6.  **Deployment**: The application is containerized with **Docker** and deployed as a serverless application on **Google Cloud Run**.

---

## 🛠️ Technology Stack

-   **Backend**: Python 3.9
-   **Frontend**: Streamlit
-   **AI/ML**: LangChain, Google Gemini
-   **Vector Database**: ChromaDB
-   **Cloud Platform**: Google Cloud Platform (Cloud Run, GCS, Firebase)
-   **Authentication**: Firebase Authentication, Google OAuth 2.0
-   **Containerization**: Docker

---

## ⚙️ Local Setup and Installation

### Prerequisites

-   Python 3.9+
-   Git
-   Google Cloud SDK (`gcloud`) for deployment

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd document-qa
```

### 2. Set Up Environment Variables

Create a `.env` file by copying the example file.

```bash
cp .env.example .env
```

Now, edit the `.env` file and fill in your actual credentials from Google Cloud and Firebase.

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Application

```bash
streamlit run app.py
```

The application will be available at `http://localhost:8501`.

---

## ☁️ Deployment

The project includes a comprehensive deployment script for Google Cloud Run.

### Prerequisites

1.  Authenticate with Google Cloud:
    ```bash
    gcloud auth login
    gcloud auth application-default login
    ```
2.  Set your project ID:
    ```bash
    gcloud config set project your-gcp-project-id
    ```
3.  Enable required Google Cloud services (Cloud Build, Cloud Run).

### Run the Deployment Script

The script will build the Docker image using Cloud Build and deploy it to Cloud Run with all necessary environment variables.

```bash
./deploy.sh
```

---

## 🧪 Testing and Evaluation

This project uses a two-pronged testing strategy to ensure both code quality and AI performance.

### Unit and Integration Tests

These tests validate the application's core logic, input handling, and component interactions.

```bash
python run_tests.py
```

### AI Quality Evaluation

This is the most critical test for a RAG system. It uses a custom, domain-specific dataset located at `evaluation/italian_student_qa_test_set.json` to measure the AI's real-world performance.

The evaluation script:
-   Processes a real Italian university document.
-   Asks a series of challenging, domain-specific questions.
-   Compares the AI's answers against ground-truth answers.
-   Calculates metrics for **accuracy** and **completeness**.

To run the evaluation:

```bash
python evaluation/run_evaluation.py
```

This evaluation framework is a key academic contribution, proving the system's effectiveness beyond generic benchmarks.

---

## 📁 Project Structure

```
├── app/                # Core application source code
│   ├── auth.py         # Firebase authentication and Firestore logic
│   ├── config.py       # Configuration and environment variables
│   ├── gcs_storage.py  # Google Cloud Storage interaction
│   ├── main.py         # Main application UI and workflow
│   ├── pdf_processing.py # PDF parsing and chunking
│   └── qa_pipeline.py  # RAG pipeline orchestration
├── evaluation/         # AI model evaluation framework
│   ├── italian_student_qa_test_set.json # Domain-specific Q&A dataset
│   └── run_evaluation.py # Evaluation script
├── tests/              # Unit and integration tests
├── .streamlit/         # Streamlit configuration
├── app.py              # Main entry point for Streamlit
├── deploy.sh           # Automated deployment script
├── Dockerfile          # Container definition for production
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

---

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for details.

---

## 👤 Authors

- **Amir Shahdadian**
- **Mahtab Taheri**
- **Mohammad Ali Yazdani**
