import os
import pandas as pd
import shutil

# ==========================================================
#  RULE-BASED TXT FORMATTER DARI CSV_LABELED
#  Input : 03_Output/Hasil_Rule_Based (Sebelum Evaluasi)/topologi_XX.csv
#  Output: 03_Output/Laporan_Rule_Based/hasil_deteksi_XX.txt
# ==========================================================

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = os.path.join(ROOT_DIR, "03_Output", "Hasil_Rule_Based (Sebelum Evaluasi)")
OUTPUT_DIR = os.path.join(ROOT_DIR, "05_Laporan_Rule_Based")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def norm(s):
    return str(s).strip().lower()

def short_ifname(name: str) -> str:
    """Ubah variasi FastEthernet → Fa dan hilangkan spasi berlebih"""
    if pd.isna(name):
        return ""
    s = str(name).strip()
    # samakan dulu: FastEthernet 0/1 -> FastEthernet0/1
    s = s.replace("FastEthernet ", "FastEthernet")
    # baru ganti ke Fa
    s = s.replace("FastEthernet", "Fa")
    # jaga-jaga kalau masih ada 'Fa ' -> 'Fa'
    s = s.replace("Fa ", "Fa")

    return s


def format_header_pair(r1, r2):
    return [
        f"=== Mismatch antara {r1} dan {r2} ===",
        "========================================================="
    ]


def format_footer():
    return ["=========================================================\n"]


# ----------------------------------------------------------
# 1. MISMATCH BERBASIS ADJACENCY (Area, MTU, NetworkTyp)
# ----------------------------------------------------------
def handle_simple_pair_mismatch(results, row, field_name, val_a, val_b):
    r1, r2 = row["router_a"], row["router_b"]
    intf1 = short_ifname(row["interface_a"])
    intf2 = short_ifname(row["interface_b"])


    results.extend(format_header_pair(r1, r2))
    results.append(f"- {field_name} Mismatch :")
    results.append(f"\t* {r1} {intf1} : {val_a}")
    results.append(f"\t* {r2} {intf2} : {val_b}")
    results.append("=========================================================")
    results.append("+ Solusi :")
    results.append(f"\t* Samakan nilai {field_name} pada {r1} dan {r2}")
    results.extend(format_footer())


def handle_interval_mismatch(results, row, field_label, val_a, val_b):
    r1, r2 = row["router_a"], row["router_b"]
    intf1 = short_ifname(row["interface_a"])
    intf2 = short_ifname(row["interface_b"])

    results.extend(format_header_pair(r1, r2))
    results.append(f"- {field_label} Interval Mismatch :")
    results.append(f"\t* {r1} {intf1} : {val_a}")
    results.append(f"\t* {r2} {intf2} : {val_b}")
    results.append("=========================================================")
    results.append("+ Solusi :")
    results.append(f"\t* Samakan nilai {field_label} Interval pada {r1} dan {r2}")
    results.extend(format_footer())


# ----------------------------------------------------------
# 1b. PASSIVE INTERFACE MISMATCH (KHUSUS)
# ----------------------------------------------------------
def handle_passive_mismatch(results, row):
    r1, r2 = row["router_a"], row["router_b"]
    intf1 = short_ifname(row["interface_a"])
    intf2 = short_ifname(row["interface_b"])

    raw_a = row.get("passive_a", "")
    raw_b = row.get("passive_b", "")

    v_a = norm(raw_a)
    v_b = norm(raw_b)

    def is_passive(v: str) -> bool:
        return v in {"yes", "true", "passive", "1", "on", "enable", "enabled"}

    side_a_passive = is_passive(v_a)
    side_b_passive = is_passive(v_b)

    results.extend(format_header_pair(r1, r2))
    results.append("- Passive Interface Mismatch :")
    results.append(f"\t* {r1} {intf1} : {raw_a}")
    results.append(f"\t* {r2} {intf2} : {raw_b}")
    results.append("=========================================================")
    results.append("+ Solusi :")

    if side_a_passive and not side_b_passive:
        results.append(f"\t* Matikan passive-interface pada interface {intf1} di {r1}.")
    elif side_b_passive and not side_a_passive:
        results.append(f"\t* Matikan passive-interface pada interface {intf2} di {r2}.")
    else:
        results.append("\t* Sesuaikan konfigurasi passive-interface agar kedua sisi konsisten.")
        results.append("\t* Pastikan tidak ada interface yang seharusnya membentuk tetangga OSPF namun diset passive.")

    results.extend(format_footer())


