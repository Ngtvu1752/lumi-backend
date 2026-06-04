import boto3
from app.core.config import Settings

def _get_s3_client(settings: Settings):
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )

def generate_presigned_url(settings: Settings, object_key: str, expiration: int = 3600) -> str:
    s3_client = _get_s3_client(settings)
    try: 
        url = s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": settings.S3_SOUNDS_BUCKET, "Key": object_key},
            ExpiresIn=expiration,
        )
        return url

    except Exception as e:
        raise ValueError(f"Failed to generate presigned URL for {object_key}: {e}")