"""
Deterministic draw.io (.drawio / diagrams.net) XML generator.

This is the core of the "no LLM draws the architecture" requirement: given a
list of parsed Terraform resources and edges, this module always produces
the exact same mxGraph XML — node positions, colors and icons are computed
with plain arithmetic (graph layering + sorting), not guessed by a model.

Layout strategy (all deterministic):
  1. Split resources into "connected" (part of at least one reference edge)
     and "isolated" (no relationship to anything else in the scanned code).
  2. Lay out the connected resources in columns using a longest-path DAG
     layering (a simplified Sugiyama layout): a resource that references
     another one is always placed to the left of what it references, so
     edges flow left-to-right instead of crossing the whole canvas.
  3. Isolated resources (e.g. unrelated bootstrap buckets) are rendered
     separately, below the main graph, grouped by category so they don't
     distort the dependency layout above.
  4. A color legend maps each category color used in the diagram.

Output is a complete `.drawio` file (an `<mxfile>` document) that opens
directly in diagrams.net / the draw.io VS Code extension, using the official
AWS4 icon stencils (`shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.*`).
"""
import time
import uuid
from typing import Dict, Iterable, List, Sequence, Set, Tuple
from xml.sax.saxutils import escape

from aws_icon_map import NON_VISUAL_RESOURCE_TYPES, category_color, resolve_icon
from terraform_parser import TFResource

NODE_SIZE = 68
COLUMN_WIDTH = 220
ROW_HEIGHT = 110
TOP_MARGIN = 70
LEFT_MARGIN = 40
SECTION_GAP = 90
LEGEND_SWATCH = 16
LEGEND_ROW_HEIGHT = 24

EDGE_STYLE = (
    "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#545B64;endArrow=block;"
    "exitX=1;exitY=0.5;exitDx=0;exitDy=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;"
)


def _safe_id(value: str) -> str:
    return "n_" + "".join(ch if ch.isalnum() else "_" for ch in value)


def _visible_resources(resources: Iterable[TFResource]) -> List[TFResource]:
    return [r for r in resources if r.tf_type not in NON_VISUAL_RESOURCE_TYPES]


def _sort_key(res: TFResource) -> Tuple[str, str]:
    return (resolve_icon(res.tf_type).category, res.tf_name)


def _compute_ranks(node_ids: Set[str], edges: Sequence[Tuple[str, str]]) -> Dict[str, int]:
    """Longest-path DAG layering: rank(x) = 1 + max(rank(y) for every edge
    (y, x)), or 0 if x has no incoming edge. Processed with Kahn's algorithm
    so every node is only ranked once its dependencies are known; any
    residual (cyclic) resources are placed deterministically right after the
    deepest rank seen so far instead of being silently dropped."""
    outgoing: Dict[str, List[str]] = {n: [] for n in node_ids}
    indegree: Dict[str, int] = {n: 0 for n in node_ids}
    for src, dst in edges:
        if src not in node_ids or dst not in node_ids or src == dst:
            continue
        outgoing[src].append(dst)
        indegree[dst] += 1

    rank: Dict[str, int] = {}
    queue = sorted(n for n in node_ids if indegree[n] == 0)
    for n in queue:
        rank[n] = 0

    i = 0
    while i < len(queue):
        current = queue[i]
        i += 1
        for nxt in sorted(outgoing[current]):
            rank[nxt] = max(rank.get(nxt, 0), rank[current] + 1)
            indegree[nxt] -= 1
            if indegree[nxt] == 0 and nxt not in rank:
                queue.append(nxt)

    remaining = sorted(n for n in node_ids if n not in rank)
    if remaining:
        fallback_rank = (max(rank.values()) + 1) if rank else 0
        for n in remaining:
            rank[n] = fallback_rank

    return rank


