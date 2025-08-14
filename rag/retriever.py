import os
import logging
from typing import List, Dict, Any, Optional
import numpy as np

# Try to import ChromaDB, fallback if not available
from .fallback_ai import FallbackVectorDB
try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False
    from .fallback_ai import FallbackVectorDB

from .embeddings import get_embedding_manager

class RAGRetriever:
    """Retrieval component for RAG system using ChromaDB"""
    
    def __init__(self, chroma_path: str = None, embedding_model: str = None, collection_name: str = "social_context"):
        self.chroma_path = chroma_path or os.getenv('CHROMA_PATH', './data/chroma')
        self.embedding_model = embedding_model or os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
        self.collection_name = collection_name
        
        # Initialize embedding manager
        self.embedding_manager = get_embedding_manager(self.embedding_model)
        
        # Initialize ChromaDB client
        self.client = None
        self.collection = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize ChromaDB client and collection"""
        if not HAS_CHROMADB:
            raise RuntimeError("ChromaDB not installed, install with: pip install chromadb")

        os.makedirs(self.chroma_path, exist_ok=True)
        try:
            self.client = chromadb.PersistentClient(path=self.chroma_path)
            try:
                self.collection = self.client.get_collection(
                    name=self.collection_name,
                    embedding_function=None
                )
                logging.info(f"Loaded existing collection: {self.collection_name}")
            except Exception:
                # If not found or any error, create it
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    embedding_function=None
                )
                logging.info(f"Created new collection: {self.collection_name}")
        except Exception as e:
            logging.error(f"Chroma init failed: {e}")
            raise
    
    

    def add_documents(self, documents: List[Dict[str, Any]]):
        """
        Add documents to the vector database
        
        Args:
            documents: List of document dictionaries with keys:
                      - content: Text content
                      - metadata: Additional metadata (optional)
                      - id: Unique identifier (optional, will generate if not provided)
        """
        try:
            texts = []
            metadatas = []
            ids = []
            
            for i, doc in enumerate(documents):
                content = doc.get('content', '')
                if not content:
                    logging.warning(f"Empty content for document {i}, skipping")
                    continue
                
                texts.append(content)
                
                # Prepare metadata
                metadata = doc.get('metadata', {})
                # Ensure all metadata values are strings (ChromaDB requirement)
                metadata = {k: str(v) for k, v in metadata.items()}
                metadatas.append(metadata)
                
                # Generate ID if not provided
                doc_id = doc.get('id') or f"doc_{i}_{hash(content[:100])}"
                ids.append(str(doc_id))
            
            if not texts:
                logging.warning("No valid documents to add")
                return
            
            # Generate embeddings
            logging.info(f"Generating embeddings for {len(texts)} documents")
            embeddings = self.embedding_manager.encode(texts)
            
            # Add to ChromaDB
            self.collection.add(
                embeddings=embeddings.tolist(),
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            logging.info(f"Added {len(texts)} documents to collection {self.collection_name}")
        
        except Exception as e:
            logging.error(f"Error adding documents: {str(e)}")
            raise
    
    def search(self, query: str, k: int = 5, where: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Search for relevant documents
        
        Args:
            query: Search query text
            k: Number of results to return
            where: Metadata filters (optional)
            
        Returns:
            List of matching documents with metadata and scores
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_manager.encode([query])
            
            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=k,
                where=where
            )
            
            # Format results
            formatted_results = []
            
            if results['documents'] and results['documents'][0]:  # ChromaDB returns nested lists
                for i in range(len(results['documents'][0])):
                    result = {
                        'content': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {},
                        'distance': results['distances'][0][i] if results['distances'] and results['distances'][0] else 0,
                        'id': results['ids'][0][i] if results['ids'] and results['ids'][0] else None
                    }
                    
                    # Convert distance to similarity score (ChromaDB uses L2 distance)
                    result['similarity'] = 1 / (1 + result['distance'])
                    
                    formatted_results.append(result)
            
            logging.info(f"Found {len(formatted_results)} results for query: '{query[:50]}...'")
            return formatted_results
        
        except Exception as e:
            logging.error(f"Error searching: {str(e)}")
            return []
    
    def search_by_metadata(self, metadata_filter: Dict, k: int = 10) -> List[Dict[str, Any]]:
        """
        Search documents by metadata filters only
        
        Args:
            metadata_filter: Dictionary of metadata key-value pairs to filter by
            k: Number of results to return
            
        Returns:
            List of matching documents
        """
        try:
            results = self.collection.get(
                where=metadata_filter,
                limit=k
            )
            
            formatted_results = []
            if results['documents']:
                for i in range(len(results['documents'])):
                    result = {
                        'content': results['documents'][i],
                        'metadata': results['metadatas'][i] if results['metadatas'] else {},
                        'id': results['ids'][i] if results['ids'] else None,
                        'similarity': 1.0  # No similarity score for metadata-only search
                    }
                    formatted_results.append(result)
            
            return formatted_results
        
        except Exception as e:
            logging.error(f"Error searching by metadata: {str(e)}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection"""
        try:
            count = self.collection.count()
            return {
                'total_documents': count,
                'collection_name': self.collection_name,
                'embedding_model': self.embedding_model
            }
        except Exception as e:
            logging.error(f"Error getting collection stats: {str(e)}")
            return {'error': str(e)}
    
    def delete_documents(self, ids: List[str]):
        """Delete documents by IDs"""
        try:
            self.collection.delete(ids=ids)
            logging.info(f"Deleted {len(ids)} documents")
        except Exception as e:
            logging.error(f"Error deleting documents: {str(e)}")
            raise
    
    def update_documents(self, documents: List[Dict[str, Any]]):
        """Update existing documents"""
        try:
            texts = []
            metadatas = []
            ids = []
            
            for doc in documents:
                if 'id' not in doc:
                    raise ValueError("Document ID required for update")
                
                texts.append(doc['content'])
                metadata = {k: str(v) for k, v in doc.get('metadata', {}).items()}
                metadatas.append(metadata)
                ids.append(str(doc['id']))
            
            # Generate embeddings
            embeddings = self.embedding_manager.encode(texts)
            
            # Update in ChromaDB
            self.collection.update(
                ids=ids,
                embeddings=embeddings.tolist(),
                documents=texts,
                metadatas=metadatas
            )
            
            logging.info(f"Updated {len(documents)} documents")
        
        except Exception as e:
            logging.error(f"Error updating documents: {str(e)}")
            raise
    
    def get_similar_documents(self, document_id: str, k: int = 5) -> List[Dict[str, Any]]:
        """Find documents similar to a given document"""
        try:
            # Get the document
            doc_results = self.collection.get(ids=[document_id])
            
            if not doc_results['documents']:
                return []
            
            doc_content = doc_results['documents'][0]
            
            # Search for similar documents
            results = self.search(doc_content, k=k+1)  # +1 to exclude the original document
            
            # Filter out the original document
            similar_docs = [r for r in results if r['id'] != document_id]
            
            return similar_docs[:k]
        
        except Exception as e:
            logging.error(f"Error finding similar documents: {str(e)}")
            return []
    
    def clear_collection(self):
        """Clear all documents from the collection"""
        try:
            # Delete the collection and recreate it
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                embedding_function=None
            )
            logging.info(f"Cleared collection {self.collection_name}")
        except Exception as e:
            logging.error(f"Error clearing collection: {str(e)}")
            raise

    def hybrid_search(self, query: str, k: int = 5, metadata_boost: Dict = None) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining semantic similarity and metadata filtering
        
        Args:
            query: Search query
            k: Number of results
            metadata_boost: Metadata fields to boost relevance
            
        Returns:
            Ranked list of documents
        """
        try:
            # First, do semantic search
            semantic_results = self.search(query, k=k*2)  # Get more results for re-ranking
            
            # Apply metadata boosting if specified
            if metadata_boost and semantic_results:
                for result in semantic_results:
                    boost_score = 0
                    metadata = result.get('metadata', {})
                    
                    for boost_field, boost_value in metadata_boost.items():
                        if boost_field in metadata and metadata[boost_field] == str(boost_value):
                            boost_score += 0.1  # Boost relevance
                    
                    result['similarity'] += boost_score
                
                # Re-sort by updated similarity scores
                semantic_results.sort(key=lambda x: x['similarity'], reverse=True)
            
            return semantic_results[:k]
        
        except Exception as e:
            logging.error(f"Error in hybrid search: {str(e)}")
            return self.search(query, k)  # Fallback to regular search