# ----------------------------------------------------------
# 2. AUTHENTICATION MISMATCH  (FORMAT SAMA DENGAN LAPORAN)
# ----------------------------------------------------------
def handle_auth_mismatch(results, row):
    """
    Output contoh:
    - ospf auth Mismatch :
        * R2 Fa1/0 : message-digest
        * R3 Fa1/0 : simple
    + Solusi :
        * Samakan nilai ospf auth pada R2 dan R3
    """
    r1, r2 = row["router_a"], row["router_b"]
    intf1 = short_ifname(row["interface_a"])
    intf2 = short_ifname(row["interface_b"])

    val1_raw = row["ospf_auth_a"]
    val2_raw = row["ospf_auth_b"]

    results.extend(format_header_pair(r1, r2))
    results.append("- ospf auth Mismatch :")
    results.append(f"\t* {r1} {intf1} : {val1_raw}")
    results.append(f"\t* {r2} {intf2} : {val2_raw}")
    results.append("=========================================================")
    results.append("+ Solusi :")
    results.append(f"\t* Samakan nilai ospf auth pada {r1} dan {r2}")
    results.extend(format_footer())


# ----------------------------------------------------------
# 3. AUTH KEY HELPERS
# ----------------------------------------------------------
def parse_auth_keys(raw):
    """
    Ubah string auth_key menjadi list (key_id, key_value)
    Contoh:
      '1:cisco123;2:cisco321' -> [('1','cisco123'), ('2','cisco321')]
      'simple:cisco123'       -> [('simple','cisco123')]
      'cisco123'              -> [('', 'cisco123')]
    """
    if pd.isna(raw):
        return []
    text = str(raw).strip()
    if not text:
        return []

    parts = [p.strip() for p in text.replace(",", ";").split(";") if p.strip()]
    result = []
    for p in parts:
        if ":" in p:
            kid, key = p.split(":", 1)
        elif " " in p:
            kid, key = p.split(None, 1)
        else:
            kid, key = "", p
        result.append((kid.strip(), key.strip()))
    return result


def handle_authkey_md5_vs_md5(results, row, keys_a, keys_b):
    r1, r2 = row["router_a"], row["router_b"]
    intf1 = short_ifname(row["interface_a"])
    intf2 = short_ifname(row["interface_b"])

    results.extend(format_header_pair(r1, r2))
    results.append("- auth_key Mismatch :")
    results.append(f"\t* {r1} {intf1} :")
    for kid, key in keys_a:
        results.append(f"\t\t* {kid} : {key}")
    results.append(f"\t* {r2} {intf2} :")
    for kid, key in keys_b:
        results.append(f"\t\t* {kid} : {key}")
    results.append("=========================================================")
    results.append("+ Solusi :")
    results.append("\t* Lakukan penyeragaman Authentication Key (ID dan key) pada kedua router.")
    results.extend(format_footer())


def handle_authkey_md5_vs_simple(results, row, keys_md5, side_md5_is_a=True):
    """
    Kasus MD5 vs SIMPLE:
    - Sisi MD5: tampilkan semua key-id + key
    - Sisi SIMPLE: tampilkan password simple (dari auth_key_x kalau ada)
    Output contoh:
    - auth_key Mismatch :
        * R2 Fa1/0 :
            * 1 : cisco123
        * R3 Fa1/0 :
            * simple : cisco123
    + Solusi :
        * R2 dan R3 memiliki jenis Authentication yang berbeda
        * Samakan jenis Authentication dan Authentication Key
    """
    r1, r2 = row["router_a"], row["router_b"]
    intf1 = short_ifname(row["interface_a"])
    intf2 = short_ifname(row["interface_b"])

    auth1, auth2 = row["ospf_auth_a"], row["ospf_auth_b"]

    if side_md5_is_a:
        router_md5, intf_md5, auth_md5 = r1, intf1, auth1
        router_simple, intf_simple, auth_simple = r2, intf2, auth2
        raw_simple_key = row.get("auth_key_b", "")
    else:
        router_md5, intf_md5, auth_md5 = r2, intf2, auth2
        router_simple, intf_simple, auth_simple = r1, intf1, auth1
        raw_simple_key = row.get("auth_key_a", "")

    simple_keys = parse_auth_keys(raw_simple_key)

    results.extend(format_header_pair(r1, r2))
    results.append("- auth_key Mismatch :")

    # Sisi MD5
    results.append(f"\t* {router_md5} {intf_md5} :")
    for kid, key in keys_md5:
        # di MD5, kita pakai apa adanya (1,2,...)
        results.append(f"\t\t* {kid} : {key}")

    # Sisi SIMPLE
    results.append(f"\t* {router_simple} {intf_simple} :")
    if simple_keys:
        for kid, key in simple_keys:
            # supaya muncul "simple : cisco123", bukan "key : ..."
            label = kid if kid else "key"
            results.append(f"\t\t* {label} : {key}")
    else:
        results.append(f"\t\t* {auth_simple}")

    results.append("=========================================================")
    results.append("+ Solusi :")
    results.append(f"\t* {r1} dan {r2} memiliki jenis Authentication yang berbeda")
    results.append("\t* Samakan jenis Authentication dan Authentication Key")
    results.extend(format_footer())


