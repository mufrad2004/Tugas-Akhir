import os
import json
import csv

# === Path utama === #
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
input_dir = os.path.join(ROOT_DIR, "03_Output", "Data_JSON")
output_dir = os.path.join(ROOT_DIR, "03_Output", "Data_CSV")

os.makedirs(output_dir, exist_ok=True)



def safe_get(d, keys, default=None):
    """Ambil nested key dari dict."""
    for k in keys:
        if isinstance(d, dict) and k in d:
            d = d[k]
        else:
            return default
    return d

def format_auth_key(auth_dict):
    """
    buat  auth_key jadi kayak :
    - {"simple": "cisco123"} -> "simple:cisco123"
    - {"1": "cisco123", "2": "cisco456"} -> "1:cisco123,2:cisco456"
    """
    if not isinstance(auth_dict, dict) or len(auth_dict) == 0:
        return "none"
    parts = []
    for k, v in auth_dict.items():
        parts.append(f"{k}:{v}")
    return ",".join(parts)

def normalize_routing_protocols(protocol_list):
    """
    Rapihin protokol routing :
    - Kalau router hanya punya 1 protokol ->'ospf' atau 'eigrp' saja.
    - Kalau router punya OSPF dan EIGRP urutannya  'ospf,eigrp'.
    - Protokol lain akan diurutkan alfabet.
    """
    if not isinstance(protocol_list, list):
        return ""

    tokens = [str(p).strip().lower() for p in protocol_list if str(p).strip()]
    unique = list(dict.fromkeys(tokens))  # hapus duplikat

    # Jika hanya ospf
    if unique == ["ospf"]:
        return "ospf"

    # Jika hanya eigrp
    if unique == ["eigrp"]:
        return "eigrp"

    # Jika punya ospf dan eigrp (urutan bebas di JSON), paksa jadi 'ospf,eigrp'
    has_ospf = "ospf" in unique
    has_eigrp = "eigrp" in unique
    if has_ospf and has_eigrp and len(unique) == 2:
        return "ospf,eigrp"

    # Kasus lain (kalau nanti ada protokol tambahan): irutin pake alpabet
    return ",".join(sorted(unique))

# === Proses semua file JSON === #
for fname in sorted(os.listdir(input_dir)):
    if not fname.endswith(".json"):
        continue

    fpath = os.path.join(input_dir, fname)
    with open(fpath, "r") as f:
        routers = json.load(f)

    print(f"[✓] Membaca {fname} ({len(routers)} router ditemukan)")

    dataset = []
    topology_id = fname.split("_")[-1].replace(".json", "")  # topologi_1.json → 1

    for r1_name, r1_data in routers.items():
        # === Data router A === #
        router1_protocols = normalize_routing_protocols(
            r1_data.get("routing", {}).get("protocol", [])
        )
        router1_id = r1_data.get("router_id", "none")
        redis1 = r1_data.get("routing", {}).get("redistribute", False)

        for if1_name, if1_data in r1_data.get("interfaces", {}).items():
            if "neighbor" not in if1_data:
                continue

            nbr_router = safe_get(if1_data, ["neighbor", "router"])
            nbr_intf = safe_get(if1_data, ["neighbor", "interface"])
            if nbr_router not in routers:
                continue
            r2_data = routers[nbr_router]

            # === Data router B === #
            router2_protocols = normalize_routing_protocols(
                r2_data.get("routing", {}).get("protocol", [])
            )
            router2_id = r2_data.get("router_id", "none")
            redis2 = r2_data.get("routing", {}).get("redistribute", False)

            # Data interface di router B
            intf2 = r2_data["interfaces"].get(nbr_intf.replace(" ", ""), {})
            ospf1 = if1_data.get("ospf", {})
            ospf2 = intf2.get("ospf", {})

            # === Format auth_key dan auth_type === #
            auth_key_a = format_auth_key(ospf1.get("auth_key", {}))
            auth_key_b = format_auth_key(ospf2.get("auth_key", {}))
            auth_type_a = ospf1.get("ospf auth", "none")
            auth_type_b = ospf2.get("ospf auth", "none")

            # === Buat baris dataset === #
            row = {
                "topologi": topology_id,

                "router_a": r1_name,
                "routing_a": router1_protocols,
                "router_id_a": router1_id,
                "redistribute_a": redis1,
                "interface_a": if1_name,
                "ip_a": if1_data.get("ip", "none"),
                "subnet_a": if1_data.get("subnet", "none"),
                "auth_key_a": auth_key_a,
                "ospf_auth_a": auth_type_a,
                "area_a": ospf1.get("area", "none"),
                "network_type_a": ospf1.get("Network Type", "none"),
                "hello_a": ospf1.get("Hello", "none"),
                "dead_a": ospf1.get("Dead", "none"),
                "passive_a": ospf1.get("passive", "none"),
                "MTU_a": if1_data.get("MTU", "none"),
                "neighbor_a": nbr_router,

                "router_b": nbr_router,
                "routing_b": router2_protocols,
                "router_id_b": router2_id,
                "redistribute_b": redis2,
                "interface_b": nbr_intf,
                "ip_b": intf2.get("ip", "none"),
                "subnet_b": intf2.get("subnet", "none"),
                "auth_key_b": auth_key_b,
                "ospf_auth_b": auth_type_b,
                "area_b": ospf2.get("area", "none"),
                "network_type_b": ospf2.get("Network Type", "none"),
                "hello_b": ospf2.get("Hello", "none"),
                "dead_b": ospf2.get("Dead", "none"),
                "passive_b": ospf2.get("passive", "none"),
                "MTU_b": intf2.get("MTU", "none"),
                "neighbor_b": safe_get(intf2, ["neighbor", "router"], "none")
            }

            dataset.append(row)

    if len(dataset) == 0:
        print(f"[!] Tidak ada pasangan router valid di {fname}")
        continue

    out_csv = os.path.join(
        output_dir,
        fname.replace("routers_", "dataset_").replace(".json", ".csv")
    )
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(dataset[0].keys()))
        writer.writeheader()
        writer.writerows(dataset)

    print(f"[✓] Dataset dari {fname} disimpan ke {out_csv} ({len(dataset)} baris)\n")

print(f"[✔] Semua file JSON telah diproses. Hasil tersimpan di folder: {output_dir}")
