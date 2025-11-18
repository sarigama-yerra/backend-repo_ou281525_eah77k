import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from bson import ObjectId

from database import db, create_document, get_documents

app = FastAPI(title="Salon Booking API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utils

def to_object_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")


def serialize(doc):
    if not doc:
        return doc
    doc = dict(doc)
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    # Convert datetimes to isoformat
    for k, v in list(doc.items()):
        if isinstance(v, datetime):
            doc[k] = v.isoformat()
    return doc


@app.get("/")
def read_root():
    return {"message": "Salon Booking API is running"}


# Schemas endpoint for the viewer
@app.get("/schema")
def get_schema():
    from schemas import Service, Stylist, Customer, Appointment
    return {
        "service": Service.model_json_schema(),
        "stylist": Stylist.model_json_schema(),
        "customer": Customer.model_json_schema(),
        "appointment": Appointment.model_json_schema(),
    }


# Seed endpoints (optional helpers)
@app.post("/seed/basic")
def seed_basic():
    # create a couple of services and stylists if not present
    services = list(db["service"].find({}).limit(1))
    if not services:
        create_document("service", {"name": "Haircut", "description": "Classic haircut", "duration_minutes": 45, "price": 35})
        create_document("service", {"name": "Hair Color", "description": "Full color", "duration_minutes": 120, "price": 120})
    stylists = list(db["stylist"].find({}).limit(1))
    if not stylists:
        create_document("stylist", {"name": "Alex Morgan", "specialties": ["Haircut", "Beard Trim"], "bio": "5 years experience"})
        create_document("stylist", {"name": "Jamie Lee", "specialties": ["Hair Color", "Highlights"], "bio": "Color specialist"})
    return {"status": "ok"}


# Public endpoints
@app.get("/services")
def list_services():
    docs = get_documents("service")
    return [serialize(d) for d in docs]


@app.get("/stylists")
def list_stylists():
    docs = get_documents("stylist")
    return [serialize(d) for d in docs]


# Booking endpoint
class BookingRequest(BaseModel):
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = None
    service_id: str
    stylist_id: str
    start_time: datetime
    notes: Optional[str] = None


@app.post("/book")
def book_appointment(payload: BookingRequest):
    # Basic validations
    service = db["service"].find_one({"_id": to_object_id(payload.service_id)})
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    stylist = db["stylist"].find_one({"_id": to_object_id(payload.stylist_id)})
    if not stylist:
        raise HTTPException(status_code=404, detail="Stylist not found")

    # Ensure customer exists or create
    customer = db["customer"].find_one({"phone": payload.customer_phone})
    if not customer:
        customer_id = create_document("customer", {
            "name": payload.customer_name,
            "phone": payload.customer_phone,
            "email": payload.customer_email,
        })
        customer = db["customer"].find_one({"_id": to_object_id(customer_id)})

    # Calculate duration from service
    duration = int(service.get("duration_minutes", 60))

    # Check for conflicts: overlapping appointments for stylist
    start = payload.start_time
    end = start + timedelta(minutes=duration)
    conflict = db["appointment"].find_one({
        "stylist_id": str(stylist["_id"]),
        "$or": [
            {"start_time": {"$lt": end}, "end_time": {"$gt": start}},
        ],
        "status": {"$in": ["scheduled", "confirmed"]}
    })
    if conflict:
        raise HTTPException(status_code=409, detail="Time slot not available for this stylist")

    appointment_id = create_document("appointment", {
        "customer_id": str(customer["_id"]),
        "service_id": str(service["_id"]),
        "stylist_id": str(stylist["_id"]),
        "start_time": start,
        "end_time": end,
        "duration_minutes": duration,
        "notes": payload.notes,
        "status": "scheduled",
    })

    appt = db["appointment"].find_one({"_id": to_object_id(appointment_id)})
    return serialize(appt)


@app.get("/appointments")
def list_appointments(limit: int = 50):
    docs = db["appointment"].find({}).sort("start_time", 1).limit(limit)
    return [serialize(d) for d in docs]


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
