"""
Storage adapter to support both local filesystem and Google Cloud Storage.
"""
import os
from typing import BinaryIO
from google.cloud import storage

class StorageAdapter:
    """Abstraction layer for file storage (local or GCS)"""
    
    def __init__(self):
        self.backend = os.getenv("STORAGE_BACKEND", "local")  # 'local' or 'gcs'
        self.bucket_name = os.getenv("GCS_BUCKET")
        
        if self.backend == "gcs":
            if not self.bucket_name:
                raise ValueError("GCS_BUCKET environment variable must be set for GCS backend")
            self.client = storage.Client()
            self.bucket = self.client.bucket(self.bucket_name)
    
    def save_file(self, file_content: BinaryIO, file_path: str):
        """Save file to storage"""
        if self.backend == "gcs":
            blob = self.bucket.blob(file_path)
            blob.upload_from_file(file_content, rewind=True)
        else:
            # Local filesystem
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'wb') as f:
                file_content.seek(0)
                f.write(file_content.read())
    
    def read_file(self, file_path: str) -> bytes:
        """Read file from storage"""
        if self.backend == "gcs":
            blob = self.bucket.blob(file_path)
            return blob.download_as_bytes()
        else:
            with open(file_path, 'rb') as f:
                return f.read()
    
    def file_exists(self, file_path: str) -> bool:
        """Check if file exists"""
        if self.backend == "gcs":
            blob = self.bucket.blob(file_path)
            return blob.exists()
        else:
            return os.path.exists(file_path)
    
    def list_files(self, prefix: str):
        """List files with prefix"""
        if self.backend == "gcs":
            blobs = self.bucket.list_blobs(prefix=prefix)
            return [blob.name for blob in blobs]
        else:
            import glob
            return glob.glob(f"{prefix}/*")
    
    def get_public_url(self, file_path: str) -> str:
        """Get public URL for file"""
        if self.backend == "gcs":
            blob = self.bucket.blob(file_path)
            return blob.public_url
        else:
            # For local, return relative path (will be served by FastAPI)
            return f"/uploads/{os.path.basename(file_path)}"
