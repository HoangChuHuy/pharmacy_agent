from src.agent.agent import RAGAgentSystem
from loguru import logger



if __name__== '__main__':
    rag_agent = RAGAgentSystem()
    while True:
        question1 = input("Nhập câu hỏi mà bạn muốn hỏi: ")
        if question1:
            logger.info("User query: {}", question1)
            answer1 = rag_agent.run(question1)
            logger.info("\n✅ [answer]:\n {}", answer1)
        else:
            break
