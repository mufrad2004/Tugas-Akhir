import os
import sys
import subprocess

# 02-0_Dataset
RUN_AMBIL_RAWDATA           = True   # 1_Ambil_RawData.py
RUN_PEMBUATAN_JSON          = True   # 2_Pembuatan_JSON.py
RUN_CONVERT_JSON_TO_CSV     = True   # 3_Convert JSON to CSV.py
RUN_CLEANING_DATASET        = True   # 4_Cleaning_Dataset.py

# 02-1_Scripts (Rule Based)
RUN_RULE_BASED_DETECTION    = True   # 1_Rule_Based.py
RUN_BUAT_LAPORAN_TXT        = True   # 3_Buat_Laporan.py
RUN_DOWNLOAD_LAPORAN        = True   # 4_Download_Laporan.py



ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def run_script(label: str, rel_path: str, enabled: bool = True, stop_on_error: bool = True):
    if not enabled:
        print(f"[SKIP] {label}")
        return

    script_path = os.path.join(ROOT_DIR, rel_path)

    if not os.path.isfile(script_path):
        print(f"[ERROR] File tidak ditemukan: {script_path}")
        if stop_on_error:
            sys.exit(1)
        return

    print("\n===================================================")
    print(f"[RUNNING] {label}")
    print(f"  -> {script_path}")
    print("===================================================\n")

    result = subprocess.run([sys.executable, script_path])

    if result.returncode != 0:
        print(f"\n[ERROR] {label} gagal (exit code {result.returncode})")
        if stop_on_error:
            sys.exit(result.returncode)
    else:
        print(f"[OK] {label} selesai.\n")


def main():
    run_script(
        "Dataset - 1_Ambil_RawData",
        os.path.join("02-0_Dataset", "1_Ambil_RawData.py"),
        enabled=RUN_AMBIL_RAWDATA,
    )

    run_script(
        "Dataset - 2_Pembuatan_JSON",
        os.path.join("02-0_Dataset", "2_Pembuatan_JSON.py"),
        enabled=RUN_PEMBUATAN_JSON,
    )

    run_script(
        "Dataset - 3_Convert JSON to CSV",
        os.path.join("02-0_Dataset", "3_Convert JSON to CSV.py"),
        enabled=RUN_CONVERT_JSON_TO_CSV,
    )

    run_script(
        "Dataset - 4_Cleaning_Dataset",
        os.path.join("02-0_Dataset", "4_Cleaning_Dataset.py"),
        enabled=RUN_CLEANING_DATASET,
    )

    run_script(
        "Rule Based - 1_Rule_Based",
        os.path.join("02-1_Scripts (Rule Based)", "1_Rule_Based.py"),
        enabled=RUN_RULE_BASED_DETECTION,
    )

    run_script(
        "Rule Based - 3_Buat_Laporan",
        os.path.join("02-1_Scripts (Rule Based)", "3_Buat_Laporan.py"),
        enabled=RUN_BUAT_LAPORAN_TXT,
    )

    run_script(
        "Rule Based - 4_Download_Laporan",
        os.path.join("02-1_Scripts (Rule Based)", "4_Download_Laporan.py"),
        enabled=RUN_DOWNLOAD_LAPORAN,
    )

    print("===================================================")
    print("[✓] Semua tahap yang di-enable sudah selesai dijalankan.")
    print("===================================================\n")


if __name__ == "__main__":
    main()
