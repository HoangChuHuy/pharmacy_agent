from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.memory import ConversationBufferMemory
from src.config.configs import *
from loguru import logger
from src.agent.tools import search_by_name, search_by_query, recommend_alternatives, recommend_by_indications
from langchain.prompts import PromptTemplate
import json


import warnings
warnings.filterwarnings('ignore')



class RAGAgentSystem:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model=LLM_MODEL, 
            google_api_key=GOOGLE_API_KEY,
            temperature=0.0,
            convert_system_message_to_human=True
        )
        self.tools = {
            "search_by_name": search_by_name,
            "search_by_query": search_by_query,
            "recommend_alternatives": recommend_alternatives,
            "recommend_by_indications": recommend_by_indications
        }
        self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        self.graph = self._build_graph()

    def _planner_node(self, state):
        question = state["question"]
        chat_history = state.get("chat_history", [])

        history_str = "\n".join([f"{msg.type}: {msg.content}" for msg in chat_history])

        allowed_tools = list(self.tools.keys())
        tool_list_str = "\n".join([f"- {tool}" for tool in allowed_tools])


        prompt = f"""
            \n---\n
            History:
            {history_str}

            Question:
            {question}

            You are an intelligent planning agent that creates execution plans using the following tools only:

            {tool_list_str}     

            Mandatory Constraints (strictly follow):
                - For each user intent or sub-question, you MUST select only one appropriate tool.
                - Do NOT use multiple tools for the same purpose or for overlapping queries.
                - You MUST NOT use both "search_by_name" and "search_by_query" for the same medicine unless the user explicitly asks for two clearly different pieces of information (e.g., both description and usage).
                - Each tool's usage must be fully justified based on its described purpose above.
                - All planned queries must strictly reflect the content and meaning of the user’s original question — NO assumptions or invented sub-questions are allowed.
                - All queries must be written in **Vietnamese**.
                - Medicine names (if used) must be a **single word only** (no compound names).
                - When using tool `recommend_by_indications`, extract all relevant symptoms or indications from the user question and pass them as a **list** of strings.

                - You can use a maximum of 2 tools in total per user query.

            Output format (strictly follow this format — one tool per line):
            Tool: <tool_name> | Query: <query_content>
            
            For tool `recommend_by_indications`, <query_content> must be a **JSON list** of strings representing symptoms or indications.

            If none of the tools are suitable for the user question, return nothing.

            Examples:

            Question: Thuốc Paracetamol có giá bao nhiêu?
            Tool: search_by_name| Query: Paracetamol

            Question: Loại thuốc tương tự thuốc Naname?
            Tool: recommend_alternatives| Query: Naname

            Question: Cách sử dụng thuốc Panadol?
            Tool: search_by_query| Query: Cách sử dụng thuốc Panadol?

            Question: Tôi bị sốt và đau đầu, nên uống thuốc gì?
            Tool: recommend_by_indications| Query: ["sốt", "đau đầu"]

            Now, carefully plan your subqueries:
                    ...
            """
        prompt_template = PromptTemplate(template=prompt, input_variables=["history_str", "question", "tool_list_str"])
        formatted_prompt = prompt_template.format(history_str=history_str, question=question, tool_list_str=tool_list_str)

        # Truyền vào Gemini LLM
        response = self.llm.invoke(formatted_prompt).content
        logger.info("response: {}", repr(response))

        plan = []
        for line in response.split("\n"):
            if "Tool:" in line and "Query:" in line:
                parts = line.split("|")
                tool_part = [p for p in parts if "Tool:" in p][0]
                query_part = [p for p in parts if "Query:" in p][0]

                tool_name = tool_part.replace("Tool:", "").strip()
                query = query_part.replace("Query:", "").strip()

                plan.append({"tool": tool_name, "query": query})

        logger.info(f"[Planner] Plan tạo ra: {plan}")


        # logger.debug("\n📋 [Planner] Truy vấn cần thực hiện:")
        # for q in queries:
        #     logger.debug("- {}", q)

        state["plan"] = plan
        state["results"] = []
        state["current_index"] = 0
        return state

    def _executor_node(self, state):
        index = state["current_index"]
        plan = state["plan"]
        results = state["results"]

        if index >= len(plan):
            return {**state, "done": True}

        step = plan[index]
        tool_name = step["tool"]
        query = step["query"]

        tool = self.tools.get(tool_name)
        if not tool:
            result = f"Tool '{tool_name}' không tồn tại."
        else:
            result = tool.run({"indications": json.loads(query)}) if tool_name == 'recommend_by_indications' else tool.run(query)

        results.append({"tool": tool_name, "query": query, "result": result})
        
        max_attempts = 3
        force_end = False
        final_answer = None
        if index + 1 >= max_attempts:
            useful_results = [
                r for r in state["results"]
                if r["result"]
            ]
            if not useful_results:
                force_end = True
                final_answer = "Không tìm được dữ liệu hữu ích sau 3 lần thử."

        return {**state,
                "results": results,
                "current_index": index + 1,
                "force_end": force_end,
                "final_answer": final_answer
        }


    def _should_continue(self, state):
        if state.get("force_end", False):
            return False  # Dừng sớm
        return state.get("current_index", 0) < len(state.get("plan", []))

    def _summarizer_node(self, state):
        question = state["question"]
        results = state["results"]
        chat_history = state.get("chat_history", [])

        context = "\n".join([f"- {r['query']}: {r['result']}" for r in results])
        history_str = "\n".join([f"{msg.type}: {msg.content}" for msg in chat_history])

        prompt = f"""You are an AI-powered assistant designed to answer user questions related to pharmaceuticals and medications using a Retrieval-Augmented Generation (RAG) system. You will receive retrieved information from a knowledge base that may or may not directly relate to the user's question.

        Your task is to carefully reason and synthesize an accurate response strictly based on the provided information.

        If the retrieved information is not relevant or does not sufficiently answer the user’s question, you must politely inform the user that no relevant information is available to provide an accurate answer.

        Do not make assumptions or generate answers beyond the scope of the retrieved data.


        Finally, remind the user that the information you provide is for reference only and should not replace professional medical advice. Always advise consulting a qualified healthcare professional or doctor for personalized guidance. Answer that question in Vietnamese"---"
            \n---\n
            History: {history_str}
            \n---\n
            Context: {context}
            \n---\n
            Question: {question}
            Helpful Answer:
            """
        prompt_template = PromptTemplate(template=prompt, input_variables=["history_str", "context" ,"question"])
        formatted_prompt = prompt_template.format(history_str=history_str, context=context ,question=question)

        final_answer = self.llm.invoke(formatted_prompt).content
        state["final_answer"] = final_answer
        return state

    def _build_graph(self):
        builder = StateGraph(dict)
        builder.add_node("Planner", self._planner_node)
        builder.add_node("Executor", self._executor_node)
        builder.add_node("Summarizer", self._summarizer_node)

        builder.set_entry_point("Planner")
        builder.add_edge("Planner", "Executor")
        builder.add_conditional_edges("Executor", self._should_continue, {
            True: "Executor",
            False: "Summarizer"
        })
        builder.add_edge("Summarizer", END)
        return builder.compile()

    def run(self, question: str) -> str:
        # Cập nhật memory với câu hỏi mới
        self.memory.chat_memory.add_user_message(question)

        # Build state với memory
        state = {
            "question": question,
            "chat_history": self.memory.chat_memory.messages
        }

        # Thực thi graph
        result_state = self.graph.invoke(state)

        # Lưu trả lời vào memory
        final_answer = result_state.get("final_answer", "Không có kết quả.")
        self.memory.chat_memory.add_ai_message(final_answer)

        return final_answer



if __name__ == "__main__":
    rag_agent = RAGAgentSystem()
    while True:
        question1 = input("Nhập câu hỏi mà bạn muốn hỏi: ")
        if question1:
            logger.info("User query: {}", question1)
            answer1 = rag_agent.run(question1)
            logger.info("\n✅ [answer]:\n {}", answer1)
        else:
            break
