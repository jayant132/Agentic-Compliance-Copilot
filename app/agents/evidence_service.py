from fastapi import FastAPI
from pydantic import BaseModel
from app.agents.evidence_agent import get_evidence

app = FastAPI(title="Evidence Agent Service")

class EvidenceRequest(BaseModel):
    question: str

@app.post("/a2a/evidence")
def a2a_get_evidence(req: EvidenceRequest) -> dict:
    return {"evidence": get_evidence(req.question)}
