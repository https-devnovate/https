"""
SRMA Hindsight smoke test  (owner: WS-H).  NOT YET RUN against Cloud when this file was written.

Run:  pip install hindsight-client==1.2.0 && \
      HINDSIGHT_BASE_URL=https://api.hindsight.vectorize.io HINDSIGHT_API_KEY=... python spike/hindsight_smoke.py
Offline harness check (no network): python spike/hindsight_smoke.py --selftest

Safety: only ever touches banks named srma-spike-*; never deletes anything.
Output: spike/results/<timestamp>.json  (paste into docs/hindsight-spike-results.md; do NOT edit by hand)
Everything recorded is OBSERVED behaviour of the installed SDK + the live service; nothing is assumed.
"""
import asyncio, json, os, sys, time, uuid, traceback
from datetime import datetime, timezone
from types import SimpleNamespace

NARR_001 = """INCIDENT INC-001 - Intermittent DB connection timeouts in payment-service
Date: 2026-08-12 | Service: payment-service | Severity: SEV2 | Status: resolved
Symptoms: intermittent 30s timeouts acquiring DB connections; began ~2h after release 3.8.0.
Error messages: HikariPool-1 - Connection is not available, request timed out after 30000ms
Investigation steps: (1) DB CPU and slow-query check: ruled out. (2) Increased app pool 10->30: INEFFECTIVE, recurred in 6h. (3) Pod restart: temporary relief only.
Root cause (CONFIRMED, cause_key=commons-db-2.3.0-retry-leak): svc-commons-db 2.3.0 retry path leaks one connection per timeout.
Resolution (EFFECTIVE, verified): upgrade svc-commons-db to 2.3.1.
Record revision: 1"""
NARR_001_APPEND = "Addendum: INC-001 follow-up - audit showed inventory and auth services were also on 2.3.0.\nRecord revision: 2"
NARR_002 = NARR_001.replace("INC-001", "INC-002").replace("payment-service", "inventory-sync-worker").replace("Record revision: 1", "Record revision: 1")

def now(): return time.perf_counter()
def dump(o):
    for attr in ("model_dump",):
        if hasattr(o, attr):
            try: return o.model_dump(mode="json")
            except Exception: pass
    return repr(o)

async def timed(label, coro, out):
    t = now()
    try:
        r = await coro
        out[label] = {"ok": True, "latency_s": round(now() - t, 3), "result": dump(r)}
        return r
    except Exception as e:  # record exception type/status faithfully
        out[label] = {"ok": False, "latency_s": round(now() - t, 3), "exc_type": type(e).__name__,
                      "exc_module": type(e).__module__, "status": getattr(e, "status", None),
                      "body": (getattr(e, "body", None) or str(e))[:500]}
        return None

