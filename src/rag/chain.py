import json
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
from sentence_transformers import CrossEncoder
from src.rag.config import GROQ_API_KEY, GROQ_MODEL
from src.rag.tracing import with_tracing
from src.rag.vectorstore import product_area_filter

REFUSAL_TEXT = "I don't know — the help center articles I have don't cover that."

SYSTEM_PROMPT = f"""You are a support assistant for a cloud file-sync product.
Answer the user's question using ONLY the excerpts inside the Context block below.

Rules:
- Every factual claim must end with a citation in the form [source: <chunk_id>], using the full chunk_id
shown above each excerpt.
- If the Context does not fully contain the answer, respond with exactly this sentence and nothing else: \
"{REFUSAL_TEXT}"
- Never use outside knowledge, and never guess to fill a gap in the Context, even if you believe you know \
the answer.
- The conversation history is there only so you can resolve references like "it" or "that" and avoid \
repeating yourself — it is never itself a source of facts. Every factual claim must still be grounded in \
and cited from the Context block.
- Be concise."""

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "Context:\n{context}\n\nQuestion: {question}"),
    ]
)

# Chat memory: a follow-up question ("what about on mobile?") is meaningless to a similarity search on
# its own, so it's rewritten into a standalone question — using the chat history — before retrieval.
# The *original* question (not the rewritten one) is still what goes to PROMPT above for the final
# answer, since the model has the chat history there too and the rewrite is a retrieval-only aid.
CONDENSE_SYSTEM_PROMPT = """Given a chat history and the latest user question, rewrite the question as a \
standalone question that includes any context (names, topics, referents like "it"/"that") it needs from \
the chat history to be understood on its own. If it is already standalone, return it unchanged. Output \
only the rewritten question, nothing else."""

CONDENSE_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", CONDENSE_SYSTEM_PROMPT),
        MessagesPlaceholder("chat_history"),
        ("human", "{question}"),
    ]
)


def condense_question(
    llm: ChatGroq, chat_history: list[tuple[str, str]], question: str, run_config: dict | None = None
) -> str:
    """Rewrite a follow-up question into a standalone one for retrieval. No-op with no history."""
    if not chat_history:
        return question
    chain = CONDENSE_PROMPT | llm | StrOutputParser()
    return chain.invoke(
        {"chat_history": chat_history, "question": question}, config=with_tracing(run_config)
    ).strip()


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


DECOMPOSE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "If the user's question blends two distinct support topics into one message, split it "
            "into up to 2 separate single-topic questions, one per line, no numbering, no extra text. "
            "If it's already about one topic, output it unchanged, on one line.",
        ),
        ("human", "{question}"),
    ]
)


def decompose_query(llm: ChatGroq, question: str, run_config: dict | None = None) -> list[str]:
    """Split a compound question into its topic-pure halves, so each half retrieves on its own —
    Week 3 showed single-topic questions retrieve fine; compound phrasing is what dilutes the
    embedding across two topics at once."""
    chain = DECOMPOSE_PROMPT | llm | StrOutputParser()
    raw = chain.invoke({"question": question}, config=with_tracing(run_config))
    sub_questions = [line.strip("- ").strip() for line in raw.splitlines() if line.strip()]
    return sub_questions[:2] if sub_questions else [question]


def retrieve_decomposed(
    vectorstore, question: str, llm: ChatGroq, k: int = 4, product_area: str | None = None, run_config: dict | None = None
) -> list[Document]:
    """Retrieve k docs per decomposed sub-question, interleaved and capped at k total, so the
    result is directly comparable to a plain retrieve() call at the same k."""
    sub_questions = decompose_query(llm, question, run_config=run_config)
    if len(sub_questions) == 1:
        return retrieve(vectorstore, sub_questions[0], k=k, product_area=product_area)

    per_question_docs = [retrieve(vectorstore, q, k=k, product_area=product_area) for q in sub_questions]
    combined, seen = [], set()
    iterators = [iter(docs) for docs in per_question_docs]
    while len(combined) < k and iterators:
        for it in list(iterators):
            try:
                doc = next(it)
            except StopIteration:
                iterators.remove(it)
                continue
            uid = doc.metadata.get("chunk_id") or doc.metadata.get("article_id")
            if uid and uid not in seen:
                combined.append(doc)
                seen.add(uid)
                if len(combined) >= k:
                    break
    return combined


JUDGE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are grading a support bot's answer against the context it was given and the question "
            "asked. Score two things from 1 (worst) to 5 (best):\n"
            "faithfulness: is every claim in the answer actually supported by the context (no invented "
            "facts)?\n"
            "relevancy: does the answer actually address the question asked?\n"
            'Respond with ONLY a JSON object, no other text: {{"faithfulness": <1-5>, "relevancy": <1-5>}}',
        ),
        ("human", "Question: {question}\n\nContext:\n{context}\n\nAnswer: {answer}"),
    ]
)


def _parse_judge_json(raw: str) -> dict:
    """Pull {"faithfulness": int, "relevancy": int} out of raw judge output, tolerating the
    markdown code fences models sometimes wrap JSON in. Returns Nones (not a raised exception)
    on a parse failure, with the raw text kept so the failure is visible, not silent."""
    cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        parsed = json.loads(cleaned)
        return {"faithfulness": parsed.get("faithfulness"), "relevancy": parsed.get("relevancy"), "raw": raw}
    except (json.JSONDecodeError, AttributeError):
        return {"faithfulness": None, "relevancy": None, "raw": raw}


def judge_answer(llm: ChatGroq, question: str, context: str, answer: str, run_config: dict | None = None) -> dict:
    """LLM-as-judge: score faithfulness and relevancy 1-5."""
    chain = JUDGE_PROMPT | llm | StrOutputParser()
    raw = chain.invoke({"question": question, "context": context, "answer": answer}, config=with_tracing(run_config))
    return _parse_judge_json(raw)


def answer_question(
    vectorstore,
    question: str,
    llm: ChatGroq | None = None,
    k: int = 4,
    product_area: str | None = None,
    use_hybrid: bool = False,
    use_rerank: bool = False,
    use_decompose: bool = False,
    chat_history: list[tuple[str, str]] | None = None,
    run_config: dict | None = None,
) -> tuple[str, list[Document]]:
    """Retrieve, optionally rerank, then answer. Returns (answer, source_docs).

    ``chat_history`` is a list of ("human"/"ai", content) tuples, oldest first. When given, the
    question is first condensed against it for retrieval (so "what about on mobile?" retrieves
    correctly), and the history is passed to the answer prompt so the model can follow the
    conversation — but every factual claim is still required to come from the retrieved Context.

    ``run_config`` is passed straight through to the underlying LangChain ``.invoke()`` calls —
    e.g. ``{"tags": ["week5-trace"], "metadata": {"trace_id": "t01"}}`` to make a run filterable
    in Langfuse. No-op if Langfuse tracing isn't enabled.
    """
    llm = llm or get_llm()
    chat_history = chat_history or []
    search_question = condense_question(llm, chat_history, question, run_config=run_config)
    if use_decompose:
        docs = retrieve_decomposed(vectorstore, search_question, llm, k=k, product_area=product_area, run_config=run_config)
    else:
        docs = retrieve(vectorstore, search_question, k=k, product_area=product_area, use_hybrid=use_hybrid)
    if use_rerank:
        reranker = get_reranker()
        docs = rerank_docs(docs, search_question, reranker)
    chain = PROMPT | llm | StrOutputParser()
    answer = chain.invoke(
        {"context": format_docs(docs), "question": question, "chat_history": chat_history},
        config=with_tracing(run_config),
    )
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
