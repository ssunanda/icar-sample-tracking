"""
Complete Record Upload with ALL Fields from CSV
================================================
Maps all CSV columns to ODR fields based on the complete record structure.

CSV columns: #ID, source, sample, type, units, tags, methods, notes, downloadable, url, sourcefile

ODR Fields (from record 777390):
- Data File: file upload
- Data Type: radio (Elemental, Isotopic, Raman, Reflectance)
- Source ID: text (from CSV 'source')
- Class: radio (Non-Indicative, Indicative)
- Subclass: radio (Non-Indicative, Alive, Non-Alive, Mixed)
- Sample Type: radio (from CSV 'sample')
- Source Links: text (from CSV 'url')
- Source Citation: text (lookup from BibTeX file)
- Tags: tag field (from CSV 'tags')
- Downloadable?: radio/checkbox (from CSV 'downloadable')
- Units: tag field (from CSV 'units')
- Methods: tag field (from CSV 'methods')
"""

import os
import sys
import pandas as pd
import re
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "client"))
from ODR_API_Client import ODRAPIClient

# =============================================================================
# CONFIGURATION
# =============================================================================
BASE_URL = "https://www.odr.io/api/v4"
USERNAME = "amshahid@ncsu.edu"
PASSWORD = "qkh8fjd6adh*NPU!ekn"
DATASET_UUID = "063c0d3d4bd183ab0dda87c544ae"

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CSV_PATH = REPO_ROOT / "defs" / "all_raw_records.csv"
DATA_DIR = REPO_ROOT / "raw_main" / "data"
BIB_PATH = REPO_ROOT / "defs" / "scobi_citations.bib"

# =============================================================================
# FIELD UUIDS (from complete record 777390)
# =============================================================================
FIELD_UUIDS = {
    "Data File": "a65467babf8a1ac7e1d7319e3928",
    "Data Type": "996f2f04be5e12bc6d251e54bb8f",
    "Source ID": "98c0dc4db715d503abc93fa598f9",
    "Class": "676b2e7658da32d4c518b3877401",
    "Subclass": "bcf6ab5a9b02de9e0594772f2c2a",
    "Sample Type": "423044bee60c5e83fcb7fbf1b713",
    "Source Links": "cb24ce292d861629416b51c40aa0",
    "Source Citation": "0719c6187a235650b437bb742bf9",
    "Tags": "fd06bebf2276eceb86cb6c1be4d8",
    "Downloadable?": "d44bf91e6214562e43c0e4a05780",
    "Units": "c8af0e150f7776e7bc6dfffdd0a7",
    "Methods": "ab94444215a38328b02bf15782f6",
}

# =============================================================================
# CLASSIFICATION MAPPINGS
# =============================================================================
SAMPLE_CLASSES = {
    "bone": "Indicative", "tooth": "Indicative", "microorganism": "Indicative",
    "plant": "Indicative", "soil": "Indicative", "human": "Indicative",
    "microbialmat": "Indicative", "kerogen": "Indicative",
    # Non-Indicative samples
    "basalt": "Non-Indicative", "meteorite": "Non-Indicative",
    "lunarregolith": "Non-Indicative", "marsregolith": "Non-Indicative",
    "magnetite": "Non-Indicative", "calcite": "Non-Indicative", 
    "clay": "Non-Indicative", "carbonatite": "Non-Indicative", 
    "coralskeleton": "Non-Indicative", "ice": "Non-Indicative", 
    "snow": "Non-Indicative", "sand": "Non-Indicative", 
    "silt": "Non-Indicative", "seawater": "Non-Indicative",
}

SAMPLE_SUBCLASSES = {
    "bone": "Non-Alive", "tooth": "Non-Alive", "human": "Non-Alive",
    "microorganism": "Alive", "plant": "Alive", "microbialmat": "Alive",
    "soil": "Mixed", "seawater": "Mixed",
    # Default to Non-Indicative for others
}


