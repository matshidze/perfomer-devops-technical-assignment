#this is for testing purpose
this_is_invalid_python !!!!

import os
from flask import Flask, request, redirect, render_template
from sqlalchemy import create_engine, text
from prometheus_flask_exporter import PrometheusMetrics


def create_app():
    app = Flask(__name__)

    # Prometheus metrics exposed at /metrics
    metrics = PrometheusMetrics(app)
    metrics.info("app_info", "Flask app info", version="1.0.0")

    db_user = os.getenv("POSTGRES_USER", "performeruser")
    db_pass = os.getenv("POSTGRES_PASSWORD", "performerpass")
    db_name = os.getenv("POSTGRES_DB", "appdb")
    db_host = os.getenv("DB_HOST", "db")     # docker compose service name
    db_port = os.getenv("DB_PORT", "5432")

    db_url = f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    engine = create_engine(db_url, pool_pre_ping=True)

    # Create table if not exists
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                message TEXT NOT NULL
            );
        """))

    @app.get("/")
    def index():
        with engine.begin() as conn:
            rows = conn.execute(
                text("SELECT message FROM messages ORDER BY id DESC LIMIT 20;")
            ).fetchall()
        messages = [r[0] for r in rows]
        return render_template("index.html", messages=messages)

    @app.post("/submit")
    def submit():
        msg = (request.form.get("message") or "").strip()
        if msg:
            with engine.begin() as conn:
                conn.execute(text("INSERT INTO messages (message) VALUES (:m);"), {"m": msg})
        return redirect("/")

    @app.get("/health")
    def health():
        return {"status": "ok"}, 200

    return app


app = create_app()

if __name__ == "__main__":
    # Important for Docker: must bind 0.0.0.0
    app.run(host="0.0.0.0", port=5000)
