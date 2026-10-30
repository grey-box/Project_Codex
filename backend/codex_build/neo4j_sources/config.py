"""
Project Codex — Neo4j Connection Configuration
"""

import os
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI      = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
NEO4J_USER     = os.getenv("NEO4J_USER",     "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "changeme")

# Paths
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_DATA_DIR = os.path.join(BASE_DIR, "sample_data")
CYPHER_DIR      = os.path.join(BASE_DIR, "cypher")

API_TITLE       = "Project Codex API"
API_DESCRIPTION = "REST API for cross-country drug name translation and lookup, backed by Neo4j."
API_VERSION     = "0.1.0"