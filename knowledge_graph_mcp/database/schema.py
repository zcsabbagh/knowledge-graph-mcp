"""SQLite schema definitions for the knowledge graph."""

NODES_TABLE = """
CREATE TABLE IF NOT EXISTS nodes (
    id TEXT PRIMARY KEY,
    concept TEXT NOT NULL,
    description TEXT,
    domain TEXT,

    -- Mastery tracking (0.0 - 1.0)
    mastery_level REAL DEFAULT 0.0,
    mastery_recall REAL DEFAULT 0.0,
    mastery_application REAL DEFAULT 0.0,
    mastery_explanation REAL DEFAULT 0.0,

    -- Spaced repetition fields
    difficulty REAL DEFAULT 0.5,
    ease_factor REAL DEFAULT 2.5,
    interval_days INTEGER DEFAULT 0,
    repetitions INTEGER DEFAULT 0,
    last_reviewed_at TEXT,
    next_review_at TEXT,
    review_count INTEGER DEFAULT 0,

    -- Metadata
    tags TEXT,
    misconceptions TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
"""

EDGES_TABLE = """
CREATE TABLE IF NOT EXISTS edges (
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    strength REAL DEFAULT 1.0,
    reasoning TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (source_id, target_id, relation_type),
    FOREIGN KEY (source_id) REFERENCES nodes(id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES nodes(id) ON DELETE CASCADE
);
"""

REVIEW_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS review_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL,
    reviewed_at TEXT DEFAULT (datetime('now')),
    quality INTEGER,
    mastery_before REAL,
    mastery_after REAL,
    notes TEXT,
    misconception_detected TEXT,
    FOREIGN KEY (node_id) REFERENCES nodes(id) ON DELETE CASCADE
);
"""

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_nodes_domain ON nodes(domain);",
    "CREATE INDEX IF NOT EXISTS idx_nodes_mastery ON nodes(mastery_level);",
    "CREATE INDEX IF NOT EXISTS idx_nodes_next_review ON nodes(next_review_at);",
    "CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);",
    "CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);",
    "CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(relation_type);",
    "CREATE INDEX IF NOT EXISTS idx_review_node ON review_history(node_id);",
    "CREATE INDEX IF NOT EXISTS idx_review_date ON review_history(reviewed_at);",
]


def create_tables(cursor) -> None:
    """Create all tables and indexes."""
    cursor.execute(NODES_TABLE)
    cursor.execute(EDGES_TABLE)
    cursor.execute(REVIEW_HISTORY_TABLE)
    for index in INDEXES:
        cursor.execute(index)
