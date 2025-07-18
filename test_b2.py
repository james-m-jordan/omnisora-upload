import os
from boto3.session import Session

# Test B2 connection
B2_KEY_ID = "005381ec3765c1f0000000002"
B2_APPLICATION_KEY = "K005w5wHDxxoGPN5s845FBmdeGQ9xhw"
B2_BUCKET = "freeload-uploads"
B2_ENDPOINT = "https://s3.us-east-005.backblazeb2.com"

print("Testing B2 connection...")
print(f"Bucket: {B2_BUCKET}")
print(f"Endpoint: {B2_ENDPOINT}")

try:
    session = Session()
    s3 = session.client(
        service_name='s3',
        endpoint_url=B2_ENDPOINT,
        aws_access_key_id=B2_KEY_ID,
        aws_secret_access_key=B2_APPLICATION_KEY
    )
    
    # Try to list bucket contents
    response = s3.list_objects_v2(Bucket=B2_BUCKET, MaxKeys=5)
    
    print("\n✅ B2 CONNECTION SUCCESSFUL!")
    print(f"Files in bucket: {response.get('KeyCount', 0)}")
    
    if 'Contents' in response:
        print("\nFirst few files:")
        for obj in response['Contents'][:5]:
            print(f"  - {obj['Key']} ({obj['Size']} bytes)")
    
except Exception as e:
    print(f"\n❌ B2 CONNECTION FAILED!")
    print(f"Error: {e}")
    print("\nCheck:")
    print("1. Are your B2 credentials correct?")
    print("2. Is the bucket name correct?")
    print("3. Is the bucket public or private?") 