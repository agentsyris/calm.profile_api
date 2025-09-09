import os
import json
import subprocess
import tempfile
from datetime import datetime
from typing import Optional
from pathlib import Path

# Optional AWS S3 import
try:
    import boto3

    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

from flask import Flask, request, jsonify, g
from flask_cors import CORS
import stripe
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://syris.studio")
SECRET_KEY = os.environ.get("SECRET_KEY", os.urandom(24).hex())

# PDF generation and storage config
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
AWS_S3_BUCKET = os.environ.get("AWS_S3_BUCKET", "")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# Email service config
POSTMARK_API_TOKEN = os.environ.get("POSTMARK_API_TOKEN", "")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
CALENDLY_URL = os.environ.get("CALENDLY_URL", "https://calendly.com/syris-studio")

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
    assessment_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("assessments.id"), nullable=True
    )
    stripe_session_id: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, nullable=True
    )
    stripe_payment_intent: Mapped[Optional[str]] = mapped_column(
        String(255), index=True, nullable=True
    )
    stripe_event_id: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, nullable=True
    )
    status: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    amount_total: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # cents
    customer_email: Mapped[Optional[str]] = mapped_column(
        String(255), index=True, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
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

# Configure logging
import logging

logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

# FIXED CORS CONFIGURATION
CORS(
    app,
    origins=[
        "https://calmprofile.vercel.app",
        "https://*.vercel.app",
        "https://syris.studio",
        "https://*.syris.studio",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:5000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5000",
    ],
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "OPTIONS"],
    supports_credentials=True,
)


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
    return "https://syris.studio"


def _json(data, status=200):
    return jsonify(data), status


