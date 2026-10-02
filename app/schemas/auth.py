# Leonardo Briquezi
# github: https://github.com/leobrqz
# linkedin: https://www.linkedin.com/in/leonardobri
from pydantic import BaseModel


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

