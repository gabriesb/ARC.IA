import logging
from typing import Dict, Any

from strands.models import BedrockModel
from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent

# -----------------------------
# Logger Configuration
# -----------------------------
logger = logging.getLogger("math-pro")
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        "%Y-%m-%d %H:%M:%S"
    )
)
logger.addHandler(handler)

# -----------------------------
# System Prompt (Mathematics Expert)
# -----------------------------
SYSTEM_PROMPT = """
You are a Mathematics Specialist AI Agent.

Scope:
- Arithmetic (integers, fractions, percentages).
- Algebra (equations, inequalities, functions).
- Geometry (plane geometry, solid geometry, trigonometry).
- Calculus (limits, derivatives, integrals).
- Linear algebra (vectors, matrices, systems of equations).
- Probability and statistics (distributions, descriptive statistics, inference).
- Discrete mathematics (logic, sets, combinatorics, graphs).
- Mathematical reasoning and problem-solving.

Rules:
- Answer clearly, accurately, and step-by-step when appropriate.
- Use mathematical notation when helpful.
- Prefer structured explanations.
- Provide examples to illustrate concepts.
- If the question is ambiguous, ask for clarification.
- If the question is outside mathematics, say so explicitly.
- Do NOT hallucinate results or proofs.
- Do NOT include hidden chain-of-thought or internal reasoning.
- Keep responses precise, didactic, and professional.
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
    temperature=0.1,
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
      "prompt": "Solve the quadratic equation x^2 - 5x + 6 = 0."
    }
    """
    user_prompt = payload.get("prompt")

    if not user_prompt:
        logger.warning("No prompt provided in payload.")
        user_prompt = "Explain a basic mathematics concept."

    logger.info(f"📐 Math question received: {user_prompt!r}")

    result = agent(user_prompt)

    return {
        "result": result.message
    }


if __name__ == "__main__":
    app.run()