def _node_cell(res: TFResource, x: int, y: int) -> str:
    icon_spec = resolve_icon(res.tf_type)
    color = category_color(icon_spec.category)
    label = escape(f"{icon_spec.label or res.tf_type}\n{res.tf_name}")
    style = (
        "sketch=0;outlineConnect=0;fontColor=#232F3E;gradientColor=none;"
        f"fillColor={color};strokeColor=none;dashed=0;verticalLabelPosition=bottom;"
        "verticalAlign=top;align=center;html=1;fontSize=11;fontStyle=0;aspect=fixed;"
        f"shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.{icon_spec.icon};"
    )
    return (
        f'<mxCell id="{_safe_id(res.id)}" value="{label}" style="{style}" '
        f'vertex="1" parent="1">'
        f'<mxGeometry x="{x}" y="{y}" width="{NODE_SIZE}" height="{NODE_SIZE}" as="geometry" />'
        f"</mxCell>"
    )


def _render_category_grid(resources: Sequence[TFResource], start_y: int) -> Tuple[List[str], Dict[str, str], int]:
    """Renders resources as columns grouped by category (used for resources
    with no dependency relationship to anything else, or as the fallback
    layout when the scanned code has no cross-references at all)."""
    cells: List[str] = []
    node_cell_id: Dict[str, str] = {}
    if not resources:
        return cells, node_cell_id, start_y

    groups: Dict[str, List[TFResource]] = {}
    for res in resources:
        groups.setdefault(resolve_icon(res.tf_type).category, []).append(res)
    for group in groups.values():
        group.sort(key=lambda r: r.tf_name)

    bottom_y = start_y
    for col_idx, category in enumerate(sorted(groups)):
        col_x = LEFT_MARGIN + col_idx * COLUMN_WIDTH
        color = category_color(category)
        cells.append(
            f'<mxCell id="grid_header_{start_y}_{col_idx}" value="{escape(category)}" '
            f'style="text;html=1;fontSize=13;fontStyle=1;align=center;fontColor={color};" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{col_x}" y="{start_y}" width="{NODE_SIZE + 60}" height="24" as="geometry" />'
            f"</mxCell>"
        )
        for row_idx, res in enumerate(groups[category]):
            node_y = start_y + 34 + row_idx * ROW_HEIGHT
            node_cell_id[res.id] = _safe_id(res.id)
            cells.append(_node_cell(res, col_x, node_y))
            bottom_y = max(bottom_y, node_y + NODE_SIZE)

    return cells, node_cell_id, bottom_y


