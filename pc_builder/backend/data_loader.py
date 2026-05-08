import os
import pandas as pd


def load_components(excel_path):
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"الملف غير موجود: {excel_path}")

    sheets = pd.read_excel(excel_path, sheet_name=None)

    required_sheets = ["CPUs", "MBs", "RAMs", "Storage", "GPUs", "PSUs"]
    missing = [sheet for sheet in required_sheets if sheet not in sheets]
    if missing:
        raise KeyError(f"أوراق العمل التالية غير موجودة في ملف Excel: {', '.join(missing)}")

    components = {
        "cpu": sheets["CPUs"].to_dict(orient="records"),
        "mb": sheets["MBs"].to_dict(orient="records"),
        "ram": sheets["RAMs"].to_dict(orient="records"),
        "storage": sheets["Storage"].to_dict(orient="records"),
        "gpu": sheets["GPUs"].to_dict(orient="records"),
        "psu": sheets["PSUs"].to_dict(orient="records"),
    }

    return components


if __name__ == "__main__":
    path = os.path.join(
        os.path.dirname(__file__),
        "data",
        "PC_Components_Dataset_small__2_.xlsx",
    )

    data = load_components(path)

    print("=== عدد المكونات المحملة ===")
    for key, items in data.items():
        print(f"  {key}: {len(items)} مكوّن")

    print("\n=== أول مكوّن من كل فئة ===")
    for key, items in data.items():
        print(f"\n[ {key.upper()} ]")
        if not items:
            print("  لا توجد بيانات")
            continue
        for col, val in items[0].items():
            print(f"  {col}: {val}")