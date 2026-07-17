# SCOBI Sync System - Quick Start Guide

## What This Does

Automatically synchronizes your local SCOBI data files with the ODR (Open Data Repository):
- ⬇️  **Download** new files from ODR to local
- ⬆️  **Upload** new/modified local files to ODR
- 🔍 **Detect conflicts** when both sides changed
- ✅ **Resolve conflicts** using your chosen strategy

## Quick Start

### 1. Install (if needed)

All dependencies should already be installed. The sync system uses:
- `ODR_API_Client.py` (existing)
- `SCOBI_sync_manager.py` (new)

### 2. Run Your First Sync

```bash
# Initial download from ODR
python example_sync.py initial

# Or for regular bidirectional sync
python example_sync.py regular
```

### 3. Understand the Output

```
🔄 Starting sync process...
📊 Record_001: local_only
  ⬆️  Pushing local changes to ODR...
📊 Record_002: odr_only
  ⬇️  Pulling ODR changes to local...
📊 Record_003: no_change
📊 Record_004: conflict
  ⚠️  CONFLICT DETECTED for Record_004
  Choose: [L]ocal, [O]DR, [S]kip? L

============================================================
📊 SYNC SUMMARY
============================================================
✅ No changes:     15
⬇️  Pulled from ODR: 3
⬆️  Pushed to ODR:   2
⚠️  Conflicts:      1
❌ Errors:         0
============================================================
```

## Common Workflows

### Scenario 1: Setting Up New Workstation

```python
from ODR_API_Client import ODRAPIClient
from SCOBI_sync_manager import SCOBISyncManager

# Initialize
client = ODRAPIClient("https://odr.io/api/v4", USERNAME, PASSWORD)
client.authenticate()

sync = SCOBISyncManager(client, data_dir="data")

# Download everything from ODR
sync.sync_dataset(DATASET_UUID, conflict_strategy='odr_wins')
```

**When to use**: First time setup, fresh clone of repo

### Scenario 2: Daily Work (Recommended)

```python
# Morning: Pull latest from ODR
sync.sync_dataset(DATASET_UUID, conflict_strategy='odr_wins')

# ... Do your work locally ...

# Evening: Push changes to ODR
sync.sync_dataset(DATASET_UUID, conflict_strategy='local_wins')
```

**When to use**: Regular daily workflow

### Scenario 3: Careful Sync (with conflict checks)

```python
# Interactive - asks you about each conflict
sync.sync_dataset(DATASET_UUID, conflict_strategy='ask')
```

**When to use**: When you know both local and ODR might have changes

### Scenario 4: Automated (cron/scheduled)

```python
# Automatic - newest file wins
sync.sync_dataset(DATASET_UUID, conflict_strategy='newest_wins')
```

**When to use**: Automated nightly syncs

## Conflict Strategies Explained

| Strategy       | When to Use                                    | Risk Level |
|----------------|------------------------------------------------|------------|
| `odr_wins`     | Initial setup, pulling updates                 | Low        |
| `local_wins`   | After local edits, publishing changes          | Medium     |
| `ask`          | When unsure, want manual control               | Low        |
| `newest_wins`  | Automated sync, trust timestamps               | Medium     |

## Understanding the Cache File

The sync system creates a file called `.scobi_sync_cache.json` that looks like:

```json
{
  "files": {
    "60862b03967fc4e8a73d57326b39": {
      "checksum": "abc123...",
      "odr_timestamp": "2025-06-27T03:56:44",
      "local_timestamp": 1735574204.123
    }
  },
  "last_sync": "2025-12-30T12:00:00"
}
```

**Purpose**: Tracks the "last known good state" so we can detect:
- ✅ Only local changed → Push to ODR
- ✅ Only ODR changed → Pull from ODR
- ⚠️  **Both changed → CONFLICT!**

**Important**:
- Don't delete this file (you'll lose conflict detection)
- Don't commit to git (add to `.gitignore`)
- If corrupted, delete and run sync with `odr_wins` to rebuild

## Troubleshooting

### "Conflict detected but files look identical"

