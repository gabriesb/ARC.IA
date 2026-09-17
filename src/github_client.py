"""
Minimal GitHub REST API client used to read repository source code so the
agent can analyze real Infrastructure-as-Code files (Terraform/CloudFormation)
instead of guessing an architecture.

Only read-only endpoints are used (git trees + contents). No write access is
ever requested.
"""
import base64
import logging
import os
from typing import Dict, List, Optional

import requests

logger = logging.getLogger("geographic-data-agent")

GITHUB_API_URL = os.environ.get("GITHUB_API_URL", "https://api.github.com")
REQUEST_TIMEOUT = 15


class GitHubClientError(Exception):
    pass


def _get_token() -> Optional[str]:
    """
    Resolves the GitHub token, preferring AWS Secrets Manager (referenced via
    GITHUB_TOKEN_SECRET_ARN) and falling back to a plain GITHUB_TOKEN env var
    for local development. Returns None for unauthenticated (public repo,
    rate-limited) access.
    """
    secret_arn = os.environ.get("GITHUB_TOKEN_SECRET_ARN")
    if secret_arn:
        try:
            import boto3

            client = boto3.client("secretsmanager")
            response = client.get_secret_value(SecretId=secret_arn)
            return response.get("SecretString")
        except Exception:  # pragma: no cover - defensive, falls back below
            logger.exception("Failed to read GitHub token from Secrets Manager (%s)", secret_arn)

    return os.environ.get("GITHUB_TOKEN")


def _session() -> requests.Session:
    session = requests.Session()
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = _get_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    session.headers.update(headers)
    return session


def get_default_branch(owner: str, repo: str) -> str:
    session = _session()
    resp = session.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}", timeout=REQUEST_TIMEOUT)
    if resp.status_code != 200:
        raise GitHubClientError(f"Could not read repository {owner}/{repo} (HTTP {resp.status_code}): {resp.text[:300]}")
    return resp.json().get("default_branch", "main")


def list_repo_tree(owner: str, repo: str, ref: str) -> List[str]:
    """Returns the list of file paths (recursively) in the given ref."""
    session = _session()
    resp = session.get(
        f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/trees/{ref}",
        params={"recursive": "1"},
        timeout=REQUEST_TIMEOUT,
    )
    if resp.status_code != 200:
        raise GitHubClientError(
            f"Could not list files for {owner}/{repo}@{ref} (HTTP {resp.status_code}): {resp.text[:300]}"
        )
    data = resp.json()
    if data.get("truncated"):
        logger.warning("GitHub tree for %s/%s@%s was truncated (very large repo)", owner, repo, ref)
    return [item["path"] for item in data.get("tree", []) if item.get("type") == "blob"]


def get_file_content(owner: str, repo: str, path: str, ref: str) -> str:
    """Fetches a single file's text content (decoded from base64)."""
    session = _session()
    resp = session.get(
        f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents/{path}",
        params={"ref": ref},
        timeout=REQUEST_TIMEOUT,
    )
    if resp.status_code != 200:
        raise GitHubClientError(
            f"Could not read {path} from {owner}/{repo}@{ref} (HTTP {resp.status_code}): {resp.text[:300]}"
        )
    payload = resp.json()
    content = payload.get("content", "")
    encoding = payload.get("encoding", "base64")
    if encoding != "base64":
        raise GitHubClientError(f"Unsupported encoding '{encoding}' for {path}")
    return base64.b64decode(content).decode("utf-8", errors="replace")


def fetch_iac_files(owner: str, repo: str, ref: str, max_files: int = 60) -> Dict[str, str]:
    """
    Walks the repository tree and downloads the content of every Terraform
    file (.tf / .tf.json) found, up to `max_files` (safety limit to avoid
    excessive API calls on huge monorepos).
    """
    from terraform_parser import is_terraform_file

    paths = [p for p in list_repo_tree(owner, repo, ref) if is_terraform_file(p)]
    paths = paths[:max_files]

    files: Dict[str, str] = {}
    for path in paths:
        try:
            files[path] = get_file_content(owner, repo, path, ref)
        except GitHubClientError:
            logger.exception("Skipping unreadable file %s", path)
    return files