def build_drawio_xml(
    resources: Sequence[TFResource],
    edges: Sequence[Tuple[str, str]],
    title: str = "AWS Architecture",
) -> str:
    """Builds a full `.drawio` (mxfile) XML document.

    Connected resources (linked by at least one Terraform reference) are
    laid out left-to-right by dependency depth, so arrows consistently flow
    forward instead of criss-crossing the canvas. Resources with no
    relationship to anything else are rendered in a separate category grid
    below, so they don't distort the dependency layout.

    `resources` / `edges` are the deterministic output of
    `terraform_parser.parse_terraform_files`.
    """
    visible = _visible_resources(resources)
    visible_ids = {res.id for res in visible}
    visible_edges = [(a, b) for a, b in edges if a in visible_ids and b in visible_ids and a != b]

    linked_ids = {n for edge in visible_edges for n in edge}
    connected = sorted((r for r in visible if r.id in linked_ids), key=_sort_key)
    isolated = sorted((r for r in visible if r.id not in linked_ids), key=_sort_key)

    cells: List[str] = []
    node_cell_id: Dict[str, str] = {}
    bottom_y = TOP_MARGIN
    rank_of: Dict[str, int] = {}

    if connected:
        rank_of = _compute_ranks({r.id for r in connected}, visible_edges)
        by_rank: Dict[int, List[TFResource]] = {}
        for res in connected:
            by_rank.setdefault(rank_of[res.id], []).append(res)

        for rank in sorted(by_rank):
            col_x = LEFT_MARGIN + rank * COLUMN_WIDTH
            column = sorted(by_rank[rank], key=_sort_key)
            for row_idx, res in enumerate(column):
                node_y = TOP_MARGIN + row_idx * ROW_HEIGHT
                node_cell_id[res.id] = _safe_id(res.id)
                cells.append(_node_cell(res, col_x, node_y))
                bottom_y = max(bottom_y, node_y + NODE_SIZE)

    if isolated:
        section_y = bottom_y + SECTION_GAP if connected else TOP_MARGIN
        if connected:
            cells.append(
                '<mxCell id="isolated_label" value="Other resources found in the repository (no direct dependency link)" '
                'style="text;html=1;fontSize=12;fontStyle=2;align=left;fontColor=#545B64;" '
                'vertex="1" parent="1">'
                f'<mxGeometry x="{LEFT_MARGIN}" y="{section_y - 26}" width="500" height="20" as="geometry" />'
                "</mxCell>"
            )
        grid_cells, grid_ids, section_bottom = _render_category_grid(isolated, section_y)
        cells.extend(grid_cells)
        node_cell_id.update(grid_ids)
        bottom_y = section_bottom

    for idx, (src, dst) in enumerate(visible_edges):
        source = node_cell_id.get(src)
        target = node_cell_id.get(dst)
        if not source or not target:
            continue
        cells.append(
            f'<mxCell id="edge_{idx}" style="{EDGE_STYLE}" edge="1" parent="1" '
            f'source="{source}" target="{target}">'
            f'<mxGeometry relative="1" as="geometry" /></mxCell>'
        )

    used_categories = sorted({resolve_icon(r.tf_type).category for r in visible})
    if used_categories:
        legend_y = bottom_y + SECTION_GAP
        cells.append(
            '<mxCell id="legend_title" value="Legend" '
            'style="text;html=1;fontSize=12;fontStyle=1;align=left;fontColor=#232F3E;" '
            'vertex="1" parent="1">'
            f'<mxGeometry x="{LEFT_MARGIN}" y="{legend_y}" width="120" height="20" as="geometry" />'
            "</mxCell>"
        )
        for i, cat in enumerate(used_categories):
            row_y = legend_y + 26 + i * LEGEND_ROW_HEIGHT
            color = category_color(cat)
            cells.append(
                f'<mxCell id="legend_swatch_{i}" value="" style="rounded=0;whiteSpace=wrap;html=1;'
                f'fillColor={color};strokeColor=none;" vertex="1" parent="1">'
                f'<mxGeometry x="{LEFT_MARGIN}" y="{row_y}" width="{LEGEND_SWATCH}" height="{LEGEND_SWATCH}" as="geometry" />'
                f"</mxCell>"
            )
            cells.append(
                f'<mxCell id="legend_label_{i}" value="{escape(cat)}" '
                'style="text;html=1;fontSize=11;align=left;verticalAlign=middle;fontColor=#232F3E;" '
                'vertex="1" parent="1">'
                f'<mxGeometry x="{LEFT_MARGIN + LEGEND_SWATCH + 8}" y="{row_y - 4}" width="160" height="{LEGEND_SWATCH + 8}" as="geometry" />'
                "</mxCell>"
            )
        bottom_y = legend_y + 26 + len(used_categories) * LEGEND_ROW_HEIGHT

    max_rank_columns = 1
    if connected:
        max_rank_columns = max(rank_of.values(), default=0) + 1
    if isolated:
        isolated_categories = {resolve_icon(r.tf_type).category for r in isolated}
        max_rank_columns = max(max_rank_columns, len(isolated_categories))

    page_width = max(1600, LEFT_MARGIN + max_rank_columns * COLUMN_WIDTH + 40)
    page_height = max(1200, bottom_y + 40)

    body = "".join(cells)
    diagram_id = uuid.uuid4().hex
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<mxfile host="Electron" modified="{timestamp}" agent="agentcore-easy-deploy" version="24.0.0">\n'
        f'  <diagram name="{escape(title)}" id="{diagram_id}">\n'
        f'    <mxGraphModel dx="1200" dy="800" grid="0" gridSize="10" guides="1" tooltips="1" '
        f'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{page_width}" pageHeight="{page_height}" math="0" shadow="0">\n'
        '      <root>\n'
        '        <mxCell id="0" />\n'
        '        <mxCell id="1" parent="0" />\n'
        f"        {body}\n"
        "      </root>\n"
        "    </mxGraphModel>\n"
        "  </diagram>\n"
        "</mxfile>\n"
    )
