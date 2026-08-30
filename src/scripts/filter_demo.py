"""Show a query where a product_area metadata filter changes the top-1 retrieved chunk."""

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import json

from src.rag.chain import product_area_filter
from src.rag.config import ROOT_DIR, SECTION_AWARE
from src.rag.vectorstore import get_vectorstore

QUERY = "Why are my notifications not working?"
FILTER_PRODUCT_AREA = "mobile"
TOP_K = 5
OUT_PATH = ROOT_DIR / "results" / "filter_demo.json"


def dump(results):
    return [
        {
            "article_id": doc.metadata["article_id"],
            "product_area": doc.metadata["product_area"],
            "chunk_id": doc.metadata["chunk_id"],
            "score": round(float(score), 4),
            "excerpt": doc.page_content[:160].replace("\n", " "),
        }
        for doc, score in results
    ]


def main() -> None:
    vectorstore = get_vectorstore(SECTION_AWARE.collection)

    unfiltered = vectorstore.similarity_search_with_score(QUERY, k=TOP_K)
    filtered = vectorstore.similarity_search_with_score(
        QUERY, k=TOP_K, filter=product_area_filter(FILTER_PRODUCT_AREA)
    )

    report = {
        "query": QUERY,
        "filter_product_area": FILTER_PRODUCT_AREA,
        "unfiltered_top1_article_id": unfiltered[0][0].metadata["article_id"],
        "filtered_top1_article_id": filtered[0][0].metadata["article_id"],
        "unfiltered": dump(unfiltered),
        "filtered": dump(filtered),
    }

    OUT_PATH.parent.mkdir(exist_ok=True)
    OUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Unfiltered top-1: {report['unfiltered_top1_article_id']}")
    print(f"Filtered (product_area={FILTER_PRODUCT_AREA}) top-1: {report['filtered_top1_article_id']}")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
