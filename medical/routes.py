from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from config import supabase
from auth.rbac import get_current_user, require_any_staff

router = APIRouter()


class MedicalCardRequest(BaseModel):
    bloodType: Optional[str] = None
    allergies: Optional[str] = None
    medications: Optional[str] = None
    medicalHistory: Optional[str] = None
    emergencyContactName: Optional[str] = None
    emergencyContactPhone: Optional[str] = None
    passportNumber: Optional[str] = None
    visaNumber: Optional[str] = None
    visaQrData: Optional[str] = None
    photoUrl: Optional[str] = None


@router.get("/card")
def getOwnMedicalCard(user=Depends(get_current_user)):
    return _getMedicalCard(user["sub"])


@router.put("/card")
def upsertOwnMedicalCard(body: MedicalCardRequest, user=Depends(get_current_user)):
    return _upsertMedicalCard(user["sub"], body)


@router.get("/card/{user_id}")
def getMedicalCardForLeader(user_id: str, user=Depends(require_any_staff)):
    return _getMedicalCard(user_id)


def _getMedicalCard(userId: str):
    try:
        res = supabase.table("medical_cards").select("*").eq("user_id", userId).limit(1).execute()
        return {"success": True, "data": res.data[0] if res.data else None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _upsertMedicalCard(userId: str, body: MedicalCardRequest):
    try:
        data = {
            "user_id": userId,
            "blood_type": body.bloodType,
            "allergies": body.allergies,
            "medications": body.medications,
            "medical_history": body.medicalHistory,
            "emergency_contact_name": body.emergencyContactName,
            "emergency_contact_phone": body.emergencyContactPhone,
            "passport_number": body.passportNumber,
            "visa_number": body.visaNumber,
            "visa_qr_data": body.visaQrData,
            "photo_url": body.photoUrl,
        }
        res = supabase.table("medical_cards").upsert(data, on_conflict="user_id").execute()
        return {"success": True, "data": res.data[0] if res.data else data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