def validate_and_normalize_assessment_data(raw_data: dict) -> dict:
    """validate required fields and normalize data for template rendering"""
    from renderer.schema import to_report_fields, validate_template_fields
    from renderer.render_report import fmt_confidence

    # required fields that must exist
    required_fields = [
        "responses",
        "context",
        "result",
        "metrics",
        "company_name",
        "assessment_date",
        "report_id",
    ]

    # check for missing required fields
    missing_fields = [field for field in required_fields if field not in raw_data]
    if missing_fields:
        raise ValueError(f"Missing required fields: {missing_fields}")

    # extract nested data
    responses = raw_data.get("responses", {})
    context = raw_data.get("context", {})
    result = raw_data.get("result", {})
    metrics = raw_data.get("metrics", {})

    # normalize to template format
    normalized = {
        # basic metadata
        "company_name": raw_data.get("company_name", "your organization"),
        "assessment_date": raw_data.get("assessment_date", "unknown"),
        "report_id": raw_data.get("report_id", "unknown"),
        "assessment_id": raw_data.get("assessment_id", "unknown"),
        "completion_date": raw_data.get("completion_date", "unknown"),
        "customer_email": raw_data.get("customer_email", "unknown"),
        # archetype data
        "archetype_primary": result.get("archetype", {}).get("primary", "unknown"),
        "archetype_confidence": result.get("archetype", {}).get("confidence", 0),
        "archetype_tagline": result.get("archetype", {}).get("tagline", ""),
        "archetype_mix_primary": result.get("archetype", {})
        .get("mix", {})
        .get("primary", 0),
        "archetype_mix_secondary": result.get("archetype", {})
        .get("mix", {})
        .get("secondary", 0),
        "archetype_mix_tertiary": result.get("archetype", {})
        .get("mix", {})
        .get("tertiary", 0),
        "archetype_mix_quaternary": result.get("archetype", {})
        .get("mix", {})
        .get("quaternary", 0),
        "archetype_secondary": result.get("archetype", {}).get("secondary", "unknown"),
        "archetype_tertiary": result.get("archetype", {}).get("tertiary", "unknown"),
        "archetype_quaternary": result.get("archetype", {}).get(
            "quaternary", "unknown"
        ),
        # axis scores
        "axis_structure": result.get("scores", {}).get("axes", {}).get("structure", 0),
        "axis_collaboration": result.get("scores", {})
        .get("axes", {})
        .get("collaboration", 0),
        "axis_scope": result.get("scores", {}).get("axes", {}).get("scope", 0),
        "axis_tempo": result.get("scores", {}).get("axes", {}).get("tempo", 0),
        # metrics
        "overhead_percentage": metrics.get("overhead_index", 0) * 100,
        "annual_cost": metrics.get("annual_cost", 0),
        "hours_lost_ppw": metrics.get("hours_lost_ppw", 0),
        # context data
        "team_size": context.get("team_size", 1),
        "meeting_load": context.get("meeting_load", "medium"),
        "hourly_rate": context.get("hourly_rate", 100),
        "platform": context.get("platform", "unknown"),
        # recommendations (generate rice scores)
        "r1_title": "optimize meeting structure",
        "r1_description": "implement structured meeting formats with clear agendas and outcomes",
        "r1_effort": "low",
        "r1_impact": "high",
        "r1_timeline": "2 weeks",
        "r1_rice": 8,
        "r1_linked_finding": "f1",
        "r2_title": "establish async communication",
        "r2_description": "implement async-first communication protocols",
        "r2_effort": "medium",
        "r2_impact": "high",
        "r2_timeline": "4 weeks",
        "r2_rice": 6,
        "r2_linked_finding": "f2",
        "r3_title": "automate routine tasks",
        "r3_description": "implement automation for administrative processes",
        "r3_effort": "medium",
        "r3_impact": "medium",
        "r3_timeline": "6 weeks",
        "r3_rice": 4,
        "r3_linked_finding": "f3",
        "r4_title": "create decision matrix",
        "r4_description": "establish clear decision ownership protocols",
        "r4_effort": "low",
        "r4_impact": "high",
        "r4_timeline": "1 week",
        "r4_rice": 9,
        "r4_linked_finding": "f4",
        "r5_title": "integrate project systems",
        "r5_description": "consolidate project tracking platforms",
        "r5_effort": "high",
        "r5_impact": "medium",
        "r5_timeline": "8 weeks",
        "r5_rice": 3,
        "r5_linked_finding": "f5",
        # calculated fields
        "break_even_timeline": "3-4 months",
        "team_multiplier": context.get("team_size", 1),
        "confidence_score": result.get("archetype", {}).get("confidence", 0),
        "response_count": len(responses) if isinstance(responses, dict) else 0,
        # top findings
        "top_findings": result.get("recommendations", {}).get(
            "summary",
            [
                "assessment completed successfully",
                "productivity improvements identified",
                "implementation roadmap available",
            ],
        ),
        # radar insights
        "radar_insights": f"archetype analysis shows {result.get('archetype', {}).get('primary', 'unknown')} tendencies with {fmt_confidence(result.get('archetype', {}).get('confidence', 0))} confidence",
        # time breakdown
        "time_productive": 45,
        "time_meetings": 25,
        "time_admin": 20,
        "time_context_switch": 10,
        # workflow data (rasci matrix)
        "workflow1_r": "pm",
        "workflow1_a": "cto",
        "workflow1_s": "design team",
        "workflow1_c": "account",
        "workflow1_i": "ops",
        "workflow2_r": "pm",
        "workflow2_a": "cto",
        "workflow2_s": "design team",
        "workflow2_c": "account",
        "workflow2_i": "ops",
        "workflow3_r": "pm",
        "workflow3_a": "cto",
        "workflow3_s": "design team",
        "workflow3_c": "account",
        "workflow3_i": "ops",
        "workflow4_r": "pm",
        "workflow4_a": "cto",
        "workflow4_s": "design team",
        "workflow4_c": "account",
        "workflow4_i": "ops",
        "workflow5_r": "pm",
        "workflow5_a": "cto",
        "workflow5_s": "design team",
        "workflow5_c": "account",
        "workflow5_i": "ops",
        # findings details
        "f1_issue": "meeting inefficiency",
        "f1_evidence": "excessive meeting time without clear outcomes",
        "f1_impact": "high",
        "f1_root_cause": "lack of structured meeting formats",
        "f1_preview": "implement structured meeting protocols",
        "f2_issue": "communication delays",
        "f2_evidence": "context switching overhead",
        "f2_impact": "high",
        "f2_root_cause": "async communication gaps",
        "f2_preview": "establish async communication protocols",
        "f3_issue": "administrative overhead",
        "f3_evidence": "routine task repetition",
        "f3_impact": "medium",
        "f3_root_cause": "manual process inefficiency",
        "f3_preview": "implement automation tools",
        "f4_issue": "decision bottlenecks",
        "f4_evidence": "delayed decision making",
        "f4_impact": "high",
        "f4_root_cause": "unclear decision ownership",
        "f4_preview": "create decision matrix",
        "f5_issue": "system fragmentation",
        "f5_evidence": "multiple tracking platforms",
        "f5_impact": "medium",
        "f5_root_cause": "lack of integrated systems",
        "f5_preview": "consolidate project tracking",
        # efficiency metrics
        "efficiency_planning": 7,
        "efficiency_execution": 6,
        "efficiency_review": 8,
        "efficiency_communication": 5,
        "workflow_bottlenecks": "meeting overload and context switching",
        # roi calculations (scale with team size)
        "base_overhead": metrics.get("overhead_index", 0) * 100,
        "archetype_adjustment": 1.2,
        "weekly_cost": metrics.get("annual_cost", 0) / 52 if metrics.get("annual_cost", 0) > 0 else context.get("hourly_rate", 100) * 5 * context.get("team_size", 1),
        # sensitivity analysis (scale with team size)
        "sensitivity_25_margin": 15.0,
        "sensitivity_25_cost": 180000.0 * (context.get("team_size", 1) / 4.0),
        "sensitivity_25_hours": 4.0,
        "sensitivity_50_margin": 20.0,
        "sensitivity_50_cost": 240000.0 * (context.get("team_size", 1) / 4.0),
        "sensitivity_50_hours": 6.0,
        "sensitivity_75_margin": 25.0,
        "sensitivity_75_cost": 300000.0 * (context.get("team_size", 1) / 4.0),
        "sensitivity_75_hours": 8.0,
        # 5-year projections (scale with team size)
        "conservative_5yr": 450000.0 * (context.get("team_size", 1) / 4.0),
        "realistic_5yr": 600000.0 * (context.get("team_size", 1) / 4.0),
        "optimistic_5yr": 750000.0 * (context.get("team_size", 1) / 4.0),
        # savings projections
        "savings_month1": 5.0,
        "savings_month3": 15.0,
        "savings_month6": 25.0,
        "savings_month12": 35.0,
        # implementation
        "critical_path": "meeting optimization → async protocols → automation",
        "milestone_schedule": "week 1-2: meetings, week 3-6: async, week 7-12: automation",
        "roadmap_30_days": "implement structured meeting formats and async protocols",
        "roadmap_60_days": "deploy automation tools and decision matrix",
        "roadmap_90_days": "integrate systems and optimize workflows",
        # success metrics
        "baseline_ontime": 65.0,
        "target_ontime": 85.0,
        "owner_ontime": "pm",
        "baseline_latency": 40.0,
        "target_latency": 20.0,
        "owner_latency": "cto",
        "baseline_variance": 25.0,
        "target_variance": 10.0,
        "owner_variance": "pm",
        "baseline_change": 15.0,
        "target_change": 5.0,
        "owner_change": "account",
        # next steps
        "next_steps": "schedule implementation kickoff meeting and assign team leads",
    }

    # Use schema mapper to ensure all template fields are present
    normalized = to_report_fields(normalized)

    # Validate normalized data
    if not validate_template_fields(normalized):
        raise ValueError("Template field validation failed")

    app.logger.info(f"Normalized data validation passed. Keys: {len(normalized)}")
    return normalized


