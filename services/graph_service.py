"""Graph service for CRUD operations on the knowledge graph."""

import json
import re
from datetime import datetime
from collections import deque

from ..database.connection import get_connection
from ..models.node import Node, NodeCreate, NodeUpdate
from ..models.edge import Edge, EdgeCreate
from ..models.enums import RelationType
from .spaced_repetition import calculate_next_review, calculate_overall_mastery


class GraphService:
    """Service for managing the knowledge graph."""

    def __init__(self):
        pass

    # ==================== Node Operations ====================

    def add_node(self, node_data: NodeCreate) -> Node:
        """
        Add a new concept node to the graph.

        Args:
            node_data: Node creation data

        Returns:
            Created Node object

        Raises:
            ValueError: If node with same ID already exists
        """
        node_id = node_data.node_id or self._generate_node_id(node_data.concept)

        with get_connection() as conn:
            cursor = conn.cursor()

            # Check if node already exists
            cursor.execute("SELECT id FROM nodes WHERE id = ?", (node_id,))
            if cursor.fetchone():
                raise ValueError(f"Node with ID '{node_id}' already exists")

            # Insert the node
            cursor.execute(
                """INSERT INTO nodes
                (id, concept, description, domain, difficulty, tags, mastery_level)
                VALUES (?, ?, ?, ?, ?, ?, 0.0)""",
                (
                    node_id,
                    node_data.concept,
                    node_data.description,
                    node_data.domain,
                    node_data.difficulty,
                    json.dumps(node_data.tags),
                ),
            )
            conn.commit()

            # Fetch and return the created node
            cursor.execute("SELECT * FROM nodes WHERE id = ?", (node_id,))
            row = cursor.fetchone()
            return Node.from_row(dict(row))

    def get_node(self, node_id: str) -> Node | None:
        """Get a node by ID."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM nodes WHERE id = ?", (node_id,))
            row = cursor.fetchone()
            if row:
                return Node.from_row(dict(row))
            return None

    def get_node_by_concept(self, concept: str) -> Node | None:
        """Get a node by concept name."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM nodes WHERE concept = ?", (concept,))
            row = cursor.fetchone()
            if row:
                return Node.from_row(dict(row))
            return None

    def update_node(self, node_id: str, update_data: NodeUpdate) -> Node:
        """
        Update a node's properties.

        If quality is provided, triggers spaced repetition calculation.
        If mastery dimensions are updated, recalculates overall mastery.

        Args:
            node_id: ID of node to update
            update_data: Fields to update

        Returns:
            Updated Node object
        """
        with get_connection() as conn:
            cursor = conn.cursor()

            # Get current node
            cursor.execute("SELECT * FROM nodes WHERE id = ?", (node_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Node '{node_id}' not found")

            current_node = Node.from_row(dict(row))
            updates = {}
            now = datetime.now().isoformat()

            # Handle basic field updates
            if update_data.concept is not None:
                updates["concept"] = update_data.concept
            if update_data.description is not None:
                updates["description"] = update_data.description
            if update_data.domain is not None:
                updates["domain"] = update_data.domain
            if update_data.difficulty is not None:
                updates["difficulty"] = update_data.difficulty

            # Handle mastery dimension updates
            mastery_recall = update_data.mastery_recall if update_data.mastery_recall is not None else current_node.mastery_recall
            mastery_application = update_data.mastery_application if update_data.mastery_application is not None else current_node.mastery_application
            mastery_explanation = update_data.mastery_explanation if update_data.mastery_explanation is not None else current_node.mastery_explanation

            if any([
                update_data.mastery_recall is not None,
                update_data.mastery_application is not None,
                update_data.mastery_explanation is not None,
            ]):
                updates["mastery_recall"] = mastery_recall
                updates["mastery_application"] = mastery_application
                updates["mastery_explanation"] = mastery_explanation
                # Recalculate overall mastery
                updates["mastery_level"] = calculate_overall_mastery(
                    mastery_recall, mastery_application, mastery_explanation
                )

            # Direct mastery_level override
            if update_data.mastery_level is not None:
                updates["mastery_level"] = update_data.mastery_level

            # Handle spaced repetition (quality rating)
            if update_data.quality is not None:
                mastery_before = current_node.mastery_level

                sm2_result = calculate_next_review(
                    quality=update_data.quality,
                    difficulty=current_node.difficulty,
                    current_ease_factor=current_node.ease_factor,
                    current_interval=current_node.interval_days,
                    current_repetitions=current_node.repetitions,
                    current_mastery=current_node.mastery_level,
                )

                updates["ease_factor"] = sm2_result.ease_factor
                updates["interval_days"] = sm2_result.interval_days
                updates["repetitions"] = sm2_result.repetitions
                updates["next_review_at"] = sm2_result.next_review_at.isoformat()
                updates["last_reviewed_at"] = now
                updates["review_count"] = current_node.review_count + 1

                # Update mastery if suggested
                if sm2_result.suggested_mastery is not None:
                    updates["mastery_level"] = sm2_result.suggested_mastery

                mastery_after = updates.get("mastery_level", current_node.mastery_level)

                # Record review history
                cursor.execute(
                    """INSERT INTO review_history
                    (node_id, quality, mastery_before, mastery_after, notes, misconception_detected)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        node_id,
                        update_data.quality,
                        mastery_before,
                        mastery_after,
                        update_data.notes,
                        update_data.misconception_detected,
                    ),
                )

            # Handle misconception tracking
            if update_data.misconception_detected:
                misconceptions = list(current_node.misconceptions)
                if update_data.misconception_detected not in misconceptions:
                    misconceptions.append(update_data.misconception_detected)
                updates["misconceptions"] = json.dumps(misconceptions)

            # Apply updates
            if updates:
                updates["updated_at"] = now
                set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
                values = list(updates.values()) + [node_id]

                cursor.execute(
                    f"UPDATE nodes SET {set_clause} WHERE id = ?",
                    values,
                )
                conn.commit()

            # Return updated node
            cursor.execute("SELECT * FROM nodes WHERE id = ?", (node_id,))
            row = cursor.fetchone()
            return Node.from_row(dict(row))

    def delete_node(self, node_id: str) -> bool:
        """Delete a node and its associated edges."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ==================== Edge Operations ====================

    def add_edge(self, edge_data: EdgeCreate) -> Edge:
        """
        Add an edge between two concepts.

        Args:
            edge_data: Edge creation data

        Returns:
            Created Edge object

        Raises:
            ValueError: If source/target don't exist or would create cycle
        """
        with get_connection() as conn:
            cursor = conn.cursor()

            # Verify nodes exist
            cursor.execute("SELECT id FROM nodes WHERE id = ?", (edge_data.source_id,))
            if not cursor.fetchone():
                raise ValueError(f"Source node '{edge_data.source_id}' not found")

            cursor.execute("SELECT id FROM nodes WHERE id = ?", (edge_data.target_id,))
            if not cursor.fetchone():
                raise ValueError(f"Target node '{edge_data.target_id}' not found")

            # Check for cycles in prerequisite edges
            if edge_data.relation_type == RelationType.PREREQUISITE:
                if self._would_create_cycle(edge_data.source_id, edge_data.target_id, cursor):
                    raise ValueError(
                        f"Adding prerequisite edge from '{edge_data.source_id}' to "
                        f"'{edge_data.target_id}' would create a cycle"
                    )

            # Check for duplicate edge
            cursor.execute(
                """SELECT 1 FROM edges
                WHERE source_id = ? AND target_id = ? AND relation_type = ?""",
                (edge_data.source_id, edge_data.target_id, edge_data.relation_type.value),
            )
            if cursor.fetchone():
                raise ValueError(
                    f"Edge already exists: {edge_data.source_id} --{edge_data.relation_type.value}--> {edge_data.target_id}"
                )

            # Insert the edge
            cursor.execute(
                """INSERT INTO edges
                (source_id, target_id, relation_type, strength, reasoning)
                VALUES (?, ?, ?, ?, ?)""",
                (
                    edge_data.source_id,
                    edge_data.target_id,
                    edge_data.relation_type.value,
                    edge_data.strength,
                    edge_data.reasoning,
                ),
            )
            conn.commit()

            # Fetch and return the created edge
            cursor.execute(
                """SELECT * FROM edges
                WHERE source_id = ? AND target_id = ? AND relation_type = ?""",
                (edge_data.source_id, edge_data.target_id, edge_data.relation_type.value),
            )
            row = cursor.fetchone()
            return Edge.from_row(dict(row))

    def get_edges(
        self,
        source_id: str | None = None,
        target_id: str | None = None,
        relation_type: RelationType | None = None,
    ) -> list[Edge]:
        """Get edges with optional filtering."""
        with get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM edges WHERE 1=1"
            params = []

            if source_id:
                query += " AND source_id = ?"
                params.append(source_id)
            if target_id:
                query += " AND target_id = ?"
                params.append(target_id)
            if relation_type:
                query += " AND relation_type = ?"
                params.append(relation_type.value)

            cursor.execute(query, params)
            return [Edge.from_row(dict(row)) for row in cursor.fetchall()]

    def delete_edge(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
    ) -> bool:
        """Delete a specific edge."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """DELETE FROM edges
                WHERE source_id = ? AND target_id = ? AND relation_type = ?""",
                (source_id, target_id, relation_type.value),
            )
            conn.commit()
            return cursor.rowcount > 0

    def _would_create_cycle(self, source_id: str, target_id: str, cursor) -> bool:
        """Check if adding an edge would create a cycle in prerequisite graph."""
        # If adding source -> target, check if target can reach source
        visited = set()
        queue = deque([target_id])

        while queue:
            current = queue.popleft()
            if current == source_id:
                return True  # Cycle detected

            if current in visited:
                continue
            visited.add(current)

            # Get prerequisites of current node
            cursor.execute(
                """SELECT source_id FROM edges
                WHERE target_id = ? AND relation_type = ?""",
                (current, RelationType.PREREQUISITE.value),
            )
            for row in cursor.fetchall():
                queue.append(row[0])

        return False

    # ==================== Statistics ====================

    def get_statistics(self, domain: str | None = None) -> dict:
        """Get learning statistics and progress metrics."""
        with get_connection() as conn:
            cursor = conn.cursor()

            domain_clause = "WHERE domain = ?" if domain else ""
            params = [domain] if domain else []

            # Total concepts
            cursor.execute(f"SELECT COUNT(*) FROM nodes {domain_clause}", params)
            total_concepts = cursor.fetchone()[0]

            # Mastery distribution
            mastery_ranges = [
                (0.0, 0.2, "not_started"),
                (0.2, 0.4, "beginning"),
                (0.4, 0.6, "learning"),
                (0.6, 0.8, "proficient"),
                (0.8, 1.01, "mastered"),
            ]

            distribution = {}
            for low, high, label in mastery_ranges:
                query = f"""SELECT COUNT(*) FROM nodes
                    WHERE mastery_level >= ? AND mastery_level < ?
                    {f'AND domain = ?' if domain else ''}"""
                cursor.execute(query, [low, high] + params)
                distribution[label] = cursor.fetchone()[0]

            # Average mastery by domain
            cursor.execute(
                """SELECT domain, AVG(mastery_level) as avg_mastery
                FROM nodes WHERE domain IS NOT NULL
                GROUP BY domain"""
            )
            avg_by_domain = {row[0]: round(row[1], 2) for row in cursor.fetchall()}

            # Due for review count
            now = datetime.now().isoformat()
            query = f"""SELECT COUNT(*) FROM nodes
                WHERE next_review_at IS NOT NULL AND next_review_at <= ?
                {f'AND domain = ?' if domain else ''}"""
            cursor.execute(query, [now] + params)
            due_for_review = cursor.fetchone()[0]

            # Misconceptions count
            query = f"""SELECT COUNT(*) FROM nodes
                WHERE misconceptions IS NOT NULL
                AND misconceptions != '[]' AND misconceptions != ''
                {f'AND domain = ?' if domain else ''}"""
            cursor.execute(query, params)
            misconceptions_count = cursor.fetchone()[0]

            # Struggling concepts (top 5)
            query = f"""SELECT id, concept, mastery_level, difficulty FROM nodes
                WHERE difficulty > 0.5 AND mastery_level < 0.4
                {f'AND domain = ?' if domain else ''}
                ORDER BY (difficulty - mastery_level) DESC LIMIT 5"""
            cursor.execute(query, params)
            struggling = [
                {"id": row[0], "concept": row[1], "mastery": row[2], "difficulty": row[3]}
                for row in cursor.fetchall()
            ]

            # Overall progress (average mastery)
            query = f"SELECT AVG(mastery_level) FROM nodes {domain_clause}"
            cursor.execute(query, params)
            overall_mastery = cursor.fetchone()[0] or 0.0

        return {
            "total_concepts": total_concepts,
            "mastery_distribution": distribution,
            "average_mastery_by_domain": avg_by_domain,
            "overall_mastery": round(overall_mastery, 2),
            "concepts_due_for_review": due_for_review,
            "misconceptions_count": misconceptions_count,
            "struggling_concepts": struggling,
        }

    # ==================== Helpers ====================

    def _generate_node_id(self, concept: str) -> str:
        """Generate a node ID from concept name."""
        # Convert to lowercase, replace spaces with underscores
        node_id = concept.lower()
        node_id = re.sub(r"[^a-z0-9]+", "_", node_id)
        node_id = node_id.strip("_")
        return node_id or "node"

    def resolve_node_id(self, identifier: str) -> str | None:
        """Resolve a node identifier (ID or concept name) to node ID."""
        # First try as ID
        node = self.get_node(identifier)
        if node:
            return node.id

        # Try as concept name
        node = self.get_node_by_concept(identifier)
        if node:
            return node.id

        # Try generating ID from concept
        generated_id = self._generate_node_id(identifier)
        node = self.get_node(generated_id)
        if node:
            return node.id

        return None
