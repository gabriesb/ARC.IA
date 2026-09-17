import json
import logging
import re
from typing import Any, Dict, Optional, Tuple

from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent, tool
from strands.models import BedrockModel

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
and `generate_diagram_from_terraform` tools.

CRITICAL RULE — the diagram is NEVER drawn by you (the language model):
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

Scope:
- AWS architecture diagrams generated from Terraform Infrastructure-as-Code.
- Explaining what a diagram/tool result contains (resources, categories,
  relationships) based strictly on the tool output.
- General questions about how this diagram-generation pipeline works.

Rules:
- Do NOT include chain-of-thought or internal reasoning in your replies.
- Respond in a clear, professional and concise tone.
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


# -----------------------------
# Agent (LLM only orchestrates tool calls / chats; never draws diagrams)
# -----------------------------
agent = Agent(
    model=bedrock_model,
    system_prompt=SYSTEM_PROMPT,
    tools=[generate_diagram_from_github, generate_diagram_from_terraform],
)


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
        return _diagram_response(diagram)

    if terraform_code:
        logger.info("Generating AWS architecture diagram from inline Terraform code")
        try:
            diagram = analyze_terraform_source(terraform_code, title=payload.get("title", "Architecture"))
        except DiagramServiceError as exc:
            logger.warning("Diagram generation failed for inline Terraform: %s", exc)
            return {"error": str(exc)}
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
    return {
        "result": summary,
        "diagram": {
            "format": "drawio",
            "xml": diagram["drawio_xml"],
            "download_url": diagram.get("download_url"),
        },
        "resources": diagram["resources"],
    }


if __name__ == "__main__":
    app.run()