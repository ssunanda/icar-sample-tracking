import requests
import json
import os
import time
import jwt  # pip install pyjwt
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import copy 

class ODRAPIClient:
    """Client for interacting with the Open Data Repository API"""
    
    def __init__(self, base_url: str, username: str = None, password: str = None):
        """
        Initialize the API client
        
        Args:
            base_url: The base URL of the API (e.g., "https://odr.io/api/v4")
            username: Username for authentication
            password: Password for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.token = None
        self.token_expiry = None
        self.headers = {
            'Content-Type': 'application/json'
        }
    
    def _is_token_expired(self) -> bool:
        """Check if the current token is expired or about to expire"""
        if not self.token or not self.token_expiry:
            return True
        # Refresh if less than 60 seconds remaining
        return time.time() > self.token_expiry - 60
    
    def authenticate(self, username: str = None, password: str = None) -> str:
        """
        Authenticate and get a Bearer token
        
        Args:
            username: Username (optional if provided in __init__)
            password: Password (optional if provided in __init__)
            
        Returns:
            The authentication token
        """
        username = username or self.username
        password = password or self.password
        
        if not username or not password:
            raise ValueError("Username and password are required for authentication")
        
        url = f"{self.base_url}/token"
        payload = {
            "username": username,
            "password": password
        }
        
        print(f"🔑 Authenticating user: {username}")
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            self.token = data.get('token')
            
            # Decode token to get expiration time
            try:
                decoded = jwt.decode(self.token, options={"verify_signature": False})
                self.token_expiry = decoded.get('exp', time.time() + 3600)
            except:
                # If decode fails, assume 1 hour validity
                self.token_expiry = time.time() + 3600
            
            self.headers['Authorization'] = f'Bearer {self.token}'
            print("✅ Authentication successful!")
            return self.token
        else:
            raise Exception(f"Authentication failed: {response.status_code} - {response.text}")
    
    def _ensure_authenticated(self):
        """Ensure we have a valid token, refresh if needed"""
        if self._is_token_expired():
            self.authenticate()
    
    def _make_request(self, method: str, url: str, **kwargs):
        """Make a request with automatic token refresh on 401"""
        self._ensure_authenticated()
        
        response = requests.request(method, url, headers=self.headers, **kwargs)
        
        # If we get a 401, refresh token and try again
        if response.status_code == 401:
            print("🔄 Token expired, refreshing...")
            self.authenticate()
            response = requests.request(method, url, headers=self.headers, **kwargs)
        
        return response
    
    def get_dataset(self, dataset_uuid: str, limit: Optional[int] = None, page: Optional[int] = None) -> Dict:
        """
        Get all records from a dataset
        
        Args:
            dataset_uuid: The UUID of the dataset
            limit: Number of records to return (optional)
            page: Page number for pagination (optional)
            
        Returns:
            Dataset information including records
        """
        url = f"{self.base_url}/dataset/{dataset_uuid}"
        
        params = {}
        if limit:
            params['limit'] = limit
        if page:
            params['page'] = page
        
        print(f"📋 Fetching dataset: {dataset_uuid}")
        response = self._make_request('GET', url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Retrieved {data.get('count', 0)} records")
            return data
        else:
            raise Exception(f"Failed to get dataset: {response.status_code} - {response.text}")
    
    def download_file(self, file_uuid: str, output_path: str = None, output_filename: str = None) -> Optional[str]:
        """
        Download a file
        
        Args:
            file_uuid: The UUID of the file to download
            output_path: Directory to save the file (default: current directory)
            output_filename: Name for the downloaded file (default: from server or file_uuid)
            
        Returns:
            Path to the downloaded file, or None if download failed
        """
        url = f"{self.base_url}/file/{file_uuid}"
        
        print(f"📥 Downloading file: {file_uuid}")
        response = self._make_request('GET', url, stream=True, timeout=30)
        
        if response.status_code == 403:
            print(f"⛔ Forbidden: You don't have access to file {file_uuid}")
            return None
        
        if response.status_code == 200:
            # Determine filename
            if not output_filename:
                # Try to get filename from Content-Disposition header
                content_disposition = response.headers.get('Content-Disposition', '')
                import re
                match = re.search(r'filename="?([^"]+)"?', content_disposition)
                if match:
                    output_filename = match.group(1)
                else:
                    output_filename = f"{file_uuid}.bin"
            
            # Determine full path
            if output_path:
                os.makedirs(output_path, exist_ok=True)
                filepath = os.path.join(output_path, output_filename)
            else:
                filepath = output_filename
            
            # Write file
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = os.path.getsize(filepath)
            print(f"✅ Downloaded: {output_filename} ({file_size:,} bytes)")
            return filepath
        else:
            print(f"❌ Failed to download file: {response.status_code}")
            return None
    
    def extract_and_download_all_files(self, dataset_uuid: str, output_dir: str = "downloads"):
        """
        Extract and download all files from a dataset recursively
        
        Args:
            dataset_uuid: The UUID of the dataset
            output_dir: Directory to save all files
        """
        # Get dataset
        dataset = self.get_dataset(dataset_uuid)
        
        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Save metadata
        metadata_file = os.path.join(output_dir, f"{dataset_uuid}_metadata.json")
        with open(metadata_file, 'w') as f:
            json.dump(dataset, f, indent=2)
        print(f"📝 Metadata saved to: {metadata_file}")
        
        # Process all records
        total_files = 0
        for i, record in enumerate(dataset.get('records', []), 1):
            record_name = record.get('record_name', record.get('record_uuid', f'record_{i}'))
            print(f"\n📦 Processing Record {i}: {record_name}")
            
            # Extract files from this record
            files_found = self._extract_files_from_record(record, output_dir, prefix="  ")
            total_files += files_found
        
        print(f"\n✅ Download complete! Total files: {total_files}")
    
    def print_metadata(self, dataset_uuid: str):
        """
        Print formatted metadata for a dataset
        
        Args:
            dataset_uuid: The UUID of the dataset
        """
        dataset = self.get_dataset(dataset_uuid)
        
        print("\n" + "="*60)
        print("📊 DATASET METADATA")
        print("="*60)
        print(f"Total Records: {dataset.get('count', 0)}")
        
        for i, record in enumerate(dataset.get('records', []), 1):
            print(f"\n📦 Record {i}:")
            print(f"  - Name: {record.get('record_name', 'N/A')}")
            print(f"  - UUID: {record.get('record_uuid', 'N/A')}")
            print(f"  - Database UUID: {record.get('database_uuid', 'N/A')}")
            print(f"  - Template UUID: {record.get('template_uuid', 'N/A')}")
            
            # Count files
            total_files = 0
            for field in record.get('fields', []):
                total_files += len(field.get('files', []))
            print(f"  - Total Files: {total_files}")
            
            # Print nested records info
            nested_records = record.get('records', [])
            if nested_records:
                print(f"  - Nested Records: {len(nested_records)}")
                for j, nested in enumerate(nested_records, 1):
                    print(f"    └─ {nested.get('record_name', 'N/A')} (UUID: {nested.get('record_uuid', 'N/A')})")
        
        print("="*60 + "\n")
    
    def create_record(self, dataset_uuid: str, user_email: str = None) -> Dict:
        """
        Create a new record in a dataset
        
        Args:
            dataset_uuid: The UUID of the dataset
            user_email: Email of the user creating the record
            
        Returns:
            The newly created record data
        """
        user_email = user_email or self.username
        url = f"{self.base_url}/dataset/{dataset_uuid}/record"
        
        # Note: Using form data, not JSON
        data = {
            'user_email': user_email
        }
        
        print(f"📝 Creating new record in dataset: {dataset_uuid}")
        
        # Remove Content-Type header for form data
        headers = self.headers.copy()
        headers.pop('Content-Type', None)
        
        response = self._make_request('POST', url, data=data, timeout=30)
        
        if response.status_code == 200:
            record = response.json()
            print(f"✅ Created new record: {record.get('record_name')} (UUID: {record.get('record_uuid')})")
            return record
        else:
            raise Exception(f"Failed to create record: {response.status_code} - {response.text}")
    
    def upload_file(self, file_path: str, record_uuid: str, dataset_uuid: str, 
                   template_field_uuid: str, field_uuid: str = "", 
                   name: str = None, user_email: str = None) -> Dict:
        """
        Upload a file to a record
        
        Args:
            file_path: Path to the file to upload
            record_uuid: UUID of the record to attach the file to
            dataset_uuid: UUID of the dataset
            template_field_uuid: UUID of the template field
            field_uuid: UUID of the field (optional)
            name: Description/name for the file
            user_email: Email of the user uploading the file
            
        Returns:
            Response data from the upload
        """
        user_email = user_email or self.username
        url = f"{self.base_url}/file"
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Prepare form data
        with open(file_path, 'rb') as f:
            files = {
                'file': (os.path.basename(file_path), f, 'application/octet-stream')
            }
            
            data = {
                'name': name or os.path.basename(file_path),
                'dataset_uuid': dataset_uuid,
                'user_email': user_email,
                'field_uuid': field_uuid,
                'template_field_uuid': template_field_uuid,
                'record_uuid': record_uuid
            }
            
            print(f"📤 Uploading file: {os.path.basename(file_path)}")
            
            # Remove Content-Type header for multipart form data
            headers = self.headers.copy()
            headers.pop('Content-Type', None)
            
            response = requests.post(url, headers=headers, files=files, data=data, timeout=60)
            
            # Handle 401 and retry
            if response.status_code == 401:
                print("🔄 Token expired, refreshing...")
                self.authenticate()
                headers = self.headers.copy()
                headers.pop('Content-Type', None)
                # Need to reopen file
                with open(file_path, 'rb') as f2:
                    files = {'file': (os.path.basename(file_path), f2, 'application/octet-stream')}
                    response = requests.post(url, headers=headers, files=files, data=data, timeout=60)
        
        if response.status_code == 200:
            print(f"✅ File uploaded successfully!")
            return response.json()
        else:
            raise Exception(f"Failed to upload file: {response.status_code} - {response.text}")
    

    def _extract_files_from_record(self, record: dict, output_dir: str, prefix: str = "") -> int:
        """
        Recursively extract and download files from a record
        
        Returns the number of files found
        """
        files_count = 0
        
        # Check fields for files
        for field in record.get('fields', []):
            for file_info in field.get('files', []):
                file_uuid = file_info.get('file_uuid')
                original_name = file_info.get('original_name', f"{file_uuid}.bin")
                
                if file_uuid:
                    print(f"{prefix}📄 Found file: {original_name}")
                    result = self.download_file(file_uuid, output_dir, original_name)
                    if result:
                        files_count += 1
        
        # Process nested records recursively
        for child_record in record.get('records', []):
            child_name = child_record.get('record_name', 'nested_record')
            print(f"{prefix}📂 Nested record: {child_name}")
            files_count += self._extract_files_from_record(child_record, output_dir, prefix + "  ")
        
        return files_count
    

    # -------------------------------------------------
    # ➊ Fetch a single record by UUID
    # -------------------------------------------------
    def get_record(self, record_uuid: str) -> Dict:
        """
        Fetch one record (all fields, nested data, files).

        Args:
            record_uuid: the UUID of the record you want.

        Returns:
            A full record dictionary identical to what you showed in the
            dev-supplied example.
        """
        url = f"{self.base_url}/dataset/record/{record_uuid}"
        response = self._make_request("GET", url, timeout=30)
        print(f"Fetching record: {record_uuid}")

        if response.status_code == 200:
            return response.json()
        raise Exception(f"Failed to fetch record: {response.status_code} - {response.text}")

    # -------------------------------------------------
    # ➋ Push an *existing* record back to the server
    # -------------------------------------------------
    def push_record(self, record_dict: Dict, user_email: Optional[str] = None) -> Dict:
        """
        Overwrite an existing record on the server.

        Args:
            record_dict : complete record payload, already edited locally
            user_email  : will be sent if required by the API (keep = None to omit)
        """
        # ------------------------------------------------------------------
        # 1) sanitise the payload ------------------------------------------
        # ------------------------------------------------------------------
        rec = copy.deepcopy(record_dict)        # work on a copy

        # strip unwanted top-level keys
        rec.pop("template_uuid", None)

        # strip unwanted keys inside each field
        for fld in rec.get("fields", []):
            fld.pop("template_field_uuid", None)

        # add user_email only if the endpoint still expects it
        if user_email:
            rec["user_email"] = user_email

        # ------------------------------------------------------------------
        # 2) POST the cleaned record (record_uuid is now at top level) ------
        # ------------------------------------------------------------------
        url = f"{self.base_url}/dataset/record"
        rsp = self._make_request("POST", url, json=rec, timeout=30)

        if rsp.status_code == 200:
            print("✅ Record updated successfully!")
            return rsp.json()

        raise RuntimeError(
            f"Failed to update record: {rsp.status_code} – {rsp.text}"
        )

    def set_field_value(self, record: Dict, field_name: str, new_value) -> None:
        """
        Mutate record['fields'] in-place.
        Creates the field if it doesn’t exist.
        """
        for fld in record.get("fields", []):
            if fld.get("field_name") == field_name:
                if "value" in fld:
                    fld["value"] = new_value              # scalar
                elif "selected" in fld:                   # checkbox / radio
                    fld["selected"] = int(bool(new_value))
                return
        # Field not present – append a new one
        record.setdefault("fields", []).append({
            "field_name": field_name,
            "field_uuid": "",                             # leave blank if unknown
            "template_field_uuid": None,
            "value": new_value
        })

# Example usage
def main():
    # Configuration
    BASE_URL = "https://odr.io/api/v4"
    USERNAME = "amshahid@ncsu.edu"
    PASSWORD = "qkh8fjd6adh*NPU!ekn"  # Replace with your actual password
    DATASET_UUID = "063c0d3d4bd183ab0dda87c544ae"
    
    # Initialize client
    client = ODRAPIClient(BASE_URL, USERNAME, PASSWORD)
    client.authenticate()
    
    try:
        # 1. Print metadata
        print("=== Dataset Metadata ===")
        client.print_metadata(DATASET_UUID)
        
        # 2. Download all files from the dataset
        print("\n=== Downloading all files from dataset ===")
        client.extract_and_download_all_files(DATASET_UUID, output_dir="downloads")
        
        # 3. Test downloading a specific file
        print("\n=== Testing specific file download ===")
        # Replace with an actual file UUID from your dataset
        test_file_uuid = "33618d62474cbf4703c60a063ad1"
        result = client.download_file(test_file_uuid, output_path="test_downloads", 
                                    output_filename="test_file.txt")
        if result:
            print(f"✅ Test download successful: {result}")
        
        # 4. Example: Create a new record (uncomment to test)
        #print("\n=== Creating new record ===")
        #new_record = client.create_record(DATASET_UUID)
        #print(f"New record created: {json.dumps(new_record, indent=2)}")
        
        # 5. Example: Upload a file to a record (uncomment to test)
        # print("\n=== Uploading file ===")
        # record_uuid = '60862b03967fc4e8a73d57326b39'
        # field_uuid = "a65467babf8a1ac7e1d7319e3928"
        #
        # # Create a test file
        # test_file_path = "test_upload.txt"
        # with open(test_file_path, 'w') as f:
        #     f.write("This is a test file for upload")
        #
        # upload_result = client.upload_file(
        #     file_path=test_file_path,
        #     record_uuid=record_uuid,
        #     field_uuid=field_uuid,
        #     template_field_uuid="",
        #     dataset_uuid=DATASET_UUID,
        #     name="Test Upload File",
        #     user_email=""
        # )
        # print(f"Upload result: {json.dumps(upload_result, indent=2)}")

        # get spcific record edit fields then push it back
        print("\n=== Fetching specific record for editing ===")
        TARGET_RECORD_UUID = "60862b03967fc4e8a73d57326b39"  # Replace with actual record UUID
        record = client.get_record(TARGET_RECORD_UUID)

        ## change field
        client.set_field_value(record, field_name="Source", new_value="RRUFF (v2)")
        client.push_record(record)        

        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


# Helper functions for specific tasks
def test_file_operations():
    """Test creating records and uploading files"""
    BASE_URL = "https://odr.io/api/v4"
    USERNAME = "amshahid@ncsu.edu"
    PASSWORD = "qkh8fjd6adh*NPU!ekn"
    DATASET_UUID = "d296255ce138360bde9f57d1d33e"
    
    client = ODRAPIClient(BASE_URL, USERNAME, PASSWORD)
    
    # Create a new record
    print("Creating new record...")
    new_record = client.create_record(DATASET_UUID)
    record_uuid = new_record['record_uuid']
    print(f"Created record: {record_uuid}")
    
    # To upload a file, you need to know the template_field_uuid
    # You can find this by examining the metadata of existing records
    # that have files attached
    
    # Example upload (you need to provide the correct template_field_uuid)
    # template_field_uuid = "get-this-from-metadata"
    # client.upload_file(
    #     "path/to/your/file.txt",
    #     record_uuid=record_uuid,
    #     dataset_uuid=DATASET_UUID,
    #     template_field_uuid=template_field_uuid,
    #     name="My uploaded file"
    # )


# Quick function for downloading everything
def quick_download_all(dataset_uuid: str, output_dir: str = "downloads"):
    """
    Quick function to download all files from a dataset
    
    Args:
        dataset_uuid: The UUID of the dataset
        output_dir: Directory to save files (default: "downloads")
    """
    BASE_URL = "https://odr.io/api/v4"
    USERNAME = "amshahid@ncsu.edu"
    PASSWORD = "qkh8fjd6adh*NPU!ekn"  # Replace with your actual password
    
    client = ODRAPIClient(BASE_URL, USERNAME, PASSWORD)
    client.extract_and_download_all_files(dataset_uuid, output_dir)


if __name__ == "__main__":
    main()
    
    # Uncomment to test file operations
    # test_file_operations()
    
    # Uncomment to examine dataset structure
    # client = ODRAPIClient("https://odr.io/api/v4", "amshahid@ncsu.edu", "qkh8fjd6adh*NPU!ekn")
    # client.examine_dataset_structure("d296255ce138360bde9f57d1d33e")