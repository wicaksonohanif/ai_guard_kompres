"""
auth.py — Autentikasi akun mahasiswa (Spec 05 addendum).

Menyediakan tiga hasil yang berbeda agar UI bisa menampilkan pesan yang tepat:
- "success"           -> username & password cocok
- "invalid_username"  -> username tidak terdaftar di tabel `students`
- "invalid_password"  -> username ada, tapi password tidak cocok

Password disimpan sebagai hash (werkzeug.security), bukan plaintext.
"""
from dataclasses import dataclass
from typing import Optional

from werkzeug.security import check_password_hash, generate_password_hash

from src.database.connection import get_db

AuthResult = str  # 'success' | 'invalid_username' | 'invalid_password'


@dataclass
class AuthOutcome:
    result: AuthResult
    student: Optional[dict] = None

    @property
    def ok(self) -> bool:
        return self.result == "success"


def authenticate(username: str, password: str) -> AuthOutcome:
    """Cek kredensial terhadap tabel `students`.

    Tidak pernah raise exception untuk kredensial salah — hanya untuk
    kegagalan sistem (mis. DB tidak bisa diakses), agar caller bisa
    membedakan error operasional vs login gagal biasa.
    """
    username = (username or "").strip()

    with get_db() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash, full_name, student_id "
            "FROM students WHERE username = ?",
            (username,),
        ).fetchone()

    if row is None:
        return AuthOutcome(result="invalid_username")

    if not check_password_hash(row["password_hash"], password or ""):
        return AuthOutcome(result="invalid_password")

    student = {
        "id": row["id"],
        "username": row["username"],
        "full_name": row["full_name"],
        "student_id": row["student_id"],
    }
    return AuthOutcome(result="success", student=student)


def create_student(username: str, password: str, full_name: str = "", student_id: str = "") -> None:
    """Helper untuk seeding/registrasi akun mahasiswa baru."""
    with get_db() as conn:
        conn.execute(
            "INSERT INTO students (username, password_hash, full_name, student_id) "
            "VALUES (?, ?, ?, ?)",
            (username.strip(), generate_password_hash(password), full_name, student_id),
        )
