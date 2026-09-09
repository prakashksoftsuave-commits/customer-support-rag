import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import uuid

import streamlit as st
from src.rag.chain import get_llm, answer_question
from src.rag.config import CHUNK_PROFILES, LANGFUSE_HOST, LANGFUSE_TRACING_ENABLED, UPLOAD_PROFILE
from src.rag.loader import SUPPORTED_UPLOAD_EXTENSIONS, load_uploaded_documents
from src.rag.splitting import split_documents
from src.rag.vectorstore import build_vectorstore, get_vectorstore, list_collections

st.set_page_config(page_title="Customer Help Center Assistant", page_icon="💬")
st.title("Customer Help Center Assistant")
st.caption("Answers only from the loaded documents — cites its source, or says it doesn't know.")
if LANGFUSE_TRACING_ENABLED:
    st.caption(f"🔍 Langfuse tracing on — [{LANGFUSE_HOST}]({LANGFUSE_HOST})")

PRODUCT_AREAS = ["All", "account", "sync", "sharing", "mobile", "notifications", "general"]
MAX_HISTORY_TURNS = 5  # exchanges (user+assistant pairs) sent back to the model as context


def new_conversation() -> str:
    conv_id = str(uuid.uuid4())
    st.session_state.conversations[conv_id] = {"title": "New conversation", "messages": []}
    st.session_state.active_id = conv_id
    return conv_id


if "conversations" not in st.session_state:
    st.session_state.conversations = {}
if "active_id" not in st.session_state or st.session_state.active_id not in st.session_state.conversations:
    new_conversation()

with st.sidebar:
    if st.button("+ New chat", use_container_width=True):
        new_conversation()
        st.rerun()

    st.divider()
    for conv_id in reversed(list(st.session_state.conversations.keys())):  # newest first
        conv = st.session_state.conversations[conv_id]
        col1, col2 = st.columns([5, 1])
        with col1:
            is_active = conv_id == st.session_state.active_id
            if st.button(
                conv["title"], key=f"switch_{conv_id}", use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state.active_id = conv_id
                st.rerun()
        with col2:
            if st.button("🗑", key=f"delete_{conv_id}"):
                del st.session_state.conversations[conv_id]
                if st.session_state.active_id == conv_id:
                    if st.session_state.conversations:
                        st.session_state.active_id = next(iter(st.session_state.conversations))
                    else:
                        new_conversation()
                st.rerun()

    st.divider()
    st.header("Settings")
    source = st.radio("Document source", ["Built-in Help Center KB", "My uploaded documents"])

    if source == "My uploaded documents":
        uploaded_files = st.file_uploader(
            "Upload documents to ask questions about",
            type=[ext.lstrip(".") for ext in SUPPORTED_UPLOAD_EXTENSIONS],
            accept_multiple_files=True,
        )
        if st.button("Ingest uploaded files", disabled=not uploaded_files):
            files = [(f.name, f.getvalue()) for f in uploaded_files]
            with st.spinner("Extracting and indexing..."):
                documents, failures = load_uploaded_documents(files)
                for filename, error in failures:
                    st.error(f"{filename}: {error}")
                if documents:
                    chunks = split_documents(documents, UPLOAD_PROFILE)
                    build_vectorstore(chunks, UPLOAD_PROFILE.collection)
                    st.session_state["uploaded_ready"] = True
                    st.success(f"Indexed {len(documents)} file(s) into {len(chunks)} chunks.")
        product_area = "All"
        top_k = st.slider("Chunks retrieved (Top-K)", min_value=1, max_value=6, value=4)
        hybrid = st.checkbox("Enable hybrid search (semantic + keyword)", value=False)
    else:
        try:
            collection_names = list_collections()
        except Exception as e:
            st.error(f"Failed to retrieve collections: {e}")
            collection_names = []
        if collection_names:
            profile_name = st.radio(
                "Chunking strategy",
                [p.name for p in CHUNK_PROFILES if p.collection in collection_names],
                help="Select a chunking strategy whose collection exists in Qdrant.")
        else:
            st.warning("No collections found in Qdrant. Please build a vectorstore first.")
            profile_name = st.radio(
                "Chunking strategy",
                [p.name for p in CHUNK_PROFILES],
                help="Select a chunking strategy (collections not yet built).")
        product_area = st.selectbox("Filter by product area", PRODUCT_AREAS)
        top_k = st.slider("Chunks retrieved (Top-K)", min_value=1, max_value=6, value=4)
        hybrid = st.checkbox("Enable hybrid search (semantic + keyword)", value=False)

    rerank = st.checkbox("Enable reranking (cross-encoder)", value=False)

if source == "My uploaded documents":
    if not st.session_state.get("uploaded_ready"):
        st.info("Upload one or more documents and click **Ingest uploaded files** to begin.")
        st.stop()
    collection = UPLOAD_PROFILE.collection
else:
    profile = next(p for p in CHUNK_PROFILES if p.name == profile_name)
    collection = profile.collection

try:
    vectorstore = get_vectorstore(collection)
except Exception as e:
    st.error(f"Failed to connect to the vector store: {e}")
    st.stop()
llm = get_llm()

active_conv = st.session_state.conversations[st.session_state.active_id]

for message in active_conv["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and message.get("docs"):
            st.write("**Retrieved documents:**")
            for i, doc in enumerate(message["docs"], 1):
                label = f"{i}. {doc.metadata['title']} — {doc.metadata['article_id']} ({doc.metadata['product_area']})"
                with st.expander(label):
                    st.text(doc.page_content)

if question := st.chat_input("Ask a question about the loaded documents"):
    filter_area = None if product_area == "All" else product_area
    chat_history = [
        ("human" if m["role"] == "user" else "ai", m["content"])
        for m in active_conv["messages"][-2 * MAX_HISTORY_TURNS :]
    ]

    active_conv["messages"].append({"role": "user", "content": question})
    if active_conv["title"] == "New conversation":
        active_conv["title"] = question[:40] + ("…" if len(question) > 40 else "")

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Searching..."):
            answer, docs = answer_question(
                vectorstore,
                question,
                llm=llm,
                k=top_k,
                product_area=filter_area,
                use_hybrid=hybrid,
                use_rerank=rerank,
                chat_history=chat_history,
                run_config={
                    "tags": ["streamlit-chat"],
                    "metadata": {"conversation_id": st.session_state.active_id, "collection": collection},
                },
            )
        st.markdown(answer)
        st.write("**Retrieved documents:**")
        for i, doc in enumerate(docs, 1):
            label = f"{i}. {doc.metadata['title']} — {doc.metadata['article_id']} ({doc.metadata['product_area']})"
            with st.expander(label):
                st.text(doc.page_content)

    active_conv["messages"].append({"role": "assistant", "content": answer, "docs": docs})
    st.rerun()  # refresh the sidebar so the auto-generated title shows immediately
