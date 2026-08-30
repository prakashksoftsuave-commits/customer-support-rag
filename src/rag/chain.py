from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from sentence_transformers import CrossEncoder
from src.rag.config import GROQ_API_KEY, GROQ_MODEL
from src.rag.vectorstore import product_area_filter

REFUSAL_TEXT = "I don't know — the help center articles I have don't cover that."

SYSTEM_PROMPT = f"""You are a support assistant for Nimbus, a cloud file-sync product.
Answer the user's question using ONLY the excerpts inside the Context block below.

Rules:
- Every factual claim must end with a citation in the form [source: <chunk_id>], using the full chunk_id
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


def format_docs(docs: list[Document]) -> str:
    return "\n\n".join(f"[source: {d.metadata['chunk_id']}]\n{d.page_content}" for d in docs)


def get_llm() -> ChatGroq:
    return ChatGroq(model=GROQ_MODEL, api_key=GROQ_API_KEY, temperature=0)


def retrieve(
    vectorstore, question: str, k: int = 4, product_area: str | None = None, use_hybrid: bool = False
) -> list[Document]:
    """Retrieve documents using semantic search, optionally augmenting with a simple keyword‑based hybrid search.
    If ``use_hybrid`` is True, we first perform semantic search, then add any additional documents that contain
    any of the query terms (case‑insensitive) to improve recall for exact codes or identifiers.
    """
    # Semantic search
    kwargs = {"k": k}
    if product_area:
        kwargs["filter"] = product_area_filter(product_area)
    semantic_docs = vectorstore.similarity_search(question, **kwargs)
    if not use_hybrid:
        return semantic_docs
    # Keyword augmentation (very simple): score docs by number of query terms contained (excluding common stop words)
    stop_words = {"what", "is", "the", "a", "an", "how", "to", "do", "does", "did", "for", "of", "in", "on", "at", "with", "about", "error", "code", "my", "why", "not"}
    query_terms = set(word.strip("?") for word in question.lower().split()) - stop_words
    # Retrieve a larger pool to scan for keyword matches (capped to 1000 for safety).
    kw_kwargs = kwargs.copy()
    kw_kwargs["k"] = 1000
    all_docs = vectorstore.similarity_search(question, **kw_kwargs) if hasattr(vectorstore, "similarity_search") else []
    
    # Score docs by how many unique keyword terms they contain
    scored_docs = []
    for doc in all_docs:
        content_lower = doc.page_content.lower()
        score = sum(1 for term in query_terms if term in content_lower)
        if score > 0:
            scored_docs.append((score, doc))
            
    scored_docs.sort(key=lambda x: x[0], reverse=True)
    keyword_docs = [doc for score, doc in scored_docs]
    
    # Interleave semantic and keyword docs to give both a fair chance
    combined = []
    seen = set()
    
    # Create iterators
    sem_iter = iter(semantic_docs)
    kw_iter = iter(keyword_docs)
    
    sem_empty = False
    kw_empty = False
    
    while len(combined) < k:
        # Try taking one from semantic
        try:
            sem_doc = next(sem_iter)
            uid = sem_doc.metadata.get("chunk_id") or sem_doc.metadata.get("article_id")
            if uid and uid not in seen:
                combined.append(sem_doc)
                seen.add(uid)
                if len(combined) >= k: break
        except StopIteration:
            sem_empty = True
            
        # Try taking one from keyword
        try:
            kw_doc = next(kw_iter)
            uid = kw_doc.metadata.get("chunk_id") or kw_doc.metadata.get("article_id")
            if uid and uid not in seen:
                combined.append(kw_doc)
                seen.add(uid)
                if len(combined) >= k: break
        except StopIteration:
            kw_empty = True
            
        # If both are empty, we're done early
        if sem_empty and kw_empty:
            break
            
    return combined


def answer_question(
    vectorstore,
    question: str,
    llm: ChatGroq | None = None,
    k: int = 4,
    product_area: str | None = None,
    use_hybrid: bool = False,
    use_rerank: bool = False,
) -> tuple[str, list[Document]]:
    """Retrieve, optionally rerank, then answer. Returns (answer, source_docs)."""
    llm = llm or get_llm()
    docs = retrieve(vectorstore, question, k=k, product_area=product_area, use_hybrid=use_hybrid)
    if use_rerank:
        reranker = get_reranker()
        docs = rerank_docs(docs, question, reranker)
    chain = PROMPT | llm | StrOutputParser()
    answer = chain.invoke({"context": format_docs(docs), "question": question})
    # The model sometimes cites the article_id instead of the full chunk_id — normalize it.
    for d in docs:
        article_id = d.metadata.get("article_id")
        chunk_id = d.metadata.get("chunk_id")
        if article_id and chunk_id:
            answer = answer.replace(f"[source: {article_id}]", f"[source: {chunk_id}]")
    return answer, docs

def get_reranker() -> CrossEncoder:
    """Load a cross‑encoder reranker model."""
    # Using a lightweight cross‑encoder; adjust model name as needed.
    return CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

def rerank_docs(docs: list[Document], query: str, reranker: CrossEncoder) -> list[Document]:
    """Score docs with the reranker and return them sorted by descending relevance."""
    if not docs:
        return docs
    pairs = [(query, doc.page_content) for doc in docs]
    scores = reranker.predict(pairs)
    scored_docs = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)
    return [doc for doc, _ in scored_docs]