def safe_str(val):
    """Convert value to string, return empty string if NaN."""
    if pd.isna(val) or str(val).lower() == 'nan':
        return ""
    return str(val).strip()


def load_metadata():
    """Load CSV metadata."""
    df = pd.read_csv(CSV_PATH)
    df = df.rename(columns={'#ID': 'id'})
    df = df.set_index('id')
    return df


def load_citations(bib_path):
    """Parse BibTeX file and return dict of {citation_key: formatted_citation}."""
    print(f"Loading citations from {bib_path}...")
    citations = {}
    
    if not bib_path.exists():
        print(f"  [WARN] BibTeX file not found: {bib_path}")
        return citations
    
    with open(bib_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse BibTeX entries using regex
    # Match @article{key, ... } or @book{key, ...} etc.
    entry_pattern = r'@\w+\{([^,]+),([^@]*?)(?=\n@|\Z)'
    field_pattern = r'(\w+)\s*=\s*[{\"](.+?)[}\"](?:,|\s*\})'
    
    for match in re.finditer(entry_pattern, content, re.DOTALL):
        key = match.group(1).strip()
        entry_content = match.group(2)
        
        # Extract fields
        fields = {}
        for field_match in re.finditer(field_pattern, entry_content, re.DOTALL):
            field_name = field_match.group(1).lower()
            field_value = field_match.group(2).strip()
            # Clean up LaTeX formatting
            field_value = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', field_value)
            field_value = re.sub(r'[{}]', '', field_value)
            fields[field_name] = field_value
        
        # Format citation: Author (Year). Title. Journal.
        author = fields.get('author', 'Unknown')
        year = fields.get('year', '')
        title = fields.get('title', '')
        journal = fields.get('journal', fields.get('booktitle', ''))
        
        # Truncate author list if too long
        if len(author) > 50:
            author = author.split(' and ')[0] + ' et al.'
        
        citation = f"{author} ({year}). {title}."
        if journal:
            citation += f" {journal}."
        
        # Truncate to 250 chars for ODR ShortVarchar limit
        if len(citation) > 250:
            citation = citation[:247] + "..."
        
        citations[key] = citation
    
    print(f"  Loaded {len(citations)} citations")
    return citations


import requests


def _fetch_template(client):
    """Fetch the template/schema which contains ALL registered options,
    not just those already used in records."""
    url = f"{BASE_URL}/template/{DATASET_UUID}"
    r = requests.get(url, headers={"Authorization": f"Bearer {client.token}"}, timeout=30)
    r.raise_for_status()
    return r.json()


def _flatten_tags(tag_list):
    """Tags can be hierarchical (children). Flatten to {name: uuid}."""
    out = {}
    for t in tag_list or []:
        name = t.get("name") or t.get("tag_name")
        uuid = t.get("template_tag_uuid")
        if name and uuid:
            out[name] = uuid
        for key in ("children", "tags"):
            if t.get(key):
                out.update(_flatten_tags(t[key]))
    return out


def discover_tag_options(client):
    """Discover all tag option UUIDs from the template (not records)."""
    print("Discovering tag options from ODR template...")
    tmpl = _fetch_template(client)
    tag_fields = ("Tags", "Units", "Methods")
    options = {f: {} for f in tag_fields}
    for f in tmpl.get("fields", []):
        name = f.get("name")
        if name in tag_fields:
            options[name] = _flatten_tags(f.get("tags", []))
    for k, v in options.items():
        print(f"  {k}: {len(v)} options")
    return options


def discover_radio_options(client):
    """Discover all radio option UUIDs from the template (not records)."""
    print("Discovering radio options from ODR template...")
    tmpl = _fetch_template(client)
    radio_fields = ("Data Type", "Sample Type", "Class", "Subclass", "Downloadable?")
    options = {f: {} for f in radio_fields}
    for f in tmpl.get("fields", []):
        name = f.get("name")
        if name in radio_fields:
            for o in f.get("radio_options", []):
                oname = o.get("name") or o.get("option_name")
                uuid = o.get("template_radio_option_uuid")
                if oname and uuid:
                    options[name][oname] = uuid
    for k, v in options.items():
        print(f"  {k}: {len(v)} options -> {list(v.keys())}")
    return options


def build_fields(row, radio_options, tag_options=None, citations=None):
    """Build complete fields payload from CSV row."""
    fields = []
    tag_options = tag_options or {}
    citations = citations or {}
    
    # 1. Source ID (text) - from 'source' column
    source_id = safe_str(row.get('source', ''))
    if source_id:
        fields.append({
            "field_name": "Source ID",
            "field_uuid": FIELD_UUIDS["Source ID"],
            "value": source_id
        })
    
    # 2. Data Type (radio) - from 'type' column
    data_type = safe_str(row.get('type', '')).capitalize()
    if data_type and data_type in radio_options["Data Type"]:
        fields.append({
            "field_name": "Data Type",
            "field_uuid": FIELD_UUIDS["Data Type"],
            "values": [{
                "template_radio_option_uuid": radio_options["Data Type"][data_type],
                "name": data_type,
                "selected": 1
            }]
        })
    
    # 3. Sample Type (radio) - from 'sample' column
    sample = safe_str(row.get('sample', ''))
    if sample and sample in radio_options["Sample Type"]:
        fields.append({
            "field_name": "Sample Type",
            "field_uuid": FIELD_UUIDS["Sample Type"],
            "values": [{
                "template_radio_option_uuid": radio_options["Sample Type"][sample],
                "name": sample,
                "selected": 1
            }]
        })
    
    # 4. Class (radio) - derived from sample type
    class_name = SAMPLE_CLASSES.get(sample, "Non-Indicative")
    if class_name in radio_options["Class"]:
        fields.append({
            "field_name": "Class",
            "field_uuid": FIELD_UUIDS["Class"],
            "values": [{
                "template_radio_option_uuid": radio_options["Class"][class_name],
                "name": class_name,
                "selected": 1
            }]
        })
    
    # 5. Subclass (radio) - derived from sample type
    subclass_name = SAMPLE_SUBCLASSES.get(sample, "Non-Indicative")
    if subclass_name in radio_options["Subclass"]:
        fields.append({
            "field_name": "Subclass",
            "field_uuid": FIELD_UUIDS["Subclass"],
            "values": [{
                "template_radio_option_uuid": radio_options["Subclass"][subclass_name],
                "name": subclass_name,
                "selected": 1
            }]
        })
    
    # 6. Tags (tag field) - from 'tags' column (semicolon-separated)
    tags_str = safe_str(row.get('tags', ''))
    if tags_str and "Tags" in tag_options:
        tag_list = []
        for tag_name in tags_str.split(';'):
            tag_name = tag_name.strip()
            if tag_name and tag_name in tag_options["Tags"]:
                tag_list.append({
                    "template_tag_uuid": tag_options["Tags"][tag_name],
                    "name": tag_name,
                    "selected": 1
                })
        if tag_list:
            fields.append({
                "field_name": "Tags",
                "field_uuid": FIELD_UUIDS["Tags"],
                "tags": tag_list
            })
    
    # 7. Units (tag field) - from 'units' column (semicolon-separated)
    units_str = safe_str(row.get('units', ''))
    if units_str and "Units" in tag_options:
        unit_list = []
        for unit_name in units_str.split(';'):
            unit_name = unit_name.strip()
            if unit_name and unit_name in tag_options["Units"]:
                unit_list.append({
                    "template_tag_uuid": tag_options["Units"][unit_name],
                    "name": unit_name,
                    "selected": 1
                })
        if unit_list:
            fields.append({
                "field_name": "Units",
                "field_uuid": FIELD_UUIDS["Units"],
                "tags": unit_list
            })
    
    # 8. Methods (tag field) - from 'methods' column (semicolon-separated)
    methods_str = safe_str(row.get('methods', ''))
    if methods_str and "Methods" in tag_options:
        method_list = []
        for method_name in methods_str.split(';'):
            method_name = method_name.strip()
            if method_name and method_name in tag_options["Methods"]:
                method_list.append({
                    "template_tag_uuid": tag_options["Methods"][method_name],
                    "name": method_name,
                    "selected": 1
                })
        if method_list:
            fields.append({
                "field_name": "Methods",
                "field_uuid": FIELD_UUIDS["Methods"],
                "tags": method_list
            })
    
    # 9. Source Links (text) - from 'url' column
    url = safe_str(row.get('url', ''))
    if url:
        fields.append({
            "field_name": "Source Links",
            "field_uuid": FIELD_UUIDS["Source Links"],
            "value": url
        })
    
    # 10. Downloadable? (radio) - from 'downloadable' column
    downloadable = safe_str(row.get('downloadable', ''))
    if downloadable:
        # Convert TRUE/FALSE to Yes/No or whatever ODR expects
        dl_val = "Yes" if downloadable.upper() == "TRUE" else "No"
        if dl_val in radio_options["Downloadable?"]:
            fields.append({
                "field_name": "Downloadable?",
                "field_uuid": FIELD_UUIDS["Downloadable?"],
                "values": [{
                    "template_radio_option_uuid": radio_options["Downloadable?"][dl_val],
                    "name": dl_val,
                    "selected": 1
                }]
            })
    
    # 11. Source Citation (text) - lookup from BibTeX citations
    citation = citations.get(source_id, source_id) if source_id else "N/A"
    # Truncate to 250 chars for ODR ShortVarchar limit
    if len(citation) > 250:
        citation = citation[:247] + "..."
    fields.append({
        "field_name": "Source Citation",
        "field_uuid": FIELD_UUIDS["Source Citation"],
        "value": citation
    })
    
    return fields


def find_data_file(record_id, data_type, sample_type, source_id):
    """Find the data file path.

    Try {type}/{sample}/{source}/{id}.csv first, fall back to
    {type}/{sample}/{id}.csv (some sources have no per-source subdir).
    """
    candidates = [
        DATA_DIR / data_type.lower() / sample_type / source_id,
        DATA_DIR / data_type.lower() / sample_type,
    ]
    for search_dir in candidates:
        if not search_dir.exists():
            continue
        for f in search_dir.glob("*.csv"):
            if "src" not in str(f.parent) and record_id in f.stem:
                return f
    return None


def upload_complete_record(client, record_id, row, radio_options, tag_options=None, citations=None):
    """Upload a single record with complete metadata."""
    print(f"\n{'='*60}")
    print(f"Uploading: {record_id}")
    print(f"{'='*60}")
    
    # Get values
    source = safe_str(row.get('source', ''))
    sample = safe_str(row.get('sample', ''))
    data_type = safe_str(row.get('type', ''))
    
    print(f"  Source: {source}")
    print(f"  Sample: {sample}")
    print(f"  Type: {data_type}")
    print(f"  Tags: {safe_str(row.get('tags', ''))}")
    print(f"  Units: {safe_str(row.get('units', ''))}")
    print(f"  Methods: {safe_str(row.get('methods', ''))}")
    print(f"  Downloadable: {safe_str(row.get('downloadable', ''))}")
    print(f"  URL: {safe_str(row.get('url', ''))}")
    
    # Find data file
    file_path = find_data_file(record_id, data_type, sample, source)
    print(f"  File: {file_path.name if file_path else 'NOT FOUND'}")
    
    if not file_path or not file_path.exists():
        print("  [SKIP] Data file not found")
        return False
    
    # Create record
    print("\n  Creating record...")
    rec = client.create_record(DATASET_UUID)
    record_uuid = rec.get("record_uuid")
    print(f"  Created: {rec.get('record_name')} ({record_uuid})")
    
    # Build fields
    fields = build_fields(row, radio_options, tag_options, citations)
    print(f"\n  Pushing {len(fields)} metadata fields:")
    for f in fields:
        # Handle different field types: value, values (radio), tags
        if 'value' in f:
            val = f.get('value', '')
        elif 'values' in f:
            val = f.get('values', [{}])[0].get('name', '?')
        elif 'tags' in f:
            val = ', '.join([t.get('name', '') for t in f.get('tags', [])])
        else:
            val = '?'
        print(f"    - {f['field_name']}: {str(val)[:50]}...")
    
    rec["fields"] = fields
    client.push_record(rec)
    print("  [OK] Metadata pushed")
    
    # Upload file
    print(f"\n  Uploading file: {file_path.name}")
    client.upload_file(
        file_path=str(file_path),
        record_uuid=record_uuid,
        dataset_uuid=DATASET_UUID,
        template_field_uuid="",
        field_uuid=FIELD_UUIDS["Data File"],
        name=file_path.name
    )
    print("  [OK] File uploaded")
    
    print(f"\n  SUCCESS: https://www.odr.io/view/record/{record_uuid}")
    return True


def main():
    print("=" * 60)
    print("COMPLETE RECORD UPLOAD - ALL FIELDS")
    print("=" * 60)
    
    # Load CSV
    print("\n1. Loading metadata CSV...")
    meta = load_metadata()
    print(f"   Loaded {len(meta)} records")
    
    # Auth
    print("\n2. Authenticating...")
    client = ODRAPIClient(BASE_URL, USERNAME, PASSWORD)
    client.authenticate()
    print("   Done!")
    
    # Discover radio options
    print("\n3. Discovering radio options...")
    radio_options = discover_radio_options(client)
    
    # Discover tag options
    print("\n4. Discovering tag options...")
    tag_options = discover_tag_options(client)
    
    # Load citations from BibTeX
    print("\n5. Loading citations...")
    citations = load_citations(BIB_PATH)
    
    # Disable tag fields (server-side hierarchy bug on ODR; re-enable once fixed)
    SKIP_TAG_FIELDS = os.environ.get("SKIP_TAG_FIELDS", "1") == "1"
    if SKIP_TAG_FIELDS:
        print("\n   [INFO] Tags / Units / Methods disabled (SKIP_TAG_FIELDS=1)")
        tag_options = {"Tags": {}, "Units": {}, "Methods": {}}

    # Mode: 'test' = one record, 'all' = entire CSV
    MODE = os.environ.get("MODE", "test")
    LIMIT = int(os.environ.get("LIMIT", "0"))  # 0 = no limit

    if MODE == "test":
        test_id = os.environ.get("TEST_ID", "table1_GiradF4-1India")
        print(f"\n6. Testing with one record: {test_id}")
        if test_id in meta.index:
            row = meta.loc[test_id]
            upload_complete_record(client, test_id, row, radio_options, tag_options, citations)
        else:
            print(f"   [ERROR] Record '{test_id}' not found in metadata")
        return

    # Bulk mode
    print(f"\n6. Bulk upload mode (LIMIT={LIMIT or 'none'})")
    ok = fail = 0
    ids = list(meta.index)
    if LIMIT:
        ids = ids[:LIMIT]
    for i, rec_id in enumerate(ids, 1):
        row = meta.loc[rec_id]
        print(f"\n[{i}/{len(ids)}] {rec_id}")
        try:
            if upload_complete_record(client, rec_id, row, radio_options, tag_options, citations):
                ok += 1
            else:
                fail += 1
        except Exception as e:
            print(f"   [ERROR] {e}")
            fail += 1
    print(f"\n{'='*60}\nDONE: {ok} succeeded, {fail} failed\n{'='*60}")


if __name__ == "__main__":
    main()
