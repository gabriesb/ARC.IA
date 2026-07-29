import logging
from typing import Dict, Any

from strands.models import BedrockModel
from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent

# -----------------------------
# Logger Configuration
# -----------------------------
logger = logging.getLogger("geo-agent")
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        "%Y-%m-%d %H:%M:%S"
    )
)
logger.addHandler(handler) #forçar pipeline 9

# -----------------------------
# System Prompt (Geography Expert)
# -----------------------------
SYSTEM_PROMPT = """
You are a Soccer Specialist AI Agent.

Scope:
- Soccer tactics (formations, strategies, set pieces).
- Player analysis (skills, strengths, weaknesses).
- Team management (transfers, training, squad rotation).
- Match analysis (statistics, performance metrics).
- Soccer history (famous matches, players, tournaments).

Rules:
- Answer clearly, accurately, and objectively.
- Prefer structured explanations when helpful.
- Use examples when they improve understanding.
- If a question is ambiguous, ask for clarification.
-- If the question is outside soccer, say so explicitly.
- Do NOT hallucinate facts or statistics.
- Do NOT include chain-of-thought or internal reasoning.
- Respond in a didactic, professional tone.
"""

# -----------------------------
# AgentCore App
# -----------------------------
app = BedrockAgentCoreApp()

# -----------------------------
# Bedrock Model
# -----------------------------
bedrock_model = BedrockModel(
    model_id="apac.amazon.nova-pro-v1:0",
    region_name="ap-south-1",
    temperature=0.2,
    max_tokens=2048,
)

# -----------------------------
# Agent
# -----------------------------
agent = Agent(
    model=bedrock_model,
    system_prompt=SYSTEM_PROMPT,
)

# -----------------------------
# Entrypoint
# -----------------------------
@app.entrypoint
def invoke(payload: Dict[str, Any]):
    """
    Expected payload example:
    {
      "prompt": "Explain why soccer matches are usually 90 minutes long."
    }
    """
    user_prompt = payload.get("prompt")

    if not user_prompt:
        logger.warning("No prompt provided in payload.")
        user_prompt = "Explain why soccer matches are usually 90 minutes long."

    logger.info(f"⚽ Soccer question received: {user_prompt!r}")

    result = agent(user_prompt)

    return {
        "result": result.message
    }


if __name__ == "__main__":
    app.run()