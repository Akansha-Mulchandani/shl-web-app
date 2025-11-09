import os
import sys
import pandas as pd
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.recommender import Recommender

TRAIN_CSV = os.path.join(ROOT, 'data', 'train.csv')


def _find_query_col(df: pd.DataFrame):
    for c in df.columns:
        lc = c.lower().strip()
        if lc in {"query", "job_description", "text", "prompt"}:
            return c
    return df.columns[0]


def _find_url_col(df: pd.DataFrame):
    candidates = [
        "Assessment_url", "assessment_url", "url", "URL", "link", "Link"
    ]
    for c in df.columns:
        if c in candidates:
            return c
        if c.lower().strip() in [x.lower() for x in candidates]:
            return c
    # if not found, try any column containing 'url'
    for c in df.columns:
        if 'url' in c.lower():
            return c
    raise ValueError("Could not find a URL column in training data")


def mean_recall_at_k(df: pd.DataFrame, k: int = 10) -> float:
    qcol = _find_query_col(df)
    ucol = _find_url_col(df)
    # group relevant URLs per query
    gold = defaultdict(set)
    for _, row in df.iterrows():
        q = str(row[qcol]).strip()
        url = str(row[ucol]).strip()
        if q and url and url.startswith("http"):
            gold[q].add(url)

    rec = Recommender()
    recalls = []
    for q, rel_urls in gold.items():
        recs = rec.recommend(q, k=k)
        top_urls = [r.assessment_url for r in recs][:k]
        num_rel = len(rel_urls)
        hit = len(set(top_urls) & rel_urls)
        recall = hit / num_rel if num_rel > 0 else 0.0
        recalls.append(recall)
    return sum(recalls) / len(recalls) if recalls else 0.0


def main():
    assert os.path.exists(TRAIN_CSV), f"Training CSV not found: {TRAIN_CSV}. Run data/process_dataset.py first."
    df = pd.read_csv(TRAIN_CSV)
    mr10 = mean_recall_at_k(df, k=10)
    print(f"Mean Recall@10: {mr10:.4f}")


if __name__ == "__main__":
    main()
