import os
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(__file__))
XLSX_PATH = os.path.join(ROOT, 'Gen_AI Dataset.xlsx')
OUT_DIR = os.path.join(ROOT, 'data')


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    assert os.path.exists(XLSX_PATH), f"Excel file not found: {XLSX_PATH}"
    xls = pd.ExcelFile(XLSX_PATH)
    print("Sheets:", xls.sheet_names)
    # Try common names
    train_sheet = None
    test_sheet = None
    for name in xls.sheet_names:
        low = name.lower()
        if 'train' in low or 'labeled' in low or 'labelled' in low:
            train_sheet = name
        if 'test' in low or 'unlabeled' in low or 'unlabelled' in low:
            test_sheet = name
    # fallback to first/second
    if train_sheet is None and len(xls.sheet_names) >= 1:
        train_sheet = xls.sheet_names[0]
    if test_sheet is None and len(xls.sheet_names) >= 2:
        test_sheet = xls.sheet_names[1]

    train_df = pd.read_excel(XLSX_PATH, sheet_name=train_sheet)
    test_df = pd.read_excel(XLSX_PATH, sheet_name=test_sheet)

    print("Train head:\n", train_df.head())
    print("Test head:\n", test_df.head())

    train_csv = os.path.join(OUT_DIR, 'train.csv')
    test_csv = os.path.join(OUT_DIR, 'test.csv')
    train_df.to_csv(train_csv, index=False)
    test_df.to_csv(test_csv, index=False)
    print("Wrote:", train_csv, test_csv)


if __name__ == '__main__':
    main()
