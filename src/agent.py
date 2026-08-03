import logging
from typing import Dict, Any

from strands.models import BedrockModel
from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent

# -----------------------------
# Logger Configuration
# -----------------------------
logger = logging.getLogger("luxury-cars-agent")
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        "%Y-%m-%d %H:%M:%S"
    )
)
logger.addHandler(handler) #forçar pipeline 10

# -----------------------------
# System Prompt (Luxury Cars Expert)
# -----------------------------
SYSTEM_PROMPT = """
You are a Luxury Cars Expert AI Agent.

Scope:
- Luxury and exotic car brands (Ferrari, Lamborghini, Rolls-Royce, Bentley, Porsche, Aston Martin, Bugatti, McLaren, Maserati, etc.).
- Vehicle specifications (engine, horsepower, torque, 0-100 km/h, top speed, etc.).
- Exclusive features, technology, and craftsmanship of high-end vehicles.
- Buying, leasing, and ownership considerations for luxury cars.
- Maintenance, servicing, and care for premium vehicles.
- Automotive history and iconic luxury car models.
- Car comparisons and recommendations based on preferences and budget.
- News and trends in the luxury automotive market.

Rules:
- Answer clearly, accurately, and objectively.
- Prefer structured explanations and detailed breakdowns when helpful.
- Use examples and practical insights when they improve understanding.
- If a question is ambiguous, ask for clarification.
- If the question is outside luxury car topics, say so explicitly.
- Do NOT hallucinate specifications, prices, or technical data.
- Do NOT include chain-of-thought or internal reasoning.
- Respond in a sophisticated, knowledgeable, and professional tone.
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
      "prompt": "What makes the Bugatti Chiron so special?"
    }
    """
    user_prompt = payload.get("prompt")

    if not user_prompt:
        logger.warning("No prompt provided in payload.")
        user_prompt = "What makes the Bugatti Chiron so special?"

    logger.info(f"🚗 Luxury car question received: {user_prompt!r}")

    result = agent(user_prompt)

    return {
        "result": result.message
    }


if __name__ == "__main__":
    app.run()