import os
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from uuid import uuid4
import traceback

load_dotenv()
app = Flask(__name__)

# CORS for local dev
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:*", "http://127.0.0.1:*", "http://localhost:3000", "http://localhost:5173"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"],
        "supports_credentials": True
    }
})

# db
db_url = os.getenv("DATABASE_URL", "sqlite:///calm_profile.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class Assessment(db.Model):
    __tablename__ = "assessments"
    id = db.Column(db.String(36), primary_key=True)
    email = db.Column(db.String(255), index=True)
    archetype_primary = db.Column(db.String(32))
    archetype_mix = db.Column(db.JSON)
    axis_scores = db.Column(db.JSON)
    overhead_index = db.Column(db.Float)
    hours_lost = db.Column(db.Float)
    annual_cost = db.Column(db.Float)
    raw_responses = db.Column(db.JSON)
    context_data = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    report_sent = db.Column(db.Boolean, default=False)
    payment_status = db.Column(db.String(20), default="pending")

from calm_profile_system import score_assessment, format_response

with app.app_context():
    db.create_all()

@app.get("/api/health")
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()})

@app.post("/api/assess")
def assess():
    try:
        data = request.get_json(force=True)
        responses = data.get("responses", {})
        context = data.get("context", {})

        # A/B -> 1/0
        formatted = {str(i): (1 if responses.get(str(i)) == "A" else 0) for i in range(20)}

        # score
        result = score_assessment(formatted)

        # context
        team_size = context.get("teamSize", "solo")
        meeting_load = context.get("meetingLoad", "light")
        hourly_rate = float(context.get("hourlyRate", 85))
        platform = context.get("platform", "web")

        overhead_multipliers = {"light": 0.6, "moderate": 0.8, "heavy": 1.0}
        meeting_key = next((k for k in overhead_multipliers if k in str(meeting_load).lower()), "moderate")
        overhead_base = overhead_multipliers[meeting_key]

        arche_adj = {"architect": 0.9, "conductor": 0.85, "curator": 1.1, "craftsperson": 1.2}
        primary = result["archetype"]["primary"].lower()
        overhead_index = overhead_base * arche_adj.get(primary, 1.0)

        team_mult = {"solo": 1, "2-5": 4, "6-15": 10, "16-50": 25, "50+": 55}
        tm = next((v for k, v in team_mult.items() if k in str(team_size)), 1)

        hours_lost_ppw = overhead_index * 5.0
        annual_cost = hours_lost_ppw * 52 * hourly_rate * tm

        # save
        assessment_id = str(uuid4())
        rec = Assessment(
            id=assessment_id,
            email=None,
            archetype_primary=result["archetype"]["primary"],
            archetype_mix=result["archetype"]["mix"],
            axis_scores=result["scores"]["axes"],
            overhead_index=overhead_index,
            hours_lost=hours_lost_ppw,
            annual_cost=annual_cost,
            raw_responses=formatted,
            context_data={"team_size": team_size, "meeting_load": meeting_load, "hourly_rate": hourly_rate, "platform": platform}
        )
        db.session.add(rec)
        db.session.commit()

        return jsonify({
            "success": True,
            "assessment_id": assessment_id,
            "archetype": result["archetype"],
            "scores": {**result["scores"]["axes"], "overhead_index": round(overhead_index * 100)},
            "metrics": {"hours_lost_ppw": round(hours_lost_ppw, 1), "annual_cost": round(annual_cost)},
            "recommendations": result["recommendations"],
            "tagline": result["archetype"].get("tagline", "")
        })
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500

@app.post("/api/create-checkout")
def create_checkout():
    """dev: return stub link; prod: uncomment stripe block below"""
    try:
        data = request.get_json(force=True) or {}
        email = data.get("email")
        assessment_id = data.get("assessment_id")
        frontend = os.getenv("FRONTEND_URL", "http://localhost:3000")

        # attach email if present
        if assessment_id and email:
            a = Assessment.query.get(assessment_id)
            if a:
                a.email = email
                db.session.commit()

        # dev stub
        return jsonify({"success": True, "checkout_url": f"{frontend}/thank-you/?session_id=mock_{assessment_id or 'dev'}"})

        # --- stripe (prod) ---
        """
        import stripe
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
        if not stripe.api_key:
            return jsonify({"error": "Stripe not configured"}), 500

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {'name': 'Calm Profile Assessment Report', 'description': 'Comprehensive workstyle analysis and recommendations'},
                    'unit_amount': 49500,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f'{frontend}/thank-you/?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'{frontend}/assessment',
            customer_email=email,
            metadata={'assessment_id': assessment_id}
        )
        return jsonify({"success": True, "checkout_url": session.url})
        """
    except Exception as e:
        print(f"Checkout error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV", "development") == "development"
    app.run(debug=debug, host="0.0.0.0", port=port)
