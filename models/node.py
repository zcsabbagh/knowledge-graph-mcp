"""Node models for the knowledge graph."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
import json


class NodeCreate(BaseModel):
    """Input model for creating a node."""

    concept: str = Field(..., description="Human-readable concept name")
    description: Optional[str] = Field(None, description="Detailed description")
    domain: Optional[str] = Field(None, description="Domain/category (e.g., 'mathematics')")
    difficulty: float = Field(default=0.5, ge=0.0, le=1.0, description="Cognitive load (0-1)")
    tags: list[str] = Field(default_factory=list, description="Categorization tags")
    node_id: Optional[str] = Field(None, description="Custom ID (auto-generated if not provided)")


class NodeUpdate(BaseModel):
    """Model for updating node fields."""

    concept: Optional[str] = None
    description: Optional[str] = None
    domain: Optional[str] = None
    difficulty: Optional[float] = Field(None, ge=0.0, le=1.0)

    # Mastery fields
    mastery_level: Optional[float] = Field(None, ge=0.0, le=1.0)
    mastery_recall: Optional[float] = Field(None, ge=0.0, le=1.0)
    mastery_application: Optional[float] = Field(None, ge=0.0, le=1.0)
    mastery_explanation: Optional[float] = Field(None, ge=0.0, le=1.0)

    # Review tracking
    quality: Optional[int] = Field(None, ge=0, le=5, description="SM-2 quality (0-5)")
    misconception_detected: Optional[str] = None
    notes: Optional[str] = None


class Node(BaseModel):
    """Full node model with all fields."""

    id: str
    concept: str
    description: Optional[str] = None
    domain: Optional[str] = None

    # Mastery tracking
    mastery_level: float = 0.0
    mastery_recall: float = 0.0
    mastery_application: float = 0.0
    mastery_explanation: float = 0.0

    # Spaced repetition
    difficulty: float = 0.5
    ease_factor: float = 2.5
    interval_days: int = 0
    repetitions: int = 0
    last_reviewed_at: Optional[datetime] = None
    next_review_at: Optional[datetime] = None
    review_count: int = 0

    # Metadata
    tags: list[str] = Field(default_factory=list)
    misconceptions: list[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_row(cls, row: dict) -> "Node":
        """Create a Node from a database row."""
        data = dict(row)

        # Parse JSON fields
        if data.get("tags"):
            try:
                data["tags"] = json.loads(data["tags"])
            except (json.JSONDecodeError, TypeError):
                data["tags"] = []
        else:
            data["tags"] = []

        if data.get("misconceptions"):
            try:
                data["misconceptions"] = json.loads(data["misconceptions"])
            except (json.JSONDecodeError, TypeError):
                data["misconceptions"] = []
        else:
            data["misconceptions"] = []

        # Parse datetime fields
        for field in ["last_reviewed_at", "next_review_at", "created_at", "updated_at"]:
            if data.get(field):
                try:
                    data[field] = datetime.fromisoformat(data[field])
                except (ValueError, TypeError):
                    data[field] = None

        return cls(**data)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "concept": self.concept,
            "description": self.description,
            "domain": self.domain,
            "mastery_level": self.mastery_level,
            "mastery_recall": self.mastery_recall,
            "mastery_application": self.mastery_application,
            "mastery_explanation": self.mastery_explanation,
            "difficulty": self.difficulty,
            "ease_factor": self.ease_factor,
            "interval_days": self.interval_days,
            "repetitions": self.repetitions,
            "last_reviewed_at": self.last_reviewed_at.isoformat() if self.last_reviewed_at else None,
            "next_review_at": self.next_review_at.isoformat() if self.next_review_at else None,
            "review_count": self.review_count,
            "tags": self.tags,
            "misconceptions": self.misconceptions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
