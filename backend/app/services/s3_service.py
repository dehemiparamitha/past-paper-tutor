import os
import re
import uuid
import logging
from pathlib import Path
from typing import BinaryIO, Optional

try:
    import boto3
    from botocore.exceptions import ClientError, BotoCoreError
except ImportError:
    boto3 = None
    ClientError = Exception  # type: ignore
    BotoCoreError = Exception  # type: ignore

from app.config.settings import settings

logger = logging.getLogger(__name__)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by stripping directory paths and keeping only
    alphanumeric characters, hyphens, underscores, and dots.
    """
    clean_name = Path(filename).name
    # Replace whitespace with underscore
    clean_name = re.sub(r"\s+", "_", clean_name)
    # Strip any characters that aren't alphanumeric, dot, underscore, or dash
    clean_name = re.sub(r"[^a-zA-Z0-9._-]", "", clean_name)
    # Ensure it doesn't start with a dot or dash
    clean_name = clean_name.lstrip(".-")
    if not clean_name:
        clean_name = "document.pdf"
    return clean_name


class S3Service:
    def __init__(
        self,
        bucket_name: Optional[str] = None,
        region_name: Optional[str] = None,
        prefix: Optional[str] = None,
    ):
        self.bucket_name = bucket_name or settings.S3_BUCKET_NAME
        self.region_name = region_name or settings.AWS_REGION
        raw_prefix = prefix or settings.AWS_S3_PREFIX or "documents/"
        self.prefix = raw_prefix if raw_prefix.endswith("/") else f"{raw_prefix}/"

        # Boto3 client uses standard credential chain:
        # 1. Environment variables (if provided)
        # 2. EC2 Instance Metadata IAM role (in production)
        # 3. ~/.aws/credentials (local development)
        if boto3 is not None:
            self.s3_client = boto3.client(
                "s3",
                region_name=self.region_name,
            )
        else:
            self.s3_client = None

    def upload_file(
        self,
        file_obj: BinaryIO,
        filename: str,
        content_type: str = "application/pdf",
    ) -> str:
        """
        Upload a file to S3 and return its S3 object key.
        """
        clean_name = sanitize_filename(filename)
        unique_filename = f"{uuid.uuid4()}_{clean_name}"
        s3_key = f"{self.prefix}{unique_filename}"

        try:
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    "ContentType": content_type,
                },
            )
            logger.info("Successfully uploaded object to S3: %s", s3_key)
            return s3_key
        except (ClientError, BotoCoreError) as e:
            logger.error("Failed to upload file to S3 (bucket: %s, key: %s): %s", self.bucket_name, s3_key, e)
            raise

    def download_file(self, s3_key: str, local_path: str) -> None:
        """
        Download an object from S3 to a local file path.
        """
        try:
            os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)
            self.s3_client.download_file(
                Bucket=self.bucket_name,
                Key=s3_key,
                Filename=local_path,
            )
            logger.info("Successfully downloaded S3 object %s to %s", s3_key, local_path)
        except (ClientError, BotoCoreError) as e:
            logger.error("Failed to download S3 object %s: %s", s3_key, e)
            raise

    def delete_file(self, s3_key: str) -> bool:
        """
        Delete a file from S3.
        Returns True if successful.
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key,
            )
            logger.info("Successfully deleted S3 object: %s", s3_key)
            return True
        except (ClientError, BotoCoreError) as e:
            logger.error("Failed to delete S3 object %s: %s", s3_key, e)
            raise

    def generate_download_url(
        self,
        s3_key: str,
        expires_in: int = 3600,
    ) -> str:
        """
        Generate a temporary presigned download URL for an S3 object.
        """
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": s3_key,
                },
                ExpiresIn=expires_in,
            )
            return url
        except (ClientError, BotoCoreError) as e:
            logger.error("Failed to generate presigned URL for %s: %s", s3_key, e)
            raise

    def file_exists(self, s3_key: str) -> bool:
        """Check if an S3 object exists."""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "404":
                return False
            raise
