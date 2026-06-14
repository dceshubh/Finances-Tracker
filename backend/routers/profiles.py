from fastapi import APIRouter, HTTPException
from ..database import get_db
from ..models import ProfileCreate, ProfileOut

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


@router.get("", response_model=list[ProfileOut])
def list_profiles():
    db = get_db()
    rows = db.execute("SELECT * FROM profiles ORDER BY id").fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.post("", response_model=ProfileOut)
def create_profile(profile: ProfileCreate):
    db = get_db()
    cursor = db.execute(
        "INSERT INTO profiles (name, role) VALUES (?, ?)",
        (profile.name, profile.role),
    )
    db.commit()
    row = db.execute("SELECT * FROM profiles WHERE id = ?", (cursor.lastrowid,)).fetchone()
    db.close()
    return dict(row)


@router.delete("/{profile_id}")
def delete_profile(profile_id: int):
    db = get_db()
    db.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
    db.commit()
    db.close()
    return {"deleted": True}
