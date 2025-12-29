"""Query engine for intelligent graph queries."""

from datetime import datetime
from collections import deque

from ..database.connection import get_connection
from ..models.node import Node
from ..models.edge import Edge
from ..models.enums import RelationType, QueryType


class QueryEngine:
    """Engine for executing intelligent queries on the knowledge graph."""

    def __init__(self):
        pass

    def query(
        self,
        query_type: QueryType | str,
        node_id: str | None = None,
        domain: str | None = None,
        limit: int = 10,
    ) -> dict:
        """
        Execute a query against the knowledge graph.

        Args:
            query_type: Type of query to execute
            node_id: Focus node for some queries
            domain: Filter by domain
            limit: Maximum results to return

        Returns:
            Dict with query results and metadata
        """
        if isinstance(query_type, str):
            query_type = QueryType(query_type)

        match query_type:
            case QueryType.PREREQUISITES:
                return self._query_prerequisites(node_id, domain, limit)
            case QueryType.READY_TO_LEARN:
                return self._query_ready_to_learn(domain, limit)
            case QueryType.DUE_FOR_REVIEW:
                return self._query_due_for_review(domain, limit)
            case QueryType.STRUGGLING:
                return self._query_struggling(domain, limit)
            case QueryType.STALLED:
                return self._query_stalled(domain, limit)
            case QueryType.MISCONCEPTIONS:
                return self._query_misconceptions(domain, limit)
            case QueryType.KNOWLEDGE_GAPS:
                return self._query_knowledge_gaps(domain, limit)
            case QueryType.NEXT_RECOMMENDED:
                return self._query_next_recommended(domain, limit)
            case QueryType.ALL_NODES:
                return self._query_all_nodes(domain, limit)
            case _:
                raise ValueError(f"Unknown query type: {query_type}")

    def get_subgraph(
        self,
        center_node_id: str,
        depth: int = 2,
        direction: str = "both",
    ) -> tuple[list[Node], list[Edge]]:
        """
        Get a subgraph centered on a node.

        Args:
            center_node_id: Node to center on
            depth: How many edge hops to traverse
            direction: "upstream" (prereqs), "downstream", or "both"

        Returns:
            Tuple of (nodes, edges) in the subgraph
        """
        visited_nodes = set()
        collected_edges = []

        with get_connection() as conn:
            cursor = conn.cursor()

            # BFS to collect nodes
            queue = deque([(center_node_id, 0)])
            visited_nodes.add(center_node_id)

            while queue:
                current_id, current_depth = queue.popleft()

                if current_depth >= depth:
                    continue

                # Get connected nodes based on direction
                if direction in ("upstream", "both"):
                    # Find nodes that are prerequisites OF current (current is target)
                    cursor.execute(
                        "SELECT * FROM edges WHERE target_id = ?",
                        (current_id,)
                    )
                    for row in cursor.fetchall():
                        edge = Edge.from_row(dict(row))
                        collected_edges.append(edge)
                        if edge.source_id not in visited_nodes:
                            visited_nodes.add(edge.source_id)
                            queue.append((edge.source_id, current_depth + 1))

                if direction in ("downstream", "both"):
                    # Find nodes that current is prerequisite FOR (current is source)
                    cursor.execute(
                        "SELECT * FROM edges WHERE source_id = ?",
                        (current_id,)
                    )
                    for row in cursor.fetchall():
                        edge = Edge.from_row(dict(row))
                        collected_edges.append(edge)
                        if edge.target_id not in visited_nodes:
                            visited_nodes.add(edge.target_id)
                            queue.append((edge.target_id, current_depth + 1))

            # Fetch all visited nodes
            nodes = []
            for node_id in visited_nodes:
                cursor.execute("SELECT * FROM nodes WHERE id = ?", (node_id,))
                row = cursor.fetchone()
                if row:
                    nodes.append(Node.from_row(dict(row)))

        return nodes, collected_edges

    def get_learning_path(
        self,
        target_node_id: str,
        include_mastered: bool = False,
    ) -> dict:
        """
        Get topologically sorted prerequisites for a target concept.

        Args:
            target_node_id: Goal concept
            include_mastered: Include already-mastered nodes?

        Returns:
            Dict with ordered path and gap analysis
        """
        # Get all prerequisites transitively
        all_prereqs = set()
        edges_in_path = []

        with get_connection() as conn:
            cursor = conn.cursor()

            # BFS to find all prerequisites
            queue = deque([target_node_id])
            visited = {target_node_id}

            while queue:
                current_id = queue.popleft()

                cursor.execute(
                    """SELECT * FROM edges
                    WHERE target_id = ? AND relation_type = ?""",
                    (current_id, RelationType.PREREQUISITE.value)
                )

                for row in cursor.fetchall():
                    edge = Edge.from_row(dict(row))
                    edges_in_path.append(edge)
                    prereq_id = edge.source_id

                    if prereq_id not in visited:
                        visited.add(prereq_id)
                        all_prereqs.add(prereq_id)
                        queue.append(prereq_id)

            # Topological sort
            sorted_path = self._topological_sort(all_prereqs | {target_node_id}, edges_in_path)

            # Fetch node details and filter
            path_nodes = []
            gaps = []

            for node_id in sorted_path:
                cursor.execute("SELECT * FROM nodes WHERE id = ?", (node_id,))
                row = cursor.fetchone()
                if row:
                    node = Node.from_row(dict(row))
                    if node.mastery_level < 0.8:
                        gaps.append(node)
                    if include_mastered or node.mastery_level < 0.8:
                        path_nodes.append(node)

        return {
            "target": target_node_id,
            "path": [n.to_dict() for n in path_nodes],
            "gaps": [n.to_dict() for n in gaps],
            "total_prerequisites": len(all_prereqs),
            "gaps_count": len(gaps),
            "ready": len(gaps) == 0 or (len(gaps) == 1 and gaps[0].id == target_node_id),
        }

    def _topological_sort(self, node_ids: set, edges: list[Edge]) -> list[str]:
        """Topological sort of nodes based on prerequisite edges."""
        # Build adjacency list and in-degree count
        in_degree = {node_id: 0 for node_id in node_ids}
        adj_list = {node_id: [] for node_id in node_ids}

        for edge in edges:
            if edge.relation_type == RelationType.PREREQUISITE:
                if edge.source_id in node_ids and edge.target_id in node_ids:
                    adj_list[edge.source_id].append(edge.target_id)
                    in_degree[edge.target_id] += 1

        # Kahn's algorithm
        queue = deque([n for n in node_ids if in_degree[n] == 0])
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)

            for neighbor in adj_list[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return result

    def _query_prerequisites(self, node_id: str | None, domain: str | None, limit: int) -> dict:
        """Get all prerequisites for a concept (transitive)."""
        if not node_id:
            return {"error": "node_id is required for prerequisites query", "nodes": []}

        nodes, edges = self.get_subgraph(node_id, depth=10, direction="upstream")

        # Filter to only prerequisite edges
        prereq_edges = [e for e in edges if e.relation_type == RelationType.PREREQUISITE]

        return {
            "query_type": "prerequisites",
            "target_node": node_id,
            "nodes": [n.to_dict() for n in nodes[:limit]],
            "edges": [e.to_dict() for e in prereq_edges],
            "total_count": len(nodes),
        }

    def _query_ready_to_learn(self, domain: str | None, limit: int) -> dict:
        """Get concepts where all prerequisites are mastered."""
        with get_connection() as conn:
            cursor = conn.cursor()

            # Get all nodes with low mastery
            query = """
                SELECT n.* FROM nodes n
                WHERE n.mastery_level < 0.8
            """
            params = []

            if domain:
                query += " AND n.domain = ?"
                params.append(domain)

            cursor.execute(query, params)
            candidates = [Node.from_row(dict(row)) for row in cursor.fetchall()]

            ready_nodes = []
            for node in candidates:
                # Check if all prerequisites are mastered
                cursor.execute(
                    """SELECT n.mastery_level FROM nodes n
                    JOIN edges e ON n.id = e.source_id
                    WHERE e.target_id = ? AND e.relation_type = ?""",
                    (node.id, RelationType.PREREQUISITE.value)
                )
                prereq_masteries = cursor.fetchall()

                # No prerequisites or all mastered
                if not prereq_masteries or all(row[0] >= 0.8 for row in prereq_masteries):
                    ready_nodes.append(node)

                if len(ready_nodes) >= limit:
                    break

        return {
            "query_type": "ready_to_learn",
            "nodes": [n.to_dict() for n in ready_nodes],
            "count": len(ready_nodes),
        }

    def _query_due_for_review(self, domain: str | None, limit: int) -> dict:
        """Get nodes where next_review_at <= now."""
        now = datetime.now().isoformat()

        with get_connection() as conn:
            cursor = conn.cursor()

            query = """
                SELECT * FROM nodes
                WHERE next_review_at IS NOT NULL
                AND next_review_at <= ?
            """
            params = [now]

            if domain:
                query += " AND domain = ?"
                params.append(domain)

            query += " ORDER BY next_review_at ASC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            nodes = [Node.from_row(dict(row)) for row in cursor.fetchall()]

        return {
            "query_type": "due_for_review",
            "nodes": [n.to_dict() for n in nodes],
            "count": len(nodes),
        }

    def _query_struggling(self, domain: str | None, limit: int) -> dict:
        """Get nodes with high difficulty + low mastery."""
        with get_connection() as conn:
            cursor = conn.cursor()

            query = """
                SELECT * FROM nodes
                WHERE difficulty > 0.5 AND mastery_level < 0.4
            """
            params = []

            if domain:
                query += " AND domain = ?"
                params.append(domain)

            query += " ORDER BY (difficulty - mastery_level) DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            nodes = [Node.from_row(dict(row)) for row in cursor.fetchall()]

        return {
            "query_type": "struggling",
            "nodes": [n.to_dict() for n in nodes],
            "count": len(nodes),
        }

    def _query_stalled(self, domain: str | None, limit: int) -> dict:
        """Get nodes with multiple reviews but mastery not improving."""
        with get_connection() as conn:
            cursor = conn.cursor()

            query = """
                SELECT * FROM nodes
                WHERE review_count >= 3 AND mastery_level < 0.5
            """
            params = []

            if domain:
                query += " AND domain = ?"
                params.append(domain)

            query += " ORDER BY review_count DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            nodes = [Node.from_row(dict(row)) for row in cursor.fetchall()]

        return {
            "query_type": "stalled",
            "nodes": [n.to_dict() for n in nodes],
            "count": len(nodes),
        }

    def _query_misconceptions(self, domain: str | None, limit: int) -> dict:
        """Get nodes with detected misconceptions."""
        with get_connection() as conn:
            cursor = conn.cursor()

            query = """
                SELECT * FROM nodes
                WHERE misconceptions IS NOT NULL
                AND misconceptions != '[]'
                AND misconceptions != ''
            """
            params = []

            if domain:
                query += " AND domain = ?"
                params.append(domain)

            query += " LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            nodes = [Node.from_row(dict(row)) for row in cursor.fetchall()]

        return {
            "query_type": "misconceptions",
            "nodes": [n.to_dict() for n in nodes],
            "count": len(nodes),
        }

    def _query_knowledge_gaps(self, domain: str | None, limit: int) -> dict:
        """Get low mastery nodes that are blocking downstream concepts."""
        with get_connection() as conn:
            cursor = conn.cursor()

            # Find nodes that are prerequisites for other nodes
            query = """
                SELECT DISTINCT n.* FROM nodes n
                JOIN edges e ON n.id = e.source_id
                WHERE e.relation_type = ?
                AND n.mastery_level < 0.6
            """
            params = [RelationType.PREREQUISITE.value]

            if domain:
                query += " AND n.domain = ?"
                params.append(domain)

            # Order by how many things they block
            query += """
                GROUP BY n.id
                ORDER BY COUNT(e.target_id) DESC
                LIMIT ?
            """
            params.append(limit)

            cursor.execute(query, params)
            nodes = [Node.from_row(dict(row)) for row in cursor.fetchall()]

        return {
            "query_type": "knowledge_gaps",
            "nodes": [n.to_dict() for n in nodes],
            "count": len(nodes),
            "description": "Concepts with low mastery that are prerequisites for other concepts",
        }

    def _query_next_recommended(self, domain: str | None, limit: int) -> dict:
        """Smart recommendation for what to study next."""
        # Combine multiple factors:
        # 1. Ready to learn (prerequisites mastered)
        # 2. Due for review (if any)
        # 3. Knowledge gaps (prioritize blockers)

        recommendations = []

        # First, check for overdue reviews
        due_result = self._query_due_for_review(domain, limit=3)
        for node in due_result["nodes"]:
            recommendations.append({
                **node,
                "reason": "Due for review",
                "priority": 1,
            })

        # Then, knowledge gaps
        gaps_result = self._query_knowledge_gaps(domain, limit=3)
        for node in gaps_result["nodes"]:
            if node["id"] not in [r["id"] for r in recommendations]:
                recommendations.append({
                    **node,
                    "reason": "Knowledge gap blocking other concepts",
                    "priority": 2,
                })

        # Finally, ready to learn
        ready_result = self._query_ready_to_learn(domain, limit=3)
        for node in ready_result["nodes"]:
            if node["id"] not in [r["id"] for r in recommendations]:
                recommendations.append({
                    **node,
                    "reason": "Prerequisites mastered, ready to learn",
                    "priority": 3,
                })

        # Sort by priority and limit
        recommendations.sort(key=lambda x: x["priority"])
        recommendations = recommendations[:limit]

        return {
            "query_type": "next_recommended",
            "recommendations": recommendations,
            "count": len(recommendations),
        }

    def _query_all_nodes(self, domain: str | None, limit: int) -> dict:
        """Get all nodes in the graph."""
        with get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM nodes"
            params = []

            if domain:
                query += " WHERE domain = ?"
                params.append(domain)

            query += " ORDER BY concept ASC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            nodes = [Node.from_row(dict(row)) for row in cursor.fetchall()]

        return {
            "query_type": "all_nodes",
            "nodes": [n.to_dict() for n in nodes],
            "count": len(nodes),
        }
