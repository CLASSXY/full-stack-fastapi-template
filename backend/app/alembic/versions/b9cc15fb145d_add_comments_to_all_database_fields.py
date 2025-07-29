"""Add comments to all database fields

Revision ID: b9cc15fb145d
Revises: 30edc268fee8
Create Date: 2025-07-29 16:08:38.818202

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'b9cc15fb145d'
down_revision = '30edc268fee8'
branch_labels = None
depends_on = None


def upgrade():
    # Add comments to User table
    op.execute('COMMENT ON TABLE "user" IS \'用户表\'')
    op.execute('COMMENT ON COLUMN "user".id IS \'用户ID，主键\'')
    op.execute('COMMENT ON COLUMN "user".email IS \'用户邮箱，唯一索引\'')
    op.execute('COMMENT ON COLUMN "user".is_active IS \'用户是否激活\'')
    op.execute('COMMENT ON COLUMN "user".is_superuser IS \'是否为超级管理员\'')
    op.execute('COMMENT ON COLUMN "user".full_name IS \'用户全名\'')
    op.execute('COMMENT ON COLUMN "user".hashed_password IS \'加密后的密码\'')
    
    # Add comments to Item table
    op.execute('COMMENT ON TABLE item IS \'项目表\'')
    op.execute('COMMENT ON COLUMN item.id IS \'项目ID，主键\'')
    op.execute('COMMENT ON COLUMN item.title IS \'项目标题\'')
    op.execute('COMMENT ON COLUMN item.description IS \'项目描述\'')
    op.execute('COMMENT ON COLUMN item.owner_id IS \'项目所有者ID，外键关联用户表\'')
    
    # Add comments to OCRRecord table
    op.execute('COMMENT ON TABLE ocr_records IS \'OCR识别记录表（运单识别）\'')
    op.execute('COMMENT ON COLUMN ocr_records.id IS \'OCR记录ID，主键\'')
    op.execute('COMMENT ON COLUMN ocr_records.device_sn IS \'设备序列号\'')
    op.execute('COMMENT ON COLUMN ocr_records.original_image_url IS \'原始图片URL\'')
    op.execute('COMMENT ON COLUMN ocr_records.result_image_url IS \'识别结果图片URL\'')
    op.execute('COMMENT ON COLUMN ocr_records.ocr_text IS \'OCR识别的文本内容\'')
    op.execute('COMMENT ON COLUMN ocr_records.ocr_confidence IS \'OCR识别置信度（0-1）\'')
    op.execute('COMMENT ON COLUMN ocr_records.language IS \'OCR识别语言\'')
    op.execute('COMMENT ON COLUMN ocr_records.processing_time IS \'处理耗时（秒）\'')
    op.execute('COMMENT ON COLUMN ocr_records.status IS \'处理状态\'')
    op.execute('COMMENT ON COLUMN ocr_records.error_message IS \'错误信息\'')
    op.execute('COMMENT ON COLUMN ocr_records.file_size IS \'文件大小（字节）\'')
    op.execute('COMMENT ON COLUMN ocr_records.image_format IS \'图片格式\'')
    op.execute('COMMENT ON COLUMN ocr_records.use_angle_cls IS \'是否使用角度分类\'')
    op.execute('COMMENT ON COLUMN ocr_records.detection_boxes IS \'检测框信息（JSON格式）\'')
    op.execute('COMMENT ON COLUMN ocr_records.scan_time IS \'扫描时间\'')
    op.execute('COMMENT ON COLUMN ocr_records.created_by IS \'创建者ID，外键关联用户表\'')
    op.execute('COMMENT ON COLUMN ocr_records.created_at IS \'创建时间\'')
    op.execute('COMMENT ON COLUMN ocr_records.updated_at IS \'更新时间\'')
    
    # Add comments to waybill related fields
    op.execute('COMMENT ON COLUMN ocr_records.waybill_number IS \'运单号/发货单号\'')
    op.execute('COMMENT ON COLUMN ocr_records.carrier IS \'承运商/物流公司\'')
    op.execute('COMMENT ON COLUMN ocr_records.shipping_date IS \'发货日期\'')
    op.execute('COMMENT ON COLUMN ocr_records.recipient IS \'签收人\'')
    op.execute('COMMENT ON COLUMN ocr_records.delivery_date IS \'签收日期\'')
    op.execute('COMMENT ON COLUMN ocr_records.upload_date IS \'上传日期\'')
    op.execute('COMMENT ON COLUMN ocr_records.uploader IS \'上传人\'')
    op.execute('COMMENT ON COLUMN ocr_records.audit_status IS \'审核状态：未审核/已审核/审核通过/审核不通过\'')


def downgrade():
    # Remove comments from all tables and columns
    op.execute('COMMENT ON TABLE "user" IS NULL')
    op.execute('COMMENT ON COLUMN "user".id IS NULL')
    op.execute('COMMENT ON COLUMN "user".email IS NULL')
    op.execute('COMMENT ON COLUMN "user".is_active IS NULL')
    op.execute('COMMENT ON COLUMN "user".is_superuser IS NULL')
    op.execute('COMMENT ON COLUMN "user".full_name IS NULL')
    op.execute('COMMENT ON COLUMN "user".hashed_password IS NULL')
    
    op.execute('COMMENT ON TABLE item IS NULL')
    op.execute('COMMENT ON COLUMN item.id IS NULL')
    op.execute('COMMENT ON COLUMN item.title IS NULL')
    op.execute('COMMENT ON COLUMN item.description IS NULL')
    op.execute('COMMENT ON COLUMN item.owner_id IS NULL')
    
    op.execute('COMMENT ON TABLE ocr_records IS NULL')
    op.execute('COMMENT ON COLUMN ocr_records.id IS NULL')
    op.execute('COMMENT ON COLUMN ocr_records.device_sn IS NULL')
    op.execute('COMMENT ON COLUMN ocr_records.original_image_url IS NULL')
    op.execute('COMMENT ON COLUMN ocr_records.result_image_url IS NULL')
    op.execute('COMMENT ON COLUMN ocr_records.ocr_text IS NULL')
    op.execute('COMMENT ON COLUMN ocr_records.ocr_confidence IS NULL')
    op.execute('COMMENT ON COLUMN ocr_records.language IS NULL')
    op.execute('COMMENT ON COLUMN ocr_records.processing_time IS NULL')
    op.execute('COMMENT ON COLUMN ocr_records.status IS NULL')
    op.execute('COMMENT ON COLUMN ocr_records.error_message IS NULL')
    op.execute('COMMENT ON COLUMN ocr_records.file_size IS NULL')
    op.execute('COMMENT ON COLUMN ocr_records.image_format IS NULL')
    op.execute('COMMENT ON COLUMN ocr_records.use_angle_cls IS NULL')
    op.execute('COMMENT ON COLUMN ocr_records.detection_boxes IS NULL')
    op.execute('COMMENT ON COLUMN ocr_records.scan_time IS NULL')
    op.execute('COMMENT ON COLUMN ocr_records.created_by IS NULL')
    op.execute('COMMENT ON COLUMN ocr_records.created_at IS NULL')
    op.execute('COMMENT ON COLUMN ocr_records.updated_at IS NULL')
    op.execute('COMMENT ON COLUMN ocr_records.waybill_number IS NULL')
    op.execute('COMMENT ON COLUMN ocr_records.carrier IS NULL')
    op.execute('COMMENT ON COLUMN ocr_records.shipping_date IS NULL')
    op.execute('COMMENT ON COLUMN ocr_records.recipient IS NULL')
    op.execute('COMMENT ON COLUMN ocr_records.delivery_date IS NULL')
    op.execute('COMMENT ON COLUMN ocr_records.upload_date IS NULL')
    op.execute('COMMENT ON COLUMN ocr_records.uploader IS NULL')
    op.execute('COMMENT ON COLUMN ocr_records.audit_status IS NULL')
