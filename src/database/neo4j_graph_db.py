from neo4j import GraphDatabase
import uuid
import os
from src.config.configs import *
from src.database import MySQLConnector
from loguru import logger
from typing import List, Any, Dict, Optional
from collections import defaultdict
import json


class Neo4j: 
    def __init__(self, uri:str = NEO4J_URI, user:str = NEO4J_USERNAME,
                 password:str = NEO4J_PASSWORD):
        
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.mysql_conntector = MySQLConnector()
    
    def insert_to_db(self):
        query = f"SELECT name, type, assign, ingredient, specification, short_description, price, note FROM medicine_detailt where assign != ''"
        
        data = self.mysql_conntector.custom_query(query)

        nodes = {}
        relationships = []
        for d in data:
            name, type, assign, ingredient = d[:4]
            name, type, assign, ingredient = name.lower(), type.lower(), assign.lower(), ingredient.lower()

            if name not in nodes:
                meta_data = dict(zip(["specification", "short_description", "price", "note"], d[4:]))
                nodes[name] = (str(uuid.uuid4()), meta_data)

            if type and type not in nodes:
                nodes[type] = (str(uuid.uuid4()), {})
            relationships.append({
                "source": nodes[name][0],
                "target": nodes[type][0],
                "type": "LOẠI THUỐC"
            })

            assigns_list = assign.split(",")
            for assign_object in assigns_list:
                assign_object = assign_object.strip()
                if assign_object:
                    if assign_object not in nodes:
                        nodes[assign_object] = (str(uuid.uuid4()), {})
                    relationships.append({
                        "source": nodes[name][0],
                        "target": nodes[assign_object][0],
                        "type": "CHỈ ĐỊNH"})
            try:    
                ingredient_list = ingredient.split("\n")
                keyword_wrap = ingredient_list.index("hàm lượng")
                
                for ingredient_object in ingredient_list[keyword_wrap+1::2]:
                    ingredient_object = ingredient_object.strip()
                    if ingredient_object:
                        if ingredient_object not in nodes:
                            nodes[ingredient_object] = (str(uuid.uuid4()), {})
                        relationships.append({
                            "source": nodes[name][0],
                            "target": nodes[ingredient_object][0],
                            "type": "THÀNH PHẦN"})
            except Exception as err:
                print(f"err: {err}, ingredient:{ingredient}")
                        
        with self.driver.session() as session: 
            for name, node_data in nodes.items():
                node_id, meta_data = node_data
                session.run(
                    "CREATE (n:Entity {id: $id, name: $name, metadata: $metadata})",
                    id=node_id,
                    name=name,
                    metadata=json.dumps(meta_data, ensure_ascii=False)
                )

            # Create relationships in Neo4j
            for relationship in relationships:
                session.run(
                    "MATCH (a:Entity {id: $source_id}), (b:Entity {id: $target_id}) "
                    "CREATE (a)-[:RELATIONSHIP {type: $type}]->(b)",
                    source_id=relationship["source"],
                    target_id=relationship["target"],
                    type=relationship["type"]
                )


    def find_medicine_exact(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Find a medicine node by its exact name.
        :param name: Exact medicine name to search
        :return: Properties of the medicine node or None if not found
        """
        query = (
            'MATCH (d: Entity) '
            'WHERE d.name = $name '
            'RETURN d LIMIT 1'
        )
        with self.driver.session() as session:
            record = session.run(query, name=name).single()
            return dict(record["d"]) if record else None

    def find_medicine_regex(self, pattern: str, case_insensitive: bool = True) -> List[Dict[str, Any]]:
        """
        Find medicine nodes whose names match a regex or contain a substring.
        Uses Cypher regex (operator =~) or CONTAINS for substring search.
        :param pattern: Regex pattern or substring
        :param case_insensitive: If True, perform case-insensitive match
        :return: List of medicine node properties matching the pattern
        """
        # Build Cypher condition
        if case_insensitive:
            # convert both sides to lowercase for contains
            # use CONTAINS for substring fallback
            cypher = (
                'MATCH (d: Entity) '
                'WHERE toLower(d.name) CONTAINS toLower($pattern) '
                'RETURN d'
            )
            params = {"pattern": pattern}
        else:
            cypher = (
                'MATCH (d: Entity) '
                'WHERE d.name =~ $pattern '
                'RETURN d'
            )
            params = {"pattern": pattern}

        with self.driver.session() as session:
            result = session.run(cypher, **params)
            return [dict(record["d"]) for record in result]

    def find_relations(
        self,
        start_id: int,
        rel_type: str,
        direction: str = "out",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Find related nodes from a start node by relationship type.
        :param start_id: Internal Neo4j node ID (integer)
        :param rel_type: Relationship type (e.g., "CHỈ_ĐỊNH")
        :param direction: "out" for outgoing, "in" for incoming relationships
        :param limit: Maximum number of results to return
        :return: List of properties dicts for related nodes
        """
        if direction == "out":
            pattern = f"(n)-[r:RELATIONSHIP]->(m)"
        else:
            pattern = f"(m)-[r:RELATIONSHIP]->(n)"

        query = (
            f"MATCH {pattern} "
            "WHERE n.id = $id and r.type=$type "
            "RETURN m LIMIT $limit"
        )
        with self.driver.session() as session:
            result = session.run(query, id=start_id, type = rel_type, limit=limit)
            return [dict(record["m"]) for record in result]

    def find_path(
        self,
        start_id: int,
        end_id: int,
        max_hops: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Find simple paths between two nodes up to a certain length.
        :param start_id: Neo4j internal ID of the start node
        :param end_id: Neo4j internal ID of the end node
        :param max_hops: Maximum number of relationships in the path
        :return: List of path dicts with nodes and relationships
        """
        query = (
            'MATCH path = (start)-[*1..$max_hops]-(end) '
            'WHERE id(start) = $start_id AND id(end) = $end_id '
            'RETURN path'
        )
        with self.driver.session() as session:
            result = session.run(
                query,
                start_id=start_id,
                end_id=end_id,
                max_hops=max_hops
            )
            paths = []
            for record in result:
                p = record["path"]
                nodes = [dict(node) for node in p.nodes]
                rels = [
                    {"type": type(rel).__name__, "properties": dict(rel)}
                    for rel in p.relationships
                ]
                paths.append({"nodes": nodes, "rels": rels})
            return paths

    def find_medicines_by_indications(
        self,
        indications: List[str],
        min_match: int = 1,
    ) -> List[Dict[str, Any]]:
        query = (
            "UNWIND $inds AS ind_key "
            "MATCH (d)-[r]->(i) "
            "WHERE toLower(i.name) CONTAINS toLower(ind_key) AND r.type='CHỈ ĐỊNH'"
            "WITH d, count(i) AS match_count "
            "WHERE match_count >= $min_match "
            "RETURN d, match_count "
            "ORDER BY match_count DESC "
        )
        with self.driver.session() as session:
            result = session.run(query, inds=indications, min_match=min_match)
            recommendations = []
            for record in result:
                medicine_props = dict(record['d'])
                recommendations.append({
                    'medicine': medicine_props,
                    'match_count': record['match_count']
                })
            return recommendations



if __name__ == '__main__':
    db = Neo4j()
    # db.insert_to_db()
    # print(db.find_relations("29fb1c9c-98ae-4ec4-8ded-6b3649acc272", 'CHỈ ĐỊNH'))
    print(db.find_medicines_by_indications(['sốt', 'đau đầu'], min_match=2))