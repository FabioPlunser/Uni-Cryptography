from pydantic import BaseModel

from typing import Optional

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str
    public_key: Optional[str] = None

class UserLogin(UserBase):
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    
class TokenData(BaseModel):
    username: str
    
class PublicKeyUpdate(BaseModel):
    public_key: str
    
class PublicKeyResponse(BaseModel):
    username: str
    public_key: str
