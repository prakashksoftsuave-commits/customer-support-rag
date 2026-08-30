import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import streamlit as st
from src.rag.chain import get_llm, answer_question
from src.rag.config import CHUNK_PROFILES
from src.rag.vectorstore import get_vectorstore, get_client

st.set_page_config(page_title="Customer Help Center Assistant", page_icon="💬")
st.title("Customer Help Center Assistant")
st.caption("Answers only from the help-center articles — cites its source, or says it doesn't know.")

PRODUCT_AREAS = ["All", "account", "sync", "sharing", "mobile", "notifications", "general"]

with st.sidebar:
    st.header("Settings")
    # List available Qdrant collections
    try:
        client = get_client()
        collections = client.get_collections().collections
        collection_names = [c.name for c in collections]
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

profile = next(p for p in CHUNK_PROFILES if p.name == profile_name)
try:
    vectorstore = get_vectorstore(profile.collection)
except Exception as e:
    st.error(f"Failed to connect to Qdrant: {e}")
    st.stop()
llm = get_llm()

question = st.text_input("Ask a question to the Customer Help Center Assistant")

# Additional toggles for Week 4 features
rerank = st.checkbox("Enable reranking (cross-encoder)", value=False)
query_rewrite = False # st.checkbox("Enable query rewriting (HyDE)", value=False)

if question:
    filter_area = None if product_area == "All" else product_area
    with st.spinner("Searching help center..."):
        answer, docs = answer_question(
            vectorstore,
            question,
            llm=llm,
            k=top_k,
            product_area=filter_area,
            use_hybrid=hybrid,
            use_rerank=rerank,
            use_query_rewrite=query_rewrite,
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


