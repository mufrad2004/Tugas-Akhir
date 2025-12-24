import os
import re
from collections import OrderedDict

import pandas as pd

# ============================================
# KONFIGURASI PATH
# ============================================
# ROOT_DIR = folder utama proyek (satu level di atas 02-*)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# GT hasil 5_Pembuatan_GT_CSV.py
GT_CSV_PATH = os.path.join(ROOT_DIR, "03_Output", "Ground_Truth", "GT.csv")

# Hasil Rule-Based per-topologi (topologi_1.csv ~ topologi_100.csv)
DATA_LABELED_DIR = os.path.join(ROOT_DIR, "03_Output", "Hasil_Rule_Based (Sebelum Evaluasi)")

# Folder & file output evaluasi
EVAL_DIR = os.path.join(ROOT_DIR, "04_Evaluasi")
os.makedirs(EVAL_DIR, exist_ok=True)

# ========= PENGATURAN SKENARIO =========
# Skenario 1 & 2 
# ! Kalau mau berapa topologi yang diambil, ubah ubah 2 var dibawah ini 
SCENARIO_MIN_TOPO = 1
SCENARIO_MAX_TOPO = 50

OUT_TXT = os.path.join(
    EVAL_DIR,
    f"Hasil_Evaluasi_Rule_Based_{SCENARIO_MIN_TOPO}_{SCENARIO_MAX_TOPO}_Topologi.txt"
)

# ============================================
# KONFIGURASI LABEL (SAMA DENGAN RF)
# ============================================
LABELS = [
    "HelloMismatch",
    "DeadMismatch",
    "NetworkTypeMismatch",
    "AreaMismatch",
    "AuthMismatch",
    "AuthKeyMismatch",
    "MTUMismatch",
    "PassiveMismatch",
    "RedistributeMismatch",
    "RouterIDMismatch",
]

# ============================================
# UTIL
# ============================================
def safe_div(a, b):
    return a / b if b else 0.0


def natural_key_topologi(fname: str) -> int:
    """
    Ekstrak nomor dari nama file topologi_XX.csv untuk sorting.
    Kalau tidak ketemu angka, kembalikan angka besar.
    """
    m = re.search(r"(\d+)", fname)
    return int(m.group(1)) if m else 10**9


# ============================================
# LOAD DATA GT & RULE-BASED (CSV)
# ============================================
def load_ground_truth_csv() -> pd.DataFrame:
    """
    Membaca GT.csv lalu sort berdasarkan topologi, router_a, router_b.
    Mengembalikan dataframe lengkap (bukan cuman labelnya).
    """
    if not os.path.exists(GT_CSV_PATH):
        raise FileNotFoundError(f"GT.csv tidak ditemukan: {GT_CSV_PATH}")

    df_gt = pd.read_csv(GT_CSV_PATH)

    #  kolom ini harus ada
    required_cols = ["topologi", "router_a", "router_b"]
    for col in required_cols:
        if col not in df_gt.columns:
            raise ValueError(f"Kolom wajib '{col}' tidak ada di GT.csv")

    # sorting supaya urutan baris dari GT.csv dan Hasil Rule Based sama persis
    df_gt = df_gt.sort_values(
        by=["topologi", "router_a", "router_b"]
    ).reset_index(drop=True)

    return df_gt


