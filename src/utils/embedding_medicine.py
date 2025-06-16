from src.database import MySQLConnector
from src.config.configs import *
from mysql.connector.cursor import MySQLCursorDict
from loguru import logger
import json
from tqdm import tqdm
from src.database.qdrant import QdrantVectorStore
from langchain_core.documents import Document


connector = MySQLConnector()

def process_overlap(text:str):
    if not text:
        return []
    
    lines = text.split("\n")
    
    prefix = lines[0]
    contents = lines[1:]

    result = []
    current = ""

    for line in contents:
        if len(current.split()) + len(line.split()) + 1 < 100:
            current += line + " "
        else:
            result.append(f"{prefix} {current.strip()}")
            current = line + " "

    if current.strip():
        result.append(f"{prefix} {current.strip()}")

    return result

def process_qa_doc(text:str, name:str):
    if not text:
        return []
    result = []
    qa_pair = text.split("||")
    for pair in qa_pair:
        if pair:
            pair = f"Câu hỏi dành cho {name}: " + pair
            pair = pair.replace("|", "\n Trả lời: ")
            result.append(pair)
    return result


def split_document():
    connector.create_table("chunks")
    data_length = connector.custom_query("SELECT COUNT(*) FROM medicine_detailt",cursor_template=MySQLCursorDict)
    data_length = list(data_length[0].values())[0]
    metadata_key = ["name", "type", "specification", "assign", "preservation", 
                    "ingredient", "price"]
    embedding_text = ['short_description',
                      "useage", "dosage", "adverseEffect", 
                      "careful"]
    
    pair_doc = ["FAQ", "rate", "QA"]

    for idx in tqdm(range(0 ,data_length, 100)):
        data = connector.custom_query(f"SELECT * FROM medicine_detailt LIMIT {idx}, 100",
                                      cursor_template=MySQLCursorDict)
        for medicine in data:
            chunks = []
            name = medicine.get('name', "UNKOWNED")
            metadata = {key: medicine.get(key, "") for key in metadata_key}
            metadata = json.dumps(metadata, ensure_ascii=False)
            for text_field in embedding_text:
                text = medicine.get(text_field)
                split_chunks = process_overlap(text)
                chunks.extend([(name + " " + t, metadata) for t in split_chunks])
            
            chunks.append((medicine.get("short_description", ""), metadata))
            FAQ, rate , QA = [medicine.get(key) for key in pair_doc]
            chunks.extend([(t, metadata) for t in FAQ.split("|")])
            chunks.extend([(t, metadata) for t in process_qa_doc(rate, name= name)])
            chunks.extend([(t, metadata) for t in process_qa_doc(QA, name= name)])

            connector.insert_to_chunks(chunks)


def embedding_and_insert_qdrand():
    data_length = connector.custom_query("SELECT COUNT(*) FROM chunks",cursor_template=MySQLCursorDict)
    data_length = list(data_length[0].values())[0]
    
    qdrant = QdrantVectorStore(QDRANT_COLLECTION)
    qdrant.create_collection()

    for idx in tqdm(range(0 ,data_length, 50)):
        data = connector.custom_query(f"SELECT * FROM chunks LIMIT {idx}, 50",
                                      cursor_template=MySQLCursorDict)

        docs = [Document(page_content=medicine.get("text", ""),
                        metadata = json.loads(medicine.get("metadata", "{}")))
                        for medicine in data]
        qdrant.add_documents(docs)

if __name__ == "__main__":
    # split_document()
    embedding_and_insert_qdrand()