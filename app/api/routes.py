import logging
from fastapi import APIRouter, Depends, HTTPException
from app.models.schemas import (
    StructuredInteractionRequest,
    LogInteractionRequest,
    EditInteractionRequest,
    ChatRequest,
    SummarizeRequest,
    DoctorCreate,
    FollowUpCreate,
    FollowUpUpdate,
    FormatNotesRequest,
)
from app.services import crm_service, ai_service, queue_service, metrics_service
from app.core.auth import get_current_user
from app.core.rate_limit import rate_limit

router = APIRouter()
logger = logging.getLogger(__name__)

_SAFE_ERROR = "Something went wrong, please try again"


@router.get("/")
def root():
    return {"message": "CRM backend is running"}


@router.get("/interactions")
def get_interactions(user: dict = Depends(get_current_user)):
    try:
        return crm_service.get_interactions(user["id"])
    except Exception:
        logger.error("GET /interactions failed", exc_info=True)
        raise HTTPException(status_code=500, detail=_SAFE_ERROR)


@router.post("/log-structured-interaction")
def log_structured_interaction(
    body: StructuredInteractionRequest,
    user: dict = Depends(get_current_user),
):
    if not body.doctor_name.strip():
        raise HTTPException(status_code=400, detail="doctor_name is required")
    try:
        new_id = crm_service.log_structured_interaction(
            doctor_name=body.doctor_name.strip(),
            interaction_type=body.interaction_type,
            notes=body.notes,
            attendees=body.attendees,
            products_discussed=body.products_discussed,
            sentiment=body.sentiment,
            follow_up=body.follow_up,
            date_time=body.date_time,
            user_id=user["id"],
        )
        return {"message": "Interaction logged", "id": new_id}
    except Exception:
        logger.error("POST /log-structured-interaction failed", exc_info=True)
        raise HTTPException(status_code=500, detail=_SAFE_ERROR)


@router.post("/log-interaction")
def log_interaction(body: LogInteractionRequest, user: dict = Depends(get_current_user)):
    try:
        new_id = crm_service.log_interaction_basic(body.doctor_name, body.notes, user["id"])
        return {"message": "Interaction logged", "id": new_id}
    except Exception:
        logger.error("POST /log-interaction failed", exc_info=True)
        raise HTTPException(status_code=500, detail=_SAFE_ERROR)


@router.post("/edit-interaction")
def edit_interaction(body: EditInteractionRequest, user: dict = Depends(get_current_user)):
    try:
        updated = crm_service.edit_interaction_basic(body.id, body.notes, user["id"])
        if not updated:
            raise HTTPException(status_code=404, detail=f"No interaction found with id {body.id}")
        return {"message": "Interaction updated", "id": body.id}
    except HTTPException:
        raise
    except Exception:
        logger.error("POST /edit-interaction failed", exc_info=True)
        raise HTTPException(status_code=500, detail=_SAFE_ERROR)


@router.post("/chat")
def chat(body: ChatRequest, user: dict = Depends(rate_limit)):
    try:
        response = ai_service.chat(body.message, user["id"], history=body.history)
        return {"response": response}
    except Exception:
        logger.error("POST /chat failed", exc_info=True)
        raise HTTPException(status_code=500, detail=_SAFE_ERROR)


@router.post("/format-notes")
def format_notes(body: FormatNotesRequest, user: dict = Depends(get_current_user)):
    try:
        formatted = ai_service.format_notes_batch(body.notes, body.types)
        return {"formatted": formatted}
    except Exception:
        logger.error("POST /format-notes failed", exc_info=True)
        raise HTTPException(status_code=500, detail=_SAFE_ERROR)


@router.post("/summarize-async")
def summarize_async(body: SummarizeRequest, user: dict = Depends(get_current_user)):
    try:
        job_id = queue_service.enqueue_summarize(body.text)
        return {"job_id": job_id}
    except Exception:
        logger.error("POST /summarize-async failed", exc_info=True)
        raise HTTPException(status_code=500, detail=_SAFE_ERROR)