def generate_pdf_report(assessment_data: dict, customer_email: str) -> str:
    """generate pdf report and return url (s3 or local)"""
    try:
        # create temporary json file with assessment data
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(assessment_data, f)
            temp_json_path = f.name

        app.logger.info(f"Created temp data file: {temp_json_path}")
        app.logger.info(f"Data file size: {os.path.getsize(temp_json_path)} bytes")

        # generate pdf using renderer
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"calm_profile_report_{customer_email}_{timestamp}.pdf"

        # run renderer subprocess
        # Debug: check what's actually available
        app.logger.info(f"Current working directory: {os.getcwd()}")
        app.logger.info(f"Directory contents: {os.listdir('.')}")

        # Try different possible paths
        possible_paths = [
            "/opt/render/project/src/renderer/render_report.py",
            "/opt/render/project/renderer/render_report.py",
            "/opt/render/renderer/render_report.py",
            "renderer/render_report.py",
            "./renderer/render_report.py",
            os.path.join(os.getcwd(), "renderer", "render_report.py"),
        ]

        renderer_script = None
        for path in possible_paths:
            app.logger.info(f"Checking: {path} - exists: {os.path.exists(path)}")
            if os.path.exists(path):
                renderer_script = path
                break

        if not renderer_script:
            raise Exception(f"Could not find renderer script. Tried: {possible_paths}")

        app.logger.info(f"Using renderer script: {renderer_script}")

        renderer_cmd = [
            "python3",
            renderer_script,
            "--data",
            temp_json_path,
            "--output",
            pdf_filename,
        ]

        result = subprocess.run(
            renderer_cmd, capture_output=True, text=True, cwd=os.getcwd()
        )

        if result.returncode != 0:
            app.logger.error(f"renderer failed with return code {result.returncode}")
            app.logger.error(f"renderer stdout: {result.stdout}")
            app.logger.error(f"renderer stderr: {result.stderr}")
            raise Exception(f"renderer failed: {result.stderr or result.stdout}")

        pdf_path = Path("out") / pdf_filename
        if not pdf_path.exists():
            raise Exception("pdf file not generated")

        # try s3 upload first, fallback to local storage
        if (
            AWS_S3_BUCKET
            and AWS_ACCESS_KEY_ID
            and AWS_SECRET_ACCESS_KEY
            and BOTO3_AVAILABLE
        ):
            try:
                s3_url = upload_to_s3(str(pdf_path), pdf_filename)
                # cleanup
                os.unlink(temp_json_path)
                pdf_path.unlink()
                return s3_url
            except Exception as e:
                app.logger.warning(f"s3 upload failed, using local storage: {e}")

        # fallback: keep file locally and return local path
        # cleanup temp json but keep pdf
        os.unlink(temp_json_path)

        # return local file path (in production, you'd want to serve this via your app)
        return f"local://{pdf_path}"

    except Exception as e:
        app.logger.error(f"pdf generation failed: {str(e)}")
        raise


