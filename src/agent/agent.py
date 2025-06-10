from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import SystemMessage
from langchain.agents import Tool
from langchain.memory import ConversationBufferMemory
import os
from src.config.configs import *
from loguru import logger
from src.agent.tools import search_by_name
from langchain.prompts import PromptTemplate

from IPython.display import Image, display



class RAGAgentSystem:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model=LLM_MODEL, 
            google_api_key=GOOGLE_API_KEY,
            temperature=0.0,
            convert_system_message_to_human=True
        )
        self.tool = search_by_name
        self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        self.graph = self._build_graph()
        self.graph.get_graph()

    def _planner_node(self, state):
        question = state["question"]
        chat_history = state.get("chat_history", [])

        history_str = "\n".join([f"{msg.type}: {msg.content}" for msg in chat_history])

        prompt = f"""
            \n---\n
            History: {history_str}

            Question: {question}

            Plan your answers (in the form of small queries). Your work is split user query to the object appered like that form:
                - Object Name 1
                - Object Name 2
            Note that the object name is what the user refers to in the sentenceand is represented by a maximum of 2 words.
            ...
            """
        prompt_template = PromptTemplate(template=prompt, input_variables=["history_str", "question"])
        formatted_prompt = prompt_template.format(history_str=history_str, question=question)

        # Truyền vào Gemini LLM
        response = self.llm.invoke(formatted_prompt).content
        logger.info("response: {}", repr(response))
        queries = [line.replace("-", "").strip() for line in response.split("\n")]

        logger.debug("\n📋 [Planner] Truy vấn cần thực hiện:")
        for q in queries:
            logger.debug("- {}", q)

        state["plan"] = queries
        state["results"] = []
        state["current_index"] = 0
        return state

    def _executor_node(self, state):
        index = state["current_index"]
        plan = state["plan"]
        if index >= len(plan):
            state["done"] = True
            return state

        query = plan[index]
        logger.debug(f"\n🔍 [Executor] Đang thực hiện: {query}")
        result = self.tool.run(query)

        state["results"].append({"query": query, "result": result})
        state["current_index"] += 1

        max_attempts = 2
        if state["current_index"] >= max_attempts:
            useful_results = [
                r for r in state["results"]
                if "không có dữ liệu" not in r["result"].lower()
            ]
            if not useful_results:
                logger.debug("⚠️ Không tìm thấy dữ liệu hữu ích sau 2 lần thử. Dừng sớm.")
                state["final_answer"] = "Xin lỗi, tôi không thể tìm thấy thông tin phù hợp để trả lời câu hỏi này."
                state["force_end"] = True

        return state

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

        logger.debug("result_state: {}", result_state)

        # Lưu trả lời vào memory
        final_answer = result_state.get("final_answer", "Không có kết quả.")
        self.memory.chat_memory.add_ai_message(final_answer)

        return final_answer



if __name__ == "__main__":
    rag_agent = RAGAgentSystem()

    question1 = "Cho tôi xin giá của thuốc Thuốc Decolgen Forte United"
    answer1 = rag_agent.run(question1)
    logger.info("\n✅ [Lần 1]:\n {}", answer1)

    # question2 = "Lỗi đó có liên quan tới timeout không?"
    # answer2 = rag_agent.run(question2)
    # print("\n✅ [Lần 2]:\n", answer2)
