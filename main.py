import uuid
from src.agent.agent import RAGAgentSystem
from loguru import logger
import gradio as gr

chat_histories = {}
rag_agents = {}

def init_session():
    session_id = str(uuid.uuid4())
    chat_histories[session_id] = []
    rag_agents[session_id] = RAGAgentSystem()
    logger.info(f"New session: {session_id}")
    return session_id

def chatbot_interface(user_input, session_id):
    agent = rag_agents[session_id]
    chat_history = chat_histories[session_id]

    response = agent.run(user_input)
    chat_history.append((user_input, response))
    return chat_history

def reset_chat(session_id):
    chat_histories[session_id] = []
    rag_agents[session_id].memory.clear()
    return "", []

if __name__ == '__main__':
    with gr.Blocks() as demo:
        gr.Markdown("## 🤖 Chatbot with RAG + Reset (Session based)")

        session_id_state = gr.State(init_session)

        chatbot = gr.Chatbot()
        with gr.Row():
            txt = gr.Textbox(placeholder="Nhập câu hỏi...", show_label=False)
            reset_btn = gr.Button("🔄 Reset")

        txt.submit(fn=chatbot_interface, inputs=[txt, session_id_state], outputs=chatbot)
        reset_btn.click(fn=reset_chat, inputs=session_id_state, outputs=[txt, chatbot])

    demo.launch(share=True, server_port=8080)
