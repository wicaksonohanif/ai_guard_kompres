"""inspect_db.py — Tampilkan isi tabel-tabel penting untuk verifikasi demo.

Usage: python3 -m scripts.inspect_db
"""
from src.database.connection import get_db


def show(conn, title, query):
    print(f"\n--- {title} ---")
    rows = conn.execute(query).fetchall()
    if not rows:
        print("(kosong)")
    for row in rows:
        print(dict(row))


def main():
    with get_db() as conn:
        show(conn, "students", "SELECT id, username, full_name, student_id FROM students")
        show(
            conn,
            "login_attempts (10 terbaru)",
            "SELECT timestamp, username, source_ip, result FROM login_attempts ORDER BY id DESC LIMIT 10",
        )
        show(
            conn,
            "traffic_logs (10 terbaru)",
            "SELECT timestamp, method, url, label, confidence, attack_class, action, is_blocked "
            "FROM traffic_logs ORDER BY id DESC LIMIT 10",
        )
        show(
            conn,
            "notification_logs (10 terbaru)",
            "SELECT timestamp, traffic_log_id, status, substr(message_preview,1,60) AS preview "
            "FROM notification_logs ORDER BY id DESC LIMIT 10",
        )


if __name__ == "__main__":
    main()
