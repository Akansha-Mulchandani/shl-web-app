import argparse
import os
import sys
import pandas as pd
import csv

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.recommender import Recommender
TEST_CSV = os.path.join(ROOT, 'data', 'test.csv')


def _find_query_col(df: pd.DataFrame):
    for c in df.columns:
        lc = c.lower().strip()
        if lc in {"query", "job_description", "text", "prompt"}:
            return c
    return df.columns[0]


def generate_predictions(out_path: str, k: int = 10):
    assert os.path.exists(TEST_CSV), f"Test CSV not found: {TEST_CSV}. Run data/process_dataset.py first."
    df = pd.read_csv(TEST_CSV)
    qcol = _find_query_col(df)

    rec = Recommender()

    rows = []
    for _, row in df.iterrows():
        q = str(row[qcol])
        # Normalize whitespace: collapse newlines/tabs/multiple spaces
        q = " ".join(q.split()).strip()
        if not q:
            continue
        recs = rec.recommend(q, k=k)
        # must be between 5-10
        recs = recs[:10]
        if len(recs) < 5:
            recs = recs + recs[: max(0, 5 - len(recs))]
        for r in recs:
            rows.append({
                'Query': q,
                'Assessment_url': r.assessment_url,
            })
    out_df = pd.DataFrame(rows, columns=["Query", "Assessment_url"])
    # Write with UTF-8 BOM so Excel detects UTF-8 and delimiter properly
    out_df.to_csv(out_path, index=False, sep=",", encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
    # Also write an Excel-friendly variant with semicolon delimiter (if locale expects ;) 
    alt_path = os.path.splitext(out_path)[0] + "_excel.csv"
    out_df.to_csv(alt_path, index=False, sep=";", encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
    # Create a human-readable version: blank repeated Query cells for consecutive rows of same query
    readable = out_df.copy()
    last_q = None
    for i in range(len(readable)):
        q = readable.at[i, 'Query']
        if q == last_q:
            readable.at[i, 'Query'] = ''
        else:
            last_q = q
    readable_path = os.path.splitext(out_path)[0] + "_readable.csv"
    readable.to_csv(readable_path, index=False, sep=",", encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
    # Write TSV (tab-delimited) which Excel opens reliably as two columns
    tsv_path = os.path.splitext(out_path)[0] + ".tsv"
    out_df.to_csv(tsv_path, index=False, sep="\t", encoding="utf-8")

    # Write XLSX to avoid delimiter detection entirely
    xlsx_path = os.path.splitext(out_path)[0] + ".xlsx"
    try:
        with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
            out_df.to_excel(writer, index=False, sheet_name="predictions")
    except Exception as e:
        print(f"Warning: could not write XLSX at {xlsx_path}: {e}")

    print(f"Wrote predictions to {out_path}, {alt_path}, {readable_path}, {tsv_path}, and {xlsx_path} with {len(out_df)} rows.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=str, default=os.path.join(ROOT, 'predictions.csv'))
    parser.add_argument('--k', type=int, default=10)
    args = parser.parse_args()
    generate_predictions(args.out, k=args.k)
