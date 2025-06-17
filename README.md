# Medicine RAG Chatbot

This project is a chatbot that uses a Retrieval-Augmented Generation (RAG) system to answer questions about medicines. It uses a combination of a Neo4j graph database and a Qdrant vector database to retrieve information.

## Features

- **Chatbot Interface**: A user-friendly interface built with Gradio to interact with the chatbot.
- **RAG Agent**: An intelligent agent that can understand user queries, plan execution steps, and generate responses based on retrieved information.
- **Multi-source Retrieval**: Retrieves information from both a Neo4j graph database for structured data and a Qdrant vector database for unstructured data.
- **Tools**: The agent is equipped with the following tools:
    - `search_by_name`: Search for medicine information by its name.
    - `search_by_query`: Search for medicine information using a natural language query.
    - `recommend_alternatives`: Recommend alternative medicines.
    - `recommend_by_indications`: Recommend medicines based on symptoms or indications.

## Project Structure

```
medicine/
├── docker/
│   └── docker-compose.yml
├── main.py
├── requirements.txt
└── src/
    ├── agent/
    │   ├── agent.py
    │   └── tools.py
    ├── config/
    │   └── configs.py
    ├── database/
    │   ├── mysql_connector.py
    │   ├── neo4j_graph_db.py
    │   └── qdrant.py
    ├── models/
    │   └── medicine_detail.py
    └── utils/
        └── embedding_medicine.py
```

## How to Run

### 1. Prerequisites

- Python 3.8+
- Docker and Docker Compose

### 2. Setup Environment

Create a `.env` file in the root directory and add the following environment variables. You can get the `GOOGLE_API_KEY` from [Google AI Studio](https://aistudio.google.com/):

```
GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY"
EMBEDDING_MODEL="Sentence Transformer Model"
QDRANT_COLLECTION="Qdrant collection"

```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Start Services

This project uses Neo4j, MySQL, and Qdrant as services. You can start them using Docker Compose:

```bash
docker-compose -f docker/docker-compose.yml up -d
```

**Note**: The `docker-compose.yml` file in the `docker` directory might have some indentation issues. Please make sure to fix them before running the command.

### 5. Run process data

Import data to sql from this file: ```(updating)```

```bash

python src/utils/embedding_medicine.py -h
usage: embedding_medicine.py [-h] [--is_spliting_chunks] [--embedding_index EMBEDDING_INDEX] [--is_insert_neo4j]

Script xử lý dữ liệu với tuỳ chọn.

options:
  -h, --help            show this help message and exit
  --is_spliting_chunks  Chia dữ liệu thành chunks hay không (bool).
  --embedding_index EMBEDDING_INDEX
                        Vị trí index hiện tại trong embedding (int).
  --is_insert_neo4j     Có insert vào Neo4j hay không (bool).

```

### 6. Run the Application

```bash
python main.py
```


This will start the Gradio interface at `http://localhost:8080`.

## How it Works

The application uses a RAG agent to answer questions about medicines. The agent is built using `langgraph` and consists of three main components:

1.  **Planner**: This component receives the user's question and creates a plan of execution. It decides which tool to use based on the user's intent.
2.  **Executor**: This component executes the plan created by the planner. It calls the appropriate tool with the given query and retrieves the information.
3.  **Summarizer**: This component receives the information from the executor and generates a final response to the user.

The agent uses a combination of a Neo4j graph database and a Qdrant vector database to retrieve information. The Neo4j database stores structured information about medicines, such as their names, types, and indications. The Qdrant database stores unstructured information, such as descriptions and usage instructions. 