"""
Knowledge Graph MCP Server

An MCP server for tracking student learning via a knowledge graph.
Features spaced repetition, misconception tracking, and intelligent queries.
"""

import os
from fastmcp import FastMCP

from .database.connection import init_database, set_db_path
from .models.node import NodeCreate, NodeUpdate
from .models.edge import EdgeCreate
from .models.enums import RelationType, QueryType
from .services.graph_service import GraphService
from .services.query_engine import QueryEngine
from .services.mermaid_generator import generate_mermaid, generate_learning_path_mermaid

# Initialize the MCP server
mcp = FastMCP(
    "Knowledge Graph",
    instructions="Educational knowledge graph for tracking student learning progress. "
    "Features spaced repetition scheduling, misconception tracking, and intelligent "
    "query capabilities for LLM-guided learning.",
)

# Initialize services
graph_service = GraphService()
query_engine = QueryEngine()


@mcp.tool()
def add_node(
    concept: str,
    description: str | None = None,
    domain: str | None = None,
    difficulty: float = 0.5,
    tags: list[str] | None = None,
    node_id: str | None = None,
) -> dict:
    """
    Create a new concept node in the knowledge graph.

    Args:
        concept: Human-readable name for the concept (e.g., "Quadratic Formula")
        description: Detailed description of what this concept represents
        domain: Category/domain (e.g., "mathematics", "physics", "programming")
        difficulty: Estimated cognitive load from 0.0 (easy) to 1.0 (hard). Default 0.5.
        tags: List of categorization tags (e.g., ["algebra", "equations"])
        node_id: Custom ID for the node. Auto-generated from concept if not provided.

    Returns:
        Created node object with all fields including initial mastery (0.0)

    Example:
        add_node(
            concept="Quadratic Formula",
            description="Formula for solving ax² + bx + c = 0",
            domain="mathematics",
            difficulty=0.7,
            tags=["algebra", "equations"]
        )
    """
    try:
        node_data = NodeCreate(
            concept=concept,
            description=description,
            domain=domain,
            difficulty=difficulty,
            tags=tags or [],
            node_id=node_id,
        )
        node = graph_service.add_node(node_data)
        return {
            "success": True,
            "node": node.to_dict(),
            "message": f"Created node '{concept}' with ID '{node.id}'",
        }
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Failed to create node: {str(e)}"}


@mcp.tool()
def add_edge(
    source_concept: str,
    target_concept: str,
    relation_type: str,
    strength: float = 1.0,
    reasoning: str | None = None,
) -> dict:
    """
    Create a relationship between two concepts in the knowledge graph.

    Args:
        source_concept: Source node ID or concept name
        target_concept: Target node ID or concept name
        relation_type: Type of relationship. One of:
            - "prerequisite": Source must be learned before target
            - "builds_on": Target extends/deepens source concept
            - "related_to": Concepts are connected (bidirectional semantically)
            - "contradicts": Common misconception (source is wrong belief about target)
            - "applies_to": Source concept applies to target domain/topic
            - "parent_of": Ontological hierarchy (source is parent category of target)
        strength: Confidence in the relationship from 0.0 to 1.0. Default 1.0.
        reasoning: Explanation of why this relationship exists

    Returns:
        Created edge object

    Example:
        add_edge(
            source_concept="Algebra",
            target_concept="Quadratic Formula",
            relation_type="prerequisite",
            reasoning="Must understand algebraic manipulation before learning the formula"
        )
    """
    try:
        # Resolve node IDs
        source_id = graph_service.resolve_node_id(source_concept)
        if not source_id:
            return {"success": False, "error": f"Source node '{source_concept}' not found"}

        target_id = graph_service.resolve_node_id(target_concept)
        if not target_id:
            return {"success": False, "error": f"Target node '{target_concept}' not found"}

        # Parse relation type
        try:
            rel_type = RelationType(relation_type)
        except ValueError:
            valid_types = [t.value for t in RelationType]
            return {
                "success": False,
                "error": f"Invalid relation_type '{relation_type}'. Must be one of: {valid_types}",
            }

        edge_data = EdgeCreate(
            source_id=source_id,
            target_id=target_id,
            relation_type=rel_type,
            strength=strength,
            reasoning=reasoning,
        )
        edge = graph_service.add_edge(edge_data)
        return {
            "success": True,
            "edge": edge.to_dict(),
            "message": f"Created {relation_type} edge: {source_id} → {target_id}",
        }
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Failed to create edge: {str(e)}"}


