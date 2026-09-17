import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from bedrock_agentcore import BedrockAgentCoreApp
from mcp.client.streamable_http import streamablehttp_client
from strands import Agent, tool
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient

from diagram_service import (
    DiagramServiceError,
    analyze_github_repository,
    analyze_terraform_source,
)

# -----------------------------
# Logger Configuration t
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
logger.addHandler(handler)

# -----------------------------
# System Prompt (AWS Architecture Diagram Agent)
# -----------------------------
SYSTEM_PROMPT = """
You are an AWS Architecture Diagram Agent.

Your job is to produce AWS architecture diagrams for a GitHub repository (or
for a Terraform snippet pasted by the user), using the `generate_diagram_from_github`
and `generate_diagram_from_terraform` tools, and to give AWS best-practice
improvement suggestions grounded in official AWS documentation.

CRITICAL RULE #1 — the diagram is NEVER drawn by you (the language model):
- The tools deterministically parse the real Terraform (.tf) source code and
  render the diagram as a draw.io (.drawio) XML file using the official AWS
  icon set. You must never invent, guess or hallucinate AWS resources,
  connections, or layouts.
- Your only job is to: (1) figure out which repository/ref/Terraform code the
  user is referring to, (2) call the right tool with the right arguments,
  and (3) summarize the tool's factual output (resource list, categories,
  counts) in plain language. If a tool returns an error, report the error
  instead of making up an answer.
- If you don't have enough information to call a tool (e.g. no repository
  and no Terraform code was given), ask the user for the GitHub
  "owner/repo" (and optionally a branch/tag/commit) or for the Terraform
  code to analyze. Do not proceed with assumptions.

CRITICAL RULE #2 — best-practice claims are NEVER made from memory alone:
- You have access to the official AWS documentation (including Well-Architected
  guidance) through MCP tools that search and read docs.aws.amazon.com.
- Whenever the user asks whether a service, feature or configuration choice
  is recommended, is a good/bad practice, or asks for improvement
  suggestions, you MUST call the documentation search/read tools first to
  verify the claim before answering, and you MUST cite the documentation
  URL(s) you used for every recommendation.
- If the documentation tools are unavailable or you cannot find a clear
  answer, say so honestly instead of guessing — never present an unverified
  opinion as an official AWS recommendation.

Scope:
- AWS architecture diagrams generated from Terraform Infrastructure-as-Code.
- Explaining what a diagram/tool result contains (resources, categories,
  relationships) based strictly on the tool output.
- AWS best-practice / Well-Architected recommendations, grounded in official
  documentation retrieved via the MCP documentation tools.
- General questions about how this diagram-generation pipeline works.

Rules:
- Do NOT include chain-of-thought or internal reasoning in your replies.
- Respond in a clear, professional and concise tone.
"""

# -----------------------------
# AWS Knowledge MCP Server (official AWS docs, incl. Well-Architected guidance)
# -----------------------------
# Public, unauthenticated, read-only MCP server maintained by AWS
# (https://github.com/awslabs/mcp/tree/main/src/aws-knowledge-mcp-server).
# Exposes tools such as `search_documentation` and `read_documentation` so the
# agent can ground best-practice answers in real docs.aws.amazon.com content
# instead of relying on the model's memory. `continue_on_error=True` means a
# network hiccup here only removes these tools for that turn — it never
# breaks diagram generation, which does not depend on them.
AWS_KNOWLEDGE_MCP_URL = os.environ.get("AWS_KNOWLEDGE_MCP_URL", "https://knowledge-mcp.global.api.aws")

aws_knowledge_mcp_client = MCPClient(
    lambda: streamablehttp_client(AWS_KNOWLEDGE_MCP_URL),
    continue_on_error=True,
    application_name="agentcore-easy-deploy",
)

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
# Deterministic diagram tools
# (all architecture content comes from these functions, never from the LLM)
# -----------------------------
@tool
def generate_diagram_from_github(owner: str, repo: str, ref: str = "") -> str:
    """Generates an AWS architecture diagram (draw.io XML) from the Terraform
    code found in a GitHub repository. This deterministically parses the
    real `.tf` files in the repo and maps each AWS resource to its official
    icon — it does not guess or invent the architecture.

    Args:
        owner: GitHub repository owner/organization (e.g. "my-org").
        repo: GitHub repository name (e.g. "my-infra-repo").
        ref: Optional branch, tag or commit SHA. Defaults to the repository's
            default branch when left empty.

    Returns:
        A JSON string with: repo, ref, resource_count, resources (list of
        {id, type, name, category}), files_scanned, drawio_xml (the full
        .drawio file content) and download_url (if diagram storage is
        configured).
    """
    try:
        result = analyze_github_repository(owner, repo, ref or None)
    except DiagramServiceError as exc:
        return json.dumps({"error": str(exc)})
    return json.dumps(result)


