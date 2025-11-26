from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# Profile Schemas
class ProfileBase(BaseModel):
    phone: str = ""
    address: str = ""
    city: str = ""
    state: str = ""

class ProfileCreate(ProfileBase):
    pass

class ProfileUpdate(ProfileBase):
    pass

class Profile(ProfileBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# User Schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr
    first_name: str = ""
    last_name: str = ""

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    password: Optional[str] = None

class PasswordUpdate(BaseModel):
    new_password: str

class PermissionsUpdate(BaseModel):
    is_staff: Optional[bool] = None
    is_superuser: Optional[bool] = None

class User(UserBase):
    id: int
    is_active: bool
    is_staff: bool
    is_superuser: bool
    date_joined: datetime
    last_login: Optional[datetime] = None
    profile: Optional[Profile] = None
    
    class Config:
        from_attributes = True

class UserWithProfile(User):
    profile: Profile
