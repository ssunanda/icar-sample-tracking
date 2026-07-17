# SCOBI Sync System Design

## Overview

This document describes the bidirectional synchronization system between local SCOBI files and the ODR (Open Data Repository).

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SCOBI Sync Manager                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────┐ │
│  │ Local Files  │◄────►│ Sync Engine  │◄────►│   ODR    │ │
│  │   (data/)    │      │              │      │   API    │ │
│  └──────────────┘      └──────────────┘      └──────────┘ │
│         │                      │                    │      │
│         │              ┌───────▼────────┐          │      │
│         └─────────────►│  Sync Cache    │◄─────────┘      │
│                        │ (.scobi_sync_  │                  │
│                        │  cache.json)   │                  │
│                        └────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. SyncState (`.scobi_sync_cache.json`)

**Purpose**: Track last known state of all files to detect conflicts

**Structure**:
```json
{
  "files": {
    "record_uuid_1": {
      "checksum": "abc123...",
      "odr_timestamp": "2025-06-27T03:56:44",
      "local_timestamp": 1735574204.123
    }
  },
  "last_sync": "2025-12-30T12:00:00"
}
```

**Why needed**: Without this, we can't tell if BOTH sides changed (conflict) vs only one side changed.

### 2. Change Detection Logic

```
┌─────────────────────────────────────────────────────────────┐
│ Change Type Decision Tree                                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Local exists?  ODR exists?  Cached?  → Action             │
│  ═══════════════════════════════════════════════════       │
│  NO            YES          -        → Download (new_odr)  │
│  YES           NO           -        → Upload (new_local)  │
│                                                             │
│  YES           YES          NO       → Compare checksums   │
│                                        (first_sync)        │
│                                                             │
│  YES           YES          YES:                           │
│    ├─ Local=cached, ODR=cached      → No change           │
│    ├─ Local≠cached, ODR=cached      → Push local          │
│    ├─ Local=cached, ODR≠cached      → Pull ODR            │
│    └─ Local≠cached, ODR≠cached      → CONFLICT!           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3. Conflict Resolution Strategies

When both local and ODR changed since last sync:

| Strategy       | Behavior                                  |
|----------------|-------------------------------------------|
| `ask`          | Prompt user for each conflict             |
| `local_wins`   | Always keep local changes                 |
| `odr_wins`     | Always keep ODR changes                   |
| `newest_wins`  | Compare timestamps, keep most recent      |

## Workflow Integration

### Initial Setup

```python
from ODR_API_Client import ODRAPIClient
from SCOBI_sync_manager import SCOBISyncManager

# Initialize
client = ODRAPIClient(BASE_URL, USERNAME, PASSWORD)
client.authenticate()

sync_manager = SCOBISyncManager(client, data_dir="data")
```

### Regular Workflow

```python
# Before making local changes - sync down
print("🔄 Syncing before work...")
sync_manager.sync_dataset(DATASET_UUID, conflict_strategy='odr_wins')

# Do your work locally
# ... modify files in data/ directory ...

# After making changes - sync up
print("🔄 Syncing after work...")
sync_manager.sync_dataset(DATASET_UUID, conflict_strategy='local_wins')
```

### Automated Sync (Cron/Scheduled)

```python
# Safe automated sync - conflicts require manual intervention
results = sync_manager.sync_dataset(
    DATASET_UUID,
    conflict_strategy='ask'  # Will skip conflicts, log for manual review
)

# Email admin if conflicts detected
if results['conflicts']:
    send_alert(f"Sync conflicts detected: {len(results['conflicts'])} files")
```

## Key Design Decisions

### 1. Why MD5 Checksums?

**Alternative**: Could use file size or timestamps only
**Chosen**: MD5 checksums
**Reason**:
- Timestamps unreliable (timezone issues, file copies lose original time)
- File size can be identical with different content
- MD5 is fast enough for typical scientific data files (<100MB)

### 2. Why Cache Last Known State?

**Alternative**: Just compare local vs ODR directly
**Problem**: Can't detect conflicts without knowing previous state
**Example**:
```
Time 0: File.csv = "A"  (both local and ODR)
Time 1: Local changes to "B", ODR changes to "C"
Time 2: Sync runs
        → Without cache: Could assume ODR is "correct", overwrite local "B" with "C"
        → With cache: Detects BOTH changed, raises conflict