def upload_to_s3(file_path: str, filename: str) -> str:
    """upload file to s3 and return signed url"""
    if not BOTO3_AVAILABLE:
        raise ImportError("boto3 not available")

    try:
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION,
        )

        # upload file
        s3_key = f"reports/{filename}"
        s3_client.upload_file(file_path, AWS_S3_BUCKET, s3_key)

        # generate signed url (valid for 7 days)
        signed_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": AWS_S3_BUCKET, "Key": s3_key},
            ExpiresIn=604800,  # 7 days
        )

        return signed_url

    except Exception as e:
        app.logger.error(f"s3 upload failed: {str(e)}")
        raise


def send_report_email(
    customer_email: str, pdf_url: str, company_name: str = "your organization"
) -> bool:
    """send transactional email with pdf link or attachment"""
    try:
        # try postmark first, fallback to resend
        if POSTMARK_API_TOKEN:
            return send_postmark_email(customer_email, pdf_url, company_name)
        elif RESEND_API_KEY:
            return send_resend_email(customer_email, pdf_url, company_name)
        else:
            app.logger.warning("no email service configured")
            return False

    except Exception as e:
        app.logger.error(f"email sending failed: {str(e)}")
        return False


def send_postmark_email(customer_email: str, pdf_url: str, company_name: str) -> bool:
    """send email via postmark with pdf link or attachment"""
    import requests
    import base64

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Postmark-Server-Token": POSTMARK_API_TOKEN,
    }

    # handle local files vs s3 urls
    if pdf_url.startswith("local://"):
        # for local files, we'll attach the PDF
        pdf_path = pdf_url.replace("local://", "")
        try:
            with open(pdf_path, "rb") as f:
                pdf_content = base64.b64encode(f.read()).decode("utf-8")

            attachments = [
                {
                    "Name": "calm_profile_report.pdf",
                    "Content": pdf_content,
                    "ContentType": "application/pdf",
                }
            ]

            download_text = (
                "your personalized diagnostic report is attached to this email."
            )
            download_link = ""
        except Exception as e:
            app.logger.error(f"failed to read local pdf: {e}")
            attachments = []
            download_text = "your personalized diagnostic report is ready, but there was an issue with the file."
            download_link = ""
    else:
        # s3 url - use download link
        attachments = []
        download_text = "your personalized diagnostic report is ready for download:"
        download_link = f'<p><a href="{pdf_url}" style="color: #00c9a7; text-decoration: none; font-weight: 500;">download report (pdf)</a></p>'

    data = {
        "From": "agent@syris.studio",
        "To": customer_email,
        "Subject": "your calm.profile diagnostic report",
        "HtmlBody": f"""
        <html>
        <body style="font-family: 'JetBrains Mono', monospace; color: #0a0a0a;">
            <h2 style="font-family: 'Inter', sans-serif; text-transform: lowercase;">your calm.profile diagnostic report</h2>
            
            <p>thank you for completing the calm.profile assessment for <strong>{company_name}</strong>.</p>
            
            <p>{download_text}</p>
            
            {download_link}
            
            <p>the report includes:</p>
            <ul>
                <li>behavioral archetype analysis</li>
                <li>productivity overhead assessment</li>
                <li>roi projections and sensitivity analysis</li>
                <li>prioritized recommendations</li>
                <li>30/60/90 implementation roadmap</li>
            </ul>
            
            <p>questions about your results? <a href="{CALENDLY_URL}" style="color: #00c9a7;">schedule a consultation</a></p>
            
            <p style="margin-top: 32px; font-size: 12px; color: #666666;">
                syrıs<span style="color: #00c9a7;">.</span> — calm in the chaos of creative work
            </p>
        </body>
        </html>
        """,
        "TextBody": f"""
        your calm.profile diagnostic report
        
        thank you for completing the calm.profile assessment for {company_name}.
        
        {download_text}
        {pdf_url if not pdf_url.startswith("local://") else "Report attached to this email."}
        
        the report includes:
        - behavioral archetype analysis
        - productivity overhead assessment  
        - roi projections and sensitivity analysis
        - prioritized recommendations
        - 30/60/90 implementation roadmap
        
        questions about your results? schedule a consultation: {CALENDLY_URL}
        
        syrıs. — calm in the chaos of creative work
        """,
    }

    # add attachments if we have them
    if attachments:
        data["Attachments"] = attachments

    response = requests.post(
        "https://api.postmarkapp.com/email", headers=headers, json=data
    )

    if response.status_code != 200:
        app.logger.error(
            f"Postmark API error: {response.status_code} - {response.text}"
        )

    return response.status_code == 200


