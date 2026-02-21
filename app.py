from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from datetime import datetime
import uuid
import os

app = FastAPI(title="NANDA CTI Swarm", version="1.0.0")


# -----------------------------
# Models
# -----------------------------
class Msg(BaseModel):
    job_id: str | None = None
    threats: list[dict] | None = None


def now_iso() -> str:
    # Simple + reliable UTC timestamp
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


# -----------------------------
# Root (health check)
# -----------------------------
@app.get("/")
def home():
    return {
        "status": "ok",
        "service": "nanda-cti-swarm",
        "endpoints": ["/collector", "/enricher", "/reporter", "/orchestrator", "/skill.md", "/docs", "/openapi.json"],
    }


# -----------------------------
# Agent 1: Collector
# -----------------------------
@app.post("/collector")
def collector(msg: Msg):
    job_id = msg.job_id or f"demo-{uuid.uuid4().hex[:6]}"
    threats = [
        {"id": "CVE-TEST-001", "summary": "RCE in web service"},
        {"id": "CVE-TEST-002", "summary": "Auth bypass"},
    ]
    return {"job_id": job_id, "threats": threats}


# -----------------------------
# Agent 2: Enricher
# -----------------------------
@app.post("/enricher")
def enricher(msg: Msg):
    out = []
    for t in (msg.threats or []):
        sev = "HIGH" if "RCE" in t.get("summary", "") else "MEDIUM"
        out.append(
            {
                **t,
                "severity": sev,
                "mitre": ["T1190"] if sev == "HIGH" else ["T1078"],
                "recommended_action": "Patch + restrict exposure" if sev == "HIGH" else "Review auth + monitor logs",
            }
        )
    return {"job_id": msg.job_id, "threats": out}


# -----------------------------
# Agent 3: Reporter
# -----------------------------
@app.post("/reporter")
def reporter(msg: Msg):
    lines = [f"CTI REPORT ({msg.job_id})", "Findings:"]
    for t in (msg.threats or []):
        lines.append(
            f"- {t['id']} | {t.get('severity')} | {t.get('summary')} | "
            f"{t.get('recommended_action')} | MITRE {','.join(t.get('mitre', []))}"
        )
    lines.append("Next steps: prioritize HIGH items within 24 hours, validate exposure, and monitor related logs.")
    return {"job_id": msg.job_id, "report": "\n".join(lines)}


# -----------------------------
# Agent 4: Orchestrator (UPGRADED OUTPUT)
# -----------------------------
@app.post("/orchestrator")
def orchestrator(request: Request):
    trace = []
    started = now_iso()

    trace.append({"ts": now_iso(), "agent": "collector", "action": "start"})
    collector_out = collector(Msg())
    trace.append(
        {
            "ts": now_iso(),
            "agent": "collector",
            "action": "done",
            "summary": f"collected {len(collector_out.get('threats', []))} threats",
        }
    )

    trace.append({"ts": now_iso(), "agent": "enricher", "action": "start"})
    enricher_out = enricher(Msg(**collector_out))
    trace.append({"ts": now_iso(), "agent": "enricher", "action": "done", "summary": "added severity/context"})

    trace.append({"ts": now_iso(), "agent": "reporter", "action": "start"})
    reporter_out = reporter(Msg(**enricher_out))
    trace.append({"ts": now_iso(), "agent": "reporter", "action": "done", "summary": "generated SOC-style report"})

    return {
        "meta": {
            "service": "nanda-cti-swarm",
            "run_started_utc": started,
            "run_finished_utc": now_iso(),
            "workflow": ["collector", "enricher", "reporter"],
        },
        "job_id": reporter_out.get("job_id"),
        "final_report": reporter_out.get("report"),
        "agent_outputs": {
            "collector": collector_out,
            "enricher": enricher_out,
            "reporter": reporter_out,
        },
        "trace": trace,
    }


# -----------------------------
# Skill discovery
# -----------------------------
@app.get("/skill.md", response_class=PlainTextResponse)
def get_skill():
    # Prefer reading local file if it exists
    if os.path.exists("skill.md"):
        with open("skill.md", "r", encoding="utf-8") as f:
            return f.read()

    # Fallback text (so endpoint never breaks)
    return """# Autonomous Cyber Threat Intelligence Swarm

This is a distributed multi-agent CTI workflow demonstrating discovery, orchestration, and collaboration.

Agents:
- collector: generates threat indicators
- enricher: adds severity + context
- reporter: produces SOC-style report
- orchestrator: coordinates the workflow
"""