```

### 3. Why Per-File Granularity?

**Alternative**: Sync entire datasets as atomic units
**Chosen**: Per-file sync with independent decisions
**Reason**:
- Large datasets (1000+ files) rarely all change at once
- Failure in one file shouldn't block others
- Easier to review/debug specific file conflicts

## Critical Edge Cases

### Case 1: Simultaneous Edits

```
Timeline:
10:00 - User A pulls file, starts editing locally
10:05 - User B edits same file in ODR web interface
10:10 - User A finishes, runs sync → CONFLICT

Resolution:
- Strategy='ask' → Prompt User A to choose
- Strategy='newest_wins' → Keep User A's (10:10 > 10:05)
```

### Case 2: File Renamed Locally

```
Problem: Record points to "old_name.csv" but local file renamed to "new_name.csv"
Current behavior: Treated as deletion + new file
Better approach: Track file moves (future enhancement)
```

### Case 3: Network Failure Mid-Sync

```
Problem: Downloaded 5/10 files, then network dies
Current behavior: Partial sync, cache updated for successful 5
Recovery: Re-run sync, picks up remaining 5
```

### Case 4: Corrupted ODR Upload

```
Problem: Upload succeeds but file corrupted on ODR
Detection: Next sync will see checksum mismatch
Resolution: Manual intervention required (check ODR file integrity)
```

## Integration with Existing Code

### Mapping Records to Local Files

**Challenge**: ODR records don't inherently know their local path

**Current heuristic** (in `_get_local_filepath_for_record`):
1. Get original filename from ODR record
2. Search `data/` directory tree for matching filename
3. Return first match

**Better approach** (requires extension):
```python
# Add metadata fields to ODR records:
# - "Data Type" → reflectance, raman, elemental, isotopic
# - "Sample Type" → tooth, bone, etc.
# - "Source" → RELAB, USGS, etc.

def _get_local_filepath_for_record(self, record: Dict) -> str:
    data_type = self._get_field_value(record, "Data Type")
    sample = self._get_field_value(record, "Sample Type")
    source = self._get_field_value(record, "Source")
    filename = self._get_original_filename(record)

    return os.path.join(
        self.data_dir,
        data_type,
        sample,
        source,
        filename
    )
```

### Extending SCOBI_record_raw

Add sync capabilities to existing record class:

```python
class SCOBI_record_raw(SCOBI_record, SCOBI_parsers, SCOBI_downloaders):

    def sync_with_odr(self, odr_client, conflict_strategy='ask'):
        """Sync this specific record with ODR"""
        sync_manager = SCOBISyncManager(odr_client, self.datadir)

        # Get the ODR record
        odr_record = odr_client.get_record(self.odr_uuid)

        # Sync it
        result = sync_manager.sync_record(odr_record, conflict_strategy)

        return result
```

## Performance Considerations

### Scalability

For 10,000 files:
- **Checksum computation**: ~2ms/file × 10,000 = 20 seconds
- **ODR API calls**: ~200ms/record × 10,000 = 33 minutes
- **Total**: ~35 minutes for full sync

**Optimization strategies**:
1. **Parallel downloads**: Use ThreadPoolExecutor for I/O-bound ops
2. **Batch API calls**: Get multiple records in one request (if API supports)
3. **Incremental sync**: Only check files modified since last_sync timestamp
4. **Smart caching**: Skip checksum if file mtime unchanged

### Example: Parallel Sync

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def sync_dataset_parallel(self, dataset_uuid, conflict_strategy='ask', workers=5):
    dataset = self.client.get_dataset(dataset_uuid)

    results = {'no_change': [], 'pulled': [], 'pushed': [], 'conflicts': [], 'errors': []}

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(self.sync_record, record, conflict_strategy): record
            for record in dataset.get('records', [])
        }

        for future in as_completed(futures):
            record = futures[future]
            try:
                result = future.result()
                results[result['status']].append(result)
            except Exception as e:
                results['errors'].append({'record': record.get('record_name'), 'error': str(e)})

    return results
```