def load_rule_based_csv() -> pd.DataFrame:
    """
    Membaca seluruh file topologi_*.csv di Hasil_Rule_Based (Sebelum Evalusi),
    gabung menjadi satu dataframe, lalu sort berdasarkan
    topologi, router_a, router_b.
    """
    if not os.path.isdir(DATA_LABELED_DIR):
        raise FileNotFoundError(f"Folder Hasil_Rule_Based (Sebelum Evalusi) tidak ditemukan: {DATA_LABELED_DIR}")

    file_list = [
        f for f in os.listdir(DATA_LABELED_DIR)
        if f.lower().endswith(".csv")
    ]

    if not file_list:
        raise FileNotFoundError("Tidak ada file .csv di Hasil_Rule_Based (Sebelum Evalusi).")

    # sort berdasar nomor di nama file (topologi_1, topologi_2, ..., topologi_100)
    file_list = sorted(file_list, key=natural_key_topologi)

    all_dfs = []
    for fname in file_list:
        path = os.path.join(DATA_LABELED_DIR, fname)
        df = pd.read_csv(path)
        all_dfs.append(df)

    df_rb = pd.concat(all_dfs, ignore_index=True)

    # pastikan kolom penting ada
    required_cols = ["topologi", "router_a", "router_b"]
    for col in required_cols:
        if col not in df_rb.columns:
            raise ValueError(f"Kolom wajib '{col}' tidak ada di {DATA_LABELED_DIR}")

    # sorting supaya urutan baris sama
    df_rb = df_rb.sort_values(
        by=["topologi", "router_a", "router_b"]
    ).reset_index(drop=True)

    return df_rb


# ============================================
# EVALUASI: GT vs RULE-BASED (PER BARIS, PER LABEL)
# ============================================
def evaluate(gt_labels: pd.DataFrame, rb_labels: pd.DataFrame):
    """
    gt_labels dan rb_labels adalah dataframe boolean
    dengan kolom persis LABELS dan shape yang sama.
    Evaluasi dilakukan per-baris x per-label.
    """
    if gt_labels.shape != rb_labels.shape:
        raise ValueError(
            f"Beda shape antara GT dan Rule-Based: "
            f"gt={gt_labels.shape}, rb={rb_labels.shape}"
        )

    n_samples = gt_labels.shape[0]
    n_labels = len(LABELS)

    # inisialisasi statistik per label
    stats = {
        lbl: {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
        for lbl in LABELS
    }

    micro_tp = micro_fp = micro_fn = micro_tn = 0
    subset_acc_list = []

    # loop per baris
    for i in range(n_samples):
        gt_row = gt_labels.iloc[i]
        rb_row = rb_labels.iloc[i]

        # subset accuracy (match 10 label di baris ini)
        if gt_row.equals(rb_row):
            subset_acc_list.append(1.0)
        else:
            subset_acc_list.append(0.0)

        # hitung TP/FP/FN/TN per label
        for lbl in LABELS:
            y_true = bool(gt_row[lbl])
            y_pred = bool(rb_row[lbl])

            if y_true and y_pred:
                stats[lbl]["tp"] += 1
                micro_tp += 1
            elif (not y_true) and (not y_pred):
                stats[lbl]["tn"] += 1
                micro_tn += 1
            elif y_true and (not y_pred):
                stats[lbl]["fn"] += 1
                micro_fn += 1
            elif (not y_true) and y_pred:
                stats[lbl]["fp"] += 1
                micro_fp += 1

    # hitung metrik per label
    per_label = OrderedDict()
    for lbl in LABELS:
        tp = stats[lbl]["tp"]
        fp = stats[lbl]["fp"]
        fn = stats[lbl]["fn"]
        tn = stats[lbl]["tn"]

        p = safe_div(tp, tp + fp)
        r = safe_div(tp, tp + fn)
        f1 = safe_div(2 * p * r, (p + r))

        support_pos = tp + fn      # jumlah kasus positif (GT = True)
        support_neg = tn + fp      # jumlah kasus negatif
        support_all = support_pos + support_neg

        acc_label = safe_div(tp + tn, support_all)

        per_label[lbl] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1": round(f1, 4),
            "accuracy": round(acc_label, 4),
            "support_pos": support_pos,
            "support_neg": support_neg,
            "support_all": support_all,
        }

    # macro-average (rata-rata per label)
    if per_label:
        macro_p = sum(v["precision"] for v in per_label.values()) / n_labels
        macro_r = sum(v["recall"]    for v in per_label.values()) / n_labels
        macro_f1= sum(v["f1"]        for v in per_label.values()) / n_labels
        macro_acc = sum(v["accuracy"] for v in per_label.values()) / n_labels
    else:
        macro_p = macro_r = macro_f1 = macro_acc = 0.0

    # micro (berbasis semua label & semua baris)
    micro_p = safe_div(micro_tp, micro_tp + micro_fp)
    micro_r = safe_div(micro_tp, micro_tp + micro_fn)
    micro_f1= safe_div(2 * micro_p * micro_r, (micro_p + micro_r))

    # micro accuracy Jaccard (pakai TP/FP/FN saja)
    micro_jaccard = safe_div(micro_tp, (micro_tp + micro_fp + micro_fn))

    # micro accuracy klasik (pakai TN juga)
    total_micro = micro_tp + micro_fp + micro_fn + micro_tn
    micro_acc_std = safe_div(micro_tp + micro_tn, total_micro)

    # Hamming Accuracy (per-label accuracy)
    total_labels = n_labels * n_samples
    hamming_accuracy = safe_div(micro_tp + micro_tn, total_labels)

    subset_acc_mean = sum(subset_acc_list) / len(subset_acc_list) if subset_acc_list else 1.0

    summary = {
        "macro": {
            "precision": round(macro_p, 4),
            "recall": round(macro_r, 4),
            "f1": round(macro_f1, 4),
            "accuracy": round(macro_acc, 4),
        },
        "micro": {
            "precision": round(micro_p, 4),
            "recall": round(micro_r, 4),
            "f1": round(micro_f1, 4),
            "accuracy_jaccard": round(micro_jaccard, 4),
            "accuracy_standard": round(micro_acc_std, 4),
            "hamming_accuracy": round(hamming_accuracy, 4),
        },
        "global_counts": {
            "tp_total": micro_tp,
            "fp_total": micro_fp,
            "fn_total": micro_fn,
            "tn_total": micro_tn,
        },
        "subset_accuracy": {
            "mean_exact_match": round(subset_acc_mean, 4),
            "num_samples": n_samples,
        },
    }
    return per_label, summary


