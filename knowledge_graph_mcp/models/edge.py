"""Edge models for the knowledge graph."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from .enums import RelationType


class EdgeCreate(BaseModel):
    """Input model for creating an edge."""

    source_id: str = Field(..., description="Source node ID")
    target_id: str = Field(..., description="Target node ID")
    relation_type: RelationType = Field(..., description="Type of relationship")
    strength: float = Field(default=1.0, ge=0.0, le=1.0, description="Relationship strength")
    reasoning: Optional[str] = Field(None, description="Why this relationship exists")


class Edge(BaseModel):
    """Full edge model."""

    source_id: str
    target_id: str
    relation_type: RelationType
    strength: float = 1.0
    reasoning: Optional[str] = None
    created_at: Optional[datetime] = None

    @classmethod
    def from_row(cls, row: dict) -> "Edge":
        """Create an Edge from a database row."""
        data = dict(row)

        # Parse datetime
        if data.get("created_at"):
            try:
                data["created_at"] = datetime.fromisoformat(data["created_at"])
            except (ValueError, TypeError):
                data["created_at"] = None

        # Parse relation_type enum
        if isinstance(data.get("relation_type"), str):
            data["relation_type"] = RelationType(data["relation_type"])

        return cls(**data)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "strength": self.strength,
            "reasoning": self.reasoning,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
