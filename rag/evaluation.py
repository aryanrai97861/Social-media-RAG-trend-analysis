import os
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
import logging
from datetime import datetime
import json
from .retriever import RAGRetriever
from .generator import RAGGenerator
from database.schema import get_engine

class RAGEvaluator:
    """Evaluation system for RAG performance"""
    
    def __init__(self, retriever: RAGRetriever, generator: RAGGenerator):
        self.retriever = retriever
        self.generator = generator
        self.evaluation_results = []
    
    def evaluate_retrieval(self, 
                          test_queries: List[Dict[str, Any]], 
                          k: int = 5) -> Dict[str, float]:
        """
        Evaluate retrieval performance
        
        Args:
            test_queries: List of test queries with expected relevant documents
            k: Number of documents to retrieve
            
        Returns:
            Dictionary of evaluation metrics
        """
        try:
            precision_scores = []
            recall_scores = []
            mrr_scores = []  # Mean Reciprocal Rank
            hit_rates = []
            
            for query_data in test_queries:
                query = query_data['query']
                relevant_docs = set(query_data.get('relevant_docs', []))
                
                # Retrieve documents
                results = self.retriever.search(query, k=k)
                retrieved_docs = set([r.get('id', '') for r in results])
                
                # Calculate metrics
                if retrieved_docs:
                    intersection = relevant_docs & retrieved_docs
                    
                    # Precision: relevant retrieved / total retrieved
                    precision = len(intersection) / len(retrieved_docs)
                    precision_scores.append(precision)
                    
                    # Recall: relevant retrieved / total relevant
                    if relevant_docs:
                        recall = len(intersection) / len(relevant_docs)
                        recall_scores.append(recall)
                    
                    # Hit rate: whether at least one relevant doc was retrieved
                    hit_rate = 1.0 if intersection else 0.0
                    hit_rates.append(hit_rate)
                    
                    # MRR: reciprocal of rank of first relevant document
                    mrr = 0.0
                    for i, result in enumerate(results):
                        if result.get('id', '') in relevant_docs:
                            mrr = 1.0 / (i + 1)
                            break
                    mrr_scores.append(mrr)
            
            metrics = {
                'precision_at_k': np.mean(precision_scores) if precision_scores else 0.0,
                'recall_at_k': np.mean(recall_scores) if recall_scores else 0.0,
                'hit_rate_at_k': np.mean(hit_rates) if hit_rates else 0.0,
                'mrr': np.mean(mrr_scores) if mrr_scores else 0.0,
                'num_queries': len(test_queries)
            }
            
            # Calculate F1 score
            if metrics['precision_at_k'] + metrics['recall_at_k'] > 0:
                metrics['f1_score'] = (2 * metrics['precision_at_k'] * metrics['recall_at_k']) / \
                                    (metrics['precision_at_k'] + metrics['recall_at_k'])
            else:
                metrics['f1_score'] = 0.0
            
            logging.info(f"Retrieval evaluation completed: {metrics}")
            return metrics
            
        except Exception as e:
            logging.error(f"Error evaluating retrieval: {str(e)}")
            return {'error': str(e)}
    
    def evaluate_generation(self, test_cases: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Evaluate generation quality
        
        Args:
            test_cases: List of test cases with query, context, and expected response
            
        Returns:
            Dictionary of evaluation metrics
        """
        try:
            scores = {
                'relevance': [],
                'coherence': [],
                'fluency': [],
                'completeness': []
            }
            
            for case in test_cases:
                query = case['query']
                context = case.get('context', '')
                expected = case.get('expected_response', '')
                
                # Generate response
                generated = self.generator.generate_explanation(query, context)
                
                # Simple heuristic scoring (in production, use more sophisticated metrics)
                relevance_score = self._calculate_relevance_score(query, generated, expected)
                coherence_score = self._calculate_coherence_score(generated)
                fluency_score = self._calculate_fluency_score(generated)
                completeness_score = self._calculate_completeness_score(generated, expected)
                
                scores['relevance'].append(relevance_score)
                scores['coherence'].append(coherence_score)
                scores['fluency'].append(fluency_score)
                scores['completeness'].append(completeness_score)
            
            # Calculate average scores
            avg_scores = {
                metric: np.mean(score_list) if score_list else 0.0 
                for metric, score_list in scores.items()
            }
            
            # Overall generation score
            avg_scores['overall_score'] = np.mean(list(avg_scores.values()))
            avg_scores['num_cases'] = len(test_cases)
            
            logging.info(f"Generation evaluation completed: {avg_scores}")
            return avg_scores
            
        except Exception as e:
            logging.error(f"Error evaluating generation: {str(e)}")
            return {'error': str(e)}
    
    def evaluate_end_to_end(self, test_queries: List[str]) -> Dict[str, Any]:
        """
        Evaluate end-to-end RAG performance
        
        Args:
            test_queries: List of test queries
            
        Returns:
            Comprehensive evaluation results
        """
        try:
            results = {
                'timestamp': datetime.now().isoformat(),
                'queries': [],
                'avg_retrieval_time': 0.0,
                'avg_generation_time': 0.0,
                'success_rate': 0.0
            }
            
            retrieval_times = []
            generation_times = []
            successful_queries = 0
            
            for query in test_queries:
                query_result = {
                    'query': query,
                    'retrieved_docs': 0,
                    'generated_response': '',
                    'retrieval_time': 0.0,
                    'generation_time': 0.0,
                    'success': False,
                    'error': None
                }
                
                try:
                    # Time retrieval
                    start_time = datetime.now()
                    retrieved_docs = self.retriever.search(query, k=3)
                    retrieval_time = (datetime.now() - start_time).total_seconds()
                    
                    query_result['retrieved_docs'] = len(retrieved_docs)
                    query_result['retrieval_time'] = retrieval_time
                    retrieval_times.append(retrieval_time)
                    
                    # Prepare context
                    context = "\n".join([doc.get('content', '')[:200] for doc in retrieved_docs])
                    
                    # Time generation
                    start_time = datetime.now()
                    generated_response = self.generator.generate_explanation(query, context)
                    generation_time = (datetime.now() - start_time).total_seconds()
                    
                    query_result['generated_response'] = generated_response
                    query_result['generation_time'] = generation_time
                    generation_times.append(generation_time)
                    
                    query_result['success'] = True
                    successful_queries += 1
                    
                except Exception as e:
                    query_result['error'] = str(e)
                    logging.error(f"Error processing query '{query}': {str(e)}")
                
                results['queries'].append(query_result)
            
            # Calculate averages
            results['avg_retrieval_time'] = np.mean(retrieval_times) if retrieval_times else 0.0
            results['avg_generation_time'] = np.mean(generation_times) if generation_times else 0.0
            results['success_rate'] = successful_queries / len(test_queries) if test_queries else 0.0
            
            logging.info(f"End-to-end evaluation completed: {successful_queries}/{len(test_queries)} successful")
            return results
            
        except Exception as e:
            logging.error(f"Error in end-to-end evaluation: {str(e)}")
            return {'error': str(e)}
    
    def _calculate_relevance_score(self, query: str, generated: str, expected: str = "") -> float:
        """Calculate relevance score using simple heuristics"""
        try:
            # Simple keyword overlap score
            query_words = set(query.lower().split())
            generated_words = set(generated.lower().split())
            
            overlap = query_words & generated_words
            relevance = len(overlap) / len(query_words) if query_words else 0.0
            
            # Boost score if response contains expected content
            if expected:
                expected_words = set(expected.lower().split())
                expected_overlap = generated_words & expected_words
                expected_score = len(expected_overlap) / len(expected_words) if expected_words else 0.0
                relevance = (relevance + expected_score) / 2
            
            return min(relevance, 1.0)
            
        except Exception:
            return 0.5  # Default score
    
    def _calculate_coherence_score(self, text: str) -> float:
        """Calculate coherence score based on text structure"""
        try:
            if not text or len(text.strip()) < 10:
                return 0.0
            
            # Simple coherence heuristics
            sentences = text.split('.')
            valid_sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
            
            if not valid_sentences:
                return 0.0
            
            # Check for repetition
            unique_sentences = set(valid_sentences)
            repetition_penalty = len(unique_sentences) / len(valid_sentences)
            
            # Check average sentence length (not too short, not too long)
            avg_length = np.mean([len(s.split()) for s in valid_sentences])
            length_score = min(avg_length / 15, 1.0) if avg_length < 30 else 0.5
            
            coherence = (repetition_penalty + length_score) / 2
            return min(coherence, 1.0)
            
        except Exception:
            return 0.5
    
    def _calculate_fluency_score(self, text: str) -> float:
        """Calculate fluency score based on text quality"""
        try:
            if not text or len(text.strip()) < 5:
                return 0.0
            
            # Simple fluency checks
            score = 1.0
            
            # Penalize for incomplete sentences
            if not text.strip().endswith(('.', '!', '?')):
                score -= 0.2
            
            # Check for reasonable sentence structure
            sentences = [s.strip() for s in text.split('.') if s.strip()]
            if sentences:
                avg_words_per_sentence = np.mean([len(s.split()) for s in sentences])
                if avg_words_per_sentence < 3 or avg_words_per_sentence > 50:
                    score -= 0.3
            
            # Penalize excessive repetition of words
            words = text.lower().split()
            if words:
                word_freq = {}
                for word in words:
                    word_freq[word] = word_freq.get(word, 0) + 1
                
                most_common_freq = max(word_freq.values())
                if most_common_freq > len(words) / 4:  # If any word appears > 25% of the time
                    score -= 0.4
            
            return max(score, 0.0)
            
        except Exception:
            return 0.5
    
    def _calculate_completeness_score(self, generated: str, expected: str = "") -> float:
        """Calculate how complete the response is"""
        try:
            if not generated or len(generated.strip()) < 10:
                return 0.0
            
            # Base completeness on length and structure
            base_score = min(len(generated) / 100, 1.0)  # Assume 100 chars is reasonable minimum
            
            # Check if response addresses the question
            sentences = [s.strip() for s in generated.split('.') if s.strip()]
            if len(sentences) >= 2:  # At least 2 complete sentences
                base_score += 0.2
            
            # If expected response provided, compare coverage
            if expected:
                expected_words = set(expected.lower().split())
                generated_words = set(generated.lower().split())
                coverage = len(expected_words & generated_words) / len(expected_words) if expected_words else 0
                base_score = (base_score + coverage) / 2
            
            return min(base_score, 1.0)
            
        except Exception:
            return 0.5
    
    def create_evaluation_report(self, results: Dict[str, Any]) -> str:
        """Create a formatted evaluation report"""
        try:
            report = f"""
RAG System Evaluation Report
Generated: {results.get('timestamp', 'Unknown')}

=== PERFORMANCE METRICS ===
Success Rate: {results.get('success_rate', 0.0):.2%}
Average Retrieval Time: {results.get('avg_retrieval_time', 0.0):.3f}s
Average Generation Time: {results.get('avg_generation_time', 0.0):.3f}s

=== DETAILED RESULTS ===
"""
            
            if 'queries' in results:
                for i, query_result in enumerate(results['queries']):
                    status = "✅ SUCCESS" if query_result['success'] else "❌ FAILED"
                    report += f"""
Query {i+1}: {query_result['query'][:50]}...
Status: {status}
Retrieved Documents: {query_result['retrieved_docs']}
Retrieval Time: {query_result['retrieval_time']:.3f}s
Generation Time: {query_result['generation_time']:.3f}s
"""
                    if query_result.get('error'):
                        report += f"Error: {query_result['error']}\n"
            
            return report
            
        except Exception as e:
            return f"Error generating report: {str(e)}"
    
    def save_evaluation_results(self, results: Dict[str, Any], filepath: str):
        """Save evaluation results to file"""
        try:
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            logging.info(f"Evaluation results saved to {filepath}")
        except Exception as e:
            logging.error(f"Error saving evaluation results: {str(e)}")

def create_test_dataset() -> Tuple[List[Dict], List[str]]:
    """Create a basic test dataset for evaluation"""
    
    # Retrieval test cases
    retrieval_tests = [
        {
            'query': 'viral memes 2023',
            'relevant_docs': ['meme_timeline_2010s', 'culture_glossary']
        },
        {
            'query': 'social media trends analysis',
            'relevant_docs': ['social_movements_overview']
        },
        {
            'query': 'Reddit trending topics',
            'relevant_docs': ['culture_glossary']
        }
    ]
    
    # End-to-end test queries
    e2e_queries = [
        "What makes a topic go viral on social media?",
        "Explain the cultural significance of internet memes",
        "How do social movements spread online?",
        "What are the characteristics of trending content?",
        "Why do certain hashtags become popular?"
    ]
    
    return retrieval_tests, e2e_queries

def run_evaluation(retriever: RAGRetriever, generator: RAGGenerator) -> Dict[str, Any]:
    """Run complete evaluation suite"""
    evaluator = RAGEvaluator(retriever, generator)
    
    # Create test dataset
    retrieval_tests, e2e_queries = create_test_dataset()
    
    # Run evaluations
    retrieval_metrics = evaluator.evaluate_retrieval(retrieval_tests)
    e2e_results = evaluator.evaluate_end_to_end(e2e_queries)
    
    # Combine results
    full_results = {
        'retrieval_metrics': retrieval_metrics,
        'end_to_end_results': e2e_results,
        'timestamp': datetime.now().isoformat()
    }
    
    return full_results