def handle_authkey_simple_vs_simple(results, row, keys_a, keys_b):
    """
    SIMPLE vs SIMPLE:
    - Tampilkan masing-masing password simple
      (label 'simple' tetap dipertahankan)
    """
    r1, r2 = row["router_a"], row["router_b"]
    intf1 = short_ifname(row["interface_a"])
    intf2 = short_ifname(row["interface_b"])


    results.extend(format_header_pair(r1, r2))
    results.append("- auth_key Mismatch :")

    results.append(f"\t* {r1} {intf1} :")
    for kid, key in keys_a:
        label = kid if kid else "key"
        results.append(f"\t\t* {label} : {key}")

    results.append(f"\t* {r2} {intf2} :")
    for kid, key in keys_b:
        label = kid if kid else "key"
        results.append(f"\t\t* {label} : {key}")

    results.append("=========================================================")
    results.append("+ Solusi :")
    results.append("\t* Samakan Authentication Key")
    results.extend(format_footer())


# ----------------------------------------------------------
# 4. REDISTRIBUTE MISMATCH
# ----------------------------------------------------------
def handle_redistribute_mismatch(results, df):
    reported = set()
    for _, row in df.iterrows():
        if not bool(row.get("RedistributeMismatch", False)):
            continue

        for side in ["a", "b"]:
            routing = norm(row.get(f"routing_{side}", ""))
            redist = bool(row.get(f"redistribute_{side}", False))
            router = row.get(f"router_{side}")

            if "ospf,eigrp" in routing and not redist:
                if router in reported:
                    continue
                reported.add(router)

                results.append(f"=== Mismatch pada {router} ===")
                results.append("=========================================================")
                results.append("- Redistribute Mismatch :")
                results.append("\t* Belum melakukan redistribute")
                results.append("\tatau")
                results.append('\t* Command "redistribute" kurang kata kunci "subnets"')
                results.append("=========================================================")
                results.append("+ Solusi :")
                results.append('\t* Tambahkan command "redistribute eigrp <as number> subnets"')
                results.extend(format_footer())


# ----------------------------------------------------------
# 5. ROUTER ID MISMATCH (GLOBAL)
# ----------------------------------------------------------
def handle_routerid_mismatch(results, df):
    router_rid = {}

    for r, rid in zip(df["router_a"], df["router_id_a"]):
        router_rid.setdefault(str(r), str(rid))

    for r, rid in zip(df["router_b"], df["router_id_b"]):
        router_rid.setdefault(str(r), str(rid))

    rid_to_routers = {}
    for r, rid in router_rid.items():
        rid_to_routers.setdefault(rid, []).append(r)

    for rid, routers in rid_to_routers.items():
        if len(routers) <= 1:
            continue

        routers_sorted = sorted(routers)
        r1, r2 = routers_sorted[0], routers_sorted[1]

        results.append(f"=== Mismatch antara {r1} dan {r2} ===")
        results.append("=========================================================")
        results.append("- Router ID Mismatch :")
        results.append(f"\t* {r1} : {rid}")
        results.append(f"\t* {r2} : {rid}")
        results.append("=========================================================")
        results.append("+ Solusi :")
        results.append("\t* Router ID pada OSPF :")
        for r_all, rid_all in sorted(router_rid.items()):
            pointer = " <-" if r_all in routers_sorted else ""
            results.append(f"\t\t- {r_all} : {rid_all}{pointer}")

        results.append("\n\t* Lakukan perubahan Router ID agar setiap router memiliki ID yang unik.")
        results.extend(format_footer())


