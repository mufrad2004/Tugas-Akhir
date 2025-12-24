from netmiko import ConnectHandler
import os
import json
import concurrent.futures

router_admin = {
    "device_type": "cisco_ios",
    "host": "192.168.6.100",
    "username": "cisco",
    "password": "cisco",
}

script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, ".."))
base_dir = os.path.join(project_root, "03_Output", "rawdata")

commands = {
    "show interfaces": "interfaces",
    "show ip ospf interface": "ospf",
    "show ip protocols": "protocols",
    "show run | section interface": "config",
    "show run | section router ospf": "ospf_config",
}

for folder in set(commands.values()):
    os.makedirs(os.path.join(base_dir, folder), exist_ok=True)

path = os.path.join(project_root, "01_IP_Management", "router_list.json")
with open(path) as f:
    router_list = json.load(f)

def nested_ssh(conn, target_ip: str, username="cisco", password="cisco"):
    out = conn.send_command_timing(f"ssh -l {username} {target_ip}")
    if "Password" in out:
        out = conn.send_command_timing(password)
    return out

def ambil_data(router_name: str, mgmt_ip: str):
    conn = None
    try:
        print(f"[+] SSH ke {router_name} ({mgmt_ip})")
        conn = ConnectHandler(**router_admin)

        nested_ssh(conn, mgmt_ip)
        conn.send_command_timing("terminal length 0")

        for cmd, folder in commands.items():
            result = conn.send_command(cmd, expect_string=r"#")
            if result and result.strip():
                filename = f"{router_name}_{cmd.replace(' ', '_').replace('|', '').replace('/', '')}.txt"
                path_out = os.path.join(base_dir, folder, filename)
                with open(path_out, "w") as f:
                    f.write(result)

        conn.send_command_timing("exit")
        print(f"[✓] Selesai: {router_name} ")

    except Exception as e:
        print(f"[!] Error {router_name}: {e}")

    finally:
        if conn:
            conn.disconnect()

if __name__ == "__main__":
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(ambil_data, rname, ip) for rname, ip in router_list.items()]
        concurrent.futures.wait(futures)
