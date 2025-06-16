import os
from dotenv import load_dotenv
load_dotenv()


REVIEW_API_URL=os.getenv("REVIEW_API_URL")
COMMENT_API_URL=os.getenv("COMMENT_API_URL")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "")
EMBEDDING_API = os.getenv("EMBEDDING_API", "")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "test")
GOOGLE_API_KEY= os.getenv("GOOGLE_API_KEY", "")
LLM_MODEL= os.getenv("LLM_MODEL","gemini-1.5-flash")
NEO4J_URI=os.getenv("NEO4J_URI", "0.0.0.0:7687")
NEO4J_USERNAME=os.getenv("NEO4J_USERNAME","neo4j")
NEO4J_PASSWORD=os.getenv("NEO4J_PASSWORD","password")

