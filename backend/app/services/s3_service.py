import uuid
from typing import BinaryIO

import boto3
from botocore.exceptions import ClientError

from app.config.settings import settings


class S3Service:
    def __init__(self):
        self.bucket_name = settings.S3_BUCKET_NAME
        self.prefix = settings.AWS_S3_PREFIX

        self.s3_client = boto3.client(
            "s3",
            region_name=settings.AWS_REGION,
        )

    def upload_file(
        self,
        file_obj: BinaryIO,
        filename: str,
        content_type: str = "application/pdf",
    ) -> str:
        """
        Upload a file to S3 and return its S3 object key.
        """

        unique_filename = f"{uuid.uuid4()}_{filename}"

        s3_key = f"{self.prefix}{unique_filename}"

        self.s3_client.upload_fileobj(
            file_obj,
            self.bucket_name,
            s3_key,
            ExtraArgs={
                "ContentType": content_type,
            },
        )

        return s3_key

    def delete_file(self, s3_key: str) -> None:
        """Delete a file from S3."""

        self.s3_client.delete_object(
            Bucket=self.bucket_name,
            Key=s3_key,
        )

    def generate_download_url(
        self,
        s3_key: str,
        expires_in: int = 3600,
    ) -> str:
        """
        Generate a temporary download URL for a private S3 file.
        """

        return self.s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": s3_key,
            },
            ExpiresIn=expires_in,
        )