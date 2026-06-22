"""
Strands agent definition with Bedrock Knowledge Base integration.

This module defines the agent and exposes a `run()` function that the
FastAPI server (main.py) calls on each invocation.

The agent is configured to use a Bedrock Knowledge Base for semantic
search over document collections (RAG - Retrieval Augmented Generation).
"""

import logging
import os
from uuid import uuid4

import boto3
from strands import Agent
from strands.models import BedrockModel
from strands.session import FileSessionManager, S3SessionManager
from strands import tool
from strands.agent.conversation_manager import SummarizingConversationManager

logger = logging.getLogger(__name__)

# Cross-region inference profile — provides higher availability than a
# single-region model ID. Requires Bedrock model access to be enabled.
MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6"
)

# Bedrock Knowledge Base ID for RAG (optional).
# Set KNOWLEDGE_BASE_ID environment variable to enable knowledge base retrieval.
KNOWLEDGE_BASE_ID = os.environ.get("KNOWLEDGE_BASE_ID")

# Optional S3-backed session persistence.
SESSION_BUCKET_NAME = os.environ.get("SESSION_BUCKET_NAME")
SESSION_BUCKET_PREFIX = os.environ.get("SESSION_BUCKET_PREFIX", "sessions")
SESSION_REGION = os.environ.get("SESSION_BUCKET_REGION", os.environ.get("AWS_REGION", "us-east-1"))
# Local fallback storage used when SESSION_BUCKET_NAME is not configured.
LOCAL_SESSION_STORAGE_DIR = os.environ.get("LOCAL_SESSION_STORAGE_DIR", ".sessions")

# Build the model. BedrockModel picks up credentials automatically from
# the environment (IAM role, ~/.aws/credentials, or AgentCore-injected creds).
model = BedrockModel(
    model_id=MODEL_ID,
    max_tokens=2048,  # Allow space for context + response
)

# Initialize Bedrock Agent Runtime client for knowledge base retrieval
# Use us-east-1 region for managed knowledge bases
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name='us-east-1')


@tool
def access_RAG(query: str) -> str:
    """Access the Retrieval Augmented Generation (RAG) system. 
    This tool is used by the agent to retrieve relevant documents from the knowledge base based on the user's query, and returns the retrieved context as a string.
    This knowledge base contains information about college courses and requirements, and is used to provide accurate and informed responses to user questions. 
    The agent will call this tool with the user's query, and the tool will return relevant information from the knowledge base that the agent can then use to formulate its response.

    Args:
        query: The search query for semantic retrieval
    Returns:
        String containing the concatenated retrieved documents from the knowledge base relevant to the query. If no knowledge base is configured or if retrieval fails, returns an empty string.
    """
    return retrieve_from_knowledge_base(query)


def build_session_manager(session_id: str) -> S3SessionManager | FileSessionManager | None:
    """Create an S3 or file-backed session manager depending on runtime config."""
    if not SESSION_BUCKET_NAME:
        return FileSessionManager(session_id=session_id, storage_dir=LOCAL_SESSION_STORAGE_DIR)

    try:
        return S3SessionManager(
            session_id=session_id,
            bucket=SESSION_BUCKET_NAME,
            prefix=SESSION_BUCKET_PREFIX,
            region_name=SESSION_REGION,
        )
    except Exception as exc:  # pragma: no cover - keep the agent usable if S3 config is wrong
        logger.warning("Falling back to stateless mode because session manager setup failed: %s", exc)
        return None


def build_agent(session_manager: S3SessionManager | None = None) -> Agent:
    """Construct a Strands agent instance with the shared model and prompt."""
    return Agent(
        model=model,
        system_prompt=(
            "You are a helpful assistant with access to a knowledge base. "
            "When answering questions, use the provided context documents to "
            "give accurate, well-informed responses. "
            "If the context doesn't contain relevant information, try calling the access_RAG tool to retrieve more information. You may need to rephrase the question to get better retrieval results."
            "Your primary goal is to assist the user in answering questions about college courses and requirements, using the knowledge base to find relevant information."
        ),
        tools=[access_RAG],  # Add strands_tools here, e.g.: from strands_tools import calculator
        session_manager=session_manager,
        conversation_manager=SummarizingConversationManager(
            proactive_compression=True,
        ),
    )


def retrieve_from_knowledge_base(query: str, max_results: int = 3) -> str:
    """
    Retrieve relevant documents from the Bedrock Managed Knowledge Base.
    
    Args:
        query: The search query for semantic retrieval
        max_results: Maximum number of results to return
        
    Returns:
        String containing the concatenated retrieved documents
    """
    if not KNOWLEDGE_BASE_ID:
        return ""
    
    try:
        # For Managed Knowledge Bases, use retrievalQuery parameter (not text)
        response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            retrievalQuery={'text': query}
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


def run(user_input: str, session_id: str | None = None) -> tuple[str, str]:
    """
    Invoke the agent with a user message and return the response as a string.
    
    If a knowledge base is configured, this function retrieves relevant context
    via semantic search and includes it in the agent prompt (RAG pattern).
    
    Args:
        user_input: The user's question or message
        session_id: Optional caller-supplied session ID. When omitted, a new ID
            is generated so the caller can reuse it on the next turn.
        
    Returns:
        A tuple of (response_text, effective_session_id).
    """
    effective_session_id = session_id or uuid4().hex
    print(f"Running agent with session_id={effective_session_id} and user_input={user_input}")
    # Retrieve context from knowledge base if available
    context = retrieve_from_knowledge_base(user_input)

    session_manager = build_session_manager(effective_session_id)
    agent = build_agent(session_manager=session_manager)
    
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
    return str(response), effective_session_id
