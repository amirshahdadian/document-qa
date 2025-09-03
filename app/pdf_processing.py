import os
import tempfile
import logging
from typing import List
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from app.config import MAX_FILE_SIZE, CHUNK_SIZE, CHUNK_OVERLAP, TEXT_SEPARATORS

logger = logging.getLogger(__name__)

class PDFProcessor:
    """Handles PDF loading, validation, and text chunking."""

    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=TEXT_SEPARATORS
        )
    
    def validate_file(self, pdf_file) -> bool:
        """Validate PDF file size and type."""
        if pdf_file.size > MAX_FILE_SIZE:
            raise ValueError(f"File size exceeds {MAX_FILE_SIZE / (1024*1024):.0f}MB limit")
        
        if not pdf_file.name.lower().endswith('.pdf'):
            raise ValueError("Only PDF files are supported")
        
        return True
    
    def load_and_process_pdf(self, pdf_file) -> List[Document]:
        """Load PDF, split into chunks, and add metadata."""
        try:
            self.validate_file(pdf_file)
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(pdf_file.getvalue())
                tmp_path = tmp_file.name
            
            loader = PyPDFLoader(tmp_path)
            documents = loader.load()
            
            if not documents:
                raise ValueError("No content found in PDF")
            
            chunks = self.text_splitter.split_documents(documents)
            
            os.unlink(tmp_path)
            
            for i, chunk in enumerate(chunks):
                chunk.metadata.update({
                    'source_file': pdf_file.name,
                    'chunk_id': i,
                    'total_chunks': len(chunks)
                })
            
            logger.info(f"Successfully processed PDF: {len(chunks)} chunks created")
            return chunks
            
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            if 'tmp_path' in locals():
                try:
                    os.unlink(tmp_path)
                except:
                    pass
            raise e
    
    def extract_text_preview(self, pdf_file, max_chars: int = 500) -> str:
        """Extract a text preview from the PDF."""
        try:
            chunks = self.load_and_process_pdf(pdf_file)
            if chunks:
                preview = chunks[0].page_content[:max_chars]
                return preview + "..." if len(chunks[0].page_content) > max_chars else preview
            return "No text found in PDF"
        except Exception as e:
            logger.error(f"Error extracting preview: {str(e)}")
            return "Error extracting preview"
    
    def get_document_stats(self, chunks: List[Document]) -> dict:
        """Get statistics about the processed document."""
        if not chunks:
            return {}
        
        total_chars = sum(len(chunk.page_content) for chunk in chunks)
        avg_chunk_size = total_chars / len(chunks) if chunks else 0
        
        return {
            'total_chunks': len(chunks),
            'total_characters': total_chars,
            'average_chunk_size': avg_chunk_size,
            'source_file': chunks[0].metadata.get('source_file', 'Unknown')
        }
