import os
import uuid
from datetime import datetime
from pathlib import Path
from fastapi import UploadFile
from sqlalchemy.orm import Session
from werkzeug.utils import secure_filename

from app.services.storage_service import StorageService

async def save_upload_file(
    upload_file: UploadFile, 
    folder_path: str, 
    prefix: str,
    db: Session = None,
    tenant_id: uuid.UUID = None
) -> str:
    """
    Saves a FastAPI UploadFile. 
    If a database session and tenant ID are provided, it attempts to save to cloud storage.
    Otherwise, it falls back to the local filesystem.
    Returns the final path or cloud key.
    """
    # 1. Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = os.path.splitext(upload_file.filename)[1]
    base_name = f"{prefix}_{timestamp}_{uuid.uuid4().hex[:8]}"
    filename = secure_filename(f"{base_name}{ext}")

    # 2. Check for Cloud Storage
    if db:
        storage_driver = StorageService.get_tenant_storage(db)
        if storage_driver:
            # Cloud Path: folder_path/filename
            cloud_key = f"{folder_path}/{filename}"
            await storage_driver.upload_file(upload_file, cloud_key)
            return cloud_key

    # 3. Fallback to Local Storage
    UPLOAD_DIR = "uploads"
    target_dir = os.path.join(UPLOAD_DIR, folder_path)
    os.makedirs(target_dir, exist_ok=True)
    
    file_path = os.path.join(target_dir, filename)
    
    import anyio
    async with await anyio.open_file(file_path, "wb") as f:
        while content := await upload_file.read(1024 * 1024):
            await f.write(content)
            
    await upload_file.seek(0)
    return file_path