def send_resend_email(customer_email: str, pdf_url: str, company_name: str) -> bool:
    """send email via resend"""
    import requests

    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "from": "reports@syris.studio",
        "to": [customer_email],
        "subject": "your calm.profile diagnostic report",
        "html": f"""
        <html>
        <body style="font-family: 'JetBrains Mono', monospace; color: #0a0a0a;">
            <h2 style="font-family: 'Inter', sans-serif; text-transform: lowercase;">your calm.profile diagnostic report</h2>
            
            <p>thank you for completing the calm.profile assessment for <strong>{company_name}</strong>.</p>
            
            <p>your personalized diagnostic report is ready for download:</p>
            
            <p><a href="{pdf_url}" style="color: #00c9a7; text-decoration: none; font-weight: 500;">download report (pdf)</a></p>
            
            <p>the report includes:</p>
            <ul>
                <li>behavioral archetype analysis</li>
                <li>productivity overhead assessment</li>
                <li>roi projections and sensitivity analysis</li>
                <li>prioritized recommendations</li>
                <li>30/60/90 implementation roadmap</li>
            </ul>
            
            <p>questions about your results? <a href="{CALENDLY_URL}" style="color: #00c9a7;">schedule a consultation</a></p>
            
            <p style="margin-top: 32px; font-size: 12px; color: #666666;">
                syrıs<span style="color: #00c9a7;">.</span> — calm in the chaos of creative work
            </p>
        </body>
        </html>
        """,
    }

    response = requests.post(
        "https://api.resend.com/emails", headers=headers, json=data
    )
    return response.status_code == 200