# ----------------------------------------------------------
# 6. PROSES SETIAP TOPOLOGI (CSV) — DEDUP PAIR
# ----------------------------------------------------------
def process_topology_csv(fpath: str, fname: str):
    df = pd.read_csv(fpath)
    results = []

    seen = set()

    for _, row in df.iterrows():
        r1, r2 = str(row["router_a"]), str(row["router_b"])
        pair_sorted = tuple(sorted([r1, r2]))

        if bool(row.get("HelloMismatch", False)):
            key = ("Hello", pair_sorted)
            if key not in seen:
                seen.add(key)
                handle_interval_mismatch(results, row, "Hello", row["hello_a"], row["hello_b"])

        if bool(row.get("DeadMismatch", False)):
            key = ("Dead", pair_sorted)
            if key not in seen:
                seen.add(key)
                handle_interval_mismatch(results, row, "Dead", row["dead_a"], row["dead_b"])

        if bool(row.get("AreaMismatch", False)):
            key = ("Area", pair_sorted)
            if key not in seen:
                seen.add(key)
                handle_simple_pair_mismatch(results, row, "Area", row["area_a"], row["area_b"])

        if bool(row.get("MTUMismatch", False)):
            key = ("MTU", pair_sorted)
            if key not in seen:
                seen.add(key)
                handle_simple_pair_mismatch(results, row, "MTU", row["MTU_a"], row["MTU_b"])

        if bool(row.get("NetworkTypeMismatch", False)):
            key = ("NetworkType", pair_sorted)
            if key not in seen:
                seen.add(key)
                handle_simple_pair_mismatch(
                    results, row, "Network Type", row["network_type_a"], row["network_type_b"]
                )

        if bool(row.get("PassiveMismatch", False)):
            key = ("Passive", pair_sorted)
            if key not in seen:
                seen.add(key)
                handle_passive_mismatch(results, row)

        if bool(row.get("AuthMismatch", False)):
            key = ("Auth", pair_sorted)
            if key not in seen:
                seen.add(key)
                handle_auth_mismatch(results, row)

        if bool(row.get("AuthKeyMismatch", False)):
            auth_a = norm(row.get("ospf_auth_a", ""))
            auth_b = norm(row.get("ospf_auth_b", ""))
            keys_a = parse_auth_keys(row.get("auth_key_a", ""))
            keys_b = parse_auth_keys(row.get("auth_key_b", ""))

            key = ("AuthKey", pair_sorted)
            if key in seen:
                continue
            seen.add(key)

            if "message-digest" in auth_a and "message-digest" in auth_b:
                handle_authkey_md5_vs_md5(results, row, keys_a, keys_b)
            elif "message-digest" in auth_a and auth_b in ("simple", "none"):
                handle_authkey_md5_vs_simple(results, row, keys_a, side_md5_is_a=True)
            elif "message-digest" in auth_b and auth_a in ("simple", "none"):
                handle_authkey_md5_vs_simple(results, row, keys_b, side_md5_is_a=False)
            elif auth_a == "simple" and auth_b == "simple":
                handle_authkey_simple_vs_simple(results, row, keys_a, keys_b)
            else:
                handle_simple_pair_mismatch(
                    results, row, "auth_key",
                    row.get("auth_key_a", ""), row.get("auth_key_b", "")
                )

    handle_redistribute_mismatch(results, df)
    handle_routerid_mismatch(results, df)

    if not results:
        results.append("[✓] Tidak ditemukan mismatch pada topologi ini.\n")

    topo_num = "".join(ch for ch in fname if ch.isdigit()) or "X"
    out_path = os.path.join(OUTPUT_DIR, f"hasil_deteksi_{topo_num}.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(results))

    print(f"[✓] Deteksi rule-based TXT selesai: {fname} → {out_path}")


# ----------------------------------------------------------
# MAIN
# ----------------------------------------------------------
def main():
    csv_files = sorted([f for f in os.listdir(INPUT_DIR) if f.endswith(".csv")])
    if not csv_files:
        print(f"[!] Tidak ada file CSV di {INPUT_DIR}")
        return

    for fname in csv_files:
        fpath = os.path.join(INPUT_DIR, fname)
        process_topology_csv(fpath, fname)

    print("[✔] Semua topologi selesai diproses.")

    # -------------------------------------------
    #  AUTO COPY KE FOLDER DOWNLOADS WINDOWS
    # -------------------------------------------
    USER = os.getlogin()
    TARGET_DIR = fr"C:\Users\{USER}\Downloads\Laporan_Rule_Based"

    # Buat folder jika belum ada
    os.makedirs(TARGET_DIR, exist_ok=True)

    # Copy semua txt dari OUTPUT_DIR → TARGET_DIR
    for file in os.listdir(OUTPUT_DIR):
        if file.endswith(".txt"):
            shutil.copy(
                os.path.join(OUTPUT_DIR, file),
                os.path.join(TARGET_DIR, file)
            )

    print(f"[✓] Semua laporan berhasil disalin ke folder:")
    print(f"    {TARGET_DIR}")


if __name__ == "__main__":
    main()