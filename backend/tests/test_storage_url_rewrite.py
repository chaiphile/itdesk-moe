from app.core.storage_s3 import StorageS3Client


def test_rewrite_presigned_url_keeps_query_and_switches_netloc():
    # Simulate a presigned URL generated against internal host
    internal_url = "http://minio:9000/bucket/key?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=ABC123"
    client = StorageS3Client(endpoint_url="http://minio:9000", access_key="a", secret_key="b", public_base_url="http://localhost:9000")

    # Use the private _rewrite_presigned_url util to assert behaviour
    out = client._rewrite_presigned_url(internal_url)

    assert out.startswith("http://localhost:9000")
    # Query string must be preserved exactly
    assert out.split("?", 1)[1] == internal_url.split("?", 1)[1]
