import os
import pandas as pd

# === Path utama === #
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
input_dir = os.path.join(ROOT_DIR, "03_Output", "Data_CSV_Cleaned")
output_dir = os.path.join(ROOT_DIR, "03_Output", "Hasil_Rule_Based (Sebelum Evaluasi)")

os.makedirs(output_dir, exist_ok=True)


# === Fungsi bantu umum === #
def normalize_case(value):
    """Ubah nilai menjadi lowercase string untuk perbandingan aman."""
    return str(value).strip().lower()


def check_redistribute(row):
    """
    Cek RedistributeMismatch sesuai logika:
    - Hanya router dengan routing 'ospf,eigrp' yang dicek.
    - Jika redistributenya False → mismatch (True)
    - Jika redistributenya True → match (False)
    """
    routing_a = str(row.get("routing_a", "")).lower()
    routing_b = str(row.get("routing_b", "")).lower()
    redist_a = bool(row.get("redistribute_a", False))
    redist_b = bool(row.get("redistribute_b", False))

    if "ospf,eigrp" in routing_a and not redist_a:
        return True
    if "ospf,eigrp" in routing_b and not redist_b:
        return True
    return False


# === Fungsi bantu khusus AUTH KEY === #
def parse_auth_keys(raw):
    """
    Ubah string auth_key menjadi set (key_id, key_value).

    Contoh:
      '1:cisco123;2:cisco321' -> {('1','cisco123'), ('2','cisco321')}
      'simple:cisco123'       -> {('simple','cisco123')}
    """
    if pd.isna(raw):
        return set()

    text = str(raw).strip()
    if not text:
        return set()

    parts = [p.strip() for p in text.replace(",", ";").split(";") if p.strip()]
    result = set()

    for p in parts:
        if ":" in p:
            kid, key = p.split(":", 1)
        elif " " in p:
            kid, key = p.split(None, 1)
        else:
            kid, key = "", p
        result.add((kid.strip(), key.strip()))

    return result


def check_authkey_mismatch(row):
    """
    Logika AuthKeyMismatch:

    - Ambil auth_key_a dan auth_key_b sebagai set (ID, KEY)
    - Jika KEDUANYA kosong   -> tidak mismatch (False)
    - Jika salah satu kosong -> mismatch (True)
    - Jika ada minimal satu pasangan (ID, KEY) yang sama -> tidak mismatch (False)
    - Jika tidak ada pasangan yang sama sama sekali -> mismatch (True)
    """
    keys_a = parse_auth_keys(row.get("auth_key_a", ""))
    keys_b = parse_auth_keys(row.get("auth_key_b", ""))

    # kedua sisi tidak punya key -> tidak dianggap mismatch
    if not keys_a and not keys_b:
        return False

    # salah satu punya key, sisi lain tidak -> mismatch
    if not keys_a or not keys_b:
        return True

    # kalau ada minimal satu pasangan (ID, KEY) yang sama -> BUKAN mismatch
    if keys_a.intersection(keys_b):
        return False

    # kalau tidak ada pasangan yang sama sama sekali -> mismatch
    return True


# === Fungsi utama === #
for fname in sorted(os.listdir(input_dir)):
    if not fname.endswith(".csv"):
        continue

    fpath = os.path.join(input_dir, fname)
    df = pd.read_csv(fpath)
    print(f"[✓] Membaca {fname} ({len(df)} baris)")

    # === RouterIDMismatch (FIXED) === #
    # 1. Mapping router_id → router names
    rid_map = {}
    
    # Tambahkan router_a
    for r, rid in zip(df["router_a"], df["router_id_a"]):
        rid_map.setdefault(rid, set()).add(r)

    # Tambahkan router_b
    for r, rid in zip(df["router_b"], df["router_id_b"]):
        rid_map.setdefault(rid, set()).add(r)

    # 2. Ambil router yang benar-benar duplicate (lebih dari 1)
    routers_with_duplicate_id = set(
        r for rid, routers in rid_map.items() if len(routers) > 1 for r in routers
    )

    # 3. Tandai mismatch hanya jika adjacency menyentuh router duplicate
    df["RouterIDMismatch"] = df.apply(
        lambda x: (x["router_a"] in routers_with_duplicate_id) or (x["router_b"] in routers_with_duplicate_id),
        axis=1
    )

    # === Labeling sesuai logika === #
    df["HelloMismatch"] = df["hello_a"] != df["hello_b"]
    df["DeadMismatch"] = df["dead_a"] != df["dead_b"]
    df["NetworkTypeMismatch"] = (
        df["network_type_a"].apply(normalize_case) !=
        df["network_type_b"].apply(normalize_case)
    )
    df["AreaMismatch"] = df["area_a"] != df["area_b"]
    df["AuthMismatch"] = (
        df["ospf_auth_a"].apply(normalize_case) !=
        df["ospf_auth_b"].apply(normalize_case)
    )

    # AuthKeyMismatch pakai set + interseksi, bukan string mentah
    df["AuthKeyMismatch"] = df.apply(check_authkey_mismatch, axis=1)

    df["MTUMismatch"] = df["MTU_a"] != df["MTU_b"]

    # PassiveMismatch: minimal salah satu side passive -> True
    df["PassiveMismatch"] = df.apply(
        lambda x: bool(x["passive_a"]) or bool(x["passive_b"]),
        axis=1
    )

    df["RedistributeMismatch"] = df.apply(check_redistribute, axis=1)

    # === Urutan kolom label === #
    label_cols = [
        "HelloMismatch", "DeadMismatch", "NetworkTypeMismatch",
        "RouterIDMismatch", "AuthMismatch", "AuthKeyMismatch",
        "PassiveMismatch", "RedistributeMismatch", "AreaMismatch", "MTUMismatch"
    ]


    # === Simpan hasil === #
    out_csv = os.path.join(
        output_dir,
        fname.replace("clean_", "labeled_").replace("dataset_", "labeled_")
    )
    df.to_csv(out_csv, index=False)
    print(f"[✓] File {fname} selesai diberi label ({len(df)} baris) → {out_csv}\n")

print(f"[✔] Semua dataset selesai diberi label. Hasil tersimpan di folder: {output_dir}")
