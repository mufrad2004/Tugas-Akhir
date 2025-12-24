import os
import re
import json

# === Direktori input/output === #
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
base_dir = os.path.join(ROOT_DIR, "03_Output", "rawdata")

config_dir = os.path.join(base_dir, "config")
interfaces_dir = os.path.join(base_dir, "interfaces")
ospf_dir = os.path.join(base_dir, "ospf")
ospf_config_dir = os.path.join(base_dir, "ospf_config")
cdp_dir = os.path.join(base_dir, "cdp")
proto_dir = os.path.join(base_dir, "ip protocols")

# === Folder output  === #
data_json_dir = os.path.join(ROOT_DIR, "03_Output", "Data_JSON")
os.makedirs(data_json_dir, exist_ok=True)

# === Ubah nama file output manual sesuai topologi === #
output_file = os.path.join(data_json_dir, "topologi_101.json") #! <-------------- ubah nama file topologinya disini


# === Parser helper === #
def parse_config_interface(config_output):
    """Parse 'show run | section interface' → ambil IP & OSPF auth key"""
    interfaces = {}
    current_intf = None

    for raw_line in config_output.splitlines():
        line = raw_line.strip()

        if line.startswith("interface"):
            current_intf = line.split()[1]
            interfaces[current_intf] = {}

        elif current_intf:
            if line.startswith("ip address"):
                parts = line.split()
                if len(parts) >= 4:
                    interfaces[current_intf]["ip"] = parts[2]
                    interfaces[current_intf]["subnet"] = parts[3]

            if line.startswith("ip ospf authentication-key"):
                key = line.split()[-1]
                if "ospf" not in interfaces[current_intf]:
                    interfaces[current_intf]["ospf"] = {"auth_key": {}}
                interfaces[current_intf]["ospf"]["auth_key"] = {"simple": key}

            elif line.startswith("ip ospf message-digest-key"):
                parts = line.split()
                if len(parts) >= 5:
                    key_id = parts[3]
                    key_val = parts[-1]
                    if "ospf" not in interfaces[current_intf]:
                        interfaces[current_intf]["ospf"] = {"auth_key": {}}
                    interfaces[current_intf]["ospf"]["auth_key"][key_id] = key_val

            elif line.startswith("ip ospf authentication") and "authentication-key" not in line:
                if "ospf" not in interfaces[current_intf]:
                    interfaces[current_intf]["ospf"] = {}
                if "auth_key" not in interfaces[current_intf]["ospf"]:
                    interfaces[current_intf]["ospf"]["auth_key"] = {}

    for intf, data in interfaces.items():
        if "ospf" in data and "auth_key" not in data["ospf"]:
            data["ospf"]["auth_key"] = {}

    return interfaces


def parse_show_interfaces(interfaces_output):
    """Parse 'show interfaces' → ambil MTU"""
    mtu_data = {}
    current_intf = None

    for line in interfaces_output.splitlines():
        if re.match(r"^(FastEthernet|GigabitEthernet|Loopback)", line):
            current_intf = line.split()[0]
        elif "MTU" in line and current_intf:
            match = re.search(r"MTU (\d+) bytes", line)
            if match:
                mtu_data[current_intf] = int(match.group(1))
    return mtu_data


def parse_show_ip_ospf_interface(ospf_output):
    """Parse 'show ip ospf interface' → area, hello/dead, net type, ospf auth"""
    ospf_data = {}
    current_intf = None

    for line in ospf_output.splitlines():
        if re.match(r"^(FastEthernet|GigabitEthernet|Loopback)", line):
            parts = line.split()
            current_intf = parts[0]
            ospf_data[current_intf] = {}
            ospf_data[current_intf]["ospf auth"] = "none"

        if current_intf:
            if "Internet Address" in line and "Area" in line:
                area = re.search(r"Area (\d+)", line).group(1)
                ospf_data[current_intf]["area"] = int(area)

            if "Timer intervals" in line:
                hello = re.search(r"Hello (\d+)", line).group(1)
                dead = re.search(r"Dead (\d+)", line).group(1)
                ospf_data[current_intf]["Hello"] = int(hello)
                ospf_data[current_intf]["Dead"] = int(dead)

            if "Network Type" in line:
                net_type = re.search(r"Network Type (\S+)", line).group(1)
                ospf_data[current_intf]["Network Type"] = net_type.rstrip(",").capitalize()

            if "Simple password authentication enabled" in line:
                ospf_data[current_intf]["ospf auth"] = "simple"
            elif "Message digest authentication enabled" in line:
                ospf_data[current_intf]["ospf auth"] = "message-digest"

    return ospf_data


