"""
Deterministic (non-LLM) Terraform HCL parser.

Extracts `resource "<type>" "<name>" { ... }` blocks from raw `.tf` source
and infers directed edges between resources by looking for Terraform
interpolation references (`<type>.<name>`) inside each block's body.

No AI/LLM is used anywhere in this module — the goal is that the same
Terraform code always produces the exact same list of resources/edges.
"""
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

_RESOURCE_BLOCK_RE = re.compile(r'resource\s+"([a-zA-Z0-9_]+)"\s+"([a-zA-Z0-9_-]+)"\s*\{')
_IAC_EXTENSIONS = (".tf", ".tf.json")


@dataclass(frozen=True)
class TFResource:
    tf_type: str
    tf_name: str
    source_file: str

    @property
    def id(self) -> str:
        return f"{self.tf_type}.{self.tf_name}"


def is_terraform_file(path: str) -> bool:
    return path.endswith(_IAC_EXTENSIONS)


def _find_matching_brace(text: str, open_brace_idx: int) -> int:
    """Given the index of an opening '{', returns the index of the matching
    closing '}' by tracking brace depth. Returns -1 if unbalanced."""
    depth = 0
    i = open_brace_idx
    length = len(text)
    while i < length:
        char = text[i]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _extract_resource_blocks(content: str, filename: str) -> List[Tuple[TFResource, str]]:
    """Returns a list of (TFResource, block_body_text) tuples found in a
    single Terraform file's raw content."""
    blocks: List[Tuple[TFResource, str]] = []
    for match in _RESOURCE_BLOCK_RE.finditer(content):
        tf_type, tf_name = match.group(1), match.group(2)
        open_idx = match.end() - 1
        close_idx = _find_matching_brace(content, open_idx)
        body = content[match.end():close_idx] if close_idx != -1 else content[match.end():]
        blocks.append((TFResource(tf_type, tf_name, filename), body))
    return blocks


def parse_terraform_files(files: Dict[str, str]) -> Tuple[List[TFResource], List[Tuple[str, str]]]:
    """
    Parses a set of Terraform files and returns:
      - resources: list of TFResource (type/name/source file), in the order
        they were declared.
      - edges: list of (from_id, to_id) tuples meaning "from_id references
        to_id" (e.g. an aws_lambda_function referencing an aws_dynamodb_table
        via `aws_dynamodb_table.my_table.arn`).

    `files` is a mapping of {relative_path: raw_file_content}. Only files
    ending in .tf / .tf.json are considered.
    """
    all_blocks: List[Tuple[TFResource, str]] = []
    for path, content in files.items():
        if not is_terraform_file(path):
            continue
        all_blocks.extend(_extract_resource_blocks(content, path))

    resources = [res for res, _ in all_blocks]

    # Sort candidate ids by length (desc) so overlapping ids (unlikely, but
    # e.g. "aws_lambda_function.foo" vs "aws_lambda_function.foo_bar") don't
    # cause a shorter id to falsely match inside a longer one first.
    known_ids = sorted({res.id for res in resources}, key=len, reverse=True)

    edges: List[Tuple[str, str]] = []
    seen_edges = set()
    for res, body in all_blocks:
        for other_id in known_ids:
            if other_id == res.id:
                continue
            if re.search(re.escape(other_id) + r"\b", body):
                edge = (res.id, other_id)
                if edge not in seen_edges:
                    seen_edges.add(edge)
                    edges.append(edge)

    return resources, edges