@router.get("/job/{job_id}")
def get_job(job_id: str, user: dict = Depends(get_current_user)):
    try:
        result = queue_service.get_job_result(job_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception:
        logger.error("GET /job/%s failed", job_id, exc_info=True)
        raise HTTPException(status_code=500, detail=_SAFE_ERROR)


# ── Metrics ───────────────────────────────────────────────────────────────────

@router.get("/metrics/sentiment-trend")
def get_sentiment_trend(user: dict = Depends(get_current_user)):
    try:
        return crm_service.get_sentiment_trend(user["id"])
    except Exception:
        logger.error("GET /metrics/sentiment-trend failed", exc_info=True)
        raise HTTPException(status_code=500, detail=_SAFE_ERROR)


@router.get("/metrics/followups")
def get_followup_metrics(user: dict = Depends(get_current_user)):
    try:
        return crm_service.get_followup_metrics(user["id"])
    except Exception:
        logger.error("GET /metrics/followups failed", exc_info=True)
        raise HTTPException(status_code=500, detail=_SAFE_ERROR)


@router.get("/metrics/top-doctors")
def get_top_doctors(user: dict = Depends(get_current_user)):
    try:
        return crm_service.get_top_doctors(user["id"])
    except Exception:
        logger.error("GET /metrics/top-doctors failed", exc_info=True)
        raise HTTPException(status_code=500, detail=_SAFE_ERROR)


@router.get("/metrics/system")
def get_system_metrics(user: dict = Depends(get_current_user)):
    try:
        return metrics_service.get_system_metrics(user["id"])
    except Exception:
        logger.error("GET /metrics/system failed", exc_info=True)
        raise HTTPException(status_code=500, detail=_SAFE_ERROR)


@router.get("/metrics/queue")
def get_queue_metrics(user: dict = Depends(get_current_user)):
    try:
        return queue_service.get_queue_metrics()
    except Exception:
        logger.error("GET /metrics/queue failed", exc_info=True)
        raise HTTPException(status_code=500, detail=_SAFE_ERROR)


@router.get("/metrics/summary")
def get_metrics_summary(user: dict = Depends(get_current_user)):
    try:
        return crm_service.get_metrics_summary(user["id"])
    except Exception:
        logger.error("GET /metrics/summary failed", exc_info=True)
        raise HTTPException(status_code=500, detail=_SAFE_ERROR)


@router.get("/doctor/{name}")
def get_doctor_profile(name: str, user: dict = Depends(get_current_user)):
    try:
        profile = crm_service.get_doctor_profile(name, user["id"])
        if not profile:
            raise HTTPException(status_code=404, detail=f"No doctor found with name '{name}'")
        return profile
    except HTTPException:
        raise
    except Exception:
        logger.error("GET /doctor/%s failed", name, exc_info=True)
        raise HTTPException(status_code=500, detail=_SAFE_ERROR)


@router.get("/doctor/{name}/timeline")
def get_doctor_timeline(name: str, user: dict = Depends(get_current_user)):
    try:
        timeline = crm_service.get_doctor_timeline(name, user["id"])
        if timeline is None:
            raise HTTPException(status_code=404, detail=f"No doctor found with name '{name}'")
        return timeline
    except HTTPException:
        raise
    except Exception:
        logger.error("GET /doctor/%s/timeline failed", name, exc_info=True)
        raise HTTPException(status_code=500, detail=_SAFE_ERROR)


# ── Doctor routes ─────────────────────────────────────────────────────────────

@router.get("/doctors")
def get_doctors(user: dict = Depends(get_current_user)):
    try:
        return crm_service.get_all_doctors(user["id"])
    except Exception:
        logger.error("GET /doctors failed", exc_info=True)
        raise HTTPException(status_code=500, detail=_SAFE_ERROR)


@router.post("/doctors")
def create_doctor(body: DoctorCreate, user: dict = Depends(get_current_user)):
    try:
        return crm_service.create_doctor_record(body.name.strip(), user["id"])
    except Exception:
        logger.error("POST /doctors failed", exc_info=True)
        raise HTTPException(status_code=500, detail=_SAFE_ERROR)


@router.get("/doctors/{doctor_id}")
def get_doctor(doctor_id: int, user: dict = Depends(get_current_user)):
    try:
        doctor = crm_service.get_doctor_by_id(doctor_id, user["id"])
        if not doctor:
            raise HTTPException(status_code=404, detail=f"No doctor found with id {doctor_id}")
        return doctor
    except HTTPException:
        raise
    except Exception:
        logger.error("GET /doctors/%s failed", doctor_id, exc_info=True)
        raise HTTPException(status_code=500, detail=_SAFE_ERROR)


# ── Follow-up routes ──────────────────────────────────────────────────────────

@router.post("/followups")
def create_followup(body: FollowUpCreate, user: dict = Depends(get_current_user)):
    try:
        return crm_service.create_followup(
            body.doctor_id, body.task, body.due_date, body.status, user["id"]
        )
    except Exception:
        logger.error("POST /followups failed", exc_info=True)
        raise HTTPException(status_code=500, detail=_SAFE_ERROR)


@router.get("/doctors/{doctor_id}/followups")
def get_followups(doctor_id: int, user: dict = Depends(get_current_user)):
    try:
        return crm_service.get_followups_by_doctor(doctor_id, user["id"])
    except Exception:
        logger.error("GET /doctors/%s/followups failed", doctor_id, exc_info=True)
        raise HTTPException(status_code=500, detail=_SAFE_ERROR)


@router.patch("/followups/{followup_id}")
def update_followup(
    followup_id: int,
    body: FollowUpUpdate,
    user: dict = Depends(get_current_user),
):
    try:
        updated = crm_service.update_followup_status(followup_id, body.status, user["id"])
        if not updated:
            raise HTTPException(status_code=404, detail=f"No follow-up found with id {followup_id}")
        return {"message": "Follow-up updated", "id": followup_id}
    except HTTPException:
        raise
    except Exception:
        logger.error("PATCH /followups/%s failed", followup_id, exc_info=True)
        raise HTTPException(status_code=500, detail=_SAFE_ERROR)


@router.delete("/followups/{followup_id}")
def delete_followup(followup_id: int, user: dict = Depends(get_current_user)):
    try:
        deleted = crm_service.delete_followup(followup_id, user["id"])
        if not deleted:
            raise HTTPException(status_code=404, detail=f"No follow-up found with id {followup_id}")
        return {"message": "Follow-up deleted", "id": followup_id}
    except HTTPException:
        raise
    except Exception:
        logger.error("DELETE /followups/%s failed", followup_id, exc_info=True)
        raise HTTPException(status_code=500, detail=_SAFE_ERROR)
