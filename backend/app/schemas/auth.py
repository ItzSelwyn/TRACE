from pydantic import BaseModel, EmailStr
from typing import Optional
import uuid

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str  # operator, analyst, admin

class UserResponse(BaseModel):
    user_id: uuid.UUID
    name: str
    email: str
    role: str

    model_config = {"from_attributes": True}
