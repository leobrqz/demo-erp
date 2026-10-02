# Leonardo Briquezi
# github: https://github.com/leobrqz
# linkedin: https://www.linkedin.com/in/leonardobri
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models import User
from app.schemas.auth import TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=TokenResponse)
def issue_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = db.scalar(select(User).where(User.username == form_data.username))
    if (
        user is None
        or not user.is_active
        or not verify_password(form_data.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token, expires_in = create_access_token(user.username, user.role)
    return TokenResponse(access_token=token, expires_in=expires_in)

