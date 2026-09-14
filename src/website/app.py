"""
Prototipe Website Flask — target simulasi serangan untuk demo AI Guard.
Endpoint dummy: /home, /login, /search, /health, /dashboard, /my/courses.

Middleware AI Guard terintegrasi via @app.before_request / @app.after_request.

Spec 05 addendum (versi ini):
- Login sungguhan terhadap tabel `students` (bukan lagi "semua kredensial valid").
- /dashboard & /my/courses hanya bisa diakses setelah login (session-based).
- StubDBLogger diganti TrafficLogger (SQLite asli) + init_db() saat startup.
- TelegramNotifier terpasang di middleware, hanya kirim saat action == 'block'.
- Detail hasil AI (label/confidence/attack_class) TIDAK PERNAH dikirim ke
  template/response yang dilihat mahasiswa — hanya header debug X-AI-Guard
  berisi action kasar (allow/flag), dan response 403 generik saat block.
"""
import os
import functools
import logging

from flask import Flask, request, jsonify, g, render_template, redirect, url_for, session

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

from src.middleware.ai_guard_middleware import AIGuardMiddleware
from src.database.connection import init_db, get_connection
from src.database.logger import TrafficLogger
from src.notifier.telegram_bot import TelegramNotifier
from src.notifier.aggregator import NotificationAggregator
from src.website.auth import authenticate


def login_required(view):
    """Gate: mahasiswa harus login untuk mengakses halaman portal."""

    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("student_id"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def create_app():
    """Application factory dengan AI Guard middleware."""
    app = Flask(__name__)
    app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-only-secret-change-me")

    # ----- Database ----- #
    init_db()
    # Koneksi persisten untuk logger (single-process demo; check_same_thread=False
    # sudah diset di connection.get_connection()).
    db_conn = get_connection()
    db_logger = TrafficLogger(db_conn)

    # ----- Telegram notifier (Spec 07) ----- #
    notifier = TelegramNotifier(
        bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
        aggregator=NotificationAggregator(),
        notify_on_block_only=True,
    )

    # ----- Middleware setup ----- #
    middleware = AIGuardMiddleware(app, db_logger, notifier=notifier)

    @app.before_request
    def ai_guard_check():
        action = middleware.process_request(request)

        if action == "block":
            return jsonify({
                "error": "Request blocked by AI Guard",
                "reason": "Anomalous traffic detected",
            }), 403

        # Store action for after_request (None = skipped)
        g.ai_guard_action = action

    @app.after_request
    def add_ai_guard_headers(response):
        """Add X-AI-Guard header (allow/flag only — never confidence/attack_class)."""
        action = getattr(g, "ai_guard_action", None)
        if action is not None:
            response.headers["X-AI-Guard"] = action
        return response

    # ----- Endpoint dummy ----- #

    @app.route("/home")
    def home():
        return jsonify({"message": "Welcome to CONNEXTS AI | Network Guard Demo"})

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "GET":
            return render_template("login.html")

        username = request.form.get("username", "")
        password = request.form.get("password", "")
        source_ip = request.headers.get("X-Forwarded-For", request.remote_addr)

        outcome = authenticate(username, password)

        # Setiap percobaan login dicatat (Spec 05 target #8)
        db_logger.log_login_attempt(username=username, source_ip=source_ip, result=outcome.result)

        if outcome.result == "invalid_username":
            return render_template("login.html", error="Username tidak ditemukan.", username=username), 401

        if outcome.result == "invalid_password":
            return render_template("login.html", error="Password salah.", username=username), 401

        # Sukses
        session.clear()
        session["student_id"] = outcome.student["id"]
        session["student_name"] = outcome.student["full_name"]
        return redirect(url_for("dashboard"))

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/dashboard")
    @app.route("/my/courses")
    @login_required
    def dashboard():
        return render_template(
            "dashboard.html",
            courses=[],
            student_name=session.get("student_name"),
        )

    @app.route("/")
    def index():
        return redirect(url_for("login"))

    @app.route("/search")
    def search():
        q = request.args.get("q", "")
        return jsonify({
            "query": q,
            "results": [f"Dummy result for '{q}'"],
            "total": 1,
        })

    @app.route("/health")
    def health():
        return jsonify({"status": "healthy", "service": "website"})

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)
