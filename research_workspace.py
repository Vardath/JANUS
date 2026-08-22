"""Epistemically typed research workspace for the JANUS programme.

This layer keeps proved mathematics, empirical findings, hypotheses, open questions,
proposed tests and negative results distinct. It is deliberately evidence-led: adding
an observation does not silently upgrade a hypothesis, and closing a question does
not erase the audit trail.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

import auth
import continuity_ledger

DB_PATH = os.getenv("JANUS_DB_PATH", "/data/janus.sqlite3")
router = APIRouter(prefix="/research", tags=["research"])

CLAIM_KINDS = {
    "theorem", "definition", "derivation", "empirical_finding", "hypothesis",
    "interpretation", "open_question", "proposed_test", "prediction",
    "negative_result", "boundary", "reference",
}
EPISTEMIC_STATES = {
    "established", "audited", "supported", "provisional", "open", "untested",
    "inconclusive", "contradicted", "falsified", "closed_negative", "deferred",
}
EVIDENCE_KINDS = {"proof", "calculation", "simulation", "measurement", "source", "counterexample", "null_result", "critique", "replication"}
RELATIONS = {"supports", "challenges", "tests", "derives", "depends_on", "supersedes", "clarifies", "bounds", "contradicts"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db() -> sqlite3.Connection:
    db = sqlite3.connect(DB_PATH, timeout=20)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    ensure_schema(db)
    return db


def ensure_schema(db: sqlite3.Connection | None = None) -> None:
    own = db is None
    db = db or sqlite3.connect(DB_PATH, timeout=20)
    db.executescript("""
    CREATE TABLE IF NOT EXISTS janus_research_claims(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      profile_id TEXT NOT NULL,
      programme TEXT NOT NULL DEFAULT 'JANUS',
      title TEXT NOT NULL,
      statement TEXT NOT NULL,
      claim_kind TEXT NOT NULL,
      epistemic_state TEXT NOT NULL,
      domain TEXT NOT NULL DEFAULT 'general',
      continuity_item_id INTEGER,
      source_label TEXT NOT NULL DEFAULT '',
      tags_json TEXT NOT NULL DEFAULT '[]',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_research_claim_profile ON janus_research_claims(profile_id,programme,domain,updated_at DESC);
    CREATE TABLE IF NOT EXISTS janus_research_evidence(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      profile_id TEXT NOT NULL,
      claim_id INTEGER NOT NULL,
      evidence_kind TEXT NOT NULL,
      summary TEXT NOT NULL,
      source_uri TEXT NOT NULL DEFAULT '',
      result TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL,
      FOREIGN KEY(claim_id) REFERENCES janus_research_claims(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_research_evidence_claim ON janus_research_evidence(profile_id,claim_id,created_at DESC);
    CREATE TABLE IF NOT EXISTS janus_research_relations(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      profile_id TEXT NOT NULL,
      from_claim_id INTEGER NOT NULL,
      to_claim_id INTEGER NOT NULL,
      relation TEXT NOT NULL,
      note TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL,
      UNIQUE(profile_id,from_claim_id,to_claim_id,relation)
    );
    """)
    db.commit()
    if own:
        db.close()


def _validate(kind: str, state: str) -> None:
    if kind not in CLAIM_KINDS:
        raise ValueError(f"unsupported claim kind: {kind}")
    if state not in EPISTEMIC_STATES:
        raise ValueError(f"unsupported epistemic state: {state}")


def add_claim(profile_id: str, title: str, statement: str, claim_kind: str, epistemic_state: str, *,
              domain: str = "general", programme: str = "JANUS", source_label: str = "",
              tags: list[str] | tuple[str, ...] = (), continuity_item_id: int | None = None) -> dict[str, Any]:
    _validate(claim_kind, epistemic_state)
    title = " ".join((title or "").split()).strip()
    statement = (statement or "").strip()
    if not profile_id or not title or not statement:
        raise ValueError("profile_id, title and statement are required")
    now = _now()
    with _db() as db:
        cur = db.execute("""INSERT INTO janus_research_claims
          (profile_id,programme,title,statement,claim_kind,epistemic_state,domain,continuity_item_id,source_label,tags_json,created_at,updated_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
          (profile_id, programme, title, statement, claim_kind, epistemic_state, domain,
           continuity_item_id, source_label, json.dumps(sorted(set(tags))), now, now))
        claim_id = int(cur.lastrowid)
        db.commit()
    return get_claim(profile_id, claim_id)


def get_claim(profile_id: str, claim_id: int) -> dict[str, Any]:
    with _db() as db:
        row = db.execute("SELECT * FROM janus_research_claims WHERE profile_id=? AND id=?", (profile_id, claim_id)).fetchone()
        if not row:
            raise KeyError(claim_id)
        ev = db.execute("SELECT * FROM janus_research_evidence WHERE profile_id=? AND claim_id=? ORDER BY id", (profile_id, claim_id)).fetchall()
    out = dict(row)
    out["tags"] = json.loads(out.pop("tags_json") or "[]")
    out["evidence"] = [dict(x) for x in ev]
    return out


def update_epistemic_state(profile_id: str, claim_id: int, state: str, note: str = "") -> dict[str, Any]:
    if state not in EPISTEMIC_STATES:
        raise ValueError(f"unsupported epistemic state: {state}")
    with _db() as db:
        row = db.execute("SELECT id FROM janus_research_claims WHERE profile_id=? AND id=?", (profile_id, claim_id)).fetchone()
        if not row:
            raise KeyError(claim_id)
        db.execute("UPDATE janus_research_claims SET epistemic_state=?,updated_at=? WHERE profile_id=? AND id=?", (state, _now(), profile_id, claim_id))
        if note:
            db.execute("INSERT INTO janus_research_evidence(profile_id,claim_id,evidence_kind,summary,result,created_at) VALUES(?,?,?,?,?,?)",
                       (profile_id, claim_id, "critique", note[:4000], f"state -> {state}", _now()))
        db.commit()
    return get_claim(profile_id, claim_id)


def add_evidence(profile_id: str, claim_id: int, evidence_kind: str, summary: str, *, source_uri: str = "", result: str = "") -> dict[str, Any]:
    if evidence_kind not in EVIDENCE_KINDS:
        raise ValueError(f"unsupported evidence kind: {evidence_kind}")
    with _db() as db:
        if not db.execute("SELECT 1 FROM janus_research_claims WHERE profile_id=? AND id=?", (profile_id, claim_id)).fetchone():
            raise KeyError(claim_id)
        cur = db.execute("INSERT INTO janus_research_evidence(profile_id,claim_id,evidence_kind,summary,source_uri,result,created_at) VALUES(?,?,?,?,?,?,?)",
                         (profile_id, claim_id, evidence_kind, summary[:12000], source_uri[:2000], result[:4000], _now()))
        db.commit()
        evidence_id = int(cur.lastrowid)
    return {"id": evidence_id, "claim_id": claim_id, "evidence_kind": evidence_kind, "summary": summary, "source_uri": source_uri, "result": result}


def relate(profile_id: str, from_claim_id: int, to_claim_id: int, relation: str, note: str = "") -> dict[str, Any]:
    if relation not in RELATIONS:
        raise ValueError(f"unsupported relation: {relation}")
    with _db() as db:
        rows = db.execute("SELECT id FROM janus_research_claims WHERE profile_id=? AND id IN (?,?)", (profile_id, from_claim_id, to_claim_id)).fetchall()
        if len(rows) != 2:
            raise KeyError("one or both research claims are unavailable")
        db.execute("INSERT OR IGNORE INTO janus_research_relations(profile_id,from_claim_id,to_claim_id,relation,note,created_at) VALUES(?,?,?,?,?,?)",
                   (profile_id, from_claim_id, to_claim_id, relation, note[:4000], _now()))
        db.commit()
    return {"from_claim_id": from_claim_id, "to_claim_id": to_claim_id, "relation": relation, "note": note}


def list_claims(profile_id: str, *, programme: str = "JANUS", domain: str | None = None, state: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
    clauses = ["profile_id=?", "programme=?"]
    args: list[Any] = [profile_id, programme]
    if domain:
        clauses.append("domain=?"); args.append(domain)
    if state:
        clauses.append("epistemic_state=?"); args.append(state)
    args.append(max(1, min(500, int(limit))))
    with _db() as db:
        rows = db.execute(f"SELECT * FROM janus_research_claims WHERE {' AND '.join(clauses)} ORDER BY domain, id LIMIT ?", args).fetchall()
    out=[]
    for row in rows:
        d=dict(row); d["tags"]=json.loads(d.pop("tags_json") or "[]"); out.append(d)
    return out


def workspace_context(profile_id: str, limit: int = 28) -> str:
    claims = list_claims(profile_id, limit=limit)
    if not claims:
        return "No JANUS research workspace has been seeded for this profile."
    order = {"established":0,"audited":1,"closed_negative":2,"contradicted":3,"falsified":4,"supported":5,"provisional":6,"open":7,"untested":8,"inconclusive":9,"deferred":10}
    claims.sort(key=lambda c: (order.get(c["epistemic_state"], 99), c["domain"], c["id"]))
    lines=["JANUS research workspace — preserve these epistemic labels exactly:"]
    for c in claims[:limit]:
        lines.append(f"- [{c['epistemic_state']} | {c['claim_kind']} | {c['domain']}] {c['title']}: {c['statement'][:360]}")
    lines.append("Do not present hypotheses/interpretations as established physics; negative results remain informative results.")
    return "\n".join(lines)


SEED_CLAIMS = [
    ("Closed JANUS mathematical core", "The audited finite mathematical core consists of exact algebraic/combinatorial structures; it is not by itself a physical cosmology.", "theorem", "audited", "mathematics", ["closed-core","boundary"]),
    ("Canonical Q operator", "For Q=[[-1,7],[1,-7]], Q^2=-8Q, with kernel direction (7,1) and active direction (-1,1).", "derivation", "established", "mathematics", ["operator","1-7"]),
    ("Steane/Fano realization", "The three-qubit Hamming/Steane syndrome construction gives an exact finite realization of the seven nonzero F2^3 directions and associated coarse JANUS/Fano projections.", "derivation", "audited", "quantum-information", ["Steane","Fano"]),
    ("Passive symmetric energy barrier result", "With the maximally symmetric seven-check Steane/Fano Z Hamiltonian, all nonzero X-error syndromes have the same excitation gap and a weight-3 logical path can cross without a growing barrier; this candidate does not yield self-correction.", "negative_result", "closed_negative", "qec-thermodynamics", ["passive-qec","negative-result"]),
    ("Solar-system literal realization", "The tested literal Solar-System mapping did not naturally realize the required Fano/JANUS dynamics and is closed as a literal physical realization.", "negative_result", "closed_negative", "physical-tests", ["astronomy","negative-result"]),
    ("Planck/fine-structure derivation", "Simple Planck-offset substitutions do not derive the fine-structure constant; offsets cancel and the natural dimensionless quantity is model-dependent.", "negative_result", "closed_negative", "physical-tests", ["fine-structure","negative-result"]),
    ("Physical dictionary", "What precise physical quantities, fields, observables or states correspond to the finite JANUS structures?", "open_question", "open", "physical-bridge", ["priority","falsifiability"]),
    ("Distinctive observable", "Find an observable or numerical prediction that distinguishes a JANUS physical interpretation from ordinary coding theory, symmetry mathematics or generic decoherence.", "open_question", "open", "physical-bridge", ["priority","prediction"]),
    ("Dynamics/locality bridge", "Can a concrete dynamical model recover continuous evolution, locality and known-physics limits from the finite structure without inserting them by hand?", "open_question", "open", "physical-bridge", ["dynamics","locality"]),
    ("Alternative passive interaction families", "Test whether any physically local, nontrivial interaction family produces a meaningful encoded energy barrier without relying on the already-closed symmetric flat-gap construction.", "proposed_test", "untested", "qec-thermodynamics", ["passive-qec","test"]),
    ("Unequal orientation ensemble", "Test unequal Fano/orientation weights and determine which conclusions survive symmetry breaking and which are artifacts of the uniform ensemble.", "proposed_test", "untested", "mathematics", ["orientation","robustness"]),
    ("Order-4 and trinity closure", "Audit the role of order-4 automorphisms and the three primitive 4|4 involutions without treating numerical recurrence as physical evidence.", "proposed_test", "untested", "mathematics", ["order-4","trinity"]),
    ("Higher-r family", "Audit the r>3 symplectic/quadratic generalization and identify which exceptional properties are genuinely specific to r=3.", "proposed_test", "untested", "mathematics", ["higher-r","uniqueness"]),
    ("Cosmological interpretation boundary", "The user's enclosed-world cosmological model is a separate interpretive model that may motivate questions but is not established by the Closed JANUS mathematical theorem.", "boundary", "audited", "cosmology", ["epistemic-boundary"]),
]


def seed_janus_program(profile_id: str) -> dict[str, Any]:
    existing = {c["title"].lower(): c for c in list_claims(profile_id, limit=500)}
    created=[]
    for title, statement, kind, state, domain, tags in SEED_CLAIMS:
        if title.lower() in existing:
            continue
        continuity_id = None
        if kind in {"open_question", "proposed_test"}:
            ci = continuity_ledger.upsert_open(profile_id, "question" if kind == "open_question" else "research", title, statement,
                                               state="investigating" if kind == "open_question" else "proposed",
                                               priority=80 if "priority" in tags else 60, source="research_workspace", tags=tags)
            continuity_id = ci["id"]
        created.append(add_claim(profile_id, title, statement, kind, state, domain=domain,
                                 source_label="JANUS audited project checkpoint", tags=tags, continuity_item_id=continuity_id))
    return {"ok": True, "created": len(created), "total": len(list_claims(profile_id, limit=500)), "claims": created}


class ClaimRequest(BaseModel):
    title: str
    statement: str
    claim_kind: str
    epistemic_state: str = "open"
    domain: str = "general"
    tags: list[str] = []


class EvidenceRequest(BaseModel):
    evidence_kind: str
    summary: str
    source_uri: str = ""
    result: str = ""


def _account(authorization: Optional[str]):
    account = auth.require_account(authorization)
    if not account:
        raise HTTPException(401, "authentication required")
    return account


@router.post("/workspace/seed")
def seed_workspace(authorization: Optional[str] = Header(default=None)):
    account=_account(authorization)
    return seed_janus_program(str(account["username"]))


@router.get("/workspace")
def get_workspace(domain: Optional[str] = None, state: Optional[str] = None, authorization: Optional[str] = Header(default=None)):
    account=_account(authorization)
    claims=list_claims(str(account["username"]), domain=domain, state=state)
    return {"ok": True, "claims": claims, "count": len(claims)}


@router.post("/claims")
def create_claim(req: ClaimRequest, authorization: Optional[str] = Header(default=None)):
    account=_account(authorization)
    try:
        claim=add_claim(str(account["username"]), req.title, req.statement, req.claim_kind, req.epistemic_state, domain=req.domain, tags=req.tags, source_label="user/JANUS workspace")
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"ok": True, "claim": claim}


@router.post("/claims/{claim_id}/evidence")
def create_evidence(claim_id: int, req: EvidenceRequest, authorization: Optional[str] = Header(default=None)):
    account=_account(authorization)
    try:
        evidence=add_evidence(str(account["username"]), claim_id, req.evidence_kind, req.summary, source_uri=req.source_uri, result=req.result)
    except KeyError:
        raise HTTPException(404, "research claim not found")
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"ok": True, "evidence": evidence}
