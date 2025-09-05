import os
import json
from datetime import datetime
from typing import Optional

from flask import Flask, request, jsonify, g
from flask_cors import CORS
import stripe

from sqlalchemy import (
    create_engine,
    String,
    Integer,
    DateTime,
    Text,
    ForeignKey,
    func,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

# ---- optional scoring import (used by /api/assess) ----
try:
    from calm_profile_system import score_assessment  # your existing scorer
except Exception:  # still allow api to boot if module missing
    score_assessment = None

# ---------- config ----------

def _normalize_db_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url

DATABASE_URL = _normalize_db_url(os.environ.get("DATABASE_URL", ""))
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required")

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
if not STRIPE_SECRET_KEY:
    raise RuntimeError("STRIPE_SECRET_KEY is required")

STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
PRICE_ID = os.environ.get("PRICE_ID", "")
FRONTEND_URL = os.environ.get("FRONTEND_URL")
SECRET_KEY = os.environ.get("SECRET_KEY", os.urandom(24).hex())

stripe.api_key = STRIPE_SECRET_KEY

# ---------- db setup ----------

class Base(DeclarativeBase):
    pass

class Assessment(Base):
    __tablename__ = "assessments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # json blob
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assessment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("assessments.id"), nullable=True)
    stripe_session_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    stripe_payment_intent: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    stripe_event_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    amount_total: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # cents
    customer_email: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
Base.metadata.create_all(engine)

# ---------- app ----------

app = Flask(__name__)
app.secret_key = SECRET_KEY

cors_origins = [FRONTEND_URL] if FRONTEND_URL else "*"
CORS(app, resources={r"/api/*": {"origins": cors_origins}, r"/*": {"origins": cors_origins}})

@app.before_request
def _open_session():
    g.db = SessionLocal()

@app.teardown_request
def _close_session(exc=None):
    db = getattr(g, "db", None)
    if db is not None:
        try:
            if exc:
                db.rollback()
        finally:
            db.close()

def _frontend_base() -> str:
    origin = request.headers.get("Origin")
    if origin and origin.startswith("http"):
        return origin
    if FRONTEND_URL:
        return FRONTEND_URL
    return "https://calmprofile.vercel.app"

def _json(data, status=200):
    return jsonify(data), status

# ---------- health ----------

@app.get("/")
def root():
    return _json({"service": "calm.profile_api", "status": "ok"})

@app.get("/health")
def health():
    return _json({"ok": True, "time": datetime.utcnow().isoformat() + "Z"})

@app.get("/db-check")
def db_check():
    try:
        with engine.connect() as conn:
            conn.execute(select(1))
        return _json({"db": "ok"})
    except Exception as e:
        return _json({"db": "error", "detail": str(e)}, status=500)

# ---------- assessment scoring (for "calculate roi") ----------

@app.post("/api/assess")
def assess():
    if not score_assessment:
        return _json({"success": False, "error": "scoring module not available"}, status=500)

    payload = request.get_json(silent=True) or {}
    responses = payload.get("responses", {})
    context = payload.get("context", {})  # teamSize, meetingLoad, hourlyRate, platform
    email = payload.get("email")

    # normalize a/b -> 1/0 for 20 items
    answers = {str(i): (1 if str(responses.get(str(i), "")).upper() == "A" else 0) for i in range(1, 21)}

    # run scorer
    result = score_assessment(answers)

    # overhead/roi calc (same logic you used before)
    meeting_map = {"light": 0.6, "moderate": 0.8, "heavy": 1.0}
    mkey = next((k for k in meeting_map if k in str(context.get("meetingLoad", "")).lower()), "moderate")
    overhead_base = meeting_map[mkey]

    arche_adj = {"architect": 0.9, "conductor": 0.85, "curator": 1.1, "craftsperson": 1.2}
    primary = (result.get("archetype", {}).get("primary") or "").lower()
    overhead_index = overhead_base * arche_adj.get(primary, 1.0)

    team_mult = {"solo": 1, "2-5": 4, "6-15": 10, "16-50": 25, "50+": 55}
    tm = next((v for k, v in team_mult.items() if k in str(context.get("teamSize", "solo"))), 1)

    hourly_rate = float(context.get("hourlyRate", 85))
    hours_lost_ppw = overhead_index * 5.0
    annual_cost = hours_lost_ppw * 52 * hourly_rate * tm

    # persist
    row = Assessment(email=email, data=json.dumps({
        "responses": answers, "context": context,
        "result": result,
        "metrics": {"hours_lost_ppw": hours_lost_ppw, "annual_cost": annual_cost, "overhead_index": overhead_index}
    }))
    g.db.add(row)
    g.db.commit()

    return _json({
        "success": True,
        "assessment_id": row.id,
        "archetype": result.get("archetype", {}),
        "scores": {**result.get("scores", {}).get("axes", {}), "overhead_index": round(overhead_index * 100)},
        "metrics": {"hours_lost_ppw": round(hours_lost_ppw, 1), "annual_cost": round(annual_cost)},
        "recommendations": result.get("recommendations", []),
        "tagline": (result.get("archetype") or {}).get("tagline", "")
    })

