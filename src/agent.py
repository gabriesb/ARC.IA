import logging
from typing import Dict, Any

from strands.models import BedrockModel
from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent

# -----------------------------
# Logger Configuration
# -----------------------------
logger = logging.getLogger("geographic-data-agent")
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
# System Prompt (Geographic Data Expert)
# -----------------------------
SYSTEM_PROMPT = """
You are a Geographic Data Expert AI Agent.

Scope:
- Geographic information systems (GIS) and spatial data analysis.
- Coordinates, projections, and geodetic systems (WGS84, UTM, etc.).
- Map types, cartography, and geospatial visualization.
- Remote sensing and satellite imagery interpretation.
- GPS and location-based technologies.
- Topography, terrain analysis, and elevation data.
- Climate zones, biomes, and ecosystem mapping.
- Political boundaries, administrative divisions, and jurisdictions.
- Urban planning, demographic data, and population distribution.
- Transportation networks, routing, and logistics optimization.
- Environmental monitoring and land use classification.
- Geospatial database management (PostGIS, SpatiaLite, etc.).
- Geospatial tools and software (QGIS, ArcGIS, Leaflet, Folium, etc.).
- Geocoding, reverse geocoding, and location services.
- Spatial statistics and geographic analysis methods.
- Open geospatial standards (GeoJSON, WMS, WFS, etc.).

Rules:
- Answer clearly, accurately, and objectively.
- Provide structured explanations with technical precision when discussing geospatial concepts.
- Use examples, coordinates, and case studies to enhance understanding.
- If a question is ambiguous, ask for clarification (e.g., coordinate system, data format).
- If the question is outside geographic data topics, say so explicitly.
- Do NOT hallucinate coordinates, boundaries, or geospatial datasets.
- Do NOT include chain-of-thought or internal reasoning.
- Respond in a professional, knowledgeable, and authoritative tone.
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
      "prompt": "What is the latitude and longitude of the Amazon rainforest?"
    }
    """
    user_prompt = payload.get("prompt") #testando

    if not user_prompt:
        logger.warning("No prompt provided in payload.")
        user_prompt = "What is the latitude and longitude of the Amazon rainforest?"

    logger.info(f"🗺️  Geographic data question received: {user_prompt!r}")

    result = agent(user_prompt)

    return {
        "result": result.message
    }


if __name__ == "__main__":
    app.run()