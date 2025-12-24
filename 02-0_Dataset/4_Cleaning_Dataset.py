import os
import pandas as pd

# === Path utama === #
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Folder input & output
input_dir = os.path.join(ROOT_DIR, "03_Output", "Data_CSV")
output_dir = os.path.join(ROOT_DIR, "03_Output", "Data_CSV_Cleaned")

os.makedirs(output_dir, exist_ok=True)

# Cek semua file dataset csv
for fname in sorted(os.listdir(input_dir)):
    if not fname.endswith(".csv"):
        continue

    fpath = os.path.join(input_dir, fname)
    df = pd.read_csv(fpath)
    print(f"[✓] Membaca {fname} ({len(df)} baris awal)")

    # Hapus baris kalo kolom Hello_a yg isinya 'none'
    col_hello = next((c for c in df.columns if c.lower() == "hello_a"), None)
    if col_hello:
        before = len(df)
        df[col_hello] = df[col_hello].astype(str).str.strip().str.lower()
        df = df[~df[col_hello].isin(["none", "nan", "", "null"])]
        removed = before - len(df)
        print(f"[–] Menghapus {removed} baris ({col_hello} kosong atau 'none')")

    # Hapus baris yg duplikat (R1–R2 sama  R2–R1)
    col_router_a = next((c for c in df.columns if c.lower() == "router_a"), None)
    col_neighbor_a = next((c for c in df.columns if c.lower() in ["neighbor_a", "neighbour_a"]), None)
    if col_router_a and col_neighbor_a:
        before = len(df)
        # buat key pasangan yang urutannya dinormalisasi (lexicographical)
        def make_pair_key(row):
            a = str(row[col_router_a]).strip()
            b = str(row[col_neighbor_a]).strip()
            # urutin biar (R1, R2) dan (R2, R1) punya key yang sama
            return "||".join(sorted([a, b]))

        df["pair_key"] = df.apply(make_pair_key, axis=1)

        # apus duplikatnya
        df = df.drop_duplicates(subset="pair_key", keep="first")

        # hapus kolom bantu
        df = df.drop(columns=["pair_key"])

        removed_pairs = before - len(df)
        print(
            f"[–] Menghapus {removed_pairs} baris duplikat pasangan router "
            f"({col_router_a} ↔ {col_neighbor_a}) yang berlawanan arah (R1-R2 vs R2-R1)"
        )
    else:
        print("[!] Kolom router_a / neighbor_a tidak ditemukan, skip penghapusan duplikat pasangan router.")

    # Reset index
    df = df.reset_index(drop=True)

    # Simpan ke folder Data_CSV_Cleaned
    out_path = os.path.join(output_dir, fname)
    df.to_csv(out_path, index=False)

    print(f"[✓] File {fname} disimpan ke Data_CSV_Cleaned ({len(df)} baris)\n")

print(f"[✔] Semua dataset selesai dibersihkan dan tersimpan di folder: {output_dir}")