# ---------- stripe checkout & webhooks ----------

@app.post("/create-checkout-session")
def create_checkout_session():
    if not PRICE_ID:
        return _json({"error": "PRICE_ID not configured"}, status=500)

    payload = request.get_json(silent=True) or {}
    assessment_id = payload.get("assessment_id")
    email = payload.get("email")

    success_base = _frontend_base()
    success_url = f"{success_base}/thank-you?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{success_base}/"

    try:
        metadata = {}
        if assessment_id is not None:
            metadata["assessment_id"] = str(assessment_id)

        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{"price": PRICE_ID, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=email if email else None,
            metadata=metadata or None,
            automatic_tax={"enabled": False},
        )

        pay = Payment(
            assessment_id=int(assessment_id) if isinstance(assessment_id, (int, str)) and str(assessment_id).isdigit() else None,
            stripe_session_id=session.id,
            status=session.get("payment_status"),
            currency=session.get("currency"),
            amount_total=session.get("amount_total"),
            customer_email=(session.get("customer_details") or {}).get("email") or email,
        )
        g.db.add(pay)
        g.db.commit()

        return _json({"url": session.url})
    except Exception as e:
        g.db.rollback()
        return _json({"error": str(e)}, status=400)

@app.post("/webhooks/stripe")
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get("Stripe-Signature", "")

    if not STRIPE_WEBHOOK_SECRET:
        return _json({"error": "webhook secret not configured"}, status=500)

    try:
        event = stripe.Webhook.construct_event(payload=payload, sig_header=sig_header, secret=STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        return _json({"error": f"invalid signature: {e}"}, status=400)

    event_type = event["type"]
    event_id = event["id"]

    existing_event = g.db.execute(select(Payment).where(Payment.stripe_event_id == event_id)).scalar_one_or_none()
    if existing_event:
        return _json({"received": True, "idempotent": True})

    try:
        if event_type == "checkout.session.completed":
            session_obj = event["data"]["object"]
            session_id = session_obj.get("id")
            payment_intent = session_obj.get("payment_intent")
            amount_total = session_obj.get("amount_total")
            currency = session_obj.get("currency")
            status = session_obj.get("payment_status")
            customer_email = (session_obj.get("customer_details") or {}).get("email")
            assessment_id = session_obj.get("metadata", {}).get("assessment_id")

            row = g.db.execute(select(Payment).where(Payment.stripe_session_id == session_id)).scalar_one_or_none()
            if row:
                row.stripe_payment_intent = payment_intent
                row.amount_total = amount_total
                row.currency = currency
                row.status = status
                row.customer_email = row.customer_email or customer_email
                row.stripe_event_id = event_id
                if assessment_id and not row.assessment_id and str(assessment_id).isdigit():
                    row.assessment_id = int(assessment_id)
                g.db.commit()
            else:
                g.db.add(Payment(
                    assessment_id=int(assessment_id) if assessment_id and str(assessment_id).isdigit() else None,
                    stripe_session_id=session_id,
                    stripe_payment_intent=payment_intent,
                    amount_total=amount_total,
                    currency=currency,
                    status=status,
                    customer_email=customer_email,
                    stripe_event_id=event_id,
                ))
                g.db.commit()

        elif event_type in ("payment_intent.succeeded", "payment_intent.payment_failed"):
            intent = event["data"]["object"]
            pi = intent.get("id")
            status = intent.get("status")
            amount = intent.get("amount")
            currency = intent.get("currency")
            email = (intent.get("charges", {}).get("data", [{}])[0].get("billing_details") or {}).get("email")

            row = g.db.execute(select(Payment).where(Payment.stripe_payment_intent == pi)).scalar_one_or_none()
            if row:
                row.status = status or row.status
                row.amount_total = amount or row.amount_total
                row.currency = currency or row.currency
                row.customer_email = row.customer_email or email
                row.stripe_event_id = event_id
                g.db.commit()
            else:
                g.db.add(Payment(
                    stripe_payment_intent=pi,
                    amount_total=amount,
                    currency=currency,
                    status=status,
                    customer_email=email,
                    stripe_event_id=event_id,
                ))
                g.db.commit()

        return _json({"received": True})
    except Exception as e:
        g.db.rollback()
        return _json({"error": str(e)}, status=500)

# aliases for old paths
@app.get("/api/health")
def api_health_alias():
    return health()

@app.post("/api/create-checkout-session")
def api_checkout_alias():
    return create_checkout_session()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
