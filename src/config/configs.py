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
MYSQL_URL=os.getenv("MYSQL_URL", "127.0.0.1")
MYSQL_PORT=os.getenv('MYSQL_PORT', "3306")
MYSQL_NAME=os.getenv("MYSQL_NAME", "admin")
MYSQL_PASSWORD=os.getenv("MYSQL_PASSWORD", "test")
MYSQL_DB=os.getenv("MYSQL_DB", "medicine")
NEO4J_URI=os.getenv("NEO4J_URI", "neo4j://localhost:7687")
NEO4J_USERNAME=os.getenv("NEO4J_USERNAME","neo4j")
NEO4J_PASSWORD=os.getenv("NEO4J_PASSWORD","password")

