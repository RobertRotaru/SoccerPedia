from langchain_community.document_loaders import YoutubeLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_mistralai.chat_models import ChatMistralAI
from langchain import PromptTemplate
from langchain.chains import LLMChain
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv
from langchain_mistralai import MistralAIEmbeddings

load_dotenv()

embeddings = MistralAIEmbeddings()

video_url = "https://www.youtube.com/watch?v=STPC8Wj7yOQ"

def create_vector_db_from_youtube(url: str) -> FAISS:
    loader = YoutubeLoader.from_youtube_url(url)
    transcript = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    docs = text_splitter.split_documents(transcript)

    vector_db = FAISS.from_documents(docs, embeddings)
    return vector_db

def get_response_from_query(vector_db: FAISS, query: str, k: int) -> str:
    relevant_docs = vector_db.similarity_search(query, k)
    context = "\n".join([doc.page_content for doc in relevant_docs])

    prompt_template = """
    You are an AI assistant that provides answers based on the following context:
    {context}

    Answer the following question:
    {question}
    """

    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template=prompt_template
    )

    llm = ChatMistralAI(model_name="mistral-small", temperature=0.7)
    chain = LLMChain(llm=llm, prompt=prompt)

    response = chain.run(context=context, question=query)
    return response

if __name__ == "__main__":
    vector_db = create_vector_db_from_youtube(video_url)
    query = "What is the main topic of the video?"
    response = get_response_from_query(vector_db, query, k=3)
    print("Response:", response)