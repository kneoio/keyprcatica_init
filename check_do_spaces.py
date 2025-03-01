import os
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, EndpointConnectionError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get environment variables
access_key = os.getenv('DO_SPACES_KEY')
secret_key = os.getenv('DO_SPACES_SECRET')
region = os.getenv('DO_SPACES_REGION')
endpoint = os.getenv('DO_SPACES_ENDPOINT')
bucket_name = os.getenv('DO_SPACES_BUCKET')

def list_files_in_bucket(client, bucket_name):
    try:
        # List objects in the bucket
        response = client.list_objects_v2(Bucket=bucket_name)
        print("API Response:", response)  # Debugging: Print the full API response

        # Check if the 'Contents' key exists in the response
        if 'Contents' in response:
            print(f"Files in bucket '{bucket_name}':")
            for file in response['Contents']:
                print(f"- {file['Key']} (Size: {file['Size']} bytes)")
        else:
            print(f"No files found in bucket '{bucket_name}'.")

    except Exception as e:
        print(f"Failed to list files: {e}")

def check_do_spaces_connection():
    try:
        # Initialize a session using DigitalOcean Spaces
        session = boto3.session.Session()
        client = session.client(
            's3',
            region_name=region,
            endpoint_url=f"https://{endpoint}",  # Add https:// here
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )

        # List buckets to test connectivity
        response = client.list_buckets()
        print("API Response:", response)  # Debugging: Print the full API response

        # Check if the 'Buckets' key exists in the response
        if 'Buckets' in response:
            print("Connection successful! Available buckets:")
            for bucket in response['Buckets']:
                print(f"- {bucket['Name']}")

            # Check if the specified bucket exists
            bucket_exists = any(bucket['Name'] == bucket_name for bucket in response['Buckets'])
            if bucket_exists:
                print(f"Bucket '{bucket_name}' exists.")
                # List files in the bucket
                list_files_in_bucket(client, bucket_name)
            else:
                print(f"Bucket '{bucket_name}' does not exist.")
        else:
            print("Connection successful, but no buckets found in your account.")

    except NoCredentialsError:
        print("Credentials not found. Please check your .env file.")
    except PartialCredentialsError:
        print("Incomplete credentials provided. Please check your .env file.")
    except EndpointConnectionError:
        print("Unable to connect to the DigitalOcean Spaces endpoint. Check your endpoint URL.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    check_do_spaces_connection()