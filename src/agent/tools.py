from langchain.tools import tool
from src.database.mysql import MySQLConnector
from src.database.qdrant import QdrantVectorStore
from typing import List
from src.config.configs import *
from loguru import logger

mysql_connector = MySQLConnector()
qdrant_connector = QdrantVectorStore(collection_name=QDRANT_COLLECTION)
@tool
def search_by_name(name: str) -> List[List[str]]:
    """ Search for exact information of a drug name in the database.
        A drug will have 4 information you can query: name, type, specification, assign, short_description, ingredient, price, note.

        Args:
            name (str): the name of the drug to query, capitalized. This is an object that is the name of a medicine that appears in the query.
        Returns:
            List[List[str]]: top 5 results with the most similar query
    """
    
    query = f"SELECT name, type, specification, assign, short_description, ingredient, price, note FROM medicine_detailt WHERE name like '%{name}%' LIMIT 5"

    logger.info(f"query: {query}")

    result = mysql_connector.custom_query(query=query)

    logger.debug("Result: {}", result)

    text = ""

    for r in result:
        text += " , ".join(r) + " \n "

    return text
