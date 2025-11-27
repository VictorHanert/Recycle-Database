"""Service for handling file uploads with support for local and cloud storage."""
from pathlib import Path
from typing import List, Optional
from uuid import uuid4
import os

from fastapi import UploadFile, HTTPException, status
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError

from app.config import get_settings


class FileUploadService:
    """Service for handling file uploads and deletions."""
    
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    MAX_IMAGES_PER_PRODUCT = 10
    ALLOWED_CONTENT_TYPES = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    
    def __init__(self, upload_base_path: str = "uploads/product_images"):
        """Initialize file upload service."""
        settings = get_settings()
        self.storage_mode = settings.storage_mode
        self.upload_base_path = Path(upload_base_path)
        
        if self.storage_mode == "local":
            self._ensure_upload_directory()
        elif self.storage_mode == "azure":
            self.azure_connection_string = settings.azure_storage_connection_string
            self.container_name = "product-images"
            self.blob_service_client = BlobServiceClient.from_connection_string(self.azure_connection_string)
            self._ensure_container()
        else:
            raise ValueError(f"Invalid storage_mode: {self.storage_mode}. Must be 'local' or 'azure'")
    
    def _ensure_upload_directory(self):
        """Create upload directory if it doesn't exist."""
        self.upload_base_path.mkdir(parents=True, exist_ok=True)
    
    def _ensure_container(self):
        """Ensure the Azure container exists."""
        try:
            self.blob_service_client.create_container(self.container_name)
        except ResourceExistsError:
            pass  # Container already exists
    
    async def validate_and_save_images(self, files: List[UploadFile], max_count: Optional[int] = None) -> List[str]:
        """Validate and save multiple image files."""
        if not files:
            return []
        
        max_count = max_count or self.MAX_IMAGES_PER_PRODUCT
        
        if len(files) > max_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum {max_count} images allowed"
            )
        
        saved_urls = []
        
        try:
            for file in files:
                url = await self._validate_and_save_single_image(file)
                saved_urls.append(url)
            
            return saved_urls
            
        except Exception:
            await self._cleanup_files(saved_urls)
            raise
    
    async def _validate_and_save_single_image(self, file: UploadFile) -> str:
        """Validate and save a single image file."""
        if file.content_type not in self.ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed types: {', '.join(self.ALLOWED_CONTENT_TYPES)}"
            )
        
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename is required"
            )
        
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in self.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file extension. Allowed extensions: {', '.join(self.ALLOWED_EXTENSIONS)}"
            )
        
        content = await file.read()
        file_size = len(content)
        
        if file_size > self.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size must be less than {self.MAX_FILE_SIZE / (1024 * 1024):.0f}MB"
            )
        
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty"
            )
        
        unique_filename = f"{uuid4()}{file_extension}"
        
        if self.storage_mode == "local":
            file_path = self.upload_base_path / unique_filename
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            return f"/{self.upload_base_path}/{unique_filename}"
        
        elif self.storage_mode == "azure":
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, 
                blob=unique_filename
            )
            blob_client.upload_blob(content, overwrite=True)
            return blob_client.url
        else:
            raise ValueError(f"Invalid storage mode: {self.storage_mode}")
    
    async def delete_images(self, image_urls: List[str]) -> None:
        """Delete image files from storage."""
        if not image_urls:
            return
        
        await self._cleanup_files(image_urls)
    
    async def _cleanup_files(self, image_urls: List[str]) -> None:
        """Clean up image files."""
        for url in image_urls:
            try:
                if self.storage_mode == "local":
                    filename = Path(url).name
                    file_path = self.upload_base_path / filename
                    if file_path.exists():
                        os.remove(file_path)
                elif self.storage_mode == "azure":
                    # Extract blob name from URL
                    blob_name = url.split('/')[-1]
                    blob_client = self.blob_service_client.get_blob_client(
                        container=self.container_name, 
                        blob=blob_name
                    )
                    blob_client.delete_blob()
            except Exception:
                pass
    
    def extract_filename_from_url(self, url: str) -> str:
        """Extract filename from image URL."""
        return Path(url).name
