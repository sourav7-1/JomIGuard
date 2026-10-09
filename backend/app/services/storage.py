import io
from functools import lru_cache

from minio import Minio

from app.core.config import settings


class Storage:
    def __init__(self, client: Minio, bucket: str):
        self.client = client
        self.bucket = bucket

    def ensure_bucket(self) -> None:
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def upload(self, key: str, data: bytes, content_type: str) -> None:
        self.client.put_object(
            self.bucket, key, io.BytesIO(data), len(data), content_type=content_type
        )


@lru_cache
def get_storage() -> Storage:
    client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=False,  # plain http inside the docker network
    )
    return Storage(client, settings.minio_bucket)
