from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DashboardPreferenceBase(BaseModel):
    show_pending_maintenance: bool = True
    show_equipment_stats: bool = True
    show_cost_analysis: bool = True
    show_upcoming_maintenance: bool = True
    days_to_alert: int = 7

class DashboardPreferenceCreate(DashboardPreferenceBase):
    pass

class DashboardPreferenceUpdate(DashboardPreferenceBase):
    show_pending_maintenance: Optional[bool] = None
    show_equipment_stats: Optional[bool] = None
    show_cost_analysis: Optional[bool] = None
    show_upcoming_maintenance: Optional[bool] = None
    days_to_alert: Optional[int] = None

class DashboardPreference(DashboardPreferenceBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

