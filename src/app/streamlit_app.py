import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import streamlit as st
from src.rag.chain import get_llm, answer_question
from src.rag.config import CHUNK_PROFILES, UPLOAD_PROFILE
from src.rag.loader import SUPPORTED_UPLOAD_EXTENSIONS, load_uploaded_documents
from src.rag.splitting import split_documents
from src.rag.vectorstore import build_vectorstore, get_vectorstore, list_collections

st.set_page_config(page_title="Customer Help Center Assistant", page_icon="💬")
st.title("Customer Help Center Assistant")
st.caption("Answers only from the loaded documents — cites its source, or says it doesn't know.")

PRODUCT_AREAS = ["All", "account", "sync", "sharing", "mobile", "notifications", "general"]

with st.sidebar:
    st.header("Settings")
    source = st.radio("Document source", ["Built-in Nimbus KB", "My uploaded documents"])

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
    st.error(f"Failed to connect to Qdrant: {e}")
    st.stop()
llm = get_llm()

question = st.text_input("Ask a question about the loaded documents")

rerank = st.checkbox("Enable reranking (cross-encoder)", value=False)

if question:
    filter_area = None if product_area == "All" else product_area
    with st.spinner("Searching..."):
        answer, docs = answer_question(
            vectorstore,
            question,
            llm=llm,
            k=top_k,
            product_area=filter_area,
            use_hybrid=hybrid,
            use_rerank=rerank,
        )

    st.markdown("### Answer")
    st.write(answer)

    # Inspection view
    st.write(f"**Question:** {question}")
    st.write("**Retrieved Documents:**")
    for i, doc in enumerate(docs, 1):
        label = f"{i}. {doc.metadata['title']} — {doc.metadata['article_id']} ({doc.metadata['product_area']})"
        with st.expander(label):
            st.text(doc.page_content)


