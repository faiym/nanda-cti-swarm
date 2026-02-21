from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.responses import PlainTextResponse
import uuid

app = FastAPI()

class Msg(BaseModel):
    job_id: str | None = None
    threats: list[dict] | None = None

@app.get("/")
def root():
    return {"status": "ok", "service": "nanda-cti-swarm"}

@app.post("/collector")
def collector(msg: Msg):
    job_id = msg.job_id or f"demo-{uuid.uuid4().hex[:6]}"
    return {
        "job_id": job_id,
        "threats":[
            {"id":"CVE-TEST-001","summary":"RCE in web service"},
            {"id":"CVE-TEST-002","summary":"Auth bypass"}
        ]
    }

@app.post("/enricher")
def enricher(msg: Msg):
    out=[]
    for t in msg.threats or []:
        sev="HIGH" if "RCE" in t["summary"] else "MEDIUM"
        out.append({**t,"severity":sev})
    return {"job_id":msg.job_id,"threats":out}

@app.post("/reporter")
def reporter(msg: Msg):
    lines=["CTI REPORT"]
    for t in msg.threats or []:
        lines.append(f"{t['id']} {t['severity']} {t['summary']}")
    return {"job_id":msg.job_id,"report":"\n".join(lines)}

@app.post("/orchestrator")
def orchestrator(request: Request):
    # internal calls (same app)
    job = collector(Msg())
    enriched = enricher(Msg(**job))
    report = reporter(Msg(**enriched))
    return report

@app.get("/skill.md", response_class=PlainTextResponse)
def skill():
    return """
# Autonomous Cyber Threat Intelligence Swarm

Agents:
collector -> generates threats
enricher -> adds severity
reporter -> outputs SOC report
orchestrator -> runs workflow
"""
