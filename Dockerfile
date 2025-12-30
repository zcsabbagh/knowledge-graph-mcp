# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir fastmcp pydantic uvicorn

# Copy application code
COPY . .

# Create data directory for SQLite
RUN mkdir -p /data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV KNOWLEDGE_GRAPH_DB_PATH=/data/knowledge.db

# Expose the port Smithery will use
EXPOSE 8081

# Run the server
CMD ["python", "-m", "knowledge_graph_mcp.server"]
