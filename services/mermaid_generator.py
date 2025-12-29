"""Mermaid diagram generation for knowledge graph visualization."""

import re
from datetime import datetime

from ..models.node import Node
from ..models.edge import Edge
from ..models.enums import RelationType


def generate_mermaid(
    nodes: list[Node],
    edges: list[Edge],
    title: str | None = None,
) -> str:
    """
    Generate a Mermaid flowchart from nodes and edges.

    Node styling based on mastery:
    - struggling (< 0.3): Red fill
    - learning (0.3-0.6): Yellow fill
    - proficient (0.6-0.85): Light green fill
    - mastered (> 0.85): Dark green fill

    Additional styling:
    - needsReview: Red dashed border for nodes due for review
    - hasMisconception: Purple thick border for nodes with misconceptions

    Edge styling by relation type:
    - prerequisite: Solid arrow
    - builds_on: Thick arrow
    - related_to: Dotted line
    - contradicts: Red dotted line
    """
    lines = ["graph TD"]

    # Add class definitions
    lines.extend([
        "    classDef struggling fill:#ff6b6b,stroke:#333,stroke-width:2px,color:#fff",
        "    classDef learning fill:#ffe066,stroke:#333,stroke-width:2px",
        "    classDef proficient fill:#8ce99a,stroke:#333,stroke-width:2px",
        "    classDef mastered fill:#2ecc71,stroke:#333,stroke-width:2px,color:#fff",
        "    classDef needsReview stroke:#e74c3c,stroke-width:4px,stroke-dasharray:5",
        "    classDef hasMisconception stroke:#9b59b6,stroke-width:3px",
    ])

    if title:
        lines.append(f"    subgraph {_sanitize_id(title)}[{title}]")

    # Generate node definitions
    for node in nodes:
        node_id = _sanitize_id(node.id)
        label = _escape_label(node.concept)
        class_name = _get_mastery_class(node.mastery_level)

        # Check for additional classes
        extra_classes = []
        if _needs_review(node):
            extra_classes.append("needsReview")
        if node.misconceptions:
            extra_classes.append("hasMisconception")

        # Build class string
        all_classes = [class_name] + extra_classes
        class_str = ",".join(all_classes)

        # Add mastery percentage to label
        mastery_pct = int(node.mastery_level * 100)
        full_label = f"{label} ({mastery_pct}%)"

        lines.append(f'    {node_id}["{full_label}"]:::{class_str}')

    if title:
        lines.append("    end")

    # Generate edge definitions
    for edge in edges:
        source = _sanitize_id(edge.source_id)
        target = _sanitize_id(edge.target_id)
        edge_str = _get_edge_style(edge.relation_type, source, target)
        lines.append(f"    {edge_str}")

    return "\n".join(lines)


def _sanitize_id(id_str: str) -> str:
    """Convert ID to valid Mermaid node ID."""
    # Replace invalid characters with underscores
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", id_str)
    # Ensure it starts with a letter
    if sanitized and sanitized[0].isdigit():
        sanitized = "n_" + sanitized
    return sanitized or "node"


def _escape_label(label: str) -> str:
    """Escape special characters in labels."""
    return (
        label.replace('"', "'")
        .replace("\n", " ")
        .replace("[", "(")
        .replace("]", ")")
    )


def _get_mastery_class(mastery_level: float) -> str:
    """Get CSS class based on mastery level."""
    if mastery_level < 0.3:
        return "struggling"
    elif mastery_level < 0.6:
        return "learning"
    elif mastery_level < 0.85:
        return "proficient"
    else:
        return "mastered"


def _needs_review(node: Node) -> bool:
    """Check if node is due for review."""
    if not node.next_review_at:
        return False
    return node.next_review_at <= datetime.now()


def _get_edge_style(relation_type: RelationType, source: str, target: str) -> str:
    """Get Mermaid edge syntax based on relation type."""
    match relation_type:
        case RelationType.PREREQUISITE:
            return f'{source} -->|"prereq"| {target}'
        case RelationType.BUILDS_ON:
            return f'{source} ==>|"builds on"| {target}'
        case RelationType.RELATED_TO:
            return f'{source} -.-|"related"| {target}'
        case RelationType.CONTRADICTS:
            return f'{source} -.->|"contradicts"| {target}'
        case RelationType.APPLIES_TO:
            return f'{source} -->|"applies to"| {target}'
        case RelationType.PARENT_OF:
            return f'{source} -->|"parent of"| {target}'
        case _:
            return f"{source} --> {target}"


def generate_learning_path_mermaid(
    nodes: list[Node],
    edges: list[Edge],
    target_concept: str,
) -> str:
    """
    Generate a Mermaid diagram specifically for a learning path.

    Shows nodes in a vertical layout optimized for prerequisite chains.
    """
    lines = ["graph TB"]

    # Add class definitions
    lines.extend([
        "    classDef struggling fill:#ff6b6b,stroke:#333,stroke-width:2px,color:#fff",
        "    classDef learning fill:#ffe066,stroke:#333,stroke-width:2px",
        "    classDef proficient fill:#8ce99a,stroke:#333,stroke-width:2px",
        "    classDef mastered fill:#2ecc71,stroke:#333,stroke-width:2px,color:#fff",
        "    classDef target fill:#3498db,stroke:#333,stroke-width:3px,color:#fff",
    ])

    # Generate nodes
    for node in nodes:
        node_id = _sanitize_id(node.id)
        label = _escape_label(node.concept)
        mastery_pct = int(node.mastery_level * 100)

        if node.id == target_concept or node.concept == target_concept:
            lines.append(f'    {node_id}["{label} ({mastery_pct}%)"]:::target')
        else:
            class_name = _get_mastery_class(node.mastery_level)
            lines.append(f'    {node_id}["{label} ({mastery_pct}%)"]:::{class_name}')

    # Generate edges (only prerequisites for learning paths)
    for edge in edges:
        if edge.relation_type == RelationType.PREREQUISITE:
            source = _sanitize_id(edge.source_id)
            target = _sanitize_id(edge.target_id)
            lines.append(f"    {source} --> {target}")

    return "\n".join(lines)