# ---------- health ----------


@app.get("/")
def root():
    app.logger.info("Root endpoint accessed")
    return _json({"service": "calm-profile-api", "status": "ok", "version": "1.1"})


@app.get("/health")
def health():
    app.logger.info("Health check requested")
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
    app.logger.info("Assessment submission received")
    if not score_assessment:
        app.logger.error("Scoring module not available")
        return _json(
            {"success": False, "error": "scoring module not available"}, status=500
        )

    try:
        payload = request.get_json(silent=True) or {}
        responses = payload.get("responses", {})
        context = payload.get(
            "context", {}
        )  # team_size, meeting_load, hourly_rate, platform
        email = payload.get("email")

        # normalize responses: convert string indices to int indices for questions 0-19
        normalized_responses = {}
        for i in range(20):
            response_value = responses.get(str(i), "")
            # Convert A/B to 1/0
            normalized_responses[str(i)] = (
                1 if str(response_value).upper() == "A" else 0
            )

        # run scorer
        result = score_assessment(normalized_responses)

        # overhead/roi calc
        meeting_map = {"light": 0.6, "moderate": 0.8, "heavy": 1.0}
        meeting_load = str(context.get("meeting_load", "moderate")).lower()
        overhead_base = meeting_map.get(meeting_load, 0.8)

        arche_adj = {
            "architect": 0.9,
            "conductor": 0.85,
            "curator": 1.1,
            "craftsperson": 1.2,
        }
        primary = str(result.get("archetype", {}).get("primary", "architect")).lower()
        overhead_index = overhead_base * arche_adj.get(primary, 1.0)

        team_mult = {"solo": 1, "2-5": 4, "6-15": 10, "16-50": 25, "50+": 55}
        team_size = str(context.get("team_size", "solo"))
        tm = team_mult.get(team_size, 1)

        hourly_rate = float(context.get("hourly_rate", 85))
        hours_lost_ppw = overhead_index * 5.0
        annual_cost = hours_lost_ppw * 52 * hourly_rate * tm

        # persist
        row = Assessment(
            email=email,
            data=json.dumps(
                {
                    "responses": normalized_responses,
                    "context": context,
                    "result": result,
                    "metrics": {
                        "hours_lost_ppw": hours_lost_ppw,
                        "annual_cost": annual_cost,
                        "overhead_index": overhead_index,
                    },
                }
            ),
        )
        g.db.add(row)
        g.db.commit()

        return _json(
            {
                "success": True,
                "assessment_id": row.id,
                "archetype": result.get("archetype", {}),
                "scores": {
                    "axes": result.get("scores", {}).get("axes", {}),
                    "overhead_index": round(overhead_index * 100),
                },
                "metrics": {
                    "hours_lost_ppw": round(hours_lost_ppw, 1),
                    "annual_cost": round(annual_cost),
                },
                "recommendations": result.get("recommendations", {}),
                "tagline": result.get("archetype", {}).get("tagline", ""),
            }
        )
    except Exception as e:
        g.db.rollback()
        app.logger.error(f"Assessment error: {str(e)}")
        return _json(
            {"success": False, "error": "Assessment processing failed"}, status=500
        )


