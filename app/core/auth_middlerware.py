import time
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
import jwt
from typing import Optional, Dict
from pydantic import BaseModel, Field, field_validator
from fastapi import HTTPException, Header

class GuestTokenResp(BaseModel):
    email: str
    email_verified: bool

def decode_jwt_token(authorization: str = Header(...), ) -> Optional[Dict]:
    print("decode_jwt_token", authorization)
    try:
        payload = jwt.decode(
            authorization.split("Bearer ")[-1],
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_signature":False},
        )
        return payload if payload["exp"] >= time.time() else None
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token Expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(status_code=403, detail="Invalid authentication scheme.")
            
            payload = self.verify_and_decode_jwt(credentials.credentials)
            if not payload:
                raise HTTPException(status_code=403, detail="Invalid token or expired token.")
            
            request.state.jwt_payload = payload
            return credentials.credentials
        else:
            raise HTTPException(status_code=403, detail="Invalid authorization code.")

    def verify_and_decode_jwt(self, jwtoken: str) -> Optional[Dict]:
        try:
            payload = decode_jwt_token(jwtoken)
            return payload
        except:
            return None