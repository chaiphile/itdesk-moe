from typing import Optional
import boto3


class StorageS3Client:
    def __init__(self, *, endpoint_url: str, access_key: str, secret_key: str, region: str = "us-east-1", secure: bool = False):
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )

    def presign_put(self, *, bucket: str, key: str, content_type: str, expires_seconds: int) -> str:
        params = {"Bucket": bucket, "Key": key, "ContentType": content_type}
        url = self._client.generate_presigned_url(
            "put_object", Params=params, ExpiresIn=int(expires_seconds)
        )
        return url

    def presign_get(self, *, bucket: str, key: str, expires_seconds: int) -> str:
        params = {"Bucket": bucket, "Key": key}
        url = self._client.generate_presigned_url(
            "get_object", Params=params, ExpiresIn=int(expires_seconds)
        )
        return url
