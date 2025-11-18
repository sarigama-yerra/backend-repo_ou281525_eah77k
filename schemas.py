"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime

# Salon booking app schemas

class Service(BaseModel):
    """
    Services offered by the salon
    Collection: "service"
    """
    name: str = Field(..., description="Service name, e.g., Haircut")
    description: Optional[str] = Field(None, description="Short description")
    duration_minutes: int = Field(..., ge=10, le=600, description="Duration in minutes")
    price: float = Field(..., ge=0, description="Price in dollars")

class Stylist(BaseModel):
    """
    Stylists/Professionals available for services
    Collection: "stylist"
    """
    name: str = Field(..., description="Full name")
    specialties: List[str] = Field(default_factory=list, description="List of services or skills")
    bio: Optional[str] = Field(None, description="Short bio")

class Customer(BaseModel):
    """
    Customers booking the appointments
    Collection: "customer"
    """
    name: str = Field(...)
    phone: str = Field(..., description="Contact phone number")
    email: Optional[EmailStr] = Field(None)

class Appointment(BaseModel):
    """
    Booked appointments
    Collection: "appointment"
    """
    customer_id: str = Field(..., description="ID of the customer")
    service_id: str = Field(..., description="ID of the service")
    stylist_id: str = Field(..., description="ID of the stylist")
    start_time: datetime = Field(..., description="Appointment start time in ISO format")
    duration_minutes: int = Field(..., ge=10, le=600)
    notes: Optional[str] = Field(None)
    status: str = Field("scheduled", description="scheduled | completed | cancelled")

# Note: The Flames database viewer will automatically:
# 1. Read these schemas from GET /schema endpoint
# 2. Use them for document validation when creating/editing
# 3. Handle all database operations (CRUD) directly
# 4. You don't need to create any database endpoints!