@tool
def generate_diagram_from_terraform(terraform_code: str, title: str = "Architecture") -> str:
    """Generates an AWS architecture diagram (draw.io XML) directly from a
    Terraform code snippet provided by the user (no GitHub access needed).
    Deterministically parses `resource` blocks and maps them to official AWS
    icons — it does not guess or invent the architecture.

    Args:
        terraform_code: Raw Terraform (HCL) source code containing one or
            more `resource "aws_..." "..." { ... }` blocks.
        title: Title to use for the generated diagram.

    Returns:
        A JSON string with: resource_count, resources, drawio_xml (the full
        .drawio file content) and download_url (if diagram storage is
        configured).
    """
    try:
        result = analyze_terraform_source(terraform_code, title=title)
    except DiagramServiceError as exc:
        return json.dumps({"error": str(exc)})
    return json.dumps(result)


# ------------------------------
# Agent (LLM only orchestrates tool calls / chats; never draws diagrams)
# ------------------------------
agent = Agent(
    model=bedrock_model,
    system_prompt=SYSTEM_PROMPT,
    tools=[generate_diagram_from_github, generate_diagram_from_terraform, aws_knowledge_mcp_client],
)


_ADVICE_RE = re.compile(
    r"melhor(ia|es\s+pr[aá]ticas)|boas\s+pr[aá]ticas|recomend|sugest[aã]o|"
    r"best[\s-]practice|good\s+practice|recommend|suggestion|should\s+i|is\s+this\s+(a\s+)?good",
    re.IGNORECASE,
)


def _wants_best_practice_review(text: str) -> bool:
    """Deterministic (regex) detection of advisory intent in the user's prompt.
    Does not decide *what* the answer is — only whether the LLM+MCP review
    step should run in addition to the deterministic diagram generation."""
    return bool(text) and bool(_ADVICE_RE.search(text))


def _review_best_practices(resources: List[Dict[str, Any]], user_question: str) -> str:
    """Asks the LLM to review the parsed resource types against official AWS
    documentation (via the AWS Knowledge MCP tools) and return grounded
    recommendations. This is the only place an LLM opinion is returned to the
    user — it never affects the diagram itself, which was already generated
    deterministically by `analyze_github_repository`/`analyze_terraform_source`."""
    resource_types = sorted({r["type"] for r in resources})
    listing = "\n".join(f"- {t}" for t in resource_types)
    prompt = (
        "Using the search_documentation and read_documentation tools (official AWS docs), "
        "review the following AWS resource types found in this project and answer the "
        "user's question below. Cite the documentation URL(s) you used for every "
        "recommendation. If a resource type has no specific best-practice concern, say so "
        "briefly instead of inventing one.\n\n"
        f"Resource types found in this project:\n{listing}\n\n"
        f"User's question: {user_question or 'Are there any AWS best-practice improvements to suggest?'}"
    )
    result = agent(prompt)
    return str(result.message)


# -----------------------------
# Fast-path repo extraction (regex, deterministic)
# -----------------------------
_GITHUB_URL_RE = re.compile(
    r"github\.com/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+?)(?:\.git)?(?:/(?:tree|blob)/(?P<ref>[\w./-]+))?(?:[/#?].*)?$",
    re.IGNORECASE,
)
_OWNER_REPO_RE = re.compile(r"(?<![\w/.])(?P<owner>[A-Za-z0-9][\w.-]*)/(?P<repo>[A-Za-z0-9][\w.-]*)(?![\w/])")