**Problem**: Line ending differences (Windows CRLF vs Unix LF)
**Solution**: Normalize line endings in your editor or git config

```bash
git config --global core.autocrlf true
```

### "Sync says file changed but I didn't touch it"

**Problem**: Cache out of sync with reality
**Solution**:

```bash
# Delete cache and rebuild
rm .scobi_sync_cache.json
python -c "
from ODR_API_Client import ODRAPIClient
from SCOBI_sync_manager import SCOBISyncManager
client = ODRAPIClient(BASE_URL, USERNAME, PASSWORD)
client.authenticate()
sync = SCOBISyncManager(client)
sync.sync_dataset(DATASET_UUID, conflict_strategy='odr_wins')
"
```

### "Upload failed with 403 Forbidden"

**Problem**: Don't have write permission on ODR dataset
**Solution**: Ask PI to grant write access to your account

### "Download speed very slow"

**Problem**: Syncing 1000+ files sequentially
**Solution**: Use parallel sync (future enhancement)

## Integration with Existing Workflow

### Before (manual process):

```python
# 1. Download files manually
client.extract_and_download_all_files(DATASET_UUID, "downloads")

# 2. Copy to data directory
# 3. Edit files
# 4. Manually upload changed files
client.upload_file(file_path, record_uuid, ...)
```

### After (automated):

```python
# 1. Sync (handles download/upload automatically)
sync.sync_dataset(DATASET_UUID, conflict_strategy='ask')

# 2. Edit files
# 3. Sync again (uploads changes)
sync.sync_dataset(DATASET_UUID, conflict_strategy='local_wins')
```

## Advanced Usage

### Sync a Single Record

```python
# Get the record from ODR
record = client.get_record(record_uuid)

# Sync just this one record
result = sync.sync_record(record, conflict_strategy='ask')
```

### Check What Would Change (Dry Run)

Currently not implemented, but you can check manually:

```python
# Get dataset
dataset = client.get_dataset(DATASET_UUID)

for record in dataset.get('records', []):
    local_path = sync._get_local_filepath_for_record(record)
    local_info = sync.get_local_file_info(local_path)
    odr_info = sync.get_odr_file_info(record)
    cached = sync.sync_state.get_file_state(record.get('record_uuid'))

    change = sync.detect_change_type(local_info, odr_info, cached, record.get('record_uuid'))
    print(f"{record.get('record_name')}: {change}")
```

### Custom Conflict Resolution

```python
def my_custom_resolver(record_name, local_info, odr_info):
    # Custom logic - e.g., always keep larger file
    if local_info['size'] > odr_info['size']:
        return 'local'
    else:
        return 'odr'

# Modify sync_manager to use your resolver
# (requires editing SCOBI_sync_manager.py)
```

## Files Overview

| File                      | Purpose                                    |
|---------------------------|--------------------------------------------|
| `SCOBI_sync_manager.py`   | Main sync engine                          |
| `example_sync.py`         | Usage examples                            |
| `SYNC_DESIGN.md`          | Detailed architecture & edge cases        |
| `SYNC_README.md`          | This file - quick start guide             |
| `.scobi_sync_cache.json`  | State cache (auto-generated, don't commit)|

## Next Steps

1. ✅ Try the examples: `python example_sync.py workflow`
2. 📖 Read the design doc: `SYNC_DESIGN.md`
3. 🔧 Customize for your needs (edit field mapping in `_get_local_filepath_for_record`)
4. ⚙️  Set up automated sync (cron job or git hooks)

## Questions?

- Architecture details: See `SYNC_DESIGN.md`
- Code reference: See `CLAUDE.md`
- ODR API: See `ODR API Client Test Notebook.ipynb`

## Contribution Ideas

Want to improve the sync system? Consider:

1. **Parallel downloads** - Speed up large dataset sync
2. **Dry-run mode** - Preview changes before executing
3. **Backup on conflict** - Auto-save `.bak` files
4. **Better file mapping** - Use ODR metadata fields to determine local path
5. **Webhook integration** - Real-time sync when ODR changes
6. **Merge tool** - For CSV files, attempt automatic merge instead of picking one version
