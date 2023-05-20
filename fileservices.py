import json
from boto3 import session
from botocore.client import Config
from dotenv import load_dotenv
import os

load_dotenv()

# Setup Boto3 Session ---------------------------------------------------------------

ACCESS_ID = os.environ.get('ACCESS_ID')
SECRET_KEY = os.environ.get('SECRET_KEY')

spaces_id = "exon-hosting"
# Initiate session

class DigitalOceanSpaces:
    def __init__(self, spaces_id, region_name, endpoint_url, aws_access_key_id, aws_secret_access_key):
        self.spaces_id = spaces_id
        self.session = session.Session()
        self.clientAWS = self.session.client('s3',
            region_name=region_name,
            endpoint_url=endpoint_url,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key)

    def get_available_files(self, json_response):
        files = []
        for item in json_response:
            if 'Key' in item:
                file_path = item['Key']
                if file_path.endswith('/'):
                    # Skip directories
                    continue
                files.append(file_path)
        return files

    def upload_file(self, local, remote):
        self.clientAWS.upload_file(local, self.spaces_id, remote)

    def download_file(self, local, remote):
        self.clientAWS.download_file(self.spaces_id, remote, local)

    def list_files(self, path):
        response = self.clientAWS.list_objects(Bucket=self.spaces_id)
        files = self.get_available_files(response['Contents'])
        # Files returns all files in the bucket, so we need to filter out the ones that don't match the path
        files = [file for file in files if file.startswith(path)]
        return files
        

    def delete_file(self, file_name):
        self.clientAWS.delete_object(Bucket=self.spaces_id, Key=file_name)

    def db_write(self, key, value, db_name='database.json'):
        self.download_file(db_name, db_name)
        with open(db_name, 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = {}
        data[key] = value
        with open(db_name, 'w') as f:
            json.dump(data, f)
        self.upload_file(db_name, db_name)

    def db_read(self, key, db_name='database.json'):
        self.download_file(db_name, db_name)
        with open(db_name, 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = {}
        return data.get(key)
