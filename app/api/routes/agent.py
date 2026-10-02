# Leonardo Briquezi
# github: https://github.com/leobrqz
# linkedin: https://www.linkedin.com/in/leonardobri
import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.agent import AgentQuestion, AgentResponse
from app.services.agent import answer_erp_question, stream_erp_question

router = APIRouter(prefix="/ai", tags=["ai-agent"])
logger = logging.getLogger(__name__)


@router.post("/ask", response_model=AgentResponse)
async def ask_erp(
    payload: AgentQuestion,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> AgentResponse:
    return await answer_erp_question(db, payload.question)


@router.post("/ask/stream")
async def ask_erp_stream(
    payload: AgentQuestion,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> StreamingResponse:
    async def events():
        try:
            async for item in stream_erp_question(db, payload.question):
                event = item["event"]
                data = json.dumps(item.get("data", {}), ensure_ascii=False, separators=(",", ":"))
                yield f"event: {event}\ndata: {data}\n\n"
        except Exception:
            logger.exception("Falha ao transmitir a resposta do agente.")
            data = json.dumps(
                {"message": "Não foi possível concluir a consulta. Tente novamente."},
                ensure_ascii=False,
            )
            yield f"event: error\ndata: {data}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
