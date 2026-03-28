import boto3
from botocore.exceptions import ClientError
from typing import Any, Dict, Optional
from fastapi import UploadFile
from app.connectors.storage.base_storage import BaseStorage

class S3Storage(BaseStorage):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # Sanitize region: Extract 'ap-south-1' from 'Mumbai (ap-south-1)' if needed
        raw_region = config.get('region')
        region = raw_region
        if raw_region and ' ' in raw_region:
            # Try to find something that looks like an AWS region (e.g., ap-south-1)
            import re
            match = re.search(r'[a-z]{2}-[a-z]+-\d', raw_region)
            if match:
                region = match.group(0)

        # Strip whitespace from keys (common cause of SignatureDoesNotMatch)
        access_key = config.get('access_key_id', '').strip()
        secret_key = config.get('secret_key', '').strip()
        
        # AWS S3 doesn't like empty string for endpoint_url
        endpoint_url = config.get('endpoint_url')
        if not endpoint_url or endpoint_url.strip() == "":
            endpoint_url = None
            
        # Force Signature Version 4 for pre-signed URLs in newer regions (like Mumbai)
        from botocore.config import Config
        s3_config = Config(
            signature_version='s3v4',
            s3={'addressing_style': 'virtual'}
        )

        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            endpoint_url=endpoint_url,
            config=s3_config
        )
        self.bucket_name = config.get('bucket_name')

    async def upload_file(self, file: UploadFile, remote_path: str) -> str:
        try:
            # We use upload_fileobj for streaming
            self.s3_client.upload_fileobj(
                file.file,
                self.bucket_name,
                remote_path,
                ExtraArgs={'ContentType': file.content_type}
            )
            return remote_path
        except ClientError as e:
            print(f"S3 Upload failed: {e}")
            raise e

    async def get_file_url(self, remote_path: str, expires_in: int = 3600) -> str:
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': remote_path
                },
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            print(f"S3 URL generation failed: {e}")
            raise e

    async def delete_file(self, remote_path: str) -> bool:
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=remote_path
            )
            return True
        except ClientError as e:
            print(f"S3 Delete failed: {e}")
            return False

    async def test_connection(self) -> bool:
        try:
            # Try to list objects (with limit 1) to verify credentials and bucket existence
            self.s3_client.list_objects_v2(Bucket=self.bucket_name, MaxKeys=1)
            return True
        except Exception as e:
            print(f"DEBUG - S3 connection test failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def download_file(self, remote_path: str) -> Optional[bytes]:
        try:
            import io
            buffer = io.BytesIO()
            self.s3_client.download_fileobj(self.bucket_name, remote_path, buffer)
            return buffer.getvalue()
        except ClientError as e:
            print(f"S3 Download failed: {e}")
            return None
