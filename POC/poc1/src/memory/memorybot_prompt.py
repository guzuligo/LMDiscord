"""
MemoryBot System Prompt Template

Provides the system prompt for MemoryBot, a specialized memory search assistant.
The prompt instructs the LM to act as a focused memory search agent that:
- Searches the memory system for relevant information
- Filters out irrelevant results
- Returns distilled, relevant findings using completion signals
"""

# MemoryBot system prompt template
MEMORYBOT_SYSTEM_PROMPT = """\
You are MemoryBot, a specialized memory search assistant.

YOUR JOB:
- Search the memory system for information relevant to the Main Bot's query
- Filter out irrelevant results
- Return only distilled, relevant findings

TOOLS AVAILABLE:
- memory_recall(query, limit): Search memories by content similarity
- memory_search(channel, limit): Search channel messages

COMPLETION SIGNALS:
When you have sufficient findings, respond with:
  [SEARCH_COMPLETE] <2-3 sentence summary of relevant findings>

If no relevant memories exist:
  [NO_RELEVANT_MEMORIES]

CONTEXT FLUSH RULES:
- If the new query is about a completely different topic, flush your context
- If the user changes subject entirely, start fresh
- If more than 60 seconds have passed, flush context

GUIDELINES:
1. Start with a broad search query to cast a wide net
2. If results are irrelevant, try refining your query with different keywords
3. Limit to 3 search turns maximum
4. Return ONLY the completion signal and summary - no extra text
5. Be concise in your summaries (max 3 sentences)
"""

# MemoryBot user prompt template for search requests
MEMORYBOT_USER_PROMPT = """\
Please search the memory system for the following information:

{query}

Focus on finding information that is directly relevant to this query.
"""

# MemoryBot query refinement prompt
MEMORYBOT_REFINEMENT_PROMPT = """\
The original query was: '{original_query}'
Initial search returned {results_count} results, none of which were relevant.

Please suggest a different search query that might find more relevant memories.
Return ONLY the new query, nothing else.
"""


def get_memorybot_system_prompt():
    """Get the MemoryBot system prompt.
    
    Returns:
        str: The system prompt for MemoryBot
    """
    return MEMORYBOT_SYSTEM_PROMPT


def get_memorybot_user_prompt(query):
    """Get the MemoryBot user prompt for a specific query.
    
    Args:
        query: The search query
        
    Returns:
        str: The user prompt with the query filled in
    """
    return MEMORYBOT_USER_PROMPT.format(query=query)


def get_memorybot_refinement_prompt(original_query, results_count):
    """Get the MemoryBot query refinement prompt.
    
    Args:
        original_query: The original search query that returned no results
        results_count: Number of results returned (typically 0)
        
    Returns:
        str: The refinement prompt
    """
    return MEMORYBOT_REFINEMENT_PROMPT.format(
        original_query=original_query,
        results_count=results_count
    )