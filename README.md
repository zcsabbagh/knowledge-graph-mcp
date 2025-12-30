<!-- mcp-name: io.github.zcsabbagh/knowledge-graph-mcp -->

# Knowledge Graph MCP Server

An MCP (Model Context Protocol) server for tracking student learning via a knowledge graph. Built with FastMCP, it enables LLMs to build, query, and update a personalized knowledge map with spaced repetition scheduling.

## Features

- **Knowledge Graph Storage**: SQLite-backed graph with concepts as nodes and relationships as edges
- **Multi-dimensional Mastery Tracking**: Track recall, application, and explanation abilities separately
- **Spaced Repetition (SM-2)**: Automatic scheduling of review sessions based on performance
- **Misconception Tracking**: Record and query common misconceptions for targeted remediation
- **Intelligent Queries**: Find knowledge gaps, ready-to-learn concepts, struggling areas
- **Mermaid Visualization**: Generate visual diagrams of the knowledge graph

## Installation

### Option 1: Install from Smithery (Recommended)

Install directly via [Smithery](https://smithery.ai):

```bash
npx @smithery/cli install @zcsabbagh/knowledge-graph-mcp --client claude
```

Or use the hosted version at: **https://smithery.ai/server/@zcsabbagh/knowledge-graph-mcp**

### Option 2: Install from source

Prerequisites: Python 3.10+

```bash
git clone https://github.com/zcsabbagh/knowledge-graph-mcp.git
cd knowledge-graph-mcp
pip install -e .
```

## Usage

### Running the Server

```bash
# From the project root
python -m knowledge_graph_mcp.server
```

### Configure with Claude Code

Add to your Claude Code MCP settings (`~/.claude/settings.json`):

```json
{
  "mcpServers": {
    "knowledge-graph": {
      "command": "python",
      "args": ["-m", "knowledge_graph_mcp.server"],
      "cwd": "/path/to/knowledge-graph-mcp"
    }
  }
}
```

### Configure with Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "knowledge-graph": {
      "command": "python",
      "args": ["-m", "knowledge_graph_mcp.server"],
      "cwd": "/path/to/knowledge-graph-mcp"
    }
  }
}
```

## MCP Tools

### 1. `add_node`
Create a new concept node.

```
add_node(
  concept="Quadratic Formula",
  description="Formula for solving ax² + bx + c = 0",
  domain="mathematics",
  difficulty=0.7,
  tags=["algebra", "formulas"]
)
```

### 2. `add_edge`
Create relationships between concepts.

**Relation types:**
- `prerequisite` - Must learn source before target
- `builds_on` - Target extends source concept
- `related_to` - Concepts are connected
- `contradicts` - Common misconception
- `applies_to` - Application domain
- `parent_of` - Category hierarchy

```
add_edge(
  source_concept="Algebra",
  target_concept="Quadratic Formula",
  relation_type="prerequisite"
)
```

### 3. `update_node`
Update mastery and record reviews. Providing a `quality` rating (0-5) triggers spaced repetition scheduling.

```
update_node(
  node_id="quadratic_formula",
  quality=4,  # SM-2 rating: 0=blackout, 5=perfect
  mastery_application=0.6,
  misconception_detected="forgets ± sign"
)
```

### 4. `query_graph`
Intelligent queries for learning insights.

**Query types:**
- `prerequisites` - All prerequisites for a concept
- `ready_to_learn` - Concepts where prereqs are mastered
- `due_for_review` - Needs review based on schedule
- `struggling` - High difficulty + low mastery
- `stalled` - Multiple reviews, no improvement
- `misconceptions` - Concepts with detected misconceptions
- `knowledge_gaps` - Low mastery blocking progress
- `next_recommended` - Best concept to study next

```
query_graph(query_type="next_recommended", domain="mathematics")
```

### 5. `read_subgraph`
Get the neighborhood around a concept with Mermaid visualization.

```
read_subgraph(
  center_node="calculus",
  depth=2,
  direction="upstream",  # or "downstream", "both"
  output_format="both"   # "json", "mermaid", or "both"
)
```

### 6. `get_learning_path`
Get ordered prerequisites for a target concept.

```
get_learning_path(target_concept="calculus")
```

### 7. `get_statistics`
Get learning progress metrics.

```
get_statistics(domain="mathematics")
```

## How It Works

### Data Model

**Nodes** represent concepts with:
- Mastery levels (overall, recall, application, explanation)
- Spaced repetition data (ease factor, interval, next review date)
- Difficulty rating and review history
- Tags and detected misconceptions

**Edges** represent relationships with:
- Relation type (prerequisite, builds_on, etc.)
- Strength/confidence rating
- Optional reasoning

### Spaced Repetition (SM-2)

When you call `update_node` with a `quality` rating:
- **5**: Perfect response → longer interval
- **4**: Correct with hesitation
- **3**: Correct with difficulty
- **2-0**: Incorrect → reset interval

The algorithm calculates the next optimal review date based on performance history.

### Mastery Calculation

Overall mastery combines dimensional scores:
```
mastery_level = 0.3 × recall + 0.4 × application + 0.3 × explanation
```

### Storage

Data is stored in SQLite at `~/.knowledge_graph/knowledge.db` by default.

## Example Workflow

```
1. LLM discovers student doesn't know "quadratic formula"
   → add_node(concept="Quadratic Formula", difficulty=0.7)

2. LLM identifies prerequisites
   → add_edge("Algebra", "Quadratic Formula", "prerequisite")

3. Student attempts problem, struggles
   → update_node("quadratic_formula", quality=2,
                 misconception_detected="confuses ± with +")

4. LLM decides what to teach next
   → query_graph("next_recommended")

5. Visualize the learning path
   → get_learning_path("quadratic_formula")
```

## License

MIT