def parse_show_run_ospf_config(ospf_config_output):
    """Parse 'show run | section router ospf' → router-id, redistribute, passive"""
    router_id = None
    redistribute = False
    passive = []

    for line in ospf_config_output.splitlines():
        line = line.strip()
        if "router-id" in line:
            router_id = line.split()[1]
        if line.startswith("redistribute eigrp"):
            if "subnets" in line:
                redistribute = True
            else:
                redistribute = False
        if "passive-interface" in line:
            intf = line.split()[1]
            passive.append(intf)

    return router_id, redistribute, passive


def parse_show_cdp_neighbor(cdp_output):
    """Parse 'show cdp neighbor' → neighbor mapping"""
    neighbors = {}
    for line in cdp_output.splitlines():
        if re.match(r"^\S+\.cisco", line):
            parts = line.split()
            device_id = parts[0].split(".")[0]  # contoh: R9.cisco -> R9
            local_intf = parts[1] + parts[2]    # contoh: Fas 2/0
            port_id = parts[-2] + " " + parts[-1]  # contoh: Fas 0/1

            # Normalisasi nama
            if local_intf.startswith("Fas"):
                local_intf = local_intf.replace("Fas", "FastEthernet")
            if port_id.startswith("Fas"):
                port_id = port_id.replace("Fas", "FastEthernet")

            neighbors[local_intf] = {
                "router": device_id,
                "interface": port_id
            }
    return neighbors


def parse_show_ip_protocols(proto_output):
    """Parse 'show ip protocols' → routing protocols, redistribute, router-id"""
    protocols = []
    redistribute = False
    router_id = None

    for line in proto_output.splitlines():
        line = line.strip()

        if line.startswith("Routing Protocol is"):
            if "ospf" in line and "ospf" not in protocols:
                protocols.append("ospf")
            if "eigrp" in line and "eigrp" not in protocols:
                protocols.append("eigrp")

        if line.startswith("eigrp") and "subnets" in line : 
            redistribute = True
        else : 
            redistribute = False
            
        # if line.startswith("Redistributing"):
        #     if "subnets" in line:
        #         redistribute = True
        #     else:
        #         redistribute = False

        if "Router ID" in line:
            parts = line.split()
            router_id = parts[-1]

    return protocols, redistribute, router_id


# === Main Processing === #
def main():
    results = {}
    
    for i in range(1, 13):
        router = f"R{i}"
        try:
            with open(os.path.join(config_dir, f"{router}_show_run__section_interface.txt")) as f:
                config_output = f.read()

            with open(os.path.join(interfaces_dir, f"{router}_show_interfaces.txt")) as f:
                interfaces_output = f.read()

            with open(os.path.join(ospf_dir, f"{router}_show_ip_ospf_interface.txt")) as f:
                ospf_output = f.read()

            with open(os.path.join(ospf_config_dir, f"{router}_show_run__section_router_ospf.txt")) as f:
                ospf_config_output = f.read()

            with open(os.path.join(cdp_dir, f"{router}_show_cdp_neighbor.txt")) as f:
                cdp_output = f.read()

            with open(os.path.join(proto_dir, f"{router}_show_ip_protocols.txt")) as f:
                proto_output = f.read()

            # === Parsing === #
            interfaces = parse_config_interface(config_output)
            mtu_data = parse_show_interfaces(interfaces_output)
            ospf_data = parse_show_ip_ospf_interface(ospf_output)
            router_id_conf, redistribute_conf, passive = parse_show_run_ospf_config(ospf_config_output)
            cdp_data = parse_show_cdp_neighbor(cdp_output)
            protocols, redistribute_proto, router_id_proto = parse_show_ip_protocols(proto_output)

            # === Gabungkan data per interface === #
            for intf, data in interfaces.items():
                if intf in mtu_data:
                    data["MTU"] = mtu_data[intf]
                if intf in ospf_data:
                    if "ospf" not in data:
                        data["ospf"] = {}
                    data["ospf"].update(ospf_data[intf])
                if intf in passive:
                    if "ospf" not in data:
                        data["ospf"] = {}
                    data["ospf"]["passive"] = True
                elif "ospf" in data:
                    data["ospf"]["passive"] = False
                if intf in cdp_data:
                    data["neighbor"] = cdp_data[intf]

            # hanya interface yg punya IP
            interfaces_clean = {k: v for k, v in interfaces.items() if "ip" in v}

            # pilih router-id
            router_id = router_id_conf or router_id_proto

            # pilih redistribute 
            redistribute = redistribute_conf or redistribute_proto

            results[router] = {
                "router_id": router_id,
                "interfaces": interfaces_clean,
                "routing": {
                    "protocol": protocols,
                    "redistribute": redistribute
                }
            }

        except FileNotFoundError:
            print(f"[!] File untuk {router} tidak lengkap, skip...")
            continue

    with open(output_file, "w") as f:
        json.dump(results, f, indent=4)

    print(f"[✓] Data berhasil digabung ke {output_file}")


if __name__ == "__main__":
    main()
