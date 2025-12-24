from netmiko import ConnectHandler
import concurrent.futures
import json
import os

router_admin = {
    "device_type": "cisco_ios",
    "host": "192.168.6.100",
    "username": "cisco",
    "password": "cisco",
}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

router_list_path = os.path.join(BASE_DIR, "01_IP_Management", "router_list.json")
with open(router_list_path) as f:
    router_list = json.load(f)

roles_path = os.path.join(BASE_DIR,"01_IP_Management", "router_roles.json")
with open(roles_path) as f:
    roles = json.load(f)

ROLES = roles["ROLES"]

def nested_ssh(conn, target_ip: str, username="cisco", password="cisco"):
    out = conn.send_command_timing(f"ssh -l {username} {target_ip}")
    if "Password" in out:
        out = conn.send_command_timing(password)
    return out

def is_mgmt_ip(ip: str) -> bool:
    return ip.startswith("100.100.100.")

def parse_show_ip_int_br(output: str):
    interfaces = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 6:
            continue
        name, ip, status, proto = parts[0], parts[1], parts[-2], parts[-1]
        if ip != "unassigned" and status == "up" and proto == "up":
            if not is_mgmt_ip(ip):
                interfaces.append((name, ip))
    return interfaces

def generate_config(router_name: str, interfaces):
    ospf_config, eigrp_config, ospf_interfaces = [], [], []

    loopbacks = [ip for name, ip in interfaces if name.lower().startswith("loopback")]
    router_id = loopbacks[0] if loopbacks else router_list[router_name]

    role = ROLES.get(router_name, {})
    ospf_area = role.get("ospf_area")
    eigrp_only = role.get("eigrp_only", False)
    extra = role.get("extra", {})

    for intf, ip in interfaces:
        if intf in extra:
            val = extra[intf]
            if isinstance(val, int):
                ospf_config.append(f" network {ip} 0.0.0.0 area {val}")
                ospf_interfaces.append(intf)
            elif isinstance(val, str) and val.upper() == "EIGRP":
                eigrp_config.append(f" network {ip} 0.0.0.0")
        else:
            if eigrp_only:
                eigrp_config.append(f" network {ip} 0.0.0.0")
            elif ospf_area is not None:
                ospf_config.append(f" network {ip} 0.0.0.0 area {ospf_area}")
                ospf_interfaces.append(intf)

    if any(isinstance(v, str) and v.upper() == "EIGRP" for v in extra.values()):
        ospf_config.append(" redistribute eigrp 1 subnets")
        eigrp_config.append(" redistribute ospf 1 metric 1 1 1 1 1")

    config_lines = []
    if ospf_config:
        config_lines.append("router ospf 1")
        config_lines.append(f" router-id {router_id}")
        config_lines.extend(ospf_config)

        for intf in ospf_interfaces:
            if intf.lower().startswith("loopback"):
                continue
            val = extra.get(intf, None)
            if isinstance(val, str) and val.upper() == "EIGRP":
                continue

            config_lines.append(f"interface {intf}")
            config_lines.append(" ip ospf authentication")
            config_lines.append(" ip ospf authentication-key cisco123")
            config_lines.append(" ip ospf network point-to-point")

    if eigrp_config:
        config_lines.append("router eigrp 1")
        config_lines.append(" no auto-summary")
        config_lines.extend(eigrp_config)

    return config_lines

def push_config(router_name: str, target_ip: str):
    conn = None
    try:
        print(f"[+] SSH ke {router_name} ({target_ip})")
        conn = ConnectHandler(**router_admin)

        nested_ssh(conn, target_ip)
        conn.send_command_timing("terminal length 0")
        output = conn.send_command_timing("show ip int br")
        interfaces = parse_show_ip_int_br(output)

        cfg = generate_config(router_name, interfaces)

        conn.send_command_timing("conf t")
        for cmd in cfg:
            conn.send_command_timing(cmd)

        conn.send_command_timing("end")
        conn.send_command_timing("wr")
        conn.send_command_timing("exit")

        print(f"[✓] Selesai: {router_name}")

    except Exception as e:
        print(f"[!] Gagal {router_name}: {e}")

    finally:
        if conn:
            conn.disconnect()

if __name__ == "__main__":
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(push_config, rname, ip) for rname, ip in router_list.items()]
        concurrent.futures.wait(futures)
