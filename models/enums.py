"""Enums for the knowledge graph."""

from enum import Enum


class RelationType(str, Enum):
    """Types of relationships between concepts."""

    PREREQUISITE = "prerequisite"  # Must know source before target
    BUILDS_ON = "builds_on"        # Target extends source
    RELATED_TO = "related_to"      # Concepts are connected (bidirectional)
    CONTRADICTS = "contradicts"    # Common misconception
    APPLIES_TO = "applies_to"      # Application domain
    PARENT_OF = "parent_of"        # Ontological hierarchy


class EdgeType(str, Enum):
    """Alias for RelationType for backwards compatibility."""

    PREREQUISITE = "prerequisite"
    BUILDS_ON = "builds_on"
    RELATED_TO = "related_to"
    CONTRADICTS = "contradicts"
    APPLIES_TO = "applies_to"
    PARENT_OF = "parent_of"


class QueryType(str, Enum):
    """Types of graph queries supported."""

    PREREQUISITES = "prerequisites"      # All prerequisites for a concept
    READY_TO_LEARN = "ready_to_learn"    # Concepts where prereqs are mastered
    DUE_FOR_REVIEW = "due_for_review"    # Nodes needing review
    STRUGGLING = "struggling"            # High difficulty + low mastery
    STALLED = "stalled"                  # Multiple reviews, no improvement
    MISCONCEPTIONS = "misconceptions"    # Nodes with misconceptions
    KNOWLEDGE_GAPS = "knowledge_gaps"    # Low mastery blocking downstream
    NEXT_RECOMMENDED = "next_recommended"  # Best concept to study next
    ALL_NODES = "all_nodes"              # All nodes in the graph
