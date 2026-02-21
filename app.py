from datetime import datetime, timezone

def now_iso():
    return datetime.now(timezone.utc).isoformat()

@app.post("/orchestrator")
def orchestrator(request: Request):
    trace = []
    t0 = now_iso()

    # 1) Collector
    trace.append({"ts": now_iso(), "agent": "collector", "action": "start"})
    collector_out = collector(Msg())
    trace.append({
        "ts": now_iso(),
        "agent": "collector",
        "action": "done",
        "summary": f"collected {len(collector_out.get('threats', []))} threats"
    })

    # 2) Enricher
    trace.append({"ts": now_iso(), "agent": "enricher", "action": "start"})
    enricher_out = enricher(Msg(**collector_out))
    trace.append({
        "ts": now_iso(),
        "agent": "enricher",
        "action": "done",
        "summary": "added severity/context"
    })

    # 3) Reporter
    trace.append({"ts": now_iso(), "agent": "reporter", "action": "start"})
    reporter_out = reporter(Msg(**enricher_out))
    trace.append({
        "ts": now_iso(),
        "agent": "reporter",
        "action": "done",
        "summary": "generated SOC-style report"
    })

    return {
        "meta": {
            "service": "nanda-cti-swarm",
            "run_started_utc": t0,
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
