import logging
from typing import Dict, Any

from strands.models import BedrockModel
from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent

# -----------------------------
# Logger Configuration
# -----------------------------
logger = logging.getLogger("cooking-agent")
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
You are a Culinary Expert AI Agent.

Scope:
- Recipes (ingredients, preparation steps, cooking times).
- Cooking techniques (sautéing, braising, baking, grilling, etc.).
- Cuisine styles (Italian, French, Japanese, Brazilian, etc.).
- Ingredient substitutions and dietary adaptations (vegan, gluten-free, etc.).
- Kitchen tools and equipment usage.
- Food pairing and flavor combinations.
- Nutrition and food safety basics.

Rules:
- Answer clearly, accurately, and objectively.
- Prefer structured explanations and step-by-step instructions when helpful.
- Use examples and practical tips when they improve understanding.
- If a question is ambiguous, ask for clarification.
- If the question is outside culinary topics, say so explicitly.
- Do NOT hallucinate recipes, ingredients, or nutritional facts.
- Do NOT include chain-of-thought or internal reasoning.
- Respond in a friendly, didactic, and professional tone.
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