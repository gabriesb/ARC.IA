"""
Deterministic draw.io (.drawio / diagrams.net) XML generator.

This is the core of the "no LLM draws the architecture" requirement: given a
list of parsed Terraform resources and edges, this module always produces
the exact same mxGraph XML — node positions, colors and icons are computed
with plain arithmetic (grid layout by category), not guessed by a model.

Output is a complete `.drawio` file (an `<mxfile>` document) that opens
directly in diagrams.net / the draw.io VS Code extension, using the official
AWS4 icon stencils (`shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.*`).
"""
import time
import uuid
from typing import Dict, Iterable, List, Sequence, Tuple
from xml.sax.saxutils import escape

from aws_icon_map import NON_VISUAL_RESOURCE_TYPES, category_color, resolve_icon
from terraform_parser import TFResource

# Preferred left-to-right column order for readability.
CATEGORY_ORDER = [
    "Network",
    "Security",
    "Compute",
    "Containers",
    "Integration",
    "Database",
    "Storage",
    "Analytics",
    "AI/ML",
    "Management",
    "Other",
]

NODE_SIZE = 68
COLUMN_WIDTH = 200
ROW_HEIGHT = 110
TOP_MARGIN = 90
LEFT_MARGIN = 40


def _safe_id(value: str) -> str:
    return "n_" + "".join(ch if ch.isalnum() else "_" for ch in value)


def _visible_resources(resources: Iterable[TFResource]) -> List[TFResource]:
    return [r for r in resources if r.tf_type not in NON_VISUAL_RESOURCE_TYPES]


def _group_by_category(resources: Sequence[TFResource]) -> Dict[str, List[TFResource]]:
    groups: Dict[str, List[TFResource]] = {}
    for res in resources:
        icon_spec = resolve_icon(res.tf_type)
        groups.setdefault(icon_spec.category, []).append(res)
    return groups


def build_drawio_xml(
    resources: Sequence[TFResource],
    edges: Sequence[Tuple[str, str]],
    title: str = "AWS Architecture",
) -> str:
    """Builds a full `.drawio` (mxfile) XML document, laid out as columns of
    AWS icons grouped by category (Network, Compute, Database, ...).

    `resources` / `edges` are the deterministic output of
    `terraform_parser.parse_terraform_files`.
    """
    visible = _visible_resources(resources)
    visible_ids = {res.id for res in visible}
    groups = _group_by_category(visible)

    ordered_categories = [c for c in CATEGORY_ORDER if c in groups]
    ordered_categories += [c for c in groups if c not in ordered_categories]

    cells: List[str] = []
    node_cell_id: Dict[str, str] = {}

    for col_idx, category in enumerate(ordered_categories):
        col_x = LEFT_MARGIN + col_idx * COLUMN_WIDTH
        color = category_color(category)

        header_id = f"header_{col_idx}"
        cells.append(
            f'<mxCell id="{header_id}" value="{escape(category)}" '
            f'style="text;html=1;fontSize=13;fontStyle=1;align=center;fontColor={color};" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{col_x}" y="20" width="{NODE_SIZE + 60}" height="30" as="geometry" />'
            f"</mxCell>"
        )

        for row_idx, res in enumerate(groups[category]):
            icon_spec = resolve_icon(res.tf_type)
            cell_id = _safe_id(res.id)
            node_cell_id[res.id] = cell_id
            node_y = TOP_MARGIN + row_idx * ROW_HEIGHT
            label = escape(f"{icon_spec.label or res.tf_type}\n{res.tf_name}")
            style = (
                "sketch=0;outlineConnect=0;fontColor=#232F3E;gradientColor=none;"
                f"fillColor={color};strokeColor=none;dashed=0;verticalLabelPosition=bottom;"
                "verticalAlign=top;align=center;html=1;fontSize=11;fontStyle=0;aspect=fixed;"
                f"shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.{icon_spec.icon};"
            )
            cells.append(
                f'<mxCell id="{cell_id}" value="{label}" style="{style}" '
                f'vertex="1" parent="1">'
                f'<mxGeometry x="{col_x}" y="{node_y}" width="{NODE_SIZE}" height="{NODE_SIZE}" as="geometry" />'
                f"</mxCell>"
            )

    edge_style = "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#545B64;endArrow=block;"
    for idx, (from_id, to_id) in enumerate(edges):
        if from_id not in visible_ids or to_id not in visible_ids:
            continue
        source = node_cell_id.get(from_id)
        target = node_cell_id.get(to_id)
        if not source or not target:
            continue
        cells.append(
            f'<mxCell id="edge_{idx}" style="{edge_style}" edge="1" parent="1" '
            f'source="{source}" target="{target}">'
            f'<mxGeometry relative="1" as="geometry" /></mxCell>'
        )

    body = "".join(cells)
    diagram_id = uuid.uuid4().hex
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<mxfile host="Electron" modified="{timestamp}" agent="agentcore-easy-deploy" version="24.0.0">\n'
        f'  <diagram name="{escape(title)}" id="{diagram_id}">\n'
        '    <mxGraphModel dx="1200" dy="800" grid="0" gridSize="10" guides="1" tooltips="1" '
        'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1600" pageHeight="1200" math="0" shadow="0">\n'
        '      <root>\n'
        '        <mxCell id="0" />\n'
        '        <mxCell id="1" parent="0" />\n'
        f"        {body}\n"
        "      </root>\n"
        "    </mxGraphModel>\n"
        "  </diagram>\n"
        "</mxfile>\n"
    )
