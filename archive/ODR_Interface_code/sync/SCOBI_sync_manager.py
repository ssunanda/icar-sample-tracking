"""
SCOBI Sync Manager
==================
Bidirectional synchronization between local SCOBI files and ODR repository.

Sync Strategy:
1. Download ODR metadata (checksums, timestamps)
2. Compare with local state cache
3. Detect conflicts (both changed since last sync)
4. Push/pull based on change detection
"""

import os
import json
import hashlib
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from ODR_API_Client import ODRAPIClient


class SyncState:
    """Tracks the last known state of files for conflict detection"""

    def __init__(self, cache_file: str = ".scobi_sync_cache.json"):
        self.cache_file = cache_file
        self.state = self._load_cache()

    def _load_cache(self) -> Dict:
        """Load the last known sync state"""
        if os.path.exists(self.cache_file):
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        return {"files": {}, "last_sync": None}

    def _save_cache(self):
        """Save current sync state"""
        self.state["last_sync"] = datetime.now().isoformat()
        with open(self.cache_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def get_file_state(self, file_id: str) -> Optional[Dict]:
        """Get last known state for a file"""
        return self.state["files"].get(file_id)

    def update_file_state(self, file_id: str, checksum: str, odr_timestamp: str, local_timestamp: float):
        """Update state after successful sync"""
        self.state["files"][file_id] = {
            "checksum": checksum,
            "odr_timestamp": odr_timestamp,
            "local_timestamp": local_timestamp
        }
        self._save_cache()


class SCOBISyncManager:
    """Manages bidirectional sync between local files and ODR"""

    def __init__(self, odr_client: ODRAPIClient, data_dir: str = "data"):
        self.client = odr_client
        self.data_dir = data_dir
        self.sync_state = SyncState()

    def compute_checksum(self, filepath: str) -> str:
        """Compute MD5 checksum of a file"""
        md5 = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                md5.update(chunk)
        return md5.hexdigest()

    def get_local_file_info(self, filepath: str) -> Dict:
        """Get local file metadata"""
        if not os.path.exists(filepath):
            return None

        return {
            "checksum": self.compute_checksum(filepath),
            "timestamp": os.path.getmtime(filepath),
            "size": os.path.getsize(filepath)
        }

    def get_odr_file_info(self, record: Dict, field_name: str = "Data File") -> Dict:
        """Extract file info from ODR record"""
        for field in record.get("fields", []):
            if field.get("field_name") == field_name:
                files = field.get("files", [])
                if files:
                    file_info = files[0]  # Assuming one file per field
                    return {
                        "file_uuid": file_info.get("file_uuid"),
                        "original_name": file_info.get("original_name"),
                        "odr_timestamp": field.get("_field_metadata", {}).get("_update_date"),
                        "size": int(file_info.get("file_size", 0))
                    }
        return None

    def detect_change_type(self, local_info: Dict, odr_info: Dict,
                          cached_state: Dict, file_id: str) -> str:
        """
        Detect what kind of change occurred:
        - 'no_change': Nothing changed
        - 'local_only': Only local file changed
        - 'odr_only': Only ODR file changed
        - 'conflict': Both changed since last sync
        - 'new_local': File exists locally but not in ODR
        - 'new_odr': File exists in ODR but not locally
        """

        # New files
        if local_info and not odr_info:
            return 'new_local'
        if odr_info and not local_info:
            return 'new_odr'

        # No cached state - first sync
        if not cached_state:
            if local_info and odr_info:
                # Compare checksums
                local_checksum = local_info["checksum"]
                # We'll need to download ODR file to compare
                return 'first_sync'
            return 'no_change'

        # Check what changed since last sync
        local_changed = local_info["checksum"] != cached_state.get("checksum")
        odr_changed = odr_info["odr_timestamp"] != cached_state.get("odr_timestamp")

        if not local_changed and not odr_changed:
            return 'no_change'
        elif local_changed and not odr_changed:
            return 'local_only'
        elif odr_changed and not local_changed:
            return 'odr_only'
        else:
            return 'conflict'

    def sync_dataset(self, dataset_uuid: str, conflict_strategy: str = 'ask') -> Dict:
        """
        Sync entire dataset between local and ODR

        Args:
            dataset_uuid: ODR dataset UUID
            conflict_strategy: How to handle conflicts
                - 'ask': Prompt user for each conflict
                - 'local_wins': Local changes take precedence
                - 'odr_wins': ODR changes take precedence
                - 'newest_wins': Use timestamp to decide

        Returns:
            Dictionary with sync results
        """
        print("🔄 Starting sync process...")

        # Get all records from ODR
        dataset = self.client.get_dataset(dataset_uuid)

        results = {
            'no_change': [],
            'pulled': [],
            'pushed': [],
            'conflicts': [],
            'errors': []
        }

        for record in dataset.get('records', []):
            record_name = record.get('record_name')
            record_uuid = record.get('record_uuid')

            try:
                result = self.sync_record(record, conflict_strategy)
                results[result['status']].append({
                    'record': record_name,
                    'action': result.get('action'),
                    'file': result.get('file')
                })
            except Exception as e:
                results['errors'].append({
                    'record': record_name,
                    'error': str(e)
                })
                print(f"❌ Error syncing {record_name}: {e}")

        # Print summary
        self._print_sync_summary(results)

        return results

    def sync_record(self, record: Dict, conflict_strategy: str = 'ask') -> Dict:
        """Sync a single record"""
        record_name = record.get('record_name')
        record_uuid = record.get('record_uuid')

        # Get ODR file info
        odr_info = self.get_odr_file_info(record)

        # Determine local file path (you'll need to map record to local path)
        # This is a placeholder - adjust based on your naming convention
        local_filepath = self._get_local_filepath_for_record(record)

        # Get local file info
        local_info = self.get_local_file_info(local_filepath) if local_filepath else None

        # Get cached state
        file_id = f"{record_uuid}"
        cached_state = self.sync_state.get_file_state(file_id)

        # Detect change type
        change_type = self.detect_change_type(local_info, odr_info, cached_state, file_id)

        print(f"📊 {record_name}: {change_type}")

        # Handle based on change type
        if change_type == 'no_change':
            return {'status': 'no_change', 'file': local_filepath}

        elif change_type == 'local_only':
            # Push local changes to ODR
            print(f"  ⬆️  Pushing local changes to ODR...")
            self._push_to_odr(record, local_filepath)
            self.sync_state.update_file_state(
                file_id,
                local_info["checksum"],
                datetime.now().isoformat(),
                local_info["timestamp"]
            )
            return {'status': 'pushed', 'action': 'local→ODR', 'file': local_filepath}

        elif change_type == 'odr_only':
            # Pull ODR changes to local
            print(f"  ⬇️  Pulling ODR changes to local...")
            self._pull_from_odr(odr_info, local_filepath)
            new_local_info = self.get_local_file_info(local_filepath)
            self.sync_state.update_file_state(
                file_id,
                new_local_info["checksum"],
                odr_info["odr_timestamp"],
                new_local_info["timestamp"]
            )
            return {'status': 'pulled', 'action': 'ODR→local', 'file': local_filepath}

        elif change_type == 'conflict':
            # Handle conflict based on strategy
            resolution = self._resolve_conflict(
                record_name, local_info, odr_info, conflict_strategy
            )

            if resolution == 'local':
                self._push_to_odr(record, local_filepath)
                return {'status': 'pushed', 'action': 'conflict→local_wins', 'file': local_filepath}
            elif resolution == 'odr':
                self._pull_from_odr(odr_info, local_filepath)
                return {'status': 'pulled', 'action': 'conflict→odr_wins', 'file': local_filepath}
            else:
                return {'status': 'conflicts', 'action': 'skipped', 'file': local_filepath}

        elif change_type == 'new_local':
            # Upload new local file to ODR
            print(f"  ⬆️  Uploading new file to ODR...")
            self._push_to_odr(record, local_filepath)
            return {'status': 'pushed', 'action': 'new_upload', 'file': local_filepath}

        elif change_type == 'new_odr':
            # Download new ODR file
            print(f"  ⬇️  Downloading new file from ODR...")
            self._pull_from_odr(odr_info, local_filepath)
            return {'status': 'pulled', 'action': 'new_download', 'file': local_filepath}

        elif change_type == 'first_sync':
            # First time seeing this file - download to compare
            temp_path = local_filepath + ".odr_temp"
            self._pull_from_odr(odr_info, temp_path)
            temp_checksum = self.compute_checksum(temp_path)

            if temp_checksum == local_info["checksum"]:
                # Files are identical
                os.remove(temp_path)
                self.sync_state.update_file_state(
                    file_id,
                    local_info["checksum"],
                    odr_info["odr_timestamp"],
                    local_info["timestamp"]
                )
                return {'status': 'no_change', 'file': local_filepath}
            else:
                # Files differ - treat as conflict
                os.remove(temp_path)
                return self.sync_record(record, conflict_strategy)

    def _resolve_conflict(self, record_name: str, local_info: Dict,
                         odr_info: Dict, strategy: str) -> str:
        """Resolve sync conflict based on strategy"""

        if strategy == 'local_wins':
            return 'local'
        elif strategy == 'odr_wins':
            return 'odr'
        elif strategy == 'newest_wins':
            # Compare timestamps
            if local_info["timestamp"] > datetime.fromisoformat(odr_info["odr_timestamp"]).timestamp():
                return 'local'
            else:
                return 'odr'
        elif strategy == 'ask':
            print(f"\n⚠️  CONFLICT DETECTED for {record_name}")
            print(f"  Local: modified {datetime.fromtimestamp(local_info['timestamp'])}")
            print(f"  ODR:   modified {odr_info['odr_timestamp']}")

            while True:
                choice = input("  Choose: [L]ocal, [O]DR, [S]kip? ").strip().upper()
                if choice == 'L':
                    return 'local'
                elif choice == 'O':
                    return 'odr'
                elif choice == 'S':
                    return 'skip'
                else:
                    print("  Invalid choice. Please enter L, O, or S.")

        return 'skip'

    def _pull_from_odr(self, odr_info: Dict, local_filepath: str):
        """Download file from ODR to local"""
        file_uuid = odr_info["file_uuid"]
        output_dir = os.path.dirname(local_filepath)
        output_filename = os.path.basename(local_filepath)

        self.client.download_file(file_uuid, output_dir, output_filename)

    def _push_to_odr(self, record: Dict, local_filepath: str):
        """Upload local file to ODR"""
        record_uuid = record.get('record_uuid')
        dataset_uuid = record.get('database_uuid')

        # Find the Data File field to get template_field_uuid and field_uuid
        template_field_uuid = ""
        field_uuid = ""

        for field in record.get('fields', []):
            if field.get('field_name') == 'Data File':
                field_uuid = field.get('field_uuid', '')
                template_field_uuid = field.get('template_field_uuid') or ''
                break

        # Upload the file
        self.client.upload_file(
            file_path=local_filepath,
            record_uuid=record_uuid,
            dataset_uuid=dataset_uuid,
            template_field_uuid=template_field_uuid,
            field_uuid=field_uuid,
            name=os.path.basename(local_filepath)
        )

    def _get_local_filepath_for_record(self, record: Dict) -> Optional[str]:
        """
        Map ODR record to local file path
        This needs to be customized based on your naming convention
        """
        # Example implementation - adjust based on your structure
        record_name = record.get('record_name')

        # Try to find file in data directory
        # You may need to use metadata from record to determine type/sample/source
        for field in record.get('fields', []):
            if field.get('field_name') == 'Data File':
                files = field.get('files', [])
                if files:
                    original_name = files[0].get('original_name')
                    # Search for this file in data directory
                    for root, dirs, filenames in os.walk(self.data_dir):
                        if original_name in filenames:
                            return os.path.join(root, original_name)

        return None

    def _print_sync_summary(self, results: Dict):
        """Print summary of sync operation"""
        print("\n" + "="*60)
        print("📊 SYNC SUMMARY")
        print("="*60)
        print(f"✅ No changes:     {len(results['no_change'])}")
        print(f"⬇️  Pulled from ODR: {len(results['pulled'])}")
        print(f"⬆️  Pushed to ODR:   {len(results['pushed'])}")
        print(f"⚠️  Conflicts:      {len(results['conflicts'])}")
        print(f"❌ Errors:         {len(results['errors'])}")
        print("="*60)

        if results['conflicts']:
            print("\n⚠️  Unresolved conflicts:")
            for item in results['conflicts']:
                print(f"  - {item['record']}")

        if results['errors']:
            print("\n❌ Errors:")
            for item in results['errors']:
                print(f"  - {item['record']}: {item['error']}")


# Example usage
def main():
    from ODR_API_Client import ODRAPIClient

    # Configuration
    BASE_URL = "https://odr.io/api/v4"
    USERNAME = "someone@example.edu"
    PASSWORD = "qkh8fjd6adh*NPU!ekn"
    DATASET_UUID = "063c0d3d4bd183ab0dda87c544ae"

    # Initialize
    client = ODRAPIClient(BASE_URL, USERNAME, PASSWORD)
    client.authenticate()

    sync_manager = SCOBISyncManager(client, data_dir="data")

    # Sync with conflict resolution strategy
    results = sync_manager.sync_dataset(
        DATASET_UUID,
        conflict_strategy='ask'  # Options: 'ask', 'local_wins', 'odr_wins', 'newest_wins'
    )

    print("\n✅ Sync complete!")


if __name__ == "__main__":
    main()
