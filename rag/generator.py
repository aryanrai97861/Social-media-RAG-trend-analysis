import os
import logging
from typing import List, Dict, Any, Optional

# Try to import ML libraries, fallback if not available
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
    import torch
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False
    from .fallback_ai import FallbackGenerator

class RAGGenerator:
    """Text generation component for RAG system"""
    
    def __init__(self, model_name: str = None, device: str = None):
        self.model_name = model_name or os.getenv('GEN_MODEL', 'google/flan-t5-base')
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        
        self.tokenizer = None
        self.model = None
        self.pipeline = None
        
        self._load_model()
    
    def _load_model(self):
        """Load the generation model"""
        try:
            if HAS_TRANSFORMERS:
                logging.info(f"Loading generation model: {self.model_name}")
                
                # Load tokenizer
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                
                # Load model
                self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)
                
                # Move to device
                if self.device == 'cuda' and torch.cuda.is_available():
                    self.model = self.model.to(self.device)
                
                # Create pipeline
                self.pipeline = pipeline(
                    "text2text-generation",
                    model=self.model,
                    tokenizer=self.tokenizer,
                    device=0 if self.device == 'cuda' else -1,
                    framework="pt"
                )
                
                logging.info(f"Successfully loaded model on {self.device}")
            else:
                # Use fallback implementation
                self.pipeline = FallbackGenerator(self.model_name)
                logging.warning(f"Using fallback text generation - transformers not available")
            
        except Exception as e:
            logging.error(f"Error loading generation model: {str(e)}")
            # Use fallback as last resort
            self.pipeline = FallbackGenerator(self.model_name)
            logging.warning(f"Using fallback text generation due to error: {str(e)}")
    
    def generate(self, 
                prompt: str, 
                max_length: int = 512,
                temperature: float = 0.7,
                num_beams: int = 4,
                do_sample: bool = True,
                top_k: int = 50,
                top_p: float = 0.95) -> str:
        """
        Generate text based on prompt
        
        Args:
            prompt: Input prompt
            max_length: Maximum length of generated text
            temperature: Sampling temperature
            num_beams: Number of beams for beam search
            do_sample: Whether to use sampling
            top_k: Top-k sampling parameter
            top_p: Top-p (nucleus) sampling parameter
            
        Returns:
            Generated text
        """
        try:
            if not self.pipeline:
                raise ValueError("Generation model not loaded")
            
            # Check if using transformers or fallback
            if HAS_TRANSFORMERS and hasattr(self.pipeline, '__call__') and self.tokenizer:
                # Using transformers pipeline
                result = self.pipeline(
                    prompt,
                    max_length=max_length,
                    temperature=temperature,
                    num_beams=num_beams,
                    do_sample=do_sample,
                    top_k=top_k,
                    top_p=top_p,
                    pad_token_id=self.tokenizer.eos_token_id
                )
                generated_text = result[0]['generated_text']
            else:
                # Using fallback generator
                generated_text = self.pipeline.generate(prompt, max_length=max_length)
            
            # Clean up the generated text
            generated_text = self._clean_generated_text(generated_text)
            
            return generated_text
            
        except Exception as e:
            logging.error(f"Error generating text: {str(e)}")
            return f"Error generating response: {str(e)}"
    
    def generate_explanation(self, 
                           query: str, 
                           context: str, 
                           max_length: int = 300) -> str:
        """
        Generate explanation based on query and context
        
        Args:
            query: User query
            context: Retrieved context information
            max_length: Maximum length of explanation
            
        Returns:
            Generated explanation
        """
        prompt = f"""Based on the following context, provide a clear and concise explanation for the query.

Context: {context[:1000]}

Query: {query}

Explanation:"""
        
        return self.generate(prompt, max_length=max_length, temperature=0.5)
    
    def generate_summary(self, text: str, max_length: int = 150) -> str:
        """
        Generate summary of text
        
        Args:
            text: Text to summarize
            max_length: Maximum length of summary
            
        Returns:
            Generated summary
        """
        prompt = f"Summarize the following text:\n\n{text[:1500]}\n\nSummary:"
        
        return self.generate(prompt, max_length=max_length, temperature=0.3)
    
    def generate_trend_analysis(self, 
                              topic: str, 
                              trend_data: Dict[str, Any], 
                              context: str = "") -> str:
        """
        Generate trend analysis explanation
        
        Args:
            topic: Trending topic
            trend_data: Trend statistics
            context: Additional context information
            
        Returns:
            Generated trend analysis
        """
        trend_score = trend_data.get('trend_score', 0)
        growth_rate = trend_data.get('growth_rate', 0)
        mentions = trend_data.get('current_count', 0)
        platform = trend_data.get('platform', 'social media')
        
        prompt = f"""Analyze the following trending topic:

Topic: {topic}
Platform: {platform}
Trend Score: {trend_score:.2f} standard deviations above normal
Growth Rate: {growth_rate:.1%}
Current Mentions: {mentions:,}

{f"Context: {context[:500]}" if context else ""}

Provide an analysis explaining why this topic is trending, its potential significance, and any relevant background information:"""
        
        return self.generate(prompt, max_length=400, temperature=0.6)
    
    def generate_content_warning(self, 
                                content: str, 
                                safety_flags: List[str]) -> str:
        """
        Generate content warning explanation
        
        Args:
            content: Content that triggered warnings
            safety_flags: List of safety concerns
            
        Returns:
            Content warning explanation
        """
        flags_text = ", ".join(safety_flags)
        
        prompt = f"""The following content has been flagged for: {flags_text}

Content sample: {content[:200]}...

Provide a brief, professional explanation of why this content may be concerning and what users should be aware of:"""
        
        return self.generate(prompt, max_length=200, temperature=0.3)
    
    def generate_cultural_context(self, 
                                 topic: str, 
                                 context_docs: List[Dict[str, Any]]) -> str:
        """
        Generate cultural context explanation
        
        Args:
            topic: Topic to explain
            context_docs: Retrieved context documents
            
        Returns:
            Cultural context explanation
        """
        context_text = ""
        for doc in context_docs[:3]:  # Use top 3 context documents
            content = doc.get('content', '')
            context_text += f"{content[:300]}...\n\n"
        
        prompt = f"""Based on the following cultural and historical context, explain the significance of "{topic}":

Context:
{context_text}

Provide a clear explanation of the cultural significance, historical background, or social context of this topic:"""
        
        return self.generate(prompt, max_length=350, temperature=0.5)
    
    def generate_comparative_analysis(self, 
                                    topics: List[str], 
                                    trend_data: List[Dict]) -> str:
        """
        Generate comparative analysis of multiple trending topics
        
        Args:
            topics: List of trending topics
            trend_data: Trend data for each topic
            
        Returns:
            Comparative analysis
        """
        comparison_text = ""
        for topic, data in zip(topics[:5], trend_data[:5]):  # Limit to 5 topics
            score = data.get('trend_score', 0)
            mentions = data.get('current_count', 0)
            comparison_text += f"- {topic}: {score:.1f}σ trend score, {mentions:,} mentions\n"
        
        prompt = f"""Compare and analyze the following trending topics:

{comparison_text}

Provide a comparative analysis explaining the relative significance and potential relationships between these trends:"""
        
        return self.generate(prompt, max_length=400, temperature=0.6)
    
    def _clean_generated_text(self, text: str) -> str:
        """Clean and format generated text"""
        # Remove common artifacts
        text = text.strip()
        
        # Remove repetitive endings
        if text.endswith('...'):
            text = text[:-3].strip()
        
        # Ensure proper sentence ending
        if text and not text.endswith(('.', '!', '?')):
            text += '.'
        
        return text
    
    def batch_generate(self, 
                      prompts: List[str], 
                      max_length: int = 256) -> List[str]:
        """
        Generate text for multiple prompts in batch
        
        Args:
            prompts: List of prompts
            max_length: Maximum length per generation
            
        Returns:
            List of generated texts
        """
        try:
            results = []
            
            # Process in smaller batches to manage memory
            batch_size = 4
            for i in range(0, len(prompts), batch_size):
                batch = prompts[i:i + batch_size]
                
                batch_results = self.pipeline(
                    batch,
                    max_length=max_length,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
                
                for result in batch_results:
                    generated = self._clean_generated_text(result['generated_text'])
                    results.append(generated)
            
            return results
            
        except Exception as e:
            logging.error(f"Error in batch generation: {str(e)}")
            return [f"Error generating response: {str(e)}" for _ in prompts]

# Global generator instance
_generator = None

def get_generator(model_name: str = None) -> RAGGenerator:
    """Get or create global generator instance"""
    global _generator
    
    if _generator is None or (model_name and model_name != _generator.model_name):
        _generator = RAGGenerator(model_name)
    
    return _generator

def generate_text(prompt: str, max_length: int = 256, model_name: str = None) -> str:
    """Convenience function to generate text"""
    generator = get_generator(model_name)
    return generator.generate(prompt, max_length=max_length)
