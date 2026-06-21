"""
Strands agent definition with Bedrock Knowledge Base integration.

This module defines the agent and exposes a `run()` function that the
FastAPI server (main.py) calls on each invocation.

The agent is configured to use a Bedrock Knowledge Base for semantic
search over document collections (RAG - Retrieval Augmented Generation).
"""

import os
from strands import Agent
from strands.models import BedrockModel
import boto3
from typing import Optional

# Cross-region inference profile — provides higher availability than a
# single-region model ID. Requires Bedrock model access to be enabled.
MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6"
)

# Bedrock Knowledge Base ID for RAG (optional).
# Set KNOWLEDGE_BASE_ID environment variable to enable knowledge base retrieval.
KNOWLEDGE_BASE_ID = os.environ.get("KNOWLEDGE_BASE_ID")

# Build the model. BedrockModel picks up credentials automatically from
# the environment (IAM role, ~/.aws/credentials, or AgentCore-injected creds).
model = BedrockModel(
    model_id=MODEL_ID,
    max_tokens=2048,  # Allow space for context + response
)

# Initialize Bedrock Agent Runtime client for knowledge base retrieval
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')


def retrieve_from_knowledge_base(query: str, max_results: int = 3) -> str:
    """
    Retrieve relevant documents from the Bedrock Knowledge Base.
    
    Args:
        query: The search query for semantic retrieval
        max_results: Maximum number of results to return
        
    Returns:
        String containing the concatenated retrieved documents
    """
    if not KNOWLEDGE_BASE_ID:
        return ""
    
    try:
        response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': max_results,
                    'overrideSearchType': 'SEMANTIC'
                }
            },
            text=query
        )
        
        # Concatenate retrieved documents into context
        context_parts = []
        for result in response.get('retrievalResults', []):
            # Include content with source reference for transparency
            content = result['content']['text']
            score = result.get('score', 0)
            context_parts.append(f"[Score: {score:.2f}]\n{content}")
        
        return "\n\n---\n\n".join(context_parts) if context_parts else ""
    except Exception as e:
        # Graceful degradation: log error but continue without context
        print(f"Error retrieving from knowledge base: {e}")
        return ""


# Define the agent. Add tools to the `tools` list as your use case grows.
agent = Agent(
    model=model,
    system_prompt=(
        "You are a helpful assistant with access to a knowledge base. "
        "When answering questions, use the provided context documents to "
        "give accurate, well-informed responses. "
        "If the context doesn't contain relevant information, say so clearly."
    ),
    tools=[],  # Add strands_tools here, e.g.: from strands_tools import calculator
)


def run(user_input: str) -> str:
    """
    Invoke the agent with a user message and return the response as a string.
    
    If a knowledge base is configured, this function retrieves relevant context
    via semantic search and includes it in the agent prompt (RAG pattern).
    
    Args:
        user_input: The user's question or message
        
    Returns:
        The agent's response as a string
    """
    # Retrieve context from knowledge base if available
    context = retrieve_from_knowledge_base(user_input)
    
    # If we have context from the knowledge base, augment the input
    if context:
        augmented_input = f"""
Based on the following documents from our knowledge base:

{context}

---

Please answer this question: {user_input}
"""
    else:
        augmented_input = user_input
    
    response = agent(augmented_input)
    return str(response)