# ---------- stripe checkout & webhooks ----------


# FIXED: Added /api/create-checkout endpoint that frontend expects
@app.post("/api/create-checkout")
def api_create_checkout():
    if not PRICE_ID:
        return _json({"error": "PRICE_ID not configured"}, status=500)

    try:
        payload = request.get_json(silent=True) or {}
        assessment_id = payload.get("assessment_id")
        email = payload.get("email")

        success_base = _frontend_base()
        success_url = f"{success_base}/thank-you?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{success_base}/"

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
            assessment_id=(
                int(assessment_id)
                if isinstance(assessment_id, (int, str))
                and str(assessment_id).isdigit()
                else None
            ),
            stripe_session_id=session.id,
            status=session.get("payment_status"),
            currency=session.get("currency"),
            amount_total=session.get("amount_total"),
            customer_email=(session.get("customer_details") or {}).get("email")
            or email,
        )
        g.db.add(pay)
        g.db.commit()

        # Return the expected field name
        return _json({"checkout_url": session.url})
    except Exception as e:
        g.db.rollback()
        app.logger.error(f"Checkout error: {str(e)}")
        return _json({"error": "Failed to create checkout session"}, status=400)


@app.post("/create-checkout-session")
def create_checkout_session():
    # Keep old endpoint for backwards compatibility
    return api_create_checkout()


