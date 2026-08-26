from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.orchestrator import ask_compliance_question
from app.config import settings
from app.workflow.graph import run_compliance_case
from app.workflow.state import create_case, get_case, update_case
from app.workflow.guardrails import check_grounding, needs_human_approval

router = APIRouter()


@router.get("/health")
def health_check() -> dict:
    return {"status": "ok", "env": settings.app_env}


class AskRequest(BaseModel):
    question: str


@router.post("/ask")
def ask(request: AskRequest) -> dict:
    return {"question": request.question, "answer": ask_compliance_question(request.question)}


class CaseRequest(BaseModel):
    question: str


@router.post("/cases")
def submit_case(request: CaseRequest) -> dict:
    case_id = create_case(request.question)
    result = run_compliance_case(request.question)

    grounded, reason = check_grounding(result["evidence"], result["findings"])
    if not grounded:
        update_case(case_id, status="BLOCKED", result=reason)
        return {"case_id": case_id, "status": "BLOCKED", "reason": reason}

    if needs_human_approval(result["findings"]):
        update_case(case_id, status="PENDING_APPROVAL", result=result["final_result"])
        return {"case_id": case_id, "status": "PENDING_APPROVAL"}

    update_case(case_id, status="DONE", result=result["final_result"])
    return {"case_id": case_id, "status": "DONE"}


@router.get("/cases/{case_id}")
def get_case_status(case_id: str) -> dict:
    case = get_case(case_id)
    if case is None:
        raise HTTPException(404, "Case not found")
    return case


class ApprovalRequest(BaseModel):
    decision: str  # APPROVE | REJECT


@router.post("/cases/{case_id}/approve")
def approve_case(case_id: str, request: ApprovalRequest) -> dict:
    case = get_case(case_id)
    if case is None:
        raise HTTPException(404, "Case not found")
    if case["status"] != "PENDING_APPROVAL":
        raise HTTPException(400, f"Case is not pending approval (status={case['status']})")
    if request.decision not in ("APPROVE", "REJECT"):
        raise HTTPException(400, "decision must be APPROVE or REJECT")

    new_status = "DONE" if request.decision == "APPROVE" else "REJECTED"
    update_case(case_id, status=new_status, approval_decision=request.decision)
    return {"case_id": case_id, "status": new_status}