async def run(client, bank, empty_bank, out):
    out["meta"] = {"started": datetime.now(timezone.utc).isoformat(), "bank": bank}
    try:
        import hindsight_client; out["meta"]["sdk_version"] = getattr(hindsight_client, "__version__", "see pip show")
    except Exception: pass
    await timed("S0_version", client.aget_version(), out)
    await timed("S1_create_bank", client.acreate_bank(bank_id=bank,
        reflect_mission="You analyse resolved production incidents. Prefer evidence over speculation; distinguish confirmed from suspected causes; cite incident IDs.",
        retain_mission="Extract incident facts: service, symptoms, error messages, failed fixes, root cause (note confirmed vs suspected), resolution and outcome. Always keep incident IDs (INC-###) in every fact."), out)
    # S2 sync retain + latency + response shape
    meta = {"incident_id": "INC-001", "service": "payment-service", "root_cause_status": "confirmed"}
    await timed("S2_retain_sync", client.aretain(bank_id=bank, content=NARR_001, context="resolved production incident record",
        timestamp="2026-08-12T10:00:00Z", document_id="INC-001", metadata=meta, tags=["incident:INC-001"]), out)
    # S3 immediate recallability: poll until first hit (cap 90s)
    t0, hits, polls = now(), None, []
    while now() - t0 < 90:
        r = await client.arecall(bank_id=bank, query="connection pool timeouts after release", max_tokens=2048)
        polls.append({"t": round(now() - t0, 2), "n": len(r.results)})
        if r.results: hits = r; break
        await asyncio.sleep(2)
    out["S3_recallability"] = {"polls": polls, "first_hit_after_s": polls[-1]["t"] if hits else None,
                               "hits": [dump(h) for h in (hits.results if hits else [])]}
    # S4 provenance fields on every hit
    if hits:
        out["S4_provenance"] = [{"id": h.id, "type": h.type, "document_id": h.document_id, "metadata": h.metadata, "tags": h.tags,
                                 "scores": dump(h.scores) if h.scores else None, "text": h.text[:200]} for h in hits.results]
    # S5 duplicate document_id (replace) + append
    async def count(): 
        l = await client.alist_memories(bank_id=bank, document_id="INC-001", limit=100); return l.total
    out["S5_counts"] = {"after_first_retain": await count()}
    await timed("S5_retain_replace", client.aretain(bank_id=bank, content=NARR_001, document_id="INC-001", update_mode="replace", metadata=meta), out)
    out["S5_counts"]["after_replace_same_content"] = await count()
    await timed("S5_retain_append", client.aretain(bank_id=bank, content=NARR_001_APPEND, document_id="INC-001", update_mode="append", metadata=meta), out)
    out["S5_counts"]["after_append"] = await count()
    # S5b: replace with CHANGED content (a root-cause correction) -> are old facts gone from recall?
    rev = NARR_001.replace("svc-commons-db 2.3.0 retry path leaks one connection per timeout.",
        "REVISED: PgBouncer default_pool_size too small (supersedes earlier retry-leak theory).").replace("Record revision: 1", "Record revision: 3")
    await timed("S5b_retain_replace_changed", client.aretain(bank_id=bank, content=rev, document_id="INC-001", update_mode="replace", metadata=meta), out)
    rr = await client.arecall(bank_id=bank, query="svc-commons-db retry path leaks one connection per timeout", max_tokens=2048)
    out["S5b_stale_check"] = {"count_after": await count(), "hit_texts": [h.text[:160] for h in rr.results],
                              "types": [h.type for h in rr.results]}
    # S6 async retain with caller-supplied operation_id, twice (idempotency), then poll status
    op = str(uuid.uuid4())
    r1 = await timed("S6_retain_async_1", client.aretain(bank_id=bank, content=NARR_002, document_id="INC-002", retain_async=True, operation_id=op,
                     metadata={"incident_id": "INC-002"}), out)
    await timed("S6_retain_async_dup_same_operation_id", client.aretain(bank_id=bank, content=NARR_002, document_id="INC-002", retain_async=True, operation_id=op,
                metadata={"incident_id": "INC-002"}), out)
    t0, status_log = now(), []
    while now() - t0 < 120:
        try:
            s = await client.operations.get_operation_status(bank_id=bank, operation_id=op)
            status_log.append({"t": round(now() - t0, 1), "status": s.status})
            if s.status in ("completed", "failed", "cancelled"): break
        except Exception as e:
            status_log.append({"t": round(now() - t0, 1), "exc": type(e).__name__, "status": getattr(e, "status", None)}); break
        await asyncio.sleep(3)
    out["S6_operation_polling"] = status_log
    # S7 consolidation (observations) timing: pending/done
    t0, cons = now(), []
    while now() - t0 < 90:
        l = await client.alist_memories(bank_id=bank, limit=100)
        cons.append({"t": round(now() - t0, 1), "total": l.total}); 
        p = await client.alist_memories(bank_id=bank, consolidation_state="pending", limit=1)
        cons[-1]["pending"] = p.total
        if p.total == 0: break
        await asyncio.sleep(5)
    out["S7_consolidation"] = cons
    # S8 reflect: free text + structured_output + based_on
    schema = {"type": "object", "properties": {"patterns": {"type": "array", "items": {"type": "object", "properties": {
        "title": {"type": "string"}, "statement": {"type": "string"},
        "supporting_incident_ids": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]}}, "required": ["title", "statement", "supporting_incident_ids"]}}},
        "required": ["patterns"]}
    q = "Across all resolved incidents, what failure patterns recur across different services? List incident IDs, ineffective fixes and what to check first. Distinguish confirmed from suspected causes."
    await timed("S8_reflect", client.areflect(bank_id=bank, query=q, budget="mid", include_facts=True, response_schema=schema), out)
    # S9 empty bank behaviour
    await timed("S9_recall_empty_bank", client.arecall(bank_id=empty_bank, query="connection timeouts"), out)
    await timed("S9_reflect_empty_bank", client.areflect(bank_id=empty_bank, query=q), out)
    # S10 error shapes: bad key
    bad = type(client)(base_url=client._base_url if hasattr(client, "_base_url") else os.environ["HINDSIGHT_BASE_URL"], api_key="invalid-key", max_attempts=1) if not isinstance(client, SimpleNamespace) else client
    await timed("S10_bad_api_key_recall", bad.arecall(bank_id=bank, query="x"), out)
    out["meta"]["finished"] = datetime.now(timezone.utc).isoformat()

class FakeClient(SimpleNamespace):
    """selftest only: proves the harness logic runs; says NOTHING about Hindsight."""
    async def _m(self, **k): return SimpleNamespace(model_dump=lambda mode=None: {"fake": True}, results=[SimpleNamespace(id="m1", type="world", text="t"*5, document_id="INC-001", metadata={}, tags=[], scores=None, model_dump=lambda mode=None: {})], total=1, status="completed")
    def __getattr__(self, n):
        if n.startswith("a"): return self._m
        raise AttributeError(n)

async def main():
    selftest = "--selftest" in sys.argv
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    bank, empty = f"srma-spike-{stamp}", f"srma-spike-{stamp}-empty"
    assert bank.startswith("srma-spike-") and empty.startswith("srma-spike-")
    if selftest:
        client = FakeClient(operations=SimpleNamespace(get_operation_status=lambda **k: asyncio.sleep(0, SimpleNamespace(status="completed"))))
    else:
        from hindsight_client import Hindsight
        client = Hindsight(base_url=os.environ["HINDSIGHT_BASE_URL"], api_key=os.environ["HINDSIGHT_API_KEY"], timeout=120.0)
    out = {}
    try: await run(client, bank, empty, out)
    except Exception: out["harness_error"] = traceback.format_exc()
    finally:
        if not selftest: await client.aclose()
    os.makedirs("spike/results", exist_ok=True)
    path = f"spike/results/{'SELFTEST-' if selftest else ''}{stamp}.json"
    json.dump(out, open(path, "w"), indent=2, default=str)
    print("wrote", path, "| harness_error:", "harness_error" in out)

if __name__ == "__main__": asyncio.run(main())
