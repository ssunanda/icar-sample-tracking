"""
SCOBI Sync Manager v2
=====================
Enhanced version with proper metadata-based file path mapping

Key improvements over v1:
1. Uses ODR metadata fields (Data Type, Sample Type, Source) for path construction
2. Checks _field_metadata._update_date for change detection
3. Preserves all metadata when syncing
4. Faster - no directory tree walking
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


class SCOBISyncManagerV2:
    """Enhanced sync manager with metadata-based path mapping"""

    def __init__(self, odr_client: ODRAPIClient, data_dir: str = "data"):
        self.client = odr_client
        self.data_dir = data_dir
        self.sync_state = SyncState()

    # ============================================================================
    # Metadata Utilities
    # ============================================================================

    def get_field_value(self, record: Dict, field_name: str) -> Optional[str]:
        """Extract a text field value from record"""
        for field in record.get('fields', []):
            if field.get('field_name') == field_name:
                return field.get('value')
        return None

    def get_file_field_info(self, record: Dict, field_name: str = "Data File") -> Optional[Dict]:
        """Extract file information from a file-type field"""
        for field in record.get('fields', []):
            if field.get('field_name') == field_name:
                files = field.get('files', [])
                if files:
                    file_info = files[0]  # Assuming one file per field
                    field_metadata = field.get('_field_metadata', {})

                    return {
                        "file_uuid": file_info.get("file_uuid"),
                        "original_name": file_info.get("original_name"),
                        "file_size": int(file_info.get("file_size", 0)),
                        # Use field metadata timestamp (more reliable than file metadata)
                        "odr_timestamp": field_metadata.get("_update_date"),
                        "field_uuid": field.get("field_uuid"),
                        "template_field_uuid": field.get("template_field_uuid")
                    }
        return None

    def build_local_path_from_metadata(self, record: Dict) -> Optional[str]:
        """
        Construct local file path using ODR metadata fields

        Path pattern: data/{data_type}/{sample_type}/{source}/{filename}
        Example: data/reflectance/meteorite/RELAB/sample_001.csv
        """
        # Extract metadata
        data_type = self.get_field_value(record, "Data Type")
        sample_type = self.get_field_value(record, "Sample Type")
        source = self.get_field_value(record, "Source")

        # Extract filename
        file_info = self.get_file_field_info(record, "Data File")
        filename = file_info.get("original_name") if file_info else None

        # Validate we have everything
        if not all([data_type, sample_type, source, filename]):
            missing = []
            if not data_type: missing.append("Data Type")
            if not sample_type: missing.append("Sample Type")
            if not source: missing.append("Source")
            if not filename: missing.append("Data File")

            print(f"⚠️  Record {record.get('record_name')} missing metadata: {', '.join(missing)}")
            return None

        # Build path
        local_path = os.path.join(
            self.data_dir,
            data_type.lower(),      # reflectance, raman, elemental, isotopic
            sample_type.lower(),    # tooth, bone, meteorite, etc.
            source,                 # RELAB, USGS, RRUFF, etc.
            filename                # actual .csv/.txt file
        )

        return local_path

    # ============================================================================
    # File Operations
    # ============================================================================

    def compute_checksum(self, filepath: str) -> str:
        """Compute MD5 checksum of a file"""
        md5 = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                md5.update(chunk)
        return md5.hexdigest()

    def get_local_file_info(self, filepath: str) -> Optional[Dict]:
        """Get local file metadata"""
        if not os.path.exists(filepath):
            return None

        return {
            "checksum": self.compute_checksum(filepath),
            "timestamp": os.path.getmtime(filepath),
            "size": os.path.getsize(filepath),
            "exists": True
        }

    def get_odr_file_info(self, record: Dict) -> Optional[Dict]:
        """Extract file info from ODR record using metadata"""
        return self.get_file_field_info(record, "Data File")

    # ============================================================================
    # Change Detection
    # ============================================================================

    def detect_change_type(self, local_info: Optional[Dict], odr_info: Optional[Dict],
                          cached_state: Optional[Dict], file_id: str) -> str:
        """
        Detect what kind of change occurred

        Returns:
            'no_change', 'local_only', 'odr_only', 'conflict',
            'new_local', 'new_odr', 'first_sync'
        """
        # New files
        if local_info and not odr_info:
            return 'new_local'
        if odr_info and not local_info:
            return 'new_odr'

        # No cached state - first sync
        if not cached_state:
            if local_info and odr_info:
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

    # ============================================================================
    # Sync Operations
    # ============================================================================

    def sync_dataset(self, dataset_uuid: str, conflict_strategy: str = 'ask') -> Dict:
        """
        Sync entire dataset between local and ODR

        Args:
            dataset_uuid: ODR dataset UUID
            conflict_strategy: 'ask', 'local_wins', 'odr_wins', 'newest_wins'

        Returns:
            Dictionary with sync results
        """
        print("🔄 Starting metadata-driven sync...")

        # Get all records from ODR
        dataset = self.client.get_dataset(dataset_uuid)

        results = {
            'no_change': [],
            'pulled': [],
            'pushed': [],
            'conflicts': [],
            'errors': [],
            'missing_metadata': []
        }

        for record in dataset.get('records', []):
            record_name = record.get('record_name')
            record_uuid = record.get('record_uuid')

            try:
                # Build local path from metadata
                local_path = self.build_local_path_from_metadata(record)

                if not local_path:
                    results['missing_metadata'].append({
                        'record': record_name,
                        'reason': 'Incomplete metadata fields'
                    })
                    continue

                result = self.sync_record(record, local_path, conflict_strategy)
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

    def sync_record(self, record: Dict, local_filepath: str, conflict_strategy: str = 'ask') -> Dict:
        """Sync a single record"""
        record_name = record.get('record_name')
        record_uuid = record.get('record_uuid')

        # Get ODR file info (using metadata timestamp)
        odr_info = self.get_odr_file_info(record)

        # Get local file info
        local_info = self.get_local_file_info(local_filepath) if local_filepath else None

        # Get cached state
        file_id = record_uuid
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
                self.sync_state.update_file_state(
                    file_id,
                    local_info["checksum"],
                    datetime.now().isoformat(),
                    local_info["timestamp"]
                )
                return {'status': 'pushed', 'action': 'conflict→local_wins', 'file': local_filepath}
            elif resolution == 'odr':
                self._pull_from_odr(odr_info, local_filepath)
                new_local_info = self.get_local_file_info(local_filepath)
                self.sync_state.update_file_state(
                    file_id,
                    new_local_info["checksum"],
                    odr_info["odr_timestamp"],
                    new_local_info["timestamp"]
                )
                return {'status': 'pulled', 'action': 'conflict→odr_wins', 'file': local_filepath}
            else:
                return {'status': 'conflicts', 'action': 'skipped', 'file': local_filepath}

        elif change_type == 'new_local':
            # Upload new local file to ODR (need to create record first)
            print(f"  ⚠️  New local file needs manual record creation: {local_filepath}")
            return {'status': 'errors', 'action': 'new_local_needs_record', 'file': local_filepath}

        elif change_type == 'new_odr':
            # Download new ODR file
            print(f"  ⬇️  Downloading new file from ODR...")
            # Create directory structure if needed
            os.makedirs(os.path.dirname(local_filepath), exist_ok=True)
            self._pull_from_odr(odr_info, local_filepath)
            new_local_info = self.get_local_file_info(local_filepath)
            self.sync_state.update_file_state(
                file_id,
                new_local_info["checksum"],
                odr_info["odr_timestamp"],
                new_local_info["timestamp"]
            )
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
                # Re-run with updated cache
                return self.sync_record(record, local_filepath, conflict_strategy)

    # ============================================================================
    # Helper Methods
    # ============================================================================

    def _resolve_conflict(self, record_name: str, local_info: Dict,
                         odr_info: Dict, strategy: str) -> str:
        """Resolve sync conflict based on strategy"""

        if strategy == 'local_wins':
            return 'local'
        elif strategy == 'odr_wins':
            return 'odr'
        elif strategy == 'newest_wins':
            # Compare timestamps
            local_time = local_info["timestamp"]
            odr_time = datetime.fromisoformat(odr_info["odr_timestamp"]).timestamp()
            return 'local' if local_time > odr_time else 'odr'
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

        return 'skip'

    def _pull_from_odr(self, odr_info: Dict, local_filepath: str):
        """Download file from ODR to local"""
        file_uuid = odr_info["file_uuid"]
        output_dir = os.path.dirname(local_filepath)
        output_filename = os.path.basename(local_filepath)

        # Ensure directory exists
        os.makedirs(output_dir, exist_ok=True)

        self.client.download_file(file_uuid, output_dir, output_filename)

    def _push_to_odr(self, record: Dict, local_filepath: str):
        """Upload local file to ODR, preserving metadata"""
        record_uuid = record.get('record_uuid')
        dataset_uuid = record.get('database_uuid')

        # Get field UUIDs from metadata
        file_info = self.get_file_field_info(record, "Data File")

        if not file_info:
            raise ValueError(f"No Data File field found in record {record_uuid}")

        field_uuid = file_info.get('field_uuid', '')
        template_field_uuid = file_info.get('template_field_uuid') or ''

        # Upload the file
        self.client.upload_file(
            file_path=local_filepath,
            record_uuid=record_uuid,
            dataset_uuid=dataset_uuid,
            template_field_uuid=template_field_uuid,
            field_uuid=field_uuid,
            name=os.path.basename(local_filepath)
        )

    def _print_sync_summary(self, results: Dict):
        """Print summary of sync operation"""
        print("\n" + "="*60)
        print("📊 SYNC SUMMARY")
        print("="*60)
        print(f"✅ No changes:        {len(results['no_change'])}")
        print(f"⬇️  Pulled from ODR:   {len(results['pulled'])}")
        print(f"⬆️  Pushed to ODR:     {len(results['pushed'])}")
        print(f"⚠️  Conflicts:         {len(results['conflicts'])}")
        print(f"❌ Errors:            {len(results['errors'])}")
        print(f"⚠️  Missing metadata:  {len(results['missing_metadata'])}")
        print("="*60)

        if results['missing_metadata']:
            print("\n⚠️  Records missing metadata (skipped):")
            for item in results['missing_metadata']:
                print(f"  - {item['record']}: {item['reason']}")

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

    sync_manager = SCOBISyncManagerV2(client, data_dir="data")

    # Sync with metadata-based path mapping
    results = sync_manager.sync_dataset(
        DATASET_UUID,
        conflict_strategy='ask'
    )

    print("\n✅ Metadata-driven sync complete!")


if __name__ == "__main__":
    main()
