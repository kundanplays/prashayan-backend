from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import List
from app.services.s3 import s3_service
from app.routers.auth import get_current_user
from app.models.user import User

router = APIRouter()

@router.post("/product-image")
async def upload_product_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a product image to S3.
    Returns the S3 key and public URL.
    Admin only.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Read file content
    content = await file.read()
    
    # Upload to S3
    s3_key = s3_service.upload_file(
        file_content=content,
        file_name=f"product-{file.filename}",
        content_type=file.content_type
    )
    
    if not s3_key:
        raise HTTPException(status_code=500, detail="Failed to upload image")
    
    # Get public URL
    public_url = s3_service.get_public_url(s3_key)
    
    return {
        "s3_key": s3_key,
        "url": public_url,
        "message": "Image uploaded successfully"
    }


@router.post("/profile-image")
async def upload_profile_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a user profile image to S3.
    Returns the S3 key and public URL.
    """
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Read file content
    content = await file.read()
    
    # Upload to S3
    s3_key = s3_service.upload_file(
        file_content=content,
        file_name=f"user-{current_user.id}-{file.filename}",
        content_type=file.content_type
    )
    
    if not s3_key:
        raise HTTPException(status_code=500, detail="Failed to upload image")
    
    # Get public URL
    public_url = s3_service.get_public_url(s3_key)
    
    return {
        "s3_key": s3_key,
        "url": public_url,
        "message": "Profile image uploaded successfully"
    }


@router.post("/blog-image")
async def upload_blog_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a blog image to S3.
    Returns the S3 key and public URL.
    Admin only.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Read file content
    content = await file.read()
    
    # Upload to S3
    s3_key = s3_service.upload_file(
        file_content=content,
        file_name=f"blog-{file.filename}",
        content_type=file.content_type
    )
    
    if not s3_key:
        raise HTTPException(status_code=500, detail="Failed to upload image")
    
    # Get public URL
    public_url = s3_service.get_public_url(s3_key)
    
    return {
        "s3_key": s3_key,
        "url": public_url,
        "message": "Blog image uploaded successfully"
    }


@router.post("/review-image")
async def upload_review_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a review image to S3.
    Returns the S3 key and public URL.
    """
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Read file content
    content = await file.read()
    
    # Upload to S3
    s3_key = s3_service.upload_file(
        file_content=content,
        file_name=f"review-{file.filename}",
        content_type=file.content_type
    )
    
    if not s3_key:
        raise HTTPException(status_code=500, detail="Failed to upload image")
    
    # Get public URL
    public_url = s3_service.get_public_url(s3_key)
    
    return {
        "s3_key": s3_key,
        "url": public_url,
        "message": "Review image uploaded successfully"
    }


@router.delete("/image/{path:path}")
async def delete_image(
    path: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete an image from S3.
    Admin only.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    success = s3_service.delete_file(path)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete image")
    
    return {"message": "Image deleted successfully"}