def _extract_github_repo(text: str) -> Optional[Tuple[str, str, Optional[str]]]:
    """Best-effort, deterministic extraction of an "owner/repo[@ref]" from
    free text. Prefers explicit github.com URLs; falls back to a bare
    "owner/repo" token. Returns None if nothing looks like a repo slug."""
    for match in _GITHUB_URL_RE.finditer(text):
        return match.group("owner"), match.group("repo"), match.group("ref")

    for match in _OWNER_REPO_RE.finditer(text):
        owner, repo = match.group("owner"), match.group("repo")
        # Skip obvious false positives such as version strings or ARNs.
        if "." in owner and owner.count(".") == owner.count("-") + 1:
            continue
        return owner, repo, None

    return None


# -----------------------------
# Entrypoint
# -----------------------------
@app.entrypoint
def invoke(payload: Dict[str, Any]):
    """
    Expected payload examples:
    {"github_repo": "owner/repo", "ref": "main"}
    {"prompt": "generate the architecture diagram for github.com/owner/repo"}
    {"terraform_code": "resource \\"aws_lambda_function\\" \\"fn\\" { ... }"}
    {"prompt": "what does this pipeline do?"}
    """
    user_prompt = payload.get("prompt") or ""
    ref = payload.get("ref") or payload.get("branch") or None
    terraform_code = payload.get("terraform_code")

    repo_slug = payload.get("github_repo") or payload.get("repo")
    owner = payload.get("owner")
    repo = payload.get("repo_name")

    if not (owner and repo) and repo_slug and "/" in repo_slug:
        owner, repo = repo_slug.split("/", 1)

    if not (owner and repo) and not terraform_code and user_prompt:
        extracted = _extract_github_repo(user_prompt)
        if extracted:
            owner, repo, extracted_ref = extracted
            ref = ref or extracted_ref

    # Deterministic fast path: if we can identify a repo or inline Terraform
    # code, generate the diagram directly (no LLM involved in the content).
    if owner and repo:
        logger.info("Generating AWS architecture diagram from GitHub repo %s/%s (ref=%s)", owner, repo, ref)
        try:
            diagram = analyze_github_repository(owner, repo, ref)
        except DiagramServiceError as exc:
            logger.warning("Diagram generation failed for %s/%s: %s", owner, repo, exc)
            return {"error": str(exc)}
        if _wants_best_practice_review(user_prompt):
            diagram["recommendations"] = _review_best_practices(diagram["resources"], user_prompt)
        return _diagram_response(diagram)

    if terraform_code:
        logger.info("Generating AWS architecture diagram from inline Terraform code")
        try:
            diagram = analyze_terraform_source(terraform_code, title=payload.get("title", "Architecture"))
        except DiagramServiceError as exc:
            logger.warning("Diagram generation failed for inline Terraform: %s", exc)
            return {"error": str(exc)}
        if _wants_best_practice_review(user_prompt):
            diagram["recommendations"] = _review_best_practices(diagram["resources"], user_prompt)
        return _diagram_response(diagram)

    # No repo/Terraform detected: let the conversational agent (with the same
    # deterministic tools available) ask for clarification or answer
    # general questions. The LLM still cannot draw a diagram itself — it can
    # only call the tools above, which are the only source of truth.
    if not user_prompt:
        logger.warning("No prompt, repo or terraform_code provided in payload.")
        user_prompt = (
            "I don't have a GitHub repository or Terraform code to analyze yet. "
            "Please ask the user for one."
        )

    logger.info("Falling back to conversational agent: %r", user_prompt)
    result = agent(user_prompt)

    return {"result": result.message}


def _diagram_response(diagram: Dict[str, Any]) -> Dict[str, Any]:
    resource_lines = "\n".join(
        f"- {r['type']} \"{r['name']}\" ({r['category']})" for r in diagram["resources"]
    )
    summary = (
        f"Analyzed {diagram.get('repo') or 'the provided Terraform code'} "
        f"({diagram.get('ref') or 'inline'}): found {diagram['resource_count']} AWS resource(s) "
        f"across {len(diagram['files_scanned'])} Terraform file(s).\n\n{resource_lines}"
    )
    response = {
        "result": summary,
        "diagram": {
            "format": "drawio",
            "xml": diagram["drawio_xml"],
            "download_url": diagram.get("download_url"),
        },
        "resources": diagram["resources"],
    }
    if diagram.get("recommendations"):
        response["recommendations"] = diagram["recommendations"]
    return response


if __name__ == "__main__":
    app.run()