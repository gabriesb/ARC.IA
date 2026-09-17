"""
Orchestrates the deterministic diagram-generation pipeline:

    GitHub repo (or raw Terraform text)
        -> terraform_parser (parse resources/edges)
        -> drawio_builder (render AWS4 icons as .drawio XML)
        -> (optional) upload to S3 and return a presigned URL

No LLM is involved in any of these steps. The Strands agent (agent.py) only
decides *when* to call these functions based on the user's prompt; the
architecture content itself is 100% derived from the actual IaC source code.
"""
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional

from aws_icon_map import NON_VISUAL_RESOURCE_TYPES, resolve_icon
from drawio_builder import build_drawio_xml
from github_client import GitHubClientError, fetch_iac_files, get_default_branch
from terraform_parser import TFResource, parse_terraform_files

logger = logging.getLogger("geographic-data-agent")

DIAGRAM_BUCKET_NAME = os.environ.get("DIAGRAM_BUCKET_NAME")


class DiagramServiceError(Exception):
    pass


def _summarize_resources(resources: List[TFResource]) -> List[Dict[str, str]]:
    summary = []
    for res in resources:
        if res.tf_type in NON_VISUAL_RESOURCE_TYPES:
            continue
        icon_spec = resolve_icon(res.tf_type)
        summary.append(
            {
                "id": res.id,
                "type": res.tf_type,
                "name": res.tf_name,
                "category": icon_spec.category,
                "source_file": res.source_file,
            }
        )
    return summary


def _maybe_upload_to_s3(xml: str, key_prefix: str) -> Optional[str]:
    """Uploads the generated .drawio file to S3 (if DIAGRAM_BUCKET_NAME is
    configured) and returns a presigned download URL valid for 1 hour."""
    if not DIAGRAM_BUCKET_NAME:
        return None
    try:
        import boto3

        s3 = boto3.client("s3")
        key = f"{key_prefix}/{uuid.uuid4().hex}.drawio"
        s3.put_object(
            Bucket=DIAGRAM_BUCKET_NAME,
            Key=key,
            Body=xml.encode("utf-8"),
            ContentType="application/xml",
        )
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": DIAGRAM_BUCKET_NAME, "Key": key},
            ExpiresIn=3600,
        )
    except Exception:  # pragma: no cover - defensive, diagram still usable inline
        logger.exception("Failed to upload diagram to S3 bucket %s", DIAGRAM_BUCKET_NAME)
        return None


def analyze_github_repository(owner: str, repo: str, ref: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetches every Terraform file from the given GitHub repository/ref,
    deterministically parses the AWS resources declared in it, and renders
    a draw.io diagram using the real AWS icon set.
    """
    owner = owner.strip().strip("/")
    repo = repo.strip().strip("/")

    try:
        resolved_ref = ref or get_default_branch(owner, repo)
        files = fetch_iac_files(owner, repo, resolved_ref)
    except GitHubClientError as exc:
        raise DiagramServiceError(str(exc)) from exc

    if not files:
        raise DiagramServiceError(
            f"No Terraform (.tf) files were found in {owner}/{repo}@{ref or 'default branch'}. "
            "Only Terraform-based repositories are supported today."
        )

    resources, edges = parse_terraform_files(files)
    if not resources:
        raise DiagramServiceError(
            f"Found {len(files)} Terraform file(s) in {owner}/{repo}, but no `resource` blocks could be parsed."
        )

    title = f"{owner}/{repo}"
    xml = build_drawio_xml(resources, edges, title=title)
    download_url = _maybe_upload_to_s3(xml, key_prefix=f"{owner}-{repo}")

    return {
        "repo": title,
        "ref": resolved_ref,
        "files_scanned": list(files.keys()),
        "resources": _summarize_resources(resources),
        "resource_count": len(_summarize_resources(resources)),
        "drawio_xml": xml,
        "download_url": download_url,
    }


def analyze_terraform_source(terraform_code: str, title: str = "Architecture") -> Dict[str, Any]:
    """Same pipeline as `analyze_github_repository`, but for Terraform code
    pasted directly by the user instead of fetched from GitHub."""
    resources, edges = parse_terraform_files({"input.tf": terraform_code})
    if not resources:
        raise DiagramServiceError("No Terraform `resource` blocks were found in the provided code.")

    xml = build_drawio_xml(resources, edges, title=title)
    download_url = _maybe_upload_to_s3(xml, key_prefix="inline-" + str(int(time.time())))

    return {
        "repo": None,
        "ref": None,
        "files_scanned": ["input.tf"],
        "resources": _summarize_resources(resources),
        "resource_count": len(_summarize_resources(resources)),
        "drawio_xml": xml,
        "download_url": download_url,
    }
