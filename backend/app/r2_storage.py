"""
Cloudflare R2 Storage Service

This module provides integration with Cloudflare R2 object storage
using S3-compatible API through boto3.
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

from app.core.config import settings

logger = logging.getLogger(__name__)


class R2StorageService:
    """Cloudflare R2 Storage Service using S3-compatible API"""
    
    def __init__(self):
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize R2 client using boto3"""
        try:
            # Configure boto3 for R2
            config = Config(
                region_name='auto',  # R2 uses 'auto' as region
                signature_version='s3v4',
                s3={
                    'addressing_style': 'path'  # Use path-style addressing
                }
            )
            
            self.client = boto3.client(
                's3',
                endpoint_url=settings.CLOUDFLARE_R2_ENDPOINT_URL,
                aws_access_key_id=settings.CLOUDFLARE_R2_ACCESS_KEY_ID,
                aws_secret_access_key=settings.CLOUDFLARE_R2_SECRET_ACCESS_KEY,
                config=config
            )
            
            # Test connection by checking if bucket exists
            self._ensure_bucket_exists()
            
            logger.info("R2 Storage Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize R2 client: {e}")
            raise RuntimeError(f"R2 storage initialization failed: {e}")
    
    def _ensure_bucket_exists(self):
        """Ensure the bucket exists, create if it doesn't"""
        try:
            self.client.head_bucket(Bucket=settings.CLOUDFLARE_R2_BUCKET_NAME)
            logger.info(f"Bucket {settings.CLOUDFLARE_R2_BUCKET_NAME} exists")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                try:
                    self.client.create_bucket(Bucket=settings.CLOUDFLARE_R2_BUCKET_NAME)
                    logger.info(f"Created bucket {settings.CLOUDFLARE_R2_BUCKET_NAME}")
                except ClientError as create_error:
                    logger.error(f"Failed to create bucket: {create_error}")
                    raise
            else:
                logger.error(f"Failed to check bucket: {e}")
                raise
    
    def upload_file(
        self, 
        file_content: bytes, 
        file_key: str, 
        content_type: str = "application/octet-stream"
    ) -> str:
        """
        Upload file to R2 storage
        
        Args:
            file_content: File content as bytes
            file_key: S3 object key (file path in bucket)
            content_type: MIME type of the file
            
        Returns:
            Public URL of the uploaded file
        """
        try:
            # Upload file to R2
            self.client.put_object(
                Bucket=settings.CLOUDFLARE_R2_BUCKET_NAME,
                Key=file_key,
                Body=file_content,
                ContentType=content_type,
                CacheControl='max-age=31536000',  # Cache for 1 year
            )
            
            # Generate public URL
            public_url = self._get_public_url(file_key)
            
            logger.info(f"File uploaded successfully: {file_key}")
            return public_url
            
        except Exception as e:
            logger.error(f"Failed to upload file {file_key}: {e}")
            raise
    
    def upload_image(
        self, 
        image_content: bytes, 
        image_format: str,
        prefix: str = "images"
    ) -> Tuple[str, str]:
        """
        Upload image file with auto-generated key
        
        Args:
            image_content: Image content as bytes
            image_format: Image format (jpg, png, etc.)
            prefix: S3 key prefix (folder name)
            
        Returns:
            Tuple of (file_key, public_url)
        """
        try:
            # Generate unique file key
            today = datetime.utcnow().strftime("%Y-%m-%d")
            file_id = str(uuid.uuid4())
            file_key = f"{prefix}/{today}/{file_id}.{image_format.lower()}"
            
            # Determine content type
            content_type_map = {
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg', 
                'png': 'image/png',
                'bmp': 'image/bmp',
                'webp': 'image/webp'
            }
            content_type = content_type_map.get(image_format.lower(), 'image/jpeg')
            
            # Upload file
            public_url = self.upload_file(image_content, file_key, content_type)
            
            return file_key, public_url
            
        except Exception as e:
            logger.error(f"Failed to upload image: {e}")
            raise
    
    def delete_file(self, file_key: str) -> bool:
        """
        Delete file from R2 storage
        
        Args:
            file_key: S3 object key to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.delete_object(
                Bucket=settings.CLOUDFLARE_R2_BUCKET_NAME,
                Key=file_key
            )
            
            logger.info(f"File deleted successfully: {file_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete file {file_key}: {e}")
            return False
    
    def generate_presigned_url(
        self, 
        file_key: str, 
        expiration: int = 3600
    ) -> str:
        """
        Generate presigned URL for temporary access
        
        Args:
            file_key: S3 object key
            expiration: URL expiration time in seconds
            
        Returns:
            Presigned URL
        """
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': settings.CLOUDFLARE_R2_BUCKET_NAME,
                    'Key': file_key
                },
                ExpiresIn=expiration
            )
            
            return url
            
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {file_key}: {e}")
            raise
    
    def _get_public_url(self, file_key: str) -> str:
        """Generate public URL for the file"""
        if settings.CLOUDFLARE_R2_PUBLIC_URL:
            # Use custom domain if configured
            return f"{settings.CLOUDFLARE_R2_PUBLIC_URL.rstrip('/')}/{file_key}"
        else:
            # Use R2 public URL format
            # Note: This assumes the bucket has public access configured
            
            # First try to extract account ID from the account-id.r2.cloudflarestorage.com format
            endpoint = settings.CLOUDFLARE_R2_ENDPOINT_URL
            if not endpoint:
                raise ValueError("CLOUDFLARE_R2_ENDPOINT_URL not configured")
                
            try:
                # Extract account ID from endpoint URL like: https://account-id.r2.cloudflarestorage.com
                if ".r2.cloudflarestorage.com" in endpoint:
                    account_id = endpoint.split('//')[1].split('.r2.cloudflarestorage.com')[0]
                else:
                    # Fallback: try to extract first part after https://
                    account_id = endpoint.split('//')[1].split('.')[0]
                
                # Generate public URL
                public_url = f"https://pub-{account_id}.r2.dev/{file_key}"
                logger.info(f"Generated public URL: {public_url}")
                return public_url
                
            except Exception as e:
                logger.error(f"Failed to extract account ID from endpoint {endpoint}: {e}")
                # Fallback to a generic error or raise an exception
                raise ValueError(f"Unable to generate public URL. Please configure CLOUDFLARE_R2_PUBLIC_URL in settings. Error: {e}")
    
    def get_file_info(self, file_key: str) -> dict:
        """
        Get file metadata from R2
        
        Args:
            file_key: S3 object key
            
        Returns:
            File metadata dict
        """
        try:
            response = self.client.head_object(
                Bucket=settings.CLOUDFLARE_R2_BUCKET_NAME,
                Key=file_key
            )
            
            return {
                'size': response.get('ContentLength', 0),
                'content_type': response.get('ContentType', ''),
                'last_modified': response.get('LastModified'),
                'etag': response.get('ETag', '').strip('"')
            }
            
        except Exception as e:
            logger.error(f"Failed to get file info for {file_key}: {e}")
            raise


# Global R2 storage service instance
r2_storage = R2StorageService() 