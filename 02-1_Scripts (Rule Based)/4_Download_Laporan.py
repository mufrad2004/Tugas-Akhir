import os
import shutil

# ==========================================================
#  DOWNLOAD / COPY LAPORAN RULE-BASED KE FOLDER DOWNLOADS
#  Source : 05_Laporan_Rule_Based/hasil_deteksi_XX.txt
#  Target : C:\Users\<user>\Downloads\Laporan_Rule_Based
# ==========================================================

# Jika file ini diletakkan di:
#   02-1_Scripts (Rule Based)/4_Download_Laporan.py
# maka ROOT_DIR = folder project (BARU\Code\Alur Baru)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SOURCE_DIR = os.path.join(ROOT_DIR, "05_Laporan_Rule_Based")

# Folder tujuan di Downloads
USER = os.getlogin()
TARGET_DIR = fr"C:\Users\{USER}\Downloads\Laporan_Rule_Based"


def main():
    if not os.path.isdir(SOURCE_DIR):
        print(f"[!] Folder sumber tidak ditemukan: {SOURCE_DIR}")
        return

    os.makedirs(TARGET_DIR, exist_ok=True)

    files = [f for f in os.listdir(SOURCE_DIR) if f.endswith(".txt")]
    if not files:
        print(f"[!] Tidak ada file .txt di {SOURCE_DIR}")
        return

    print("===================================================")
    print(f"[INFO] Menyalin laporan dari:")
    print(f"       {SOURCE_DIR}")
    print(f"   ke  {TARGET_DIR}")
    print("===================================================\n")

    copied = 0
    for fname in sorted(files):
        src = os.path.join(SOURCE_DIR, fname)
        dst = os.path.join(TARGET_DIR, fname)
        shutil.copy2(src, dst)
        copied += 1
        print(f"[COPY] {fname}")

    print("\n===================================================")
    print(f"[✓] Selesai. Total file tersalin: {copied}")
    print(f"[✓] Cek folder: {TARGET_DIR}")
    print("===================================================\n")


if __name__ == "__main__":
    main()
