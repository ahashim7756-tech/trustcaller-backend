import hashlib
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, String, Boolean, Float, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os

# 1. إعدادات قاعدة البيانات - سيتم جلب الرابط من متغيرات البيئة في السيرفر
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/trustcaller")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. نموذج بيانات المستخدم (User Model)
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    hashed_phone = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    job_title = Column(String)
    is_verified = Column(Boolean, default=False)
    trust_score = Column(Float, default=0.0)

# 3. دالة المزامنة الأولية (Seeding Logic)
def init_db_data(db_session: Session):
    if db_session.query(User).count() > 0:
        return

    def hash_phone(phone: str) -> str:
        clean = ''.join(filter(str.isdigit, phone))
        return hashlib.sha256(clean.encode('utf-8')).hexdigest()

    test_users = [
        {"phone": "+201234567890", "name": "Dr. Ahmed Ali", "job": "Cardiologist (Verified)", "trust": 9.8, "verified": True},
        {"phone": "+201112223333", "name": "Fast Delivery Co.", "job": "Official Courier", "trust": 8.5, "verified": True},
        {"phone": "+201555555555", "name": "Unknown Spammer", "job": "Suspected Fraud", "trust": 1.2, "verified": False},
    ]

    for u in test_users:
        db_user = User(
            hashed_phone=hash_phone(u["phone"]),
            full_name=u["name"],
            job_title=u["job"],
            trust_score=u["trust"],
            is_verified=u["verified"]
        )
        db_session.add(db_user)
    db_session.commit()

# 4. تشغيل FastAPI
app = FastAPI(title="TrustCaller API")

# اعتمادية الحصول على الجلسة
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# تنفيذ إنشاء الجداول والبيانات عند بدء التشغيل
@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    init_db_data(db)
    db.close()

# 5. نقطة البحث (The Search Endpoint)
@app.post("/search-number")
def search_number(data: dict, db: Session = Depends(get_db)):
    hashed_phone = data.get("hashed_phone")
    if not hashed_phone:
        raise HTTPException(status_code=400, detail="Missing hashed_phone")
    
    user = db.query(User).filter(User.hashed_phone == hashed_phone).first()
    
    if not user or not user.is_verified:
        raise HTTPException(status_code=404, detail="User not found or unverified")
    
    return {
        "full_name": user.full_name,
        "job_title": user.job_title,
        "trust_score": user.trust_score,
        "status": "Verified"
    }

@app.get("/")
def health_check():
    return {"status": "TrustCaller API is Live"}
