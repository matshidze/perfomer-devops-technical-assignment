import os
import time
import logging
from urllib.parse import quote_plus
from flask import Flask, request, redirect, render_template, jsonify
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from prometheus_flask_exporter import PrometheusMetrics


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("perfomer-app")


def build_db_url() -> str:
    db_user = os.getenv("POSTGRES_USER", "performeruser")
    db_pass = quote_plus(os.getenv("POSTGRES_PASSWORD", "performerpass"))
    db_name = os.getenv("POSTGRES_DB", "appdb")
    db_host = os.getenv("DB_HOST", "db")
    db_port = os.getenv("DB_PORT", "5432")

    return f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"


def wait_for_db(engine, retries: int = 25, delay_seconds: int = 2) -> None:

    for attempt in range(1, retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1;"))
            logger.info("Database connection successful.")
            return
        except OperationalError as e:
            logger.warning(
                "DB not ready (attempt %s/%s). Retrying in %ss. Error: %s",
                attempt, retries, delay_seconds, str(e).splitlines()[0],
            )
            time.sleep(delay_seconds)

    raise RuntimeError("Database not ready after retries")


def ensure_schema(engine) -> None:
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    message TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """))
        logger.info("Schema ensured (messages table).")
    except SQLAlchemyError:
        logger.exception("Failed to create/ensure schema.")
        raise


def create_app() -> Flask:
    app = Flask(__name__)


    metrics = PrometheusMetrics(app)
    metrics.info("app_info", "Flask app info", version="1.0.0")

    db_url = build_db_url()
    logger.info("Starting app. DB host configured: %s", os.getenv("DB_HOST", "db"))

    engine = create_engine(db_url, pool_pre_ping=True)


    wait_for_db(engine)
    ensure_schema(engine)

    @app.get("/health")
    def health():
        return jsonify(status="ok"), 200

    @app.get("/ready")
    def ready():
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1;"))
            return jsonify(status="ready"), 200
        except OperationalError:
            return jsonify(status="not_ready"), 503

    @app.get("/")
    def index():
        try:
            with engine.begin() as conn:
                rows = conn.execute(
                    text("SELECT message FROM messages ORDER BY id DESC LIMIT 20;")
                ).fetchall()
            messages = [r[0] for r in rows]
            return render_template("index.html", messages=messages)
        except SQLAlchemyError:
            logger.exception("Failed to fetch messages.")
            return "Internal Server Error", 500

    @app.post("/submit")
    def submit():
        msg = (request.form.get("message") or "").strip()
        if not msg:
            return redirect("/")

        try:
            with engine.begin() as conn:
                conn.execute(
                    text("INSERT INTO messages (message) VALUES (:m);"),
                    {"m": msg},
                )
            logger.info("Message stored successfully. length=%s", len(msg))
            return redirect("/")
        except SQLAlchemyError:
            logger.exception("Failed to store message.")
            return "Internal Server Error", 500

    return app


app = create_app()


if __name__ == "__main__":
   app.run(host="0.0.0.0", port=5000)