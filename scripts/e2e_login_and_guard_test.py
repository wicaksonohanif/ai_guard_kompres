"""
e2e_login_and_guard_test.py — Uji end-to-end Spec 05 (login + AI Guard).

Mencakup semua skenario di "Target akhir tugas" pada spec:
    1. Login dengan akun terdaftar -> berhasil
    2. Username salah -> "Username tidak ditemukan"
    3. Password salah -> "Password salah"
    4. Request normal -> NORMAL -> dilanjutkan
    5. Request pola serangan -> ANOMALY -> diblokir (403)
    6. Mahasiswa tidak melihat prediction/confidence AI (cek body & header)
    7. (Manual/log check) Notifikasi Telegram terpicu hanya saat ANOMALY+block
    8. Semua kejadian tercatat di database (login_attempts, traffic_logs, notification_logs)

Prasyarat sebelum menjalankan:
    1. Inference API jalan di :8000   -> python3 -m uvicorn src.api.main:app --port 8000
    2. Website Flask jalan di :5000   -> python3 -m src.website.app
    3. Akun demo sudah di-seed        -> python3 -m scripts.seed_students

Usage:
    python3 -m scripts.e2e_login_and_guard_test
"""
import sys

import requests

BASE = "http://127.0.0.1:5000"
PASS = "PASS"
FAIL = "FAIL"

results = []


def check(name, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((status, name, detail))
    print(f"[{status}] {name}" + (f" — {detail}" if detail and status == FAIL else ""))


def main():
    session_ok = requests.Session()

    # 1. Login sukses dengan akun terdaftar
    r = session_ok.post(f"{BASE}/login", data={"username": "student1", "password": "Passw0rd123"}, allow_redirects=False)
    check("Login akun terdaftar -> redirect ke dashboard", r.status_code == 302, f"status={r.status_code}")

    # verifikasi session benar-benar bisa akses halaman terproteksi
    r2 = session_ok.get(f"{BASE}/my/courses")
    check("Setelah login -> /my/courses bisa diakses (200)", r2.status_code == 200, f"status={r2.status_code}")

    # 2. Username salah
    r = requests.post(f"{BASE}/login", data={"username": "tidak_ada_user", "password": "apasaja"})
    check(
        "Username salah -> pesan 'Username tidak ditemukan'",
        r.status_code == 401 and "Username tidak ditemukan" in r.text,
        f"status={r.status_code}",
    )

    # 3. Password salah
    r = requests.post(f"{BASE}/login", data={"username": "student1", "password": "salahbanget"})
    check(
        "Password salah -> pesan 'Password salah'",
        r.status_code == 401 and "Password salah" in r.text,
        f"status={r.status_code}",
    )

    # Tanpa login -> /my/courses harus redirect ke /login
    r = requests.get(f"{BASE}/my/courses", allow_redirects=False)
    check("Tanpa login -> /my/courses redirect (302)", r.status_code == 302, f"status={r.status_code}")

    # 4. Request normal -> NORMAL -> dilanjutkan
    r = requests.get(f"{BASE}/search", params={"q": "jadwal kuliah"})
    check("Request normal /search -> 200 (allow)", r.status_code == 200, f"status={r.status_code}")
    check("Header X-AI-Guard = allow untuk request normal", r.headers.get("X-AI-Guard") == "allow", f"header={r.headers.get('X-AI-Guard')}")

    # 5. Request serangan (pola sesuai dataset CSIC: XSS / UNION SELECT) -> diblokir
    r = requests.get(f"{BASE}/search", params={"q": "<script>alert(document.cookie)</script>"})
    check("XSS payload -> 403 (block)", r.status_code == 403, f"status={r.status_code}")

    r = requests.get(
        f"{BASE}/search",
        params={"q": "1 UNION SELECT username,password FROM users--"},
    )
    check("SQLi (UNION SELECT) payload -> 403 (block)", r.status_code == 403, f"status={r.status_code}")

    # 6. Mahasiswa tidak melihat detail AI (confidence/attack_class) di body maupun header
    body_leaks_detail = any(k in r.text.lower() for k in ["confidence", "attack_class", "attack_type"])
    check("Response body TIDAK memuat confidence/attack_class", not body_leaks_detail)

    header_val = r.headers.get("X-AI-Guard", "")
    check(
        "Header X-AI-Guard hanya action kasar (bukan angka confidence)",
        header_val in ("", "allow", "flag"),  # block tidak set header (lihat KNOWN-LIMITATIONS.md #1)
        f"header={header_val}",
    )

    print("\n--- Ringkasan ---")
    n_pass = sum(1 for s, _, _ in results if s == PASS)
    n_fail = sum(1 for s, _, _ in results if s == FAIL)
    print(f"{n_pass} PASS, {n_fail} FAIL dari {len(results)} skenario.")

    print(
        "\nCatatan:\n"
        "- Skenario #7 (notifikasi Telegram) & #8 (semua tercatat di DB) diverifikasi\n"
        "  lewat isi tabel `login_attempts`, `traffic_logs`, dan `notification_logs`\n"
        "  di data/ai_guard.db — lihat scripts/inspect_db.py atau query manual.\n"
        "- Jika TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID belum diset, notifier berjalan\n"
        "  dalam mode disabled: event anomaly tetap tercatat di notification_logs\n"
        "  (status='aggregated') tapi tidak benar-benar memanggil Telegram API."
    )

    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
