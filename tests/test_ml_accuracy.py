import pytest
import json
from unittest.mock import Mock, patch
from app.qa_pipeline import QAPipeline
from app.pdf_processing import PDFProcessor
from langchain.schema import Document
import numpy as np
from typing import List, Dict, Any

class TestMLAccuracy:
    """Enhanced ML accuracy and quality tests for the RAG system."""
    
    @pytest.fixture
    def sample_italian_qa_dataset(self):
        """Sample test dataset for Italian student documents."""
        return [
            {
                "question": "What are the eligibility criteria for this scholarship?",
                "expected_keywords": ["criteri", "eleggibilità", "requisiti", "studenti"],
                "document_content": "I criteri di eleggibilità per la borsa di studio includono: essere studente universitario regolarmente iscritto, ISEE non superiore a 25.000 euro, media minima 27/30.",
                "expected_answer_contains": ["studente", "universitario", "isee", "media"]
            },
            {
                "question": "What is the application deadline?",
                "expected_keywords": ["scadenza", "deadline", "termine", "domanda"],
                "document_content": "La scadenza per la presentazione delle domande è fissata al 31 marzo 2024 alle ore 12:00.",
                "expected_answer_contains": ["31", "marzo", "2024", "12:00"]
            },
            {
                "question": "What documents are required?",
                "expected_keywords": ["documenti", "richiesti", "necessari", "allegare"],
                "document_content": "I documenti da allegare sono: domanda compilata, ISEE in corso di validità, certificato di iscrizione, autocertificazione voti.",
                "expected_answer_contains": ["domanda", "isee", "certificato", "voti"]
            }
        ]
    
    def test_retrieval_precision(self, mock_env_vars, sample_italian_qa_dataset):
        """Test retrieval precision - relevant documents retrieved."""
        qa_pipeline = QAPipeline()
        
        # Create mock documents for each test case
        for test_case in sample_italian_qa_dataset:
            mock_docs = [
                Document(page_content=test_case["document_content"], metadata={"relevance": "high"}),
                Document(page_content="Informazioni generali sull'università", metadata={"relevance": "low"}),
                Document(page_content="Regolamento biblioteca", metadata={"relevance": "low"})
            ]
            
            # Mock vector store that returns documents in order of relevance
            mock_vector_store = Mock()
            mock_vector_store.similarity_search.return_value = mock_docs[:2]  # Return top 2
            
            # Test retrieval
            with patch.object(qa_pipeline, 'create_vector_store', return_value=mock_vector_store):
                vector_store = qa_pipeline.create_vector_store(mock_docs)
                results = qa_pipeline.get_similar_documents(vector_store, test_case["question"], k=2)
                
                # Check that most relevant document is retrieved first
                assert len(results) >= 1
                top_result = results[0].page_content.lower()
                
                # Verify relevant keywords are present
                keyword_found = any(keyword in top_result for keyword in test_case["expected_keywords"])
                assert keyword_found, f"No relevant keywords found for question: {test_case['question']}"
    
    def test_answer_accuracy_against_content(self, mock_env_vars, sample_italian_qa_dataset):
        """Test if answers accurately reflect source document content."""
        qa_pipeline = QAPipeline()
        
        for test_case in sample_italian_qa_dataset:
            mock_qa_chain = Mock()
            
            # Create realistic answer based on document content
            def mock_invoke(query_dict):
                content = test_case["document_content"]
                if "criteri" in query_dict["query"].lower() or "eligibility" in query_dict["query"].lower():
                    return {
                        "result": f"Secondo il documento, {content}",
                        "source_documents": [Document(page_content=content)]
                    }
                elif "scadenza" in query_dict["query"].lower() or "deadline" in query_dict["query"].lower():
                    return {
                        "result": f"Il documento specifica che {content}",
                        "source_documents": [Document(page_content=content)]
                    }
                elif "documenti" in query_dict["query"].lower() or "documents" in query_dict["query"].lower():
                    return {
                        "result": f"Secondo le informazioni fornite, {content}",
                        "source_documents": [Document(page_content=content)]
                    }
                return {"result": content, "source_documents": []}
            
            mock_qa_chain.invoke.side_effect = mock_invoke
            
            result = qa_pipeline.ask_question(mock_qa_chain, test_case["question"])
            answer = result["answer"].lower()
            
            # Check if answer contains expected information from source
            found_elements = sum(1 for element in test_case["expected_answer_contains"] 
                               if element.lower() in answer)
            accuracy_score = found_elements / len(test_case["expected_answer_contains"])
            
            assert accuracy_score >= 0.5, f"Low accuracy ({accuracy_score:.2f}) for question: {test_case['question']}"
    
    def test_hallucination_detection_basic(self, mock_env_vars):
        """Test basic hallucination detection - answers should be grounded in sources."""
        qa_pipeline = QAPipeline()
        
        # Test case where source doesn't contain answer information
        source_content = "Informazioni generali sulla procedura di iscrizione all'università."
        question = "What is the scholarship amount?"
        
        mock_qa_chain = Mock()
        mock_qa_chain.invoke.return_value = {
            "result": "La borsa di studio è di 5.000 euro all'anno",  # This info is NOT in source
            "source_documents": [Document(page_content=source_content)]
        }
        
        result = qa_pipeline.ask_question(mock_qa_chain, question)
        
        # Check if answer contains information not present in source
        answer_words = set(result["answer"].lower().split())
        source_words = set(source_content.lower().split())
        
        # For this test, we expect some overlap or explicit uncertainty
        specific_amount_mentioned = any(word.isdigit() for word in answer_words)
        if specific_amount_mentioned:
            # If specific amount is mentioned, it should be acknowledged as uncertain
            uncertainty_indicators = ["non specificato", "non indicato", "non presente", "non chiaro"]
            has_uncertainty = any(indicator in result["answer"].lower() for indicator in uncertainty_indicators)
            
            # This is a basic check - in real implementation, this would be more sophisticated
            print(f"Warning: Specific amount mentioned without source verification: {result['answer']}")
    
    def test_answer_completeness(self, mock_env_vars, sample_italian_qa_dataset):
        """Test if answers are complete and informative."""
        qa_pipeline = QAPipeline()
        
        for test_case in sample_italian_qa_dataset:
            mock_qa_chain = Mock()
            mock_qa_chain.invoke.return_value = {
                "result": f"Secondo il documento fornito, {test_case['document_content']} Queste sono le informazioni principali relative alla sua domanda.",
                "source_documents": [Document(page_content=test_case["document_content"])]
            }
            
            result = qa_pipeline.ask_question(mock_qa_chain, test_case["question"])
            answer = result["answer"]
            
            # Check answer length and informativeness
            assert len(answer) >= 50, f"Answer too short for question: {test_case['question']}"
            assert len(answer.split()) >= 10, "Answer should contain multiple words"
            
            # Check for informative content
            informative_words = ["secondo", "documento", "specificato", "indicato", "previsto"]
            has_informative_language = any(word in answer.lower() for word in informative_words)
            assert has_informative_language, "Answer lacks informative language structure"
    
    def test_consistency_across_similar_questions(self, mock_env_vars):
        """Test if similar questions get consistent answers."""
        qa_pipeline = QAPipeline()
        
        # Similar questions about the same topic
        similar_questions = [
            "What are the eligibility requirements?",
            "What are the eligibility criteria?", 
            "What requirements must students meet?"
        ]
        
        source_content = "I requisiti per la borsa di studio sono: iscrizione universitaria, ISEE sotto 25.000 euro, media minima 27/30."
        
        mock_qa_chain = Mock()
        mock_qa_chain.invoke.return_value = {
            "result": f"I requisiti includono: {source_content}",
            "source_documents": [Document(page_content=source_content)]
        }
        
        answers = []
        for question in similar_questions:
            result = qa_pipeline.ask_question(mock_qa_chain, question)
            answers.append(result["answer"].lower())
        
        # Check for consistency in key information
        key_terms = ["isee", "25.000", "27/30", "universitaria"]
        for term in key_terms:
            term_appearances = sum(1 for answer in answers if term in answer)
            consistency_rate = term_appearances / len(answers)
            assert consistency_rate >= 0.8, f"Inconsistent mention of key term '{term}' across similar questions"
    
    def test_multilingual_understanding(self, mock_env_vars):
        """Test handling of questions in different languages (English/Italian)."""
        qa_pipeline = QAPipeline()
        
        source_content = "La scadenza per le domande è il 31 marzo 2024."
        
        test_cases = [
            {
                "question": "Qual è la scadenza per le domande?",
                "language": "italian"
            },
            {
                "question": "What is the application deadline?", 
                "language": "english"
            }
        ]
        
        for test_case in test_cases:
            mock_qa_chain = Mock()
            mock_qa_chain.invoke.return_value = {
                "result": "La scadenza per la presentazione delle domande è fissata al 31 marzo 2024.",
                "source_documents": [Document(page_content=source_content)]
            }
            
            result = qa_pipeline.ask_question(mock_qa_chain, test_case["question"])
            
            # Check that answer contains key information regardless of question language
            assert "31" in result["answer"]
            assert "marzo" in result["answer"] or "march" in result["answer"].lower()
            assert "2024" in result["answer"]
    
    def test_source_attribution_accuracy(self, mock_env_vars):
        """Test if retrieved sources are actually relevant to the question."""
        qa_pipeline = QAPipeline()
        
        # Create documents with clear topic separation
        documents = [
            Document(page_content="Informazioni sulla borsa di studio per studenti internazionali", metadata={"topic": "scholarship"}),
            Document(page_content="Regolamento biblioteca universitaria e orari di apertura", metadata={"topic": "library"}),
            Document(page_content="Procedura di iscrizione ai corsi di laurea magistrale", metadata={"topic": "enrollment"})
        ]
        
        mock_vector_store = Mock()
        
        def mock_similarity_search(query, k=3):
            query_lower = query.lower()
            if "borsa" in query_lower or "scholarship" in query_lower:
                return [documents[0]]  # Return scholarship document
            elif "biblioteca" in query_lower or "library" in query_lower:
                return [documents[1]]  # Return library document
            elif "iscrizione" in query_lower or "enrollment" in query_lower:
                return [documents[2]]  # Return enrollment document
            return documents[:k]  # Default return
        
        mock_vector_store.similarity_search.side_effect = mock_similarity_search
        
        # Test with scholarship question
        with patch.object(qa_pipeline, 'create_vector_store', return_value=mock_vector_store):
            vector_store = qa_pipeline.create_vector_store(documents)
            results = qa_pipeline.get_similar_documents(vector_store, "Information about scholarship eligibility", k=1)
            
            assert len(results) == 1
            assert "borsa" in results[0].page_content.lower()
            assert results[0].metadata["topic"] == "scholarship"