# ============================================
# SIMPAN TXT
# ============================================
def save_txt(per_label, summary, out_path, info_note: str, title_line: str):
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"{title_line}\n")
        f.write(f"{info_note}\n")

        f.write("\n== Per Label ==\n")
        f.write("Label                  | TP  FP  FN  TN  | Prec   Rec    F1     Acc    | Pos  Neg  All\n")
        f.write("-" * 96 + "\n")
        for lbl, v in per_label.items():
            f.write(
                f"{lbl:22} | "
                f"{v['tp']:4} {v['fp']:4} {v['fn']:4} {v['tn']:4} | "
                f"{v['precision']:.4f} {v['recall']:.4f} {v['f1']:.4f} {v['accuracy']:.4f} | "
                f"{v['support_pos']:4} {v['support_neg']:4} {v['support_all']:4}\n"
            )

        f.write("\n== Rata-rata (Macro) ==\n")
        f.write(f"Macro Precision       : {summary['macro']['precision']}\n")
        f.write(f"Macro Recall          : {summary['macro']['recall']}\n")
        f.write(f"Macro F1-Score        : {summary['macro']['f1']}\n")
        f.write(f"Macro Accuracy        : {summary['macro']['accuracy']}\n")

        f.write("\n== Metrik Mikro (Global) ==\n")
        f.write(f"Micro Precision       : {summary['micro']['precision']}\n")
        f.write(f"Micro Recall          : {summary['micro']['recall']}\n")
        f.write(f"Micro F1-Score        : {summary['micro']['f1']}\n")
        f.write(f"Micro Accuracy Jaccard: {summary['micro']['accuracy_jaccard']}\n")
        f.write(f"Micro Accuracy Std    : {summary['micro']['accuracy_standard']}\n")
        f.write(f"Hamming Accuracy      : {summary['micro']['hamming_accuracy']}\n")

        f.write("\n== TP/FP/FN/TN & Subset Accuracy ==\n")
        f.write(
            f"Total TP/FP/FN/TN     : "
            f"{summary['global_counts']['tp_total']}/"
            f"{summary['global_counts']['fp_total']}/"
            f"{summary['global_counts']['fn_total']}/"
            f"{summary['global_counts']['tn_total']}\n"
        )
        f.write(
            f"Subset Accuracy (Exact Match, mean per-sample) : "
            f"{summary['subset_accuracy']['mean_exact_match']}\n"
        )
        f.write(
            f"Total Samples Evaluated                       : "
            f"{summary['subset_accuracy']['num_samples']}\n"
        )

    print(f"[✔] Hasil evaluasi disimpan ke: {out_path}")


