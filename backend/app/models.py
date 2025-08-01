import uuid
from datetime import datetime, date
from typing import Any

from pydantic import EmailStr
from sqlmodel import Field, Relationship, SQLModel, JSON, Column


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=40)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=40)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=40)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=40)
    new_password: str = Field(min_length=8, max_length=40)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    items: list["Item"] = Relationship(back_populates="owner", cascade_delete=True)
    ocr_records: list["OCRRecord"] = Relationship(back_populates="creator", cascade_delete=True)


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Shared properties
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, min_length=1, max_length=255)  # type: ignore


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


# Shared properties for OCR records (运单识别记录)
class OCRRecordBase(SQLModel):
    # 基础信息
    original_image_url: str = Field(max_length=500)
    result_image_url: str | None = Field(default=None, max_length=500)
    ocr_text: str | None = Field(default=None)
    ocr_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    language: str = Field(default="ch", max_length=20)
    processing_time: float | None = Field(default=None)
    status: str = Field(default="processing", max_length=50)
    error_message: str | None = Field(default=None)
    file_size: int | None = Field(default=None)
    image_format: str | None = Field(default=None, max_length=20)
    use_angle_cls: bool = Field(default=False)
    
    # 运单相关字段
    waybill_number: str | None = Field(default=None, max_length=255, index=True)  # 发货单号
    carrier: str | None = Field(default=None, max_length=255)  # 承运商
    shipping_date: date | None = Field(default=None)  # 发货日期
    recipient: str | None = Field(default=None, max_length=255)  # 签收人
    delivery_date: date | None = Field(default=None)  # 签收日期
    upload_date: date | None = Field(default=None)  # 上传日期
    uploader: str | None = Field(default=None, max_length=255)  # 上传人
    audit_status: str = Field(default="未审核", max_length=50)  # 审核状态: 未审核/已审核/审核通过/审核不通过


# Properties to receive on OCR record creation
class OCRRecordCreate(SQLModel):
    language: str = Field(default="ch", max_length=20)
    use_angle_cls: bool = Field(default=False)
    use_dilation: bool = Field(default=False)
    confidence_thresh: float = Field(default=0.5, ge=0.0, le=1.0)


# Properties to receive on OCR record update
class OCRRecordUpdate(SQLModel):
    ocr_text: str | None = Field(default=None)
    ocr_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    result_image_url: str | None = Field(default=None, max_length=500)
    processing_time: float | None = Field(default=None)
    status: str | None = Field(default=None, max_length=50)
    error_message: str | None = Field(default=None)
    detection_boxes: dict[str, Any] | None = Field(default=None)


# Database model for OCR records
class OCRRecord(OCRRecordBase, table=True):
    __tablename__ = "ocr_records"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    detection_boxes: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    scan_time: datetime = Field(default_factory=datetime.utcnow, index=True)
    created_by: uuid.UUID = Field(foreign_key="user.id", nullable=False, ondelete="CASCADE")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    creator: User | None = Relationship(back_populates="ocr_records")


# Properties to return via API
class OCRRecordPublic(OCRRecordBase):
    id: uuid.UUID
    detection_boxes: dict[str, Any] | None = None
    scan_time: datetime
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class OCRRecordsPublic(SQLModel):
    data: list[OCRRecordPublic]
    count: int


# Detection box model for structured data
class DetectionBox(SQLModel):
    text: str
    confidence: float = Field(ge=0.0, le=1.0)
    box: list[list[float]]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=40)
