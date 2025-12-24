from netmiko import ConnectHandler
import concurrent.futures
import json
import os

router_admin = {
    "device_type": "cisco_ios",
    "ip": "192.168.6.100",   
    "username": "cisco",
    "password": "cisco",
}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
json_path = os.path.join(BASE_DIR, "01_IP_Management", "router_list.json")

with open(json_path) as f:
    router_list = json.load(f)

# Mapping IP router -> list perintah konfigurasi
router_configs = {
    router_list["R1"]: [
        "hostname R1",
        "cdp run",
        "no cdp log mismatch duplex",
        "int fa0/0",
        "no cdp enable",
        "int lo0",
        "ip add 1.1.1.1 255.255.255.255",
        "int fa0/1",
        "no shut",
        "ip add 192.168.1.5 255.255.255.252",
        "int fa1/0",
        "no switchport ",
        "no shut",
        "ip add 192.168.1.1 255.255.255.252",
        "int fa2/0",
        "no switchport ",
        "no shut",
        "ip add 192.168.1.33 255.255.255.252",
    ],
    router_list["R2"]: [
        "hostname R2",
        "cdp run",
        "no cdp log mismatch duplex",
        "int fa0/0",
        "no cdp enable",
        "int lo0",
        "ip add 2.2.2.2 255.255.255.255",
        "int fa0/1",
        "no shut",
        "ip add 192.168.1.6 255.255.255.252",
        "int fa1/0",
        "no switchport ",
        "no shut",
        "ip add 192.168.1.9 255.255.255.252",
        "int fa1/1",
        "no switchport ",
        "no shut",
        "ip add 192.168.1.17 255.255.255.252",
        "int fa1/2",
        "no switchport ",
        "no shut",
        "ip add 192.168.1.45 255.255.255.252",
    ],
    router_list["R3"]: [
        "hostname R3",
        "cdp run",
        "no cdp log mismatch duplex",
        "int fa0/0",
        "no cdp enable",
        "int lo0",
        "ip add 3.3.3.3 255.255.255.255",
        "int fa0/1",
        "no shut",
        "ip add 192.168.1.2 255.255.255.252",
        "int fa1/0",
        "no switchport ",
        "no shut",
        "ip add 192.168.1.10 255.255.255.252",
        "int fa1/1",
        "no switchport ",
        "no shut",
        "ip add 192.168.1.13 255.255.255.252",
        "int fa1/2",
        "no switchport ",
        "no shut",
        "ip add 192.168.1.41 255.255.255.252",
    ],
    router_list["R4"]: [
        "hostname R4",
        "cdp run",
        "no cdp log mismatch duplex",
        "int fa0/0",
        "no cdp enable",
        "int lo0",
        "ip add 4.4.4.4 255.255.255.255",
        "int fa1/0",
        "no switchport ",
        "no shut",
        "ip add 192.168.1.14 255.255.255.252",
        "int fa0/1",
        "no shut",
        "ip add 192.168.1.18 255.255.255.252",
        "int fa2/0",
        "no switchport ",
        "no shut",
        "ip add 192.168.1.21 255.255.255.252",
    ],
    router_list["R5"]: [
        "hostname R5",
        "cdp run",
        "no cdp log mismatch duplex",
        "int fa0/0",
        "no cdp enable",
        "int lo0",
        "ip add 5.5.5.5 255.255.255.255",
        "int fa0/1",
        "no shut",
        "ip add 192.168.1.22 255.255.255.252",
        "int fa1/0",
        "no switchport ",
        "no shut",
        "ip add 192.168.1.25 255.255.255.252",
        "int fa2/0",
        "no switchport ",
        "no shut",
        "ip add 192.168.1.29 255.255.255.252",
    ],
    router_list["R6"]: [
        "hostname R6",
        "cdp run",
        "no cdp log mismatch duplex",
        "int fa0/0",
        "no cdp enable",
        "int lo0",
        "ip add 6.6.6.6 255.255.255.255",
        "int fa0/1",
        "no shut",
        "ip add 192.168.1.26 255.255.255.252",
    ],
    router_list["R7"]: [
        "hostname R7",
        "cdp run",
        "no cdp log mismatch duplex",
        "int fa0/0",
        "no cdp enable",
        "int lo0",
        "ip add 7.7.7.7 255.255.255.255",
        "int fa0/1",
        "no shut",
        "ip add 192.168.1.30 255.255.255.252",
        "int fa1/0",
        "no switchport ",
        "no shut",
        "ip add 192.168.1.49 255.255.255.252",
    ],
    router_list["R8"]: [
        "hostname R8",
        "cdp run",
        "no cdp log mismatch duplex",
        "int fa0/0",
        "no cdp enable",
        "int lo0",
        "ip add 8.8.8.8 255.255.255.255",
        "int fa0/1",
        "no shut",
        "ip add 192.168.1.50 255.255.255.252",
    ],
    router_list["R9"]: [
        "hostname R9",
        "cdp run",
        "no cdp log mismatch duplex",
        "int fa0/0",
        "no cdp enable",
        "int lo0",
        "ip add 9.9.9.9 255.255.255.255",
        "int fa0/1",
        "no shut",
        "ip add 192.168.1.34 255.255.255.252",
        "int fa1/0",
        "no switchport ",
        "no shut",
        "ip add 192.168.1.37 255.255.255.252",
    ],
    router_list["R10"]: [
        "hostname R10",
        "cdp run",
        "no cdp log mismatch duplex",
        "int fa0/0",
        "no cdp enable",
        "int lo0",
        "ip add 10.10.10.10 255.255.255.255",
        "int fa0/1",
        "no shut",
        "ip add 192.168.1.38 255.255.255.252",
    ],
    router_list["R11"]: [
        "hostname R11",
        "cdp run",
        "no cdp log mismatch duplex",
        "int fa0/0",
        "no cdp enable",
        "int lo0",
        "ip add 11.11.11.11 255.255.255.255",
        "int fa0/1",
        "no shut",
        "ip add 192.168.1.46 255.255.255.252",
    ],
    router_list["R12"]: [
        "hostname R12",
        "cdp run",
        "no cdp log mismatch duplex",
        "int fa0/0",
        "no cdp enable",
        "int lo0",
        "ip add 12.12.12.12 255.255.255.255",
        "int fa0/1",
        "no shut",
        "ip add 192.168.1.42 255.255.255.252",
    ],
}


def configure_router(name, ip, commands):
    conn = None
    try:
        print(f"[+] SSH ke Admin → {name} ({ip})")
        conn = ConnectHandler(**router_admin)
        conn.find_prompt()

        # Nested SSH ke router target
        ssh_cmd = f"ssh -l cisco {ip}"
        out = conn.send_command_timing(ssh_cmd)
        if "Password" in out:
            conn.send_command_timing("cisco")

        # Masuk konfigurasi
        conn.send_command_timing("conf t")

        # Konfig 
        for cmd in commands:
            conn.send_command_timing(cmd)

        # Keluar ama simpan konpik
        conn.send_command_timing("end")
        conn.send_command_timing("wr")
        conn.send_command_timing("exit")

        print(f"[✓] Selesai: {name}")

    except Exception as e:
        print(f"[!] Error pada {name}: {e}")

    finally:
        if conn:
            conn.disconnect()


if __name__ == "__main__":
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(configure_router, rname, ip, router_configs[ip])
            for rname, ip in router_list.items()
            if ip in router_configs
        ]
        concurrent.futures.wait(futures)