## Testing Strategy

### Unit Tests

```python
def test_detect_change_local_only():
    """Test detection when only local file changed"""
    local_info = {"checksum": "new123", "timestamp": 1000}
    odr_info = {"odr_timestamp": "2025-01-01T00:00:00"}
    cached = {"checksum": "old456", "odr_timestamp": "2025-01-01T00:00:00"}

    result = sync_manager.detect_change_type(local_info, odr_info, cached, "test_id")
    assert result == 'local_only'

def test_detect_conflict():
    """Test detection when both sides changed"""
    local_info = {"checksum": "new123", "timestamp": 1000}
    odr_info = {"odr_timestamp": "2025-01-02T00:00:00"}
    cached = {"checksum": "old456", "odr_timestamp": "2025-01-01T00:00:00"}

    result = sync_manager.detect_change_type(local_info, odr_info, cached, "test_id")
    assert result == 'conflict'
```

### Integration Tests

```python
def test_full_sync_workflow():
    """Test complete sync workflow"""
    # Setup: Create local file, upload to ODR, record in cache
    # Action: Modify local file, run sync
    # Assert: ODR updated, cache updated, no conflicts
```

## Future Enhancements

1. **Incremental sync**: Only check files modified since last_sync
2. **File move tracking**: Detect renames instead of treating as delete+add
3. **Conflict merging**: For CSV files, attempt automatic merge
4. **Webhook listeners**: Real-time sync on ODR changes
5. **Backup before overwrite**: Keep `.bak` before pulling ODR changes
6. **Dry-run mode**: Preview what would be synced without executing
7. **Rollback capability**: Undo last sync operation

## Usage Examples

### Example 1: Daily Sync Script

```bash
#!/bin/bash
# daily_sync.sh

cd /path/to/scobi
python3 << EOF
from ODR_API_Client import ODRAPIClient
from SCOBI_sync_manager import SCOBISyncManager

client = ODRAPIClient("https://odr.io/api/v4", "$ODR_USER", "$ODR_PASS")
client.authenticate()

sync = SCOBISyncManager(client, "data")
results = sync.sync_dataset("$DATASET_UUID", conflict_strategy='newest_wins')

if results['errors']:
    exit(1)
EOF
```

### Example 2: Pre-commit Hook

```python
# .git/hooks/pre-commit
# Ensure local changes are synced before commit

from SCOBI_sync_manager import SCOBISyncManager

sync = SCOBISyncManager(client, "data")
results = sync.sync_dataset(DATASET_UUID, conflict_strategy='local_wins')

if results['conflicts']:
    print("❌ Resolve sync conflicts before committing")
    exit(1)
```

### Example 3: Interactive Workflow

```python
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--mode', choices=['pull', 'push', 'sync'], required=True)
args = parser.parse_args()

if args.mode == 'pull':
    # Download only, local changes overwritten
    results = sync.sync_dataset(DATASET_UUID, conflict_strategy='odr_wins')
elif args.mode == 'push':
    # Upload only, ODR overwritten
    results = sync.sync_dataset(DATASET_UUID, conflict_strategy='local_wins')
else:
    # Interactive conflict resolution
    results = sync.sync_dataset(DATASET_UUID, conflict_strategy='ask')
```

## Troubleshooting

### Problem: "Checksum mismatch after sync"

**Cause**: File modified during download or upload corrupted
**Solution**: Re-run sync, file will be re-downloaded

### Problem: "Endless conflicts on same file"

**Cause**: File encoding differences (CRLF vs LF) causing checksum changes
**Solution**: Normalize line endings before checksumming

### Problem: "Sync cache out of sync with reality"

**Cause**: Manual file operations bypassed sync system
**Solution**: Delete `.scobi_sync_cache.json`, re-run with `first_sync` mode
