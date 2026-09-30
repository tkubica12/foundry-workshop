from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Text = Annotated[str, Field(min_length=1, max_length=200)]
Description = Annotated[str, Field(min_length=1, max_length=4000)]
Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")]
Status = Literal["new", "triaged", "in_progress", "awaiting_customer", "resolved", "closed"]
Priority = Literal["low", "normal", "high", "critical"]
Category = Literal["late_arrival", "repair_quality", "billing", "communication", "warranty", "safety"]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Address(Model):
    street: Text
    city: Text
    region: Text
    postal_code: Text
    country_code: Annotated[str, Field(pattern=r"^[A-Z]{2}$")]
    latitude: Annotated[float, Field(ge=-90, le=90)]
    longitude: Annotated[float, Field(ge=-180, le=180)]


class PartnerInput(Model):
    name: Text
    address: Address
    contact_name: Text
    email: Annotated[str, Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=200)]
    phone: Text
    website: Annotated[str, Field(pattern=r"^https://", max_length=300)]
    status: Literal["active", "suspended", "pending"] = "active"
    tier: Literal["standard", "silver", "gold", "platinum"] = "standard"
    specialties: Annotated[list[Literal["hvac", "appliances", "solar", "electrical", "plumbing"]], Field(min_length=1, max_length=5)]
    languages: Annotated[list[Text], Field(min_length=1, max_length=10)]
    certifications: Annotated[list[Text], Field(max_length=10)] = []
    service_radius_km: Annotated[int, Field(ge=1, le=1000)] = 50
    emergency_service: bool = False
    rating: Annotated[float, Field(ge=0, le=5)] = 0
    capacity_per_week: Annotated[int, Field(ge=0, le=500)] = 10
    authorized_since: Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")]


class Partner(PartnerInput):
    id: Identifier
    version: int
    updated_at: datetime


class Customer(Model):
    name: Text
    email: Annotated[str, Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=200)]
    country_code: Annotated[str, Field(pattern=r"^[A-Z]{2}$")]
    preferred_language: Text = "en"


class ComplaintInput(Model):
    customer: Customer
    subject: Text
    description: Description
    category: Category
    priority: Priority = "normal"
    channel: Literal["email", "phone", "web", "chat"] = "web"
    product: Text
    order_reference: Text


class Note(Model):
    author: Text
    text: Description
    created_at: datetime


class Event(Model):
    from_status: Status
    to_status: Status
    reason: Description
    created_at: datetime


class Complaint(ComplaintInput):
    id: Identifier
    status: Status = "new"
    assigned_partner_id: Identifier | None = None
    assigned_agent: Text | None = None
    resolution: Description | None = None
    created_at: datetime
    updated_at: datetime
    due_at: datetime
    version: int
    notes: Annotated[list[Note], Field(max_length=100)] = []
    history: Annotated[list[Event], Field(max_length=100)] = []


class ComplaintPatch(Model):
    priority: Priority | None = None
    category: Category | None = None
    subject: Text | None = None
    description: Description | None = None
    assigned_agent: Text | None = None
