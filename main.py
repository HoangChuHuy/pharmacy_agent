from src.agent.agent import RAGAgentSystem
from loguru import logger
import gradio as gr


chat_history = []
rag_agent = RAGAgentSystem()

def chatbot_interface(user_input):
    global chat_history
    # Gọi RAG flow của bạn ở đây
    response = rag_agent.run(user_input)
    chat_history.append((user_input, response))
    return chat_history

# Hàm reset lịch sử
def reset_chat():
    global chat_history
    chat_history = []
    rag_agent.memory.clear()
    return "", gr.update(value="")

if __name__== '__main__':
    with gr.Blocks() as demo:
        gr.Markdown("## 🤖 Chatbot with RAG + Reset")
        chatbot = gr.Chatbot()
        with gr.Row():
            txt = gr.Textbox(placeholder="Nhập câu hỏi...", show_label=False)
            reset_btn = gr.Button("🔄 Reset")
        
        # Sự kiện gửi tin nhắn
        txt.submit(fn=chatbot_interface, inputs=txt, outputs=chatbot)
        
        # Sự kiện nút reset
        reset_btn.click(fn=reset_chat, outputs=[txt, chatbot])

    demo.launch(share=True, server_port=8080)


