"""
Fallback AI implementations when ML libraries are not available
"""
import logging
import random
import re
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from collections import Counter
import json
import os

logger = logging.getLogger(__name__)

class FallbackEmbeddings:
    """Simple fallback embedding implementation using TF-IDF like approach"""
    
    def __init__(self, model_name: str = "fallback-embeddings"):
        self.model_name = model_name
        self.vocab = {}
        self.idf_scores = {}
        self.embedding_dim = 384  # Match typical sentence transformer dimensions
        
    def encode(self, texts: List[str], **kwargs) -> np.ndarray:
        """Create simple embeddings using word frequency and TF-IDF like approach"""
        if not texts:
            return np.array([]).reshape(0, self.embedding_dim)
        
        # Build vocabulary if not exists
        if not self.vocab:
            self._build_vocab(texts)
        
        embeddings = []
        for text in texts:
            embedding = self._text_to_embedding(text)
            embeddings.append(embedding)
        
        return np.array(embeddings)
    
    def _build_vocab(self, texts: List[str]):
        """Build vocabulary from texts"""
        all_words = []
        word_doc_count = Counter()
        
        for text in texts:
            words = self._tokenize(text)
            unique_words = set(words)
            all_words.extend(words)
            for word in unique_words:
                word_doc_count[word] += 1
        
        # Build vocabulary with most common words
        word_freq = Counter(all_words)
        self.vocab = {word: idx for idx, (word, _) in enumerate(word_freq.most_common(10000))}
        
        # Calculate IDF scores
        total_docs = len(texts)
        for word, doc_count in word_doc_count.items():
            if word in self.vocab:
                self.idf_scores[word] = np.log(total_docs / (doc_count + 1))
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization"""
        # Convert to lowercase and extract words
        words = re.findall(r'\b\w+\b', text.lower())
        return words
    
    def _text_to_embedding(self, text: str) -> np.ndarray:
        """Convert text to embedding vector"""
        words = self._tokenize(text)
        
        if not words:
            return np.zeros(self.embedding_dim)
        
        # Create TF-IDF like vector
        word_counts = Counter(words)
        vector = np.zeros(self.embedding_dim)
        
        for word, count in word_counts.items():
            if word in self.vocab:
                idx = self.vocab[word] % self.embedding_dim
                tf = count / len(words)
                idf = self.idf_scores.get(word, 1.0)
                vector[idx] += tf * idf
        
        # Add some randomness for diversity
        noise = np.random.normal(0, 0.1, self.embedding_dim)
        vector = vector + noise
        
        # Normalize
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        
        return vector

class FallbackGenerator:
    """Simple fallback text generation using templates and patterns"""
    
    def __init__(self, model_name: str = "fallback-generator"):
        self.model_name = model_name
        self.templates = self._load_templates()
        
    def _load_templates(self) -> Dict[str, List[str]]:
        """Load explanation templates"""
        return {
            'trending_explanation': [
                "This topic is trending because it has gained significant attention recently.",
                "The popularity of this topic appears to be growing based on social media activity.",
                "This content is receiving increased engagement across multiple platforms.",
                "There's been a notable spike in discussions around this topic.",
                "This trend reflects current social media conversations and interests."
            ],
            'context_explanation': [
                "This topic relates to current events and social discussions.",
                "The subject appears to be part of broader cultural conversations.",
                "This content reflects ongoing themes in social media discourse.",
                "The topic has connections to recent developments in its field.",
                "This subject matter is relevant to current social and cultural trends."
            ],
            'general_explanation': [
                "This is a topic of interest that has been gaining attention.",
                "The content appears to be engaging to social media users.",
                "This subject matter is part of ongoing online conversations.",
                "The topic has relevance to current discussions and trends.",
                "This content reflects popular interests and concerns."
            ]
        }
    
    def generate(self, prompt: str, max_length: int = 200, **kwargs) -> str:
        """Generate text using templates and simple pattern matching"""
        try:
            # Analyze prompt to determine type
            prompt_lower = prompt.lower()
            
            if 'trending' in prompt_lower or 'viral' in prompt_lower:
                template_key = 'trending_explanation'
            elif 'context' in prompt_lower or 'background' in prompt_lower:
                template_key = 'context_explanation'
            else:
                template_key = 'general_explanation'
            
            # Select template
            templates = self.templates.get(template_key, self.templates['general_explanation'])
            base_response = random.choice(templates)
            
            # Extract topic from prompt
            topic = self._extract_topic(prompt)
            if topic:
                base_response = f"Regarding '{topic}': {base_response}"
            
            # Add some context based on prompt content
            if 'reddit' in prompt_lower:
                base_response += " This trend was observed in Reddit discussions."
            elif 'news' in prompt_lower or 'rss' in prompt_lower:
                base_response += " This appears in recent news coverage."
            
            # Truncate if too long
            if len(base_response) > max_length:
                base_response = base_response[:max_length-3] + "..."
            
            return base_response
            
        except Exception as e:
            logger.error(f"Error in fallback generation: {e}")
            return "Unable to generate explanation at this time."
    
    def _extract_topic(self, prompt: str) -> Optional[str]:
        """Extract topic from prompt"""
        # Look for quoted strings first
        quoted = re.search(r'"([^"]+)"', prompt)
        if quoted:
            return quoted.group(1)
        
        quoted = re.search(r"'([^']+)'", prompt)
        if quoted:
            return quoted.group(1)
        
        # Look for topic indicators
        topic_patterns = [
            r'(?:about|regarding|concerning|topic:?)\s+([^\s]+(?:\s+[^\s]+)*?)(?:\s+(?:is|was|has|that|because)|$)',
            r'(?:explain|analyze|discuss)\s+([^\s]+(?:\s+[^\s]+)*?)(?:\s+(?:is|was|has|that|because)|$)'
        ]
        
        for pattern in topic_patterns:
            match = re.search(pattern, prompt, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None

class FallbackVectorDB:
    """Simple fallback vector database using in-memory storage"""
    
    def __init__(self, collection_name: str = "fallback_collection"):
        self.collection_name = collection_name
        self.documents = []
        self.embeddings = []
        self.metadata = []
        self.ids = []
        self.embedding_model = FallbackEmbeddings()
    
    def add(self, documents: List[str], metadatas: List[Dict] = None, ids: List[str] = None):
        """Add documents to the collection"""
        if not documents:
            return
        
        # Generate embeddings
        new_embeddings = self.embedding_model.encode(documents)
        
        # Generate IDs if not provided
        if ids is None:
            start_id = len(self.documents)
            ids = [f"doc_{start_id + i}" for i in range(len(documents))]
        
        # Generate metadata if not provided
        if metadatas is None:
            metadatas = [{} for _ in documents]
        
        # Store everything
        self.documents.extend(documents)
        self.embeddings.extend(new_embeddings.tolist())
        self.metadata.extend(metadatas)
        self.ids.extend(ids)
    
    def query(self, query_texts: List[str], n_results: int = 5) -> Dict[str, Any]:
        """Query the collection for similar documents"""
        if not self.documents or not query_texts:
            return {
                'documents': [[]],
                'metadatas': [[]],
                'distances': [[]],
                'ids': [[]]
            }
        
        # Get query embeddings
        query_embeddings = self.embedding_model.encode(query_texts)
        
        results = {
            'documents': [],
            'metadatas': [],
            'distances': [],
            'ids': []
        }
        
        for query_embedding in query_embeddings:
            # Calculate similarities
            similarities = []
            for doc_embedding in self.embeddings:
                similarity = self._cosine_similarity(query_embedding, np.array(doc_embedding))
                similarities.append(1 - similarity)  # Convert to distance
            
            # Get top results
            if similarities:
                top_indices = np.argsort(similarities)[:n_results]
                
                query_docs = [self.documents[i] for i in top_indices]
                query_metadata = [self.metadata[i] for i in top_indices]
                query_distances = [similarities[i] for i in top_indices]
                query_ids = [self.ids[i] for i in top_indices]
            else:
                query_docs = []
                query_metadata = []
                query_distances = []
                query_ids = []
            
            results['documents'].append(query_docs)
            results['metadatas'].append(query_metadata)
            results['distances'].append(query_distances)
            results['ids'].append(query_ids)
        
        return results
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0
        
        return dot_product / (norm_a * norm_b)
    
    def count(self) -> int:
        """Get number of documents in collection"""
        return len(self.documents)
    
    def delete_collection(self):
        """Clear the collection"""
        self.documents = []
        self.embeddings = []
        self.metadata = []
        self.ids = []

def get_fallback_embeddings() -> FallbackEmbeddings:
    """Get fallback embeddings model"""
    return FallbackEmbeddings()

def get_fallback_generator() -> FallbackGenerator:
    """Get fallback text generator"""
    return FallbackGenerator()

def get_fallback_vectordb(collection_name: str = "fallback") -> FallbackVectorDB:
    """Get fallback vector database"""
    return FallbackVectorDB(collection_name)

# Module-level availability check
def check_ai_availability() -> Dict[str, bool]:
    """Check which AI components are available"""
    availability = {
        'transformers': False,
        'sentence_transformers': False,
        'chromadb': False,
        'torch': False,
        'fallback_mode': True
    }
    
    try:
        import transformers
        availability['transformers'] = True
    except ImportError:
        pass
    
    try:
        import sentence_transformers
        availability['sentence_transformers'] = True
    except ImportError:
        pass
    
    try:
        import chromadb
        availability['chromadb'] = True
    except ImportError:
        pass
    
    try:
        import torch
        availability['torch'] = True
    except ImportError:
        pass
    
    return availability

if __name__ == "__main__":
    # Test the fallback implementations
    print("Testing fallback AI implementations...")
    
    # Test embeddings
    embeddings = FallbackEmbeddings()
    texts = ["This is a test", "Another test sentence", "Final test text"]
    vectors = embeddings.encode(texts)
    print(f"Generated embeddings shape: {vectors.shape}")
    
    # Test generator
    generator = FallbackGenerator()
    prompt = "Explain why 'artificial intelligence' is trending"
    response = generator.generate(prompt)
    print(f"Generated response: {response}")
    
    # Test vector DB
    vectordb = FallbackVectorDB()
    vectordb.add(texts)
    results = vectordb.query(["test sentence"], n_results=2)
    print(f"Vector DB query results: {len(results['documents'][0])} documents found")
    
    # Check availability
    availability = check_ai_availability()
    print(f"AI component availability: {availability}")