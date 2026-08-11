import streamlit as st

from src.rag.chain import get_llm, answer_question
from src.rag.config import CHUNK_PROFILES
from src.rag.vectorstore import get_vectorstore

st.set_page_config(page_title="Nimbus Help Center Assistant", page_icon="💬")
st.title("Nimbus Help Center Assistant")
st.caption("Answers only from the Nimbus help-center articles — cites its source, or says it doesn't know.")

PRODUCT_AREAS = ["All", "account", "sync", "sharing", "mobile", "notifications", "general"]

with st.sidebar:
    st.header("Settings")
    profile_name = st.radio(
        "Chunking strategy",
        [p.name for p in CHUNK_PROFILES],
        help="Compare chunk size/overlap (recursive_small vs recursive_large) against a "
             "header-based strategy that keeps each section's table intact (section_aware).",
    )
    product_area = st.selectbox("Filter by product area", PRODUCT_AREAS)
    top_k = st.slider("Chunks retrieved (Top-K)", min_value=1, max_value=6, value=4)

profile = next(p for p in CHUNK_PROFILES if p.name == profile_name)
vectorstore = get_vectorstore(profile.collection)
llm = get_llm()

question = st.text_input("Ask a question about Nimbus")

if question:
    filter_area = None if product_area == "All" else product_area
    with st.spinner("Searching help center..."):
        answer, docs = answer_question(vectorstore, question, llm=llm, k=top_k, product_area=filter_area)

    st.markdown("### Answer")
    st.write(answer)

    st.markdown("### Retrieved sources")
    for doc in docs:
        label = f"{doc.metadata['title']} — {doc.metadata['article_id']} ({doc.metadata['product_area']})"
        with st.expander(label):
            st.text(doc.page_content)