# ============================================
# MAIN
# ============================================
def main():
    print("=== 4_Evaluasi_Rule_Based_CSV (Skenario Topologi Range) ===")
    print(f"ROOT_DIR          : {ROOT_DIR}")
    print(f"GT_CSV_PATH       : {GT_CSV_PATH}")
    print(f"DATA_LABELED_DIR  : {DATA_LABELED_DIR}")
    print(f"Output TXT        : {OUT_TXT}")
    print(f"Topologi dipakai  : {SCENARIO_MIN_TOPO}–{SCENARIO_MAX_TOPO}")
    print("")

    # --- Load data lengkap ---
    df_gt_full = load_ground_truth_csv()
    df_rb_full = load_rule_based_csv()

    # --- Filter sesuai skenario (misal 1–50) ---
    mask_gt = df_gt_full["topologi"].between(SCENARIO_MIN_TOPO, SCENARIO_MAX_TOPO)
    mask_rb = df_rb_full["topologi"].between(SCENARIO_MIN_TOPO, SCENARIO_MAX_TOPO)

    df_gt = df_gt_full[mask_gt].reset_index(drop=True)
    df_rb = df_rb_full[mask_rb].reset_index(drop=True)

    # cek konsistensi jumlah baris
    if len(df_gt) != len(df_rb):
        raise ValueError(
            f"Jumlah baris GT ({len(df_gt)}) != jumlah baris Rule-Based ({len(df_rb)}) "
            f"setelah filtering topologi {SCENARIO_MIN_TOPO}–{SCENARIO_MAX_TOPO}"
        )

    # cek konsistensi pasangan (topologi, router_a, router_b)
    for col in ["topologi", "router_a", "router_b"]:
        if not (df_gt[col].astype(str).tolist() == df_rb[col].astype(str).tolist()):
            raise ValueError(f"Kolom {col} tidak selaras antara GT.csv dan Hasil_Rule_Based setelah filtering")

    # pastikan semua label ada di kedua dataframe
    for lbl in LABELS:
        if lbl not in df_gt.columns:
            raise ValueError(f"Label '{lbl}' tidak ditemukan di GT.csv")
        if lbl not in df_rb.columns:
            raise ValueError(f"Label '{lbl}' tidak ditemukan di Hasil_Rule_Based")

    # ambil hanya kolom label dan convert ke boolean
    gt_labels = df_gt[LABELS].astype(bool)
    rb_labels = df_rb[LABELS].astype(bool)

    n_topo = df_gt["topologi"].nunique()
    topo_min = df_gt["topologi"].min()
    topo_max = df_gt["topologi"].max()

    # info untuk header
    info_note = (
        f"Total topologi    : {n_topo} (range: {topo_min}–{topo_max})\n"
        f"Total sampel baris: {len(df_gt)}\n"
        f"Total label       : {len(LABELS)} (per sampel)"
    )
    title_line = "=== HASIL EVALUASI RULE-BASED (CSV vs CSV, SKENARIO TOPOLOGI TERBATAS) ==="

    # --- Evaluasi ---
    per_label, summary = evaluate(gt_labels, rb_labels)

    # --- Simpan hasil ---
    save_txt(per_label, summary, OUT_TXT, info_note, title_line)


if __name__ == "__main__":
    main()
