from langchain.tools import tool
from typing import List
from src.config.configs import *
from loguru import logger
import json
from collections import defaultdict
from src.database.neo4j_graph_db import Neo4j
from src.database.qdrant import QdrantVectorStore

neo4j_connector = Neo4j()
qdrant_connector = QdrantVectorStore(collection_name=QDRANT_COLLECTION)


@tool
def search_by_name(user_query: str, neo4j_connector= neo4j_connector, top_k:int = 5) -> List[List[str]]:
    """
    Search for medicine information in the Neo4j graph database based on a keyword or partial name.

    This function extracts the medicine name from the `user_query`, performs a regex-based
    search using the Neo4j connector, and returns detailed information (metadata) about 
    all matching medicines as a formatted string.

    Note:
        This function is for retrieving detailed information about a specific medicine 
        (or list of matching medicines) and is NOT used for recommending alternative medicines.

    Args:
        user_query (str):
            The input query string from the user. If the query contains a '|' character,
            only the part after the last '|' is treated as the medicine name for searching.

    Returns:
        str:
            A formatted string containing the name and metadata of each matching medicine 
            found in the Neo4j database.
    """
    
    logger.success("Using search by find exact name with query: {}", user_query)
    result = neo4j_connector.find_medicine_regex(user_query)
    text = ""

    for r in result[:top_k]:
        r.pop("id")
        text += r.get('name', "")
        text += "  ".join([f"{key} : {value}" for key, value in json.loads(r['metadata']).items()]) + " \n "

    logger.info("Neo4j_search: {}", text)

    return text

@tool
def search_by_query(user_query: str, qdrant_connector = qdrant_connector) -> List[List[str]]:
    """ Used in cases where the user's question does not refer to any object, or is about an object unrelated to basic knowledge such as: name, type, specification, assign, short_description, ingredient, price

        Args:
            user_query (str): The query of user using to search in vector database.
        Returns:
            List[List[str]]: top 5 results with the most similar query
    """

    logger.success("Using search by Qdrant with query: {}", user_query)
    split_text = user_query.split("|")
    medicine_name = split_text[0]
    vector_result = qdrant_connector.search(query=medicine_name)
    
    result = ""

    for r in vector_result:
        result += r.payload.get('text', "") + "\n"

    logger.info("Qdrant_search: {}", result)

    return result

@tool
def recommend_alternatives(keyword, top_k=5, searcher = neo4j_connector):
    """
    Recommend alternative medicines based on medicine type and indications using a Neo4j graph database.

    This function performs the following steps:
        1. Finds the medicine node(s) matching the given keyword using regex search.
        2. Selects the best matching medicine as the target.
        3. Retrieves the medicine's types and indications.
        4. Finds other medicines that share the same type(s) or indication(s).
        5. Scores alternative medicines based on how many attributes they share with the target medicine.
           (1 point for same type, 1 point for same indication)
        6. Returns the top_k alternative medicines sorted by their relevance score.

    Args:
        searcher (GraphSearcher): 
            An instance of GraphSearcher used to query the Neo4j database.
        keyword (str): 
            A keyword or partial name used to search for the target medicine.
        top_k (int, optional): 
            The maximum number of alternative medicines to return. Defaults to 5.

    Returns:
        list of dict: 
            A list of dictionaries representing the recommended alternative medicines. 
            Each dictionary contains:
                - 'metadata' (dict): Metadata of similarity medicine found.
    """

    logger.info("Find similarity medicine with query: {}", keyword)

    candidates = searcher.find_medicine_regex(keyword, case_insensitive=True)
    if not candidates:
        return []
    medicine = candidates[0]
    medicine_id = medicine["id"]

    types = searcher.find_relations(medicine_id, "LOẠI THUỐC")
    inds  = searcher.find_relations(medicine_id, "CHỈ ĐỊNH")
    ingres = searcher.find_relations(medicine_id, "THÀNH PHẦN")

    alts_type = []
    for t in types:
        meds = searcher.find_relations(t["id"], "LOẠI THUỐC", direction="in")
        alts_type += meds

    alts_ind = []
    for ind in inds:
        meds = searcher.find_relations(ind["id"], "CHỈ ĐỊNH", direction="in")
        alts_ind += meds

    alts_ingre = []
    for ind in ingres:
        meds = searcher.find_relations(ind["id"], "THÀNH PHẦN", direction="in")
        alts_ingre += meds
    scores = defaultdict(lambda: [0, None])

    for m in alts_type:
        if m["id"] != medicine_id:
            scores[m["name"]][0] += 1
            scores[m["name"]][1] = m.get("metadata", "{}")

    for m in alts_ind:
        if m["id"] != medicine_id:
            scores[m["name"]][0] += 1
            scores[m["name"]][1] = m.get("metadata", "{}")

    for m in alts_ingre:
        if m["id"] != medicine_id:
            scores[m["name"]][0] += 1
            scores[m["name"]][1] = m.get("metadata", "{}")
    

    recs = [{"name": n, "score": s[0], "metadata" : s[1]} for n, s in scores.items()]
    recs.sort(key=lambda x: -x["score"])

    result_match = ""
    for rec in recs[:top_k]:
        metadata = json.loads(rec.get('metadata', ""))
        result_match += f"Tên: {rec.get('name', "")} "
        result_match += f"Miêu tả ngắn: {metadata.get('short_description', "")}"
        result_match += "\n"

    logger.info("Similarity result: {}", result_match)

    return result_match

@tool
def recommend_by_indications(indications: List[str], top_k=5, searcher = neo4j_connector):
    """
        Recommend medicines based on given indication keywords.

        Matches medicines that have CHỈ_ĐỊNH relationships to nodes whose 'name' property matches provided keywords.
        Scores each medicine by the number of matching indications and returns top hits.

        :param indications: List of indication keywords to match (substring match).
        :param min_match: Minimum number of indication matches required to include a medicine.
        :param limit: Maximum number of medicine recommendations to return.
        :return: List of dicts with keys 'medicine' (node properties) and 'match_count'.
        """
    data = searcher.find_medicines_by_indications(indications=indications)
    result = ""
    for d in data[:top_k]:
        medicine_infor = d.get('medicine')
        metadata = json.loads(medicine_infor.get('metadata', {}))
        result += f"Tên: {medicine_infor.get('name', "")} "
        result += f"Miêu tả ngắn: {metadata.get('short_description', "")}"
        result += f"Thành phần: {metadata.get('ingredient', "")}"
        result += "\n"
    
    logger.info("Using recommend_by_indications tools with result: {}", result)
    return result