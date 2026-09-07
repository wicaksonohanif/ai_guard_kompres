"""
Prototipe Website Flask — target simulasi serangan untuk demo AI Guard.
Endpoint dummy: /home, /login, /search, /health.

Middleware AI Guard terintegrasi via @app.before_request / @app.after_request.
"""
from flask import Flask, request, jsonify, g

from src.middleware.ai_guard_middleware import AIGuardMiddleware
from src.middleware.stub_logger import StubDBLogger


def create_app():
    """Application factory dengan AI Guard middleware."""
    app = Flask(__name__)

    # ----- Middleware setup ----- #
    db_logger = StubDBLogger()
    middleware = AIGuardMiddleware(app, db_logger)

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
        """Add X-AI-Guard header to show classification result."""
        action = getattr(g, "ai_guard_action", None)
        if action is not None:
            response.headers["X-AI-Guard"] = action
        return response

    # ----- Endpoint dummy ----- #

    @app.route("/home")
    def home():
        return jsonify({"message": "Welcome to CONNEXTS AI | Network Guard Demo"})

    @app.route("/login", methods=["POST"])
    def login():
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        return jsonify({
            "status": "login_attempt",
            "username": username,
            "message": "Demo login — no real authentication",
        })

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
