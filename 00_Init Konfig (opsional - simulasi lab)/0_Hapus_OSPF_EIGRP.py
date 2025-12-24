from netmiko import ConnectHandler
import concurrent.futures
import json
import os
import re

router_admin = {
    "device_type": "cisco_ios",
    "host": "192.168.6.100",
    "username": "cisco",
    "password": "cisco",
}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
json_path = os.path.join(BASE_DIR, "01_IP_Management", "router_list.json")

with open(json_path) as f:
    router_list = json.load(f)

def nested_ssh(conn, target_ip: str, username="cisco", password="cisco"):
    out = conn.send_command_timing(f"ssh -l {username} {target_ip}")
    if "Password" in out:
        out = conn.send_command_timing(password)
    return out

def clear_config(router_name: str, target_ip: str):
    conn = None
    try:
        print(f"[+] SSH ke {router_name} ({target_ip})")
        conn = ConnectHandler(**router_admin)

        nested_ssh(conn, target_ip)
        conn.send_command_timing("terminal length 0")

        # hapus routing process
        conn.send_command_timing("conf t")
        conn.send_command_timing("no router ospf 1")
        conn.send_command_timing("no router eigrp 1")
        conn.send_command_timing("end")

        # ambil daftar interface
        output = conn.send_command_timing("show run | s interface")
        interfaces = re.findall(r"^interface (\\S+)", output, re.M)

        # bersiin OSPF di interface
        conn.send_command_timing("conf t")
        for intf in interfaces:
            conn.send_command_timing(f"interface {intf}")
            conn.send_command_timing("no ip ospf authentication")
            conn.send_command_timing("no ip ospf authentication-key")
            conn.send_command_timing("no ip ospf message-digest-key 1 md5")
            conn.send_command_timing("no ip ospf message-digest-key 2 md5")
            conn.send_command_timing("no ip ospf message-digest-key 3 md5")
            conn.send_command_timing("no mtu")
            conn.send_command_timing("no ip ospf network")

            conn.send_command_timing("exit")

        conn.send_command_timing("end")
        conn.send_command_timing("wr")
        conn.send_command_timing("exit")

        print(f"[✓] Clear selesai: {router_name}")

    except Exception as e:
        print(f"[!] Gagal {router_name}: {e}")

    finally:
        if conn:
            conn.disconnect()

if __name__ == "__main__":
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(clear_config, rname, ip) for rname, ip in router_list.items()]
        concurrent.futures.wait(futures)
