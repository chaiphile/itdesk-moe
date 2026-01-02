from typing import Optional
import boto3
from urllib.parse import urlsplit, urlunsplit


class StorageS3Client:
    def __init__(self, *, endpoint_url: str, access_key: str, secret_key: str, region: str = "us-east-1", secure: bool = False, public_base_url: Optional[str] = None):
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )
        self._public_base_url = public_base_url

    def _rewrite_presigned_url(self, url: str) -> str:
        if not self._public_base_url:
            return url

        # Parse both URLs and replace scheme+netloc while preserving path and query verbatim
        orig = urlsplit(url)
        public = urlsplit(self._public_base_url)

        new = urlunsplit((public.scheme, public.netloc, orig.path, orig.query, orig.fragment))
        return new

    def presign_put(self, *, bucket: str, key: str, content_type: str, expires_seconds: int) -> str:
        params = {"Bucket": bucket, "Key": key, "ContentType": content_type}
        url = self._client.generate_presigned_url(
            "put_object", Params=params, ExpiresIn=int(expires_seconds)
        )
        return self._rewrite_presigned_url(url)

    def presign_get(self, *, bucket: str, key: str, expires_seconds: int) -> str:
        params = {"Bucket": bucket, "Key": key}
        url = self._client.generate_presigned_url(
            "get_object", Params=params, ExpiresIn=int(expires_seconds)
        )
        return self._rewrite_presigned_url(url)