@app.post("/webhooks/stripe")
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get("Stripe-Signature", "")

    if not STRIPE_WEBHOOK_SECRET:
        return _json({"error": "webhook secret not configured"}, status=500)

    try:
        event = stripe.Webhook.construct_event(
            payload=payload, sig_header=sig_header, secret=STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        return _json({"error": f"invalid signature: {e}"}, status=400)

    event_type = event["type"]
    event_id = event["id"]

    existing_event = g.db.execute(
        select(Payment).where(Payment.stripe_event_id == event_id)
    ).scalar_one_or_none()
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

            row = g.db.execute(
                select(Payment).where(Payment.stripe_session_id == session_id)
            ).scalar_one_or_none()
            if row:
                row.stripe_payment_intent = payment_intent
                row.amount_total = amount_total
                row.currency = currency
                row.status = status
                row.customer_email = row.customer_email or customer_email
                row.stripe_event_id = event_id
                if (
                    assessment_id
                    and not row.assessment_id
                    and str(assessment_id).isdigit()
                ):
                    row.assessment_id = int(assessment_id)
                g.db.commit()
            else:
                g.db.add(
                    Payment(
                        assessment_id=(
                            int(assessment_id)
                            if assessment_id and str(assessment_id).isdigit()
                            else None
                        ),
                        stripe_session_id=session_id,
                        stripe_payment_intent=payment_intent,
                        amount_total=amount_total,
                        currency=currency,
                        status=status,
                        customer_email=customer_email,
                        stripe_event_id=event_id,
                    )
                )
                g.db.commit()

        elif event_type in (
            "payment_intent.succeeded",
            "payment_intent.payment_failed",
        ):
            intent = event["data"]["object"]
            pi = intent.get("id")
            status = intent.get("status")
            amount = intent.get("amount")
            currency = intent.get("currency")
            email = (
                intent.get("charges", {}).get("data", [{}])[0].get("billing_details")
                or {}
            ).get("email")

            row = g.db.execute(
                select(Payment).where(Payment.stripe_payment_intent == pi)
            ).scalar_one_or_none()
            if row:
                row.status = status or row.status
                row.amount_total = amount or row.amount_total
                row.currency = currency or row.currency
                row.customer_email = row.customer_email or email
                row.stripe_event_id = event_id
                g.db.commit()
            else:
                g.db.add(
                    Payment(
                        stripe_payment_intent=pi,
                        amount_total=amount,
                        currency=currency,
                        status=status,
                        customer_email=email,
                        stripe_event_id=event_id,
                    )
                )
                g.db.commit()

        return _json({"received": True})
    except Exception as e:
        g.db.rollback()
        return _json({"error": str(e)}, status=500)


@app.post("/api/stripe/webhook")
def api_stripe_webhook():
    """new webhook endpoint for pdf generation and email"""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get("Stripe-Signature", "")

    if not STRIPE_WEBHOOK_SECRET:
        return _json({"error": "webhook secret not configured"}, status=500)

    try:
        event = stripe.Webhook.construct_event(
            payload=payload, sig_header=sig_header, secret=STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        return _json({"error": f"invalid signature: {e}"}, status=400)

    event_type = event["type"]
    event_id = event["id"]

    # check for duplicate events
    existing_event = g.db.execute(
        select(Payment).where(Payment.stripe_event_id == event_id)
    ).scalar_one_or_none()
    if existing_event:
        return _json({"received": True, "idempotent": True})

    try:
        if event_type == "checkout.session.completed":
            session_obj = event["data"]["object"]
            session_id = session_obj.get("id")
            customer_email = (session_obj.get("customer_details") or {}).get("email")
            assessment_id = session_obj.get("metadata", {}).get("assessment_id")

            if not customer_email:
                app.logger.error("no customer email in session")
                return _json({"error": "no customer email"}, status=400)

            if not assessment_id:
                app.logger.error("no assessment_id in session metadata")
                return _json({"error": "no assessment_id"}, status=400)

            # fetch assessment data
            assessment_row = g.db.execute(
                select(Assessment).where(Assessment.id == int(assessment_id))
            ).scalar_one_or_none()

            if not assessment_row:
                app.logger.error(f"assessment not found: {assessment_id}")
                return _json({"error": "assessment not found"}, status=404)

            # parse assessment data
            assessment_data = json.loads(assessment_row.data or "{}")

            # add metadata
            assessment_data.update(
                {
                    "company_name": "your organization",  # could be extracted from context
                    "assessment_date": assessment_row.created_at.strftime("%b %d, %Y"),
                    "report_id": f"report-{assessment_id}-{datetime.now().strftime('%Y%m%d')}",
                    "assessment_id": str(assessment_id),
                    "completion_date": assessment_row.created_at.strftime("%Y-%m-%d"),
                    "customer_email": customer_email,
                }
            )

            # validate and normalize assessment data (hard-fail on missing data)
            try:
                normalized_data = validate_and_normalize_assessment_data(
                    assessment_data
                )
            except ValueError as e:
                app.logger.error(f"Data validation failed: {e}")
                return _json({"error": f"Invalid assessment data: {e}"}, status=400)

            # generate pdf and get s3 url (locked pipeline order)
            pdf_url = generate_pdf_report(normalized_data, customer_email)

            # send email
            email_sent = send_report_email(
                customer_email,
                pdf_url,
                assessment_data.get("company_name", "your organization"),
            )

            if not email_sent:
                app.logger.warning(f"email failed to send for {customer_email}")

            # update payment record
            payment_row = g.db.execute(
                select(Payment).where(Payment.stripe_session_id == session_id)
            ).scalar_one_or_none()

            if payment_row:
                payment_row.stripe_event_id = event_id
                payment_row.status = "completed"
                g.db.commit()
            else:
                # create payment record if not exists
                g.db.add(
                    Payment(
                        assessment_id=int(assessment_id),
                        stripe_session_id=session_id,
                        stripe_event_id=event_id,
                        status="completed",
                        customer_email=customer_email,
                    )
                )
                g.db.commit()

            app.logger.info(
                f"report generated and emailed for assessment {assessment_id}"
            )
            return _json(
                {"received": True, "pdf_url": pdf_url, "email_sent": email_sent}
            )

        return _json({"received": True, "event_type": event_type})

    except Exception as e:
        g.db.rollback()
        app.logger.error(f"webhook processing failed: {str(e)}")
        return _json({"error": str(e)}, status=500)


# aliases for old paths
@app.get("/api/health")
def api_health_alias():
    return health()


@app.post("/api/create-checkout-session")
def api_checkout_session_alias():
    return api_create_checkout()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
