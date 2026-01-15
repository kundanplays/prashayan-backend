import boto3
from botocore.exceptions import ClientError
from app.core.config import settings
from typing import Optional
import uuid
import os

class S3Service:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.bucket_name = settings.S3_BUCKET
    
    def upload_file(self, file_content: bytes, file_name: str, content_type: str = "image/jpeg") -> Optional[str]:
        """
        Upload a file to S3 and return the relative URL.
        
        Args:
            file_content: Binary content of the file
            file_name: Original filename
            content_type: MIME type of the file
            
        Returns:
            Relative URL path (e.g., "products/uuid-filename.jpg") or None if failed
        """
        try:
            # Generate unique filename
            file_extension = os.path.splitext(file_name)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            
            # Determine folder based on content type or file name
            if "product" in file_name.lower():
                folder = "products"
            elif "profile" in file_name.lower() or "user" in file_name.lower():
                folder = "users"
            elif "blog" in file_name.lower():
                folder = "blogs"
            elif "review" in file_name.lower():
                folder = "reviews"
            else:
                folder = "misc"
            
            # S3 key (path)
            s3_key = f"{folder}/{unique_filename}"
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type
                # ACL='public-read' is removed to support buckets where ACLs are disabled (Object Ownership = Bucket owner enforced)
                # Public access should be handled via S3 Bucket Policy
            )
            
            # Return relative URL (we'll construct full URL in API response)
            return s3_key
            
        except ClientError as e:
            print(f"Error uploading to S3: {e}")
            return None
    
    def delete_file(self, s3_key: str) -> bool:
        """
        Delete a file from S3.
        
        Args:
            s3_key: The S3 key (relative path) of the file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True
        except ClientError as e:
            print(f"Error deleting from S3: {e}")
            return False
    
    def get_public_url(self, s3_key: str) -> str:
        """
        Get the public URL for an S3 object.
        
        Args:
            s3_key: The S3 key (relative path) of the file
            
        Returns:
            Full public URL
        """
        return f"{settings.S3_BASE_URL}/{s3_key}"

# Singleton instance
s3_service = S3Service()
