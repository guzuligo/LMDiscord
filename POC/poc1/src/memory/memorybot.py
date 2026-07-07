"""
MemoryBot - Specialized memory search assistant with fresh isolated context.

MemoryBot is a sub-bot that handles memory search operations for the main bot.
It maintains a fresh isolated context to prevent the main conversation context
from being saturated with irrelevant memory results.

Architecture:
    Main Bot requests memory search → MemoryBot (fresh context) calls memory_recall
    → Memory System returns results → MemoryBot filters noise and distills findings
    → Main Bot receives only relevant info

Design Decisions:
    1. Name: MemoryBot
    2. Single vs Multiple: One shared MemoryBot per session
    3. Synchronous vs Async: Synchronous - Main Bot waits for response
    4. Fallback: If MemoryBot unavailable, Main Bot calls memory tools directly
"""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class MemoryBot:
    """Specialized memory search assistant with fresh isolated context.
    
    MemoryBot handles memory search operations by:
    1. Receiving search queries from the Main Bot
    2. Calling memory_recall with broad queries
    3. Filtering out irrelevant results
    4. Returning distilled, relevant findings
    """
    
    def __init__(self, memory_manager, lm_caller=None, max_search_turns=3):
        """Initialize MemoryBot.
        
        Args:
            memory_manager: MemoryManager instance for memory operations
            lm_caller: LMCaller instance for making LM calls (optional)
            max_search_turns: Maximum number of search turns (default: 3)
        """
        self.memory_manager = memory_manager
        self.lm_caller = lm_caller
        self.max_search_turns = max_search_turns
        self.current_context = None
        self.search_history = []
        self.topic = None
    
    def reset(self):
        """Reset MemoryBot state for a new search session."""
        self.current_context = None
        self.search_history = []
        self.topic = None
        logger.debug("MemoryBot reset")
    
    def search_memories(self, query, limit=10, user_id=None):
        """Search memories using the memory manager.
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            user_id: Optional user ID for per-user filtering
            
        Returns:
            list: List of memory results
        """
        logger.debug(f"MemoryBot searching memories: query='{query}', limit={limit}")
        results = self.memory_manager.memory_recall(query, limit=limit)
        logger.debug(f"MemoryBot found {len(results)} raw results")
        return results
    
    def filter_results(self, results, query, min_confidence=0.3):
        """Filter memory results to remove irrelevant findings.
        
        Args:
            results: List of memory results from memory_recall
            query: Original search query
            min_confidence: Minimum relevance score (0.0-1.0)
            
        Returns:
            list: Filtered results with relevance >= min_confidence
        """
        if not results:
            return []
        
        filtered = []
        for result in results:
            score = result.get('score', 0)
            if score >= min_confidence:
                filtered.append(result)
            else:
                logger.debug(f"MemoryBot filtering out low-score result: score={score}")
        
        logger.debug(f"MemoryBot filtered {len(results)} → {len(filtered)} results")
        return filtered
    
    def distill_results(self, results, query):
        """Distill filtered results into a concise summary.
        
        Args:
            results: List of filtered memory results
            query: Original search query
            
        Returns:
            str: Distilled summary of relevant findings
        """
        if not results:
            return "No relevant memories found."
        
        # Build a concise summary from relevant findings
        summary_parts = []
        for i, result in enumerate(results[:5]):  # Limit to top 5 results
            content = result.get('content', '')
            score = result.get('score', 0)
            summary_parts.append(f"- [{score:.0%}] {content}")
        
        summary = f"Found {len(results)} relevant memory(s):\n" + "\n".join(summary_parts)
        return summary
    
    def is_complete(self, last_response):
        """Check if the search is complete based on the last response.
        
        Args:
            last_response: The last response string from MemoryBot
            
        Returns:
            bool: True if search is complete
        """
        if not last_response:
            return False
        
        # Check for completion signals
        completion_signals = ['[SEARCH_COMPLETE]', '[SEARCH_DONE]', '[NO_RELEVANT_MEMORIES]']
        for signal in completion_signals:
            if signal in last_response:
                return True
        
        return False
    
    def detect_topic_mismatch(self, new_query, current_topic):
        """Detect if the new query is about a completely different topic.
        
        Args:
            new_query: The new search query
            current_topic: The current tracked topic
            
        Returns:
            bool: True if topic mismatch detected (should flush context)
        """
        if not current_topic:
            return False
        
        # Simple keyword/topic mismatch detection
        # In production, this could use more sophisticated NLP
        new_words = set(new_query.lower().split())
        topic_words = set(current_topic.lower().split())
        
        # If less than 30% overlap, consider it a mismatch
        if len(new_words) > 0 and len(topic_words) > 0:
            overlap = len(new_words & topic_words)
            overlap_ratio = overlap / max(len(new_words | topic_words), 1)
            if overlap_ratio < 0.3:
                logger.debug(f"MemoryBot topic mismatch detected: {overlap_ratio:.2f} overlap")
                return True
        
        return False
    
    def run_search(self, query, user_id=None, lm_context=None, channel_id=None):
        """Execute a complete memory search cycle.
        
        This is the main entry point that orchestrates the search:
        1. Set up context and topic
        2. Search memories
        3. Filter results
        4. Distill findings
        5. Optionally use LM to refine search
        
        Args:
            query: Search query string
            user_id: Optional user ID for per-user filtering
            lm_context: Optional LM context for multi-turn refinement
            channel_id: Optional channel ID for context
            
        Returns:
            str: Search result summary or completion signal
        """
        self.reset()
        self.topic = query.split()[0] if query else None
        
        results = self.search_memories(query, limit=10, user_id=user_id)
        filtered = self.filter_results(results, query)
        summary = self.distill_results(filtered, query)
        
        self.search_history.append({
            'query': query,
            'results_count': len(results),
            'filtered_count': len(filtered),
            'summary': summary
        })
        
        return f"[SEARCH_COMPLETE] {summary}"
    
    async def run_search_with_lm_refinement(self, query, user_id=None, 
                                            lm_context=None, channel_id=None,
                                            max_turns=3):
        """Execute a memory search with LM-based refinement.
        
        Uses the LM to analyze results and potentially refine the search
        in multiple turns for better accuracy.
        
        Args:
            query: Initial search query
            user_id: Optional user ID for per-user filtering
            lm_context: LM conversation context
            channel_id: Optional channel ID for context
            max_turns: Maximum number of refinement turns
            
        Returns:
            str: Final search result summary or completion signal
        """
        if not self.lm_caller:
            # Fallback to simple search if no LM caller
            return self.run_search(query, user_id=user_id)
        
        self.reset()
        self.topic = query.split()[0] if query else None
        
        current_query = query
        last_response = None
        
        for turn in range(max_turns):
            logger.debug(f"MemoryBot search turn {turn + 1}/{max_turns}: query='{current_query}'")
            
            # Search memories with current query
            results = self.search_memories(current_query, limit=10, user_id=user_id)
            
            # Check for completion signal in previous response
            if last_response and self.is_complete(last_response):
                break
            
            # Filter results
            filtered = self.filter_results(results, current_query)
            
            # Distill findings
            summary = self.distill_results(filtered, current_query)
            
            # Check if we have enough relevant findings
            if len(filtered) > 0:
                last_response = f"[SEARCH_COMPLETE] {summary}"
                self.search_history.append({
                    'turn': turn + 1,
                    'query': current_query,
                    'results_count': len(results),
                    'filtered_count': len(filtered),
                    'summary': summary
                })
                break
            else:
                # No relevant results - try refining the query via LM
                last_response = f"[NO_RELEVANT_MEMORIES] No relevant memories for: {current_query}"
                self.search_history.append({
                    'turn': turn + 1,
                    'query': current_query,
                    'results_count': len(results),
                    'filtered_count': 0,
                    'summary': last_response
                })
                
                # If this is not the last turn, try to refine the query
                if turn < max_turns - 1:
                    refined_query = await self._refine_query(current_query, results, lm_context)
                    if refined_query:
                        current_query = refined_query
                    else:
                        break
        
        return last_response or "[NO_RELEVANT_MEMORIES] No relevant memories found."
    
    async def _refine_query(self, original_query, results, lm_context):
        """Use LM to refine the search query based on initial results.
        
        Args:
            original_query: The original search query
            results: Initial search results (empty or irrelevant)
            lm_context: LM conversation context
            
        Returns:
            str: Refined query string, or None if refinement fails
        """
        if not lm_context:
            return None
        
        try:
            # Build a prompt for query refinement
            refinement_prompt = (
                f"The original query was: '{original_query}'\n"
                f"Initial search returned {len(results)} results, none of which were relevant.\n"
                f"Please suggest a different search query that might find more relevant memories.\n"
                f"Return ONLY the new query, nothing else."
            )
            
            # Add refinement prompt to context
            refined_context = list(lm_context) if lm_context else []
            refined_context.append({
                'role': 'user',
                'content': refinement_prompt
            })
            
            # Call LM for refinement
            response = await self.lm_caller.call(
                refined_context,
                channel_id=None,
                use_tool_calling=False
            )
            
            # Extract the refined query from response
            refined_query = response.get('content', '').strip() if isinstance(response, dict) else str(response).strip()
            
            if refined_query and len(refined_query) > 3:
                logger.debug(f"MemoryBot query refined: '{original_query}' → '{refined_query}'")
                return refined_query
            
        except Exception as e:
            logger.warning(f"MemoryBot query refinement failed: {e}")
        
        return None