@mcp.tool()
def update_node(
    node_id: str,
    mastery_level: float | None = None,
    mastery_recall: float | None = None,
    mastery_application: float | None = None,
    mastery_explanation: float | None = None,
    quality: int | None = None,
    difficulty: float | None = None,
    misconception_detected: str | None = None,
    notes: str | None = None,
) -> dict:
    """
    Update a node's properties and record a review session.

    Args:
        node_id: ID or concept name of the node to update
        mastery_level: Overall mastery (0.0-1.0). Overrides dimensional calculation.
        mastery_recall: Ability to retrieve from memory (0.0-1.0)
        mastery_application: Ability to use in new contexts (0.0-1.0)
        mastery_explanation: Ability to teach/explain to others (0.0-1.0)
        quality: SM-2 review quality rating (0-5). Triggers spaced repetition scheduling.
            - 5: Perfect response
            - 4: Correct after hesitation
            - 3: Correct with serious difficulty
            - 2: Incorrect, but correct answer seemed easy
            - 1: Incorrect, correct answer remembered after seeing it
            - 0: Complete blackout
        difficulty: Update estimated difficulty (0.0-1.0)
        misconception_detected: Specific misconception observed (e.g., "confuses ± with +")
        notes: LLM observations about the student's understanding

    Returns:
        Updated node object with new mastery levels and next review date

    Example:
        update_node(
            node_id="quadratic_formula",
            quality=3,
            mastery_application=0.4,
            misconception_detected="forgets to include ± sign",
            notes="Student solved correctly but forgot ± on second attempt"
        )
    """
    try:
        # Resolve node ID
        resolved_id = graph_service.resolve_node_id(node_id)
        if not resolved_id:
            return {"success": False, "error": f"Node '{node_id}' not found"}

        update_data = NodeUpdate(
            mastery_level=mastery_level,
            mastery_recall=mastery_recall,
            mastery_application=mastery_application,
            mastery_explanation=mastery_explanation,
            quality=quality,
            difficulty=difficulty,
            misconception_detected=misconception_detected,
            notes=notes,
        )

        node = graph_service.update_node(resolved_id, update_data)

        result = {
            "success": True,
            "node": node.to_dict(),
            "message": f"Updated node '{node.concept}'",
        }

        # Add review-specific info if quality was provided
        if quality is not None:
            result["review_recorded"] = True
            result["next_review_at"] = node.next_review_at.isoformat() if node.next_review_at else None
            result["interval_days"] = node.interval_days

        return result

    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Failed to update node: {str(e)}"}


@mcp.tool()
def query_graph(
    query_type: str,
    node_id: str | None = None,
    domain: str | None = None,
    limit: int = 10,
) -> dict:
    """
    Query the knowledge graph for learning insights.

    Args:
        query_type: Type of query to execute. One of:
            - "prerequisites": All prerequisites for a concept (requires node_id)
            - "ready_to_learn": Concepts where all prerequisites are mastered
            - "due_for_review": Nodes where scheduled review date has passed
            - "struggling": High difficulty + low mastery concepts
            - "stalled": Multiple reviews but mastery not improving
            - "misconceptions": Nodes with detected misconceptions
            - "knowledge_gaps": Low mastery nodes blocking other concepts
            - "next_recommended": Smart recommendation for what to study next
            - "all_nodes": All nodes in the graph
        node_id: Focus node for some queries (required for "prerequisites")
        domain: Filter results by domain (e.g., "mathematics")
        limit: Maximum number of results to return. Default 10.

    Returns:
        Query results with nodes and metadata

    Example:
        # What should the student study next?
        query_graph(query_type="next_recommended", domain="mathematics", limit=5)

        # What are the prerequisites for calculus?
        query_graph(query_type="prerequisites", node_id="calculus")
    """
    try:
        # Parse query type
        try:
            q_type = QueryType(query_type)
        except ValueError:
            valid_types = [t.value for t in QueryType]
            return {
                "success": False,
                "error": f"Invalid query_type '{query_type}'. Must be one of: {valid_types}",
            }

        # Resolve node_id if provided
        resolved_node_id = None
        if node_id:
            resolved_node_id = graph_service.resolve_node_id(node_id)
            if not resolved_node_id:
                return {"success": False, "error": f"Node '{node_id}' not found"}

        result = query_engine.query(
            query_type=q_type,
            node_id=resolved_node_id,
            domain=domain,
            limit=limit,
        )

        return {"success": True, **result}

    except Exception as e:
        return {"success": False, "error": f"Query failed: {str(e)}"}


@mcp.tool()
def read_subgraph(
    center_node: str,
    depth: int = 2,
    direction: str = "both",
    include_mastery: bool = True,
    output_format: str = "both",
) -> dict:
    """
    Get the neighborhood around a concept for context.

    Args:
        center_node: Node ID or concept name to center on
        depth: How many edge hops to traverse (1=direct connections, 2=neighbors of neighbors)
        direction: Which edges to follow:
            - "upstream": Follow edges where center is target (prerequisites)
            - "downstream": Follow edges where center is source (what it unlocks)
            - "both": Follow edges in both directions
        include_mastery: Whether to include mastery data in response
        output_format: Output format:
            - "json": Just the structured data
            - "mermaid": Just the Mermaid diagram
            - "both": Both JSON and Mermaid (default)

    Returns:
        Subgraph with nodes, edges, and optional Mermaid visualization

    Example:
        # Get context around quadratic equations
        read_subgraph(
            center_node="quadratic_equations",
            depth=2,
            direction="upstream",  # See prerequisites
            output_format="both"
        )
    """
    try:
        # Resolve center node
        resolved_id = graph_service.resolve_node_id(center_node)
        if not resolved_id:
            return {"success": False, "error": f"Node '{center_node}' not found"}

        # Validate direction
        if direction not in ("upstream", "downstream", "both"):
            return {
                "success": False,
                "error": f"Invalid direction '{direction}'. Must be 'upstream', 'downstream', or 'both'",
            }

        # Get subgraph
        nodes, edges = query_engine.get_subgraph(
            center_node_id=resolved_id,
            depth=depth,
            direction=direction,
        )

        result = {
            "success": True,
            "center_node": resolved_id,
            "depth": depth,
            "direction": direction,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

        # Add JSON output
        if output_format in ("json", "both"):
            if include_mastery:
                result["nodes"] = [n.to_dict() for n in nodes]
            else:
                result["nodes"] = [
                    {"id": n.id, "concept": n.concept, "domain": n.domain}
                    for n in nodes
                ]
            result["edges"] = [e.to_dict() for e in edges]

        # Add Mermaid output
        if output_format in ("mermaid", "both"):
            result["mermaid"] = generate_mermaid(nodes, edges)

        return result

    except Exception as e:
        return {"success": False, "error": f"Failed to read subgraph: {str(e)}"}


@mcp.tool()
def get_learning_path(
    target_concept: str,
    include_mastered: bool = False,
) -> dict:
    """
    Get the ordered learning path to reach a target concept.

    Returns a topologically sorted list of prerequisites, highlighting
    which concepts the student still needs to learn (gaps).

    Args:
        target_concept: The goal concept to learn (node ID or concept name)
        include_mastered: Whether to include already-mastered concepts in the path

    Returns:
        Ordered path with gap analysis and Mermaid visualization

    Example:
        # What do I need to learn before calculus?
        get_learning_path(target_concept="calculus")
    """
    try:
        # Resolve target node
        resolved_id = graph_service.resolve_node_id(target_concept)
        if not resolved_id:
            return {"success": False, "error": f"Target concept '{target_concept}' not found"}

        # Get learning path
        path_result = query_engine.get_learning_path(
            target_node_id=resolved_id,
            include_mastered=include_mastered,
        )

        # Get nodes and edges for visualization
        nodes, edges = query_engine.get_subgraph(
            center_node_id=resolved_id,
            depth=10,
            direction="upstream",
        )

        # Filter to just prerequisite edges
        prereq_edges = [e for e in edges if e.relation_type == RelationType.PREREQUISITE]

        # Generate Mermaid
        mermaid = generate_learning_path_mermaid(nodes, prereq_edges, resolved_id)

        return {
            "success": True,
            **path_result,
            "mermaid": mermaid,
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to get learning path: {str(e)}"}


@mcp.tool()
def get_statistics(domain: str | None = None) -> dict:
    """
    Get summary statistics for learning progress.

    Args:
        domain: Filter statistics by domain (e.g., "mathematics"). If None, returns all.

    Returns:
        Statistics including:
        - total_concepts: Number of concepts in the graph
        - mastery_distribution: Counts by mastery level
        - average_mastery_by_domain: Average mastery per domain
        - overall_mastery: Overall average mastery
        - concepts_due_for_review: Count of concepts needing review
        - misconceptions_count: Count of concepts with misconceptions
        - struggling_concepts: Top 5 concepts with high difficulty and low mastery

    Example:
        # Get overall stats
        get_statistics()

        # Get math-specific stats
        get_statistics(domain="mathematics")
    """
    try:
        stats = graph_service.get_statistics(domain=domain)
        return {"success": True, **stats}
    except Exception as e:
        return {"success": False, "error": f"Failed to get statistics: {str(e)}"}


def main():
    """Run the MCP server."""
    # Check for custom database path from environment
    db_path = os.environ.get("KNOWLEDGE_GRAPH_DB_PATH")
    if db_path:
        set_db_path(db_path)

    # Initialize the database
    init_database()

    # Check if running in HTTP mode (for Smithery deployment)
    port = os.environ.get("PORT")
    if port:
        # HTTP mode for Smithery
        import uvicorn
        from starlette.middleware.cors import CORSMiddleware

        # Create the HTTP app with CORS for browser clients
        app = mcp.streamable_http_app()
        app = CORSMiddleware(
            app=app,
            allow_origins=["*"],
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
            expose_headers=["mcp-session-id", "mcp-protocol-version"],
            max_age=86400,
        )

        uvicorn.run(app, host="0.0.0.0", port=int(port))
    else:
        # Standard stdio mode for local usage
        mcp.run()


if __name__ == "__main__":
    main()
