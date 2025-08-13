import os
import numpy as np
from typing import List, Union
import logging

# Try to import ML libraries, fallback if not available
try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False
    from .fallback_ai import FallbackEmbeddings

class EmbeddingManager:
    """Manages text embeddings using sentence-transformers"""
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
        self.model = None
        self.embedding_dim = None
        self._load_model()
    
    def _load_model(self):
        """Load the embedding model"""
        try:
            if HAS_SENTENCE_TRANSFORMERS:
                self.model = SentenceTransformer(self.model_name)
                # Get embedding dimension
                test_embedding = self.model.encode(["test"])
                self.embedding_dim = test_embedding.shape[1]
                logging.info(f"Loaded embedding model: {self.model_name} (dim: {self.embedding_dim})")
            else:
                # Use fallback implementation
                self.model = FallbackEmbeddings(self.model_name)
                self.embedding_dim = 384
                logging.warning(f"Using fallback embeddings - sentence-transformers not available")
        except Exception as e:
            logging.error(f"Error loading embedding model {self.model_name}: {str(e)}")
            # Use fallback as last resort
            self.model = FallbackEmbeddings(self.model_name)
            self.embedding_dim = 384
            logging.warning(f"Using fallback embeddings due to error: {str(e)}")
    
    def encode(self, texts: Union[str, List[str]], normalize: bool = True) -> np.ndarray:
        """
        Encode texts to embeddings
        
        Args:
            texts: Single text or list of texts to encode
            normalize: Whether to normalize embeddings
            
        Returns:
            numpy array of embeddings
        """
        if not self.model:
            raise ValueError("Embedding model not loaded")
        
        if isinstance(texts, str):
            texts = [texts]
        
        try:
            if HAS_SENTENCE_TRANSFORMERS and hasattr(self.model, 'encode'):
                # Using sentence-transformers
                embeddings = self.model.encode(
                    texts,
                    normalize_embeddings=normalize,
                    show_progress_bar=len(texts) > 100
                )
            else:
                # Using fallback implementation
                embeddings = self.model.encode(texts)
            return embeddings
        
        except Exception as e:
            logging.error(f"Error encoding texts: {str(e)}")
            raise
    
    def encode_batch(self, texts: List[str], batch_size: int = 32, normalize: bool = True) -> np.ndarray:
        """
        Encode texts in batches for better memory management
        
        Args:
            texts: List of texts to encode
            batch_size: Size of each batch
            normalize: Whether to normalize embeddings
            
        Returns:
            numpy array of embeddings
        """
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = self.encode(batch, normalize=normalize)
            all_embeddings.append(batch_embeddings)
        
        return np.vstack(all_embeddings)
    
    def similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score
        """
        # Ensure embeddings are 1D
        if embedding1.ndim > 1:
            embedding1 = embedding1.flatten()
        if embedding2.ndim > 1:
            embedding2 = embedding2.flatten()
        
        # Calculate cosine similarity
        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def find_most_similar(self, query_embedding: np.ndarray, 
                         candidate_embeddings: np.ndarray, 
                         top_k: int = 5) -> List[tuple]:
        """
        Find most similar embeddings to query
        
        Args:
            query_embedding: Query embedding vector
            candidate_embeddings: Array of candidate embeddings
            top_k: Number of top results to return
            
        Returns:
            List of (index, similarity_score) tuples
        """
        similarities = []
        
        for i, candidate in enumerate(candidate_embeddings):
            similarity = self.similarity(query_embedding, candidate)
            similarities.append((i, similarity))
        
        # Sort by similarity score (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model"""
        return self.embedding_dim
    
    def cluster_embeddings(self, embeddings: np.ndarray, n_clusters: int = 5):
        """
        Cluster embeddings using K-means
        
        Args:
            embeddings: Array of embeddings to cluster
            n_clusters: Number of clusters
            
        Returns:
            Cluster labels
        """
        try:
            from sklearn.cluster import KMeans
            
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            labels = kmeans.fit_predict(embeddings)
            
            return labels, kmeans.cluster_centers_
        
        except ImportError:
            logging.warning("scikit-learn not available for clustering")
            return None, None
        except Exception as e:
            logging.error(f"Error clustering embeddings: {str(e)}")
            return None, None
    
    def reduce_dimensionality(self, embeddings: np.ndarray, n_components: int = 2):
        """
        Reduce embedding dimensionality for visualization
        
        Args:
            embeddings: Array of embeddings
            n_components: Target number of dimensions
            
        Returns:
            Reduced embeddings
        """
        try:
            from sklearn.decomposition import PCA
            
            pca = PCA(n_components=n_components)
            reduced_embeddings = pca.fit_transform(embeddings)
            
            return reduced_embeddings, pca.explained_variance_ratio_
        
        except ImportError:
            logging.warning("scikit-learn not available for dimensionality reduction")
            return None, None
        except Exception as e:
            logging.error(f"Error reducing dimensionality: {str(e)}")
            return None, None

# Global embedding manager instance
_embedding_manager = None

def get_embedding_manager(model_name: str = None) -> EmbeddingManager:
    """Get or create global embedding manager instance"""
    global _embedding_manager
    
    if _embedding_manager is None or (model_name and model_name != _embedding_manager.model_name):
        _embedding_manager = EmbeddingManager(model_name)
    
    return _embedding_manager

def encode_texts(texts: Union[str, List[str]], model_name: str = None) -> np.ndarray:
    """Convenience function to encode texts"""
    manager = get_embedding_manager(model_name)
    return manager.encode(texts)

def calculate_similarity(text1: str, text2: str, model_name: str = None) -> float:
    """Convenience function to calculate similarity between two texts"""
    manager = get_embedding_manager(model_name)
    
    embeddings = manager.encode([text1, text2])
    return manager.similarity(embeddings[0], embeddings[1])
