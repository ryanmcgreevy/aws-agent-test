"""
Strands agent definition.

This module defines the agent and exposes a `run()` function that the
FastAPI server (main.py) calls on each invocation.
"""

import os
from strands import Agent
from strands.models import BedrockModel

# Cross-region inference profile — provides higher availability than a
# single-region model ID. Requires Bedrock model access to be enabled.
MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6"
)

# Build the model. BedrockModel picks up credentials automatically from
# the environment (IAM role, ~/.aws/credentials, or AgentCore-injected creds).
model = BedrockModel(
    model_id=MODEL_ID,
    max_tokens=1024,  # Always set explicitly to avoid quota over-reservation
)

# Define the agent. Add tools to the `tools` list as your use case grows.
agent = Agent(
    model=model,
    system_prompt=(
        "You are a helpful assistant. "
        "Answer questions clearly and concisely."
    ),
    tools=[],  # Add strands_tools here, e.g.: from strands_tools import calculator
)


def run(user_input: str) -> str:
    """Invoke the agent with a user message and return the response as a string."""
    response = agent(user_input)
    return str(response)
