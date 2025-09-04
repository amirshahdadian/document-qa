#!/usr/bin/env python3
"""
Evaluation script for the RAG system using enhanced semantic similarity.
This script runs a real end-to-end evaluation by processing a PDF,
building a vector store, and querying the actual LLM.

Usage: python evaluation/run_evaluation.py
"""

import json
import os
import sys
import re
import unicodedata
from pathlib import Path
from dotenv import load_dotenv
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Add the parent directory to the Python path to find app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.qa_pipeline import QAPipeline
from app.pdf_processing import PDFProcessor
from langchain.schema import Document
from typing import Dict, List, Any

class RAGEvaluator:
    """Evaluator for RAG system performance using enhanced semantic similarity."""

    def __init__(self):
        self.qa_pipeline = QAPipeline()
        self.pdf_processor = PDFProcessor()
        # Use a more advanced multilingual sentence transformer for better accuracy
        self.similarity_model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')
        self.results = []

    def load_test_dataset(self, dataset_path: str) -> Dict:
        """Load the test dataset from JSON file."""
        with open(dataset_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _preprocess_text(self, text: str) -> str:
        """
        Enhanced text preprocessing for better semantic similarity.
        """
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Normalize unicode characters (handle accents, etc.)
        text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
        
        # Remove punctuation and extra whitespace
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove common stop words that don't contribute to meaning
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'il', 'la', 'le', 'i', 'gli', 'lo', 'un', 'una', 'uno', 'e', 'o', 'ma', 'in', 'su', 'a', 'per', 'di', 'con', 'da'
        }
        words = text.split()
        filtered_words = [word for word in words if word not in stop_words and len(word) > 1]
        
        return ' '.join(filtered_words)

    def evaluate_answer_accuracy(self, answer: str, expected_answer: str, threshold: float = 0.6) -> float:
        """
        Enhanced semantic similarity evaluation with better preprocessing and scoring.
        Returns a score between 0 and 1.
        """
        if not answer or not expected_answer:
            return 0.0
        
        # Preprocess both texts
        answer_clean = self._preprocess_text(answer)
        expected_clean = self._preprocess_text(expected_answer)
        
        if not answer_clean or not expected_clean:
            return 0.0
        
        # Handle exact matches after preprocessing
        if answer_clean == expected_clean:
            return 1.0
        
        # Calculate semantic similarity using sentence transformers
        try:
            # Use batch processing for efficiency
            embeddings = self.similarity_model.encode([answer_clean, expected_clean], convert_to_tensor=False)
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            
            # Enhanced scoring logic
            if similarity >= threshold:
                # Full credit for high similarity
                return float(similarity)
            elif similarity >= threshold * 0.7:
                # Partial credit for moderate similarity
                return float(similarity * 0.8)
            else:
                # Minimal credit for low similarity, but not zero
                return float(similarity * 0.3)
                
        except Exception as e:
            print(f"Error calculating similarity: {e}")
            # Enhanced fallback with better word overlap
            return self._enhanced_fallback_similarity(answer_clean, expected_clean)

    def _enhanced_fallback_similarity(self, answer: str, expected: str) -> float:
        """Enhanced fallback similarity calculation with better word matching."""
        if not answer or not expected:
            return 0.0
        
        answer_words = set(answer.split())
        expected_words = set(expected.split())
        
        if not expected_words:
            return 0.0
        
        # Calculate Jaccard similarity (intersection over union)
        intersection = len(answer_words.intersection(expected_words))
        union = len(answer_words.union(expected_words))
        
        if union == 0:
            return 0.0
        
        jaccard_similarity = intersection / union
        
        # Also consider partial word matches
        partial_matches = 0
        for a_word in answer_words:
            for e_word in expected_words:
                if len(a_word) > 3 and len(e_word) > 3:
                    # Check for substring matches
                    if a_word in e_word or e_word in a_word:
                        partial_matches += 0.5
        
        total_similarity = jaccard_similarity + (partial_matches / len(expected_words))
        return min(total_similarity, 1.0)  # Cap at 1.0

    def evaluate_answer_completeness(self, answer: str, min_words: int = 10) -> bool:
        """Check if answer meets minimum word count and isn't an error message."""
        if not answer:
            return False
        
        # Enhanced error pattern detection
        error_patterns = [
            "non sono specificati", "not specified",
            "non è presente", "not present", "not available",
            "non fornisce", "does not provide",
            "non sono presenti", "not found",
            "i'm sorry", "sorry", "unable to",
            "non riesco", "non posso", "mi dispiace"
        ]
        
        answer_lower = answer.lower()
        if any(pattern in answer_lower for pattern in error_patterns):
            return False
        
        # Count meaningful words (exclude very short words)
        words = [word for word in answer.split() if len(word) > 2]
        return len(words) >= min_words

    def run_full_evaluation(self, dataset_path: str, pdf_path: str) -> Dict[str, Any]:
        """
        Runs a full, real evaluation on a given PDF using a test dataset.
        """
        print("="*60)
        print("Starting Enhanced RAG System Evaluation (Semantic Similarity)")
        print("="*60)

        # 1. Load Test Dataset
        dataset = self.load_test_dataset(dataset_path)
        test_cases = dataset["test_cases"]
        print(f"✅ Loaded {len(test_cases)} test cases from '{dataset_path}'")

        # 2. Process the real PDF document
        print(f"📄 Processing evaluation document: '{pdf_path}'...")
        try:
            with open(pdf_path, "rb") as f:
                from io import BytesIO
                mock_pdf_file = BytesIO(f.read())
                mock_pdf_file.name = os.path.basename(pdf_path)
                mock_pdf_file.size = os.path.getsize(pdf_path)
                
                chunks = self.pdf_processor.load_and_process_pdf(mock_pdf_file)
                print(f"✅ Document processed into {len(chunks)} chunks.")
        except Exception as e:
            print(f"❌ Critical Error: Failed to process PDF. {e}")
            return {}

        # 3. Build the Vector Store and QA Chain
        print("🧠 Building vector store and setting up QA chain...")
        try:
            vector_store = self.qa_pipeline.create_vector_store(chunks, "evaluation_user", "evaluation_session", persist=False)
            qa_chain = self.qa_pipeline.setup_qa_chain(vector_store)
            print("✅ QA pipeline is ready.")
        except Exception as e:
            print(f"❌ Critical Error: Failed to set up QA pipeline. {e}")
            return {}

        # 4. Run questions against the real QA chain
        results_detail = []
        print(f"\n🔬 Running {len(test_cases)} test cases against the live model...")
        
        for i, test_case in enumerate(test_cases):
            print(f"  - Running test case {i+1}/{len(test_cases)}: {test_case['id']}")
            
            for lang in ['en', 'it']:
                question_key = f"question_{lang}"
                expected_key = f"expected_answer_{lang}"
                
                if question_key not in test_case or expected_key not in test_case:
                    continue
                
                question = test_case[question_key]
                expected_answer = test_case[expected_key]
                
                try:
                    # This is the real call to the AI model
                    result = self.qa_pipeline.ask_question(qa_chain, question)
                    answer = result.get("answer", "")
                    
                    # Calculate enhanced semantic similarity score
                    accuracy = self.evaluate_answer_accuracy(answer, expected_answer)
                    completeness = self.evaluate_answer_completeness(answer)
                    
                    results_detail.append({
                        "test_id": test_case["id"],
                        "language": lang,
                        "question": question,
                        "answer": answer,
                        "expected_answer": expected_answer,
                        "accuracy_score": accuracy,
                        "is_complete": completeness,
                    })
                    
                    # Enhanced logging for debugging
                    print(f"    - {lang.upper()}: {accuracy:.2%} accuracy (complete: {'✅' if completeness else '❌'})")
                    
                except Exception as e:
                    print(f"    - ⚠️ Error processing question '{question}': {e}")
                    results_detail.append({
                        "test_id": test_case["id"], "language": lang, "question": question,
                        "answer": f"ERROR: {str(e)}", "expected_answer": expected_answer,
                        "accuracy_score": 0.0, "is_complete": False,
                    })

        # 5. Calculate and summarize results
        successful_tests = [r for r in results_detail if not r["answer"].startswith("ERROR:")]
        overall_accuracy = sum(r["accuracy_score"] for r in successful_tests) / len(successful_tests) if successful_tests else 0.0
        overall_completeness = sum(1 for r in successful_tests if r["is_complete"]) / len(successful_tests) if successful_tests else 0.0

        # Calculate language-specific performance
        en_tests = [r for r in successful_tests if r["language"] == "en"]
        it_tests = [r for r in successful_tests if r["language"] == "it"]
        
        en_accuracy = sum(r["accuracy_score"] for r in en_tests) / len(en_tests) if en_tests else 0.0
        it_accuracy = sum(r["accuracy_score"] for r in it_tests) / len(it_tests) if it_tests else 0.0

        summary = {
            "total_test_cases": len(test_cases),
            "total_questions_tested": len(results_detail),
            "successful_tests": len(successful_tests),
            "failed_tests": len(results_detail) - len(successful_tests),
            "overall_accuracy": overall_accuracy,
            "english_accuracy": en_accuracy,
            "italian_accuracy": it_accuracy,
            "overall_completeness_rate": overall_completeness,
            "accuracy_threshold": dataset["evaluation_metrics"]["accuracy_threshold"],
            "passed_accuracy": overall_accuracy >= dataset["evaluation_metrics"]["accuracy_threshold"],
            "detailed_results": results_detail
        }
        return summary

    def save_results(self, results: Dict, output_path: str):
        """Save evaluation results to JSON file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Detailed results saved to: {output_path}")

def main():
    """Main function to run the evaluation."""
    try:
        # Load environment variables from .env file for API keys
        load_dotenv()
        if not os.getenv('GOOGLE_API_KEY'):
            print("❌ Error: GOOGLE_API_KEY not found. Make sure it's in your .env file.")
            return False

        evaluator = RAGEvaluator()
        
        pdf_for_evaluation = "evaluation/sample_bando.pdf"
        dataset_path = "evaluation/italian_student_qa_test_set.json"
        results_path = "evaluation/evaluation_results.json"
        
        if not os.path.exists(pdf_for_evaluation):
            print(f"❌ Error: Evaluation PDF not found at '{pdf_path}'")
            print("Please add a sample PDF to the evaluation folder and update the path in this script.")
            return False

        # Run full, real evaluation
        results = evaluator.run_full_evaluation(dataset_path, pdf_for_evaluation)
        if not results:
            return False

        evaluator.save_results(results, results_path)
        
        # Print enhanced summary
        print("\n" + "="*60)
        print("ENHANCED EVALUATION SUMMARY")
        print("="*60)
        print(f"Overall Accuracy: {results['overall_accuracy']:.2%}")
        print(f"  ├─ English Tests: {results['english_accuracy']:.2%}")
        print(f"  └─ Italian Tests: {results['italian_accuracy']:.2%}")
        print(f"Completeness Rate: {results['overall_completeness_rate']:.2%}")
        print(f"Accuracy Threshold: {results['accuracy_threshold']:.2%}")
        print(f"Passed Accuracy Test: {'✅ YES' if results['passed_accuracy'] else '❌ NO'}")
        print(f"Successful Tests: {results['successful_tests']}/{results['total_questions_tested']}")
        
        return results['passed_accuracy']
        
    except Exception as e:
        print(f"An unexpected error occurred during evaluation: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    print("\nEvaluation finished.")
    sys.exit(0 if success else 1)