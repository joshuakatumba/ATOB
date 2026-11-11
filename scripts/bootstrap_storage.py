"""Create the local private bucket; do not grant public access."""

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from civis.config import Settings

settings = Settings.from_env()
if settings.environment == "production":
    raise SystemExit("Production storage is provisioned externally")
client = boto3.client(
    "s3",
    endpoint_url=settings.s3_endpoint,
    aws_access_key_id=settings.s3_access_key.get_secret_value(),
    aws_secret_access_key=settings.s3_secret_key.get_secret_value(),
    config=Config(region_name="us-east-1", s3={"addressing_style": "path"}),
)
try:
    client.head_bucket(Bucket=settings.s3_bucket)
except ClientError as exc:
    if exc.response["ResponseMetadata"]["HTTPStatusCode"] != 404:
        raise SystemExit("Storage bootstrap failed") from None
    client.create_bucket(Bucket=settings.s3_bucket)
print("Private local bucket available")
