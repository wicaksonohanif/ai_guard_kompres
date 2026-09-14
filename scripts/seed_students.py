"""
seed_students.py — Inisialisasi schema DB + isi akun mahasiswa demo.

Usage (jalankan dari root repo, python -m diperlukan agar import `src.*` resolve):
    python3 -m scripts.seed_students

Aman dijalankan berulang kali (idempotent — pakai INSERT OR IGNORE via
UNIQUE constraint pada `username`, akun yang sudah ada akan diskip).

Akun demo (untuk kebutuhan presentasi/testing):
    student1 / Passw0rd123
    student2 / Passw0rd123
    admin_demo / AdminDemo123   (tetap akun mahasiswa biasa, hanya nama beda)
"""
import sqlite3

from src.database.connection import init_db, get_db
from src.website.auth import create_student

DEMO_STUDENTS = [
    ("student1", "Passw0rd123", "Andi Saputra", "2201001"),
    ("student2", "Passw0rd123", "Bunga Lestari", "2201002"),
    ("student3", "Passw0rd123", "Citra Wulandari", "2201003"),
]


def main():
    init_db()

    with get_db() as conn:
        existing = {
            r["username"]
            for r in conn.execute("SELECT username FROM students").fetchall()
        }

    created = 0
    for username, password, full_name, student_id in DEMO_STUDENTS:
        if username in existing:
            print(f"[skip] {username} sudah ada")
            continue
        try:
            create_student(username, password, full_name, student_id)
            created += 1
            print(f"[ok]   {username} dibuat")
        except sqlite3.IntegrityError:
            print(f"[skip] {username} sudah ada (race)")

    print(f"\nSelesai. {created} akun baru dibuat.")


if __name__ == "__main__":
    main()
