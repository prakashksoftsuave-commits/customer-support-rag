from qdrant_client.http import models as qmodels
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from src.rag.config import GROQ_API_KEY, GROQ_MODEL

REFUSAL_TEXT = "I don't know — the help center articles I have don't cover that."

SYSTEM_PROMPT = f"""You are a support assistant for Nimbus, a cloud file-sync product.
Answer the user's question using ONLY the excerpts inside the Context block below.

Rules:
- Every factual claim must end with a citation in the form [source: <chunk_id>], using the full chunk_id (e.g., kb-account-001::section_aware::6).
shown above each excerpt.
- If the Context does not fully contain the answer, respond with exactly this sentence and nothing else: \
"{REFUSAL_TEXT}"
- Never use outside knowledge, and never guess to fill a gap in the Context, even if you believe you know \
the answer.
- Be concise."""

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", "Context:\n{context}\n\nQuestion: {question}"),
    ]
)


def product_area_filter(product_area: str) -> qmodels.Filter:
    return qmodels.Filter(
        must=[
            qmodels.FieldCondition(
                key="metadata.product_area", match=qmodels.MatchValue(value=product_area)
            )
        ]
    )


def format_docs(docs: list[Document]) -> str:
    return "\n\n".join(f"[source: {d.metadata['chunk_id']}]\n{d.page_content}" for d in docs)


def get_llm() -> ChatGroq:
    return ChatGroq(model=GROQ_MODEL, api_key=GROQ_API_KEY, temperature=0)


def retrieve(
    vectorstore, question: str, k: int = 4, product_area: str | None = None
) -> list[Document]:
    kwargs = {"k": k}
    if product_area:
        kwargs["filter"] = product_area_filter(product_area)
    return vectorstore.similarity_search(question, **kwargs)


def answer_question(
    vectorstore, question: str, llm: ChatGroq | None = None, k: int = 4, product_area: str | None = None
) -> tuple[str, list[Document]]:
    """Retrieve, then answer strictly from retrieved context. Returns (answer, source_docs)."""
    llm = llm or get_llm()
    docs = retrieve(vectorstore, question, k=k, product_area=product_area)
    chain = PROMPT | llm | StrOutputParser()
    answer = chain.invoke({"context": format_docs(docs), "question": question})
    # Replace any article_id citations with the corresponding chunk_id from retrieved docs
    for d in docs:
        article_id = d.metadata.get("article_id")
        chunk_id = d.metadata.get("chunk_id")
        if article_id and chunk_id:
            answer = answer.replace(f"[source: {article_id}]", f"[source: {chunk_id}]")
    return answer, docs
