import os
import re
from collections import defaultdict

import pandas as pd

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Folder input dari hasil cleaning
DATA_CLEAN_DIR = os.path.join(ROOT_DIR, "03_Output", "Data_CSV_Cleaned")

# File ground truth (teks) ada di folder yang sama, sama script ini
GT_TXT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ground_truth.txt")

# Folder & file output GT CSV
GT_OUTPUT_DIR = os.path.join(ROOT_DIR, "03_Output", "Ground_Truth")
GT_OUTPUT_PATH = os.path.join(GT_OUTPUT_DIR, "GT.csv")

os.makedirs(GT_OUTPUT_DIR, exist_ok=True)


#  LABEL
LABELS = [
    "RouterIDMismatch",
    "HelloMismatch",
    "DeadMismatch",
    "NetworkTypeMismatch",
    "AreaMismatch",
    "AuthMismatch",
    "AuthKeyMismatch",
    "MTUMismatch",
    "PassiveMismatch",
    "RedistributeMismatch",
]


# PARSING GROUND TRUTH
def parse_ground_truth(gt_path: str):
    """
    baca ground_truth.txt :
      - pair_rules[topologi][frozenset({R1,R2})] = set([label1, label2, ...])
      - single_rules[topologi][router] = set([label1, label2, ...])

    Contoh GT:
      Topologi 3  -> DeadMismatch R1 & R9
      Topologi 10 -> RedistributeMismatch R2
      Topologi 7  -> AuthKeyMismatch & AuthMismatch R2 & R3
      Topologi 12 -> (HelloMismatch R1 & R2)  & (DeadMismatch R1 & R9)
    """
    pair_rules = defaultdict(lambda: defaultdict(set))
    single_rules = defaultdict(lambda: defaultdict(set))

    with open(gt_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    for line in lines:
        # Format: "Topologi X -> ...."
        m = re.match(r"Topologi\s+(\d+)\s*->\s*(.+)", line)
        if not m:
            continue

        topo_id = int(m.group(1))
        desc = m.group(2).strip()

        # Jika Normal, berarti tidak ada mismatch di topologi ini
        if "Normal" in desc:
            continue

        # Rapiin ama pisah beberapa segmen mismatch:
        # "(A)  & (B)" atau "(A) & (B)" → "<<A>>###<<B>>"
        desc = desc.replace(")  & (", ") & (")
        desc = desc.replace(") & (", ")###(")
        segments = [seg.strip("() ").strip() for seg in desc.split("###")]

        for seg in segments:
            if not seg or seg == "...":
                continue

            # Bentuk segmen:
            # 1) "DeadMismatch R1 & R9"
            # 2) "RedistributeMismatch R2"
            # 3) "AuthKeyMismatch & AuthMismatch R2 & R3"

            # Cari pasangan router di ujung segmen
            m_pair = re.search(r"(R\d+)\s*&\s*(R\d+)", seg)
            m_single = re.search(r"(R\d+)\s*$", seg)

            if m_pair:
                r1, r2 = m_pair.group(1), m_pair.group(2)
                label_part = seg[:m_pair.start()].strip()
                label_names = [x.strip() for x in label_part.split("&")]

                for lbl in label_names:
                    if lbl in LABELS:
                        # ==== pair-based ====
                        key = frozenset({r1, r2})
                        pair_rules[topo_id][key].add(lbl)

                        # UNTUK RouterIDMismatch 
                        # kalau ada "RouterIDMismatch R1 & R7"
                        # artinya: R1 dan R7 adalah router bermasalah.
                        # maka, semua adjacency yang melibatkan R1 atau R7
                        # perlu diberi RouterIDMismatch = True.
                        if lbl == "RouterIDMismatch":
                            single_rules[topo_id][r1].add(lbl)
                            single_rules[topo_id][r2].add(lbl)

            elif m_single:
                r = m_single.group(1)
                label_part = seg[:m_single.start()].strip()
                label_names = [x.strip() for x in label_part.split("&")]

                for lbl in label_names:
                    if lbl in LABELS:
                        # Contoh utama: RedistributeMismatch R2
                        single_rules[topo_id][r].add(lbl)

    return pair_rules, single_rules


# MENGISI LABEL GT UNTUK SATU DATAFRAME
def apply_ground_truth_to_df(df: pd.DataFrame, pair_rules, single_rules) -> pd.DataFrame:
    """
    df: satu file CSV (hasil cleaning) yang punya kolom:
        topologi, router_a, router_b, dan fitur lainnya.

    Fungsi ini:
      - menghapus kolom label lama jika ada
      - menambahkan ulang 10 kolom LABELS dengan default False
      - mengisi True berdasarkan ground_truth.
    """
    required_cols = ["topologi", "router_a", "router_b"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Kolom wajib '{col}' tidak ditemukan di dataset.")

    # Hapus kolom label lama (bisi ada)
    for lbl in LABELS:
        if lbl in df.columns:
            df = df.drop(columns=[lbl])

    # Tambahin kolom label baru dengan default False
    for lbl in LABELS:
        df[lbl] = False
    
    # Isi label berdasarkan pair_rules dan single_rules
    for idx, row in df.iterrows():
        topo_raw = row["topologi"]
        try:
            topo_id = int(topo_raw)
        except (ValueError, TypeError):
            continue

        ra = str(row["router_a"]).strip()
        rb = str(row["router_b"]).strip()
        pair_key = frozenset({ra, rb})

        # 1) Label pasangan (Hello, Dead, NetworkType, Area, Auth,
        #    AuthKey, MTU, Passive, RouterID) 
        pair_for_topo = pair_rules.get(topo_id, {})
        if pair_key in pair_for_topo:
            for lbl in pair_for_topo[pair_key]:
                if lbl in LABELS:
                    df.at[idx, lbl] = True

        # 2) Label single-router (RedistributeMismatch, dan
        #    RouterIDMismatch hybrid yang tadi dimasukkan ke single_rules)
        single_for_topo = single_rules.get(topo_id, {})
        if ra in single_for_topo:
            for lbl in single_for_topo[ra]:
                if lbl in LABELS:
                    df.at[idx, lbl] = True
        if rb in single_for_topo:
            for lbl in single_for_topo[rb]:
                if lbl in LABELS:
                    df.at[idx, lbl] = True

    return df


# BACA SEMUA CSV CLEANED, ISI GT, GABUNG, SIMPAN GT.csv
def main():
    print("=== 5_Pembuatan_GT_CSV.py ===")
    print(f"ROOT_DIR           : {ROOT_DIR}")
    print(f"Data_CSV_Cleaned   : {DATA_CLEAN_DIR}")
    print(f"ground_truth.txt   : {GT_TXT_PATH}")
    print(f"Output GT          : {GT_OUTPUT_PATH}")
    print("")

    # --- Parsing ground_truth.txt ---
    pair_rules, single_rules = parse_ground_truth(GT_TXT_PATH)

    print(f"[i] Jumlah topologi dengan pair_rules   : {len(pair_rules)}")
    print(f"[i] Jumlah topologi dengan single_rules : {len(single_rules)}")
    print("")

    # --- Proses semua file di Data_CSV_Cleaned ---
    all_dfs = []
    file_list = sorted(
        f for f in os.listdir(DATA_CLEAN_DIR) if f.endswith(".csv")
    )

    if not file_list:
        print("[!] Tidak ada file .csv di Data_CSV_Cleaned.")
        return

    for fname in file_list:
        in_path = os.path.join(DATA_CLEAN_DIR, fname)
        print(f"[+] Memproses file: {fname}")

        # 1) Baca CSV hasil cleaning
        df = pd.read_csv(in_path)
        print(f"    - Jumlah baris awal (dari cleaning): {len(df)}")

        # 2) Terapkan ground truth ke dataframe ini
        df_gt = apply_ground_truth_to_df(df, pair_rules, single_rules)
        all_dfs.append(df_gt)

        topo_values = df_gt["topologi"].unique()
        print(f"    - Topologi di file ini : {list(topo_values)}")
        print(f"    - Jumlah baris final   : {len(df_gt)}\n")

    # 3) Gabungkan semua topologi menjadi satu GT.csv
    final_df = pd.concat(all_dfs, ignore_index=True)

    # SORTING DARI TOPOLOGI 1 sampe 100 
    final_df = final_df.sort_values(by=["topologi", "router_a", "router_b"]).reset_index(drop=True)

    final_df.to_csv(GT_OUTPUT_PATH, index=False)

    print(f"[✔] Ground Truth CSV berhasil dibuat: {GT_OUTPUT_PATH}")
    print(f"    Total baris: {len(final_df)}")
    print(f"    Total kolom: {len(final_df.columns)}")


if __name__ == "__main__":
    main()
