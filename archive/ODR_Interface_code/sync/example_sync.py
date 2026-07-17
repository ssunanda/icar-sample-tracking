#!/usr/bin/env python3
"""
Example usage of SCOBI Sync Manager

This script demonstrates common sync workflows:
1. Initial sync (download all from ODR)
2. Regular sync (bidirectional with conflict detection)
3. Push-only workflow (upload local changes)
"""

from ODR_API_Client import ODRAPIClient
from SCOBI_sync_manager import SCOBISyncManager
import sys

# Configuration
BASE_URL = "https://odr.io/api/v4"
USERNAME = "amshahid@ncsu.edu"
PASSWORD = "qkh8fjd6adh*NPU!ekn"
DATASET_UUID = "063c0d3d4bd183ab0dda87c544ae"


def example_initial_sync():
    """
    Example 1: Initial sync - download everything from ODR
    Use this when setting up a new local copy
    """
    print("="*60)
    print("EXAMPLE 1: Initial Sync (Download from ODR)")
    print("="*60)

    client = ODRAPIClient(BASE_URL, USERNAME, PASSWORD)
    client.authenticate()

    sync = SCOBISyncManager(client, data_dir="data")

    # Pull everything from ODR, overwriting local
    results = sync.sync_dataset(
        DATASET_UUID,
        conflict_strategy='odr_wins'  # ODR is source of truth for initial sync
    )

    print(f"\n✅ Initial sync complete!")
    print(f"   Downloaded {len(results['pulled'])} files")
    print(f"   Already up-to-date: {len(results['no_change'])} files")


def example_regular_sync():
    """
    Example 2: Regular bidirectional sync with conflict detection
    Use this for ongoing work where both local and ODR might have changes
    """
    print("\n" + "="*60)
    print("EXAMPLE 2: Regular Sync (Bidirectional)")
    print("="*60)

    client = ODRAPIClient(BASE_URL, USERNAME, PASSWORD)
    client.authenticate()

    sync = SCOBISyncManager(client, data_dir="data")

    # Interactive sync - ask user to resolve conflicts
    results = sync.sync_dataset(
        DATASET_UUID,
        conflict_strategy='ask'  # Prompt for each conflict
    )

    print(f"\n✅ Sync complete!")
    print(f"   Pulled: {len(results['pulled'])} files")
    print(f"   Pushed: {len(results['pushed'])} files")
    print(f"   Conflicts: {len(results['conflicts'])} files")
    print(f"   Errors: {len(results['errors'])} files")


def example_push_local_changes():
    """
    Example 3: Push local changes to ODR
    Use this after making local edits that should go to ODR
    """
    print("\n" + "="*60)
    print("EXAMPLE 3: Push Local Changes")
    print("="*60)

    client = ODRAPIClient(BASE_URL, USERNAME, PASSWORD)
    client.authenticate()

    sync = SCOBISyncManager(client, data_dir="data")

    # Push local changes, keeping local version in conflicts
    results = sync.sync_dataset(
        DATASET_UUID,
        conflict_strategy='local_wins'  # Local changes take precedence
    )

    print(f"\n✅ Push complete!")
    print(f"   Uploaded: {len(results['pushed'])} files")

    if results['conflicts']:
        print(f"\n⚠️  Warning: {len(results['conflicts'])} conflicts resolved by keeping local version")


def example_newest_wins_sync():
    """
    Example 4: Automatic sync using timestamps
    Use this for automated syncing (cron jobs) where no manual intervention
    """
    print("\n" + "="*60)
    print("EXAMPLE 4: Automated Sync (Newest Wins)")
    print("="*60)

    client = ODRAPIClient(BASE_URL, USERNAME, PASSWORD)
    client.authenticate()

    sync = SCOBISyncManager(client, data_dir="data")

    # Automatic conflict resolution based on timestamps
    results = sync.sync_dataset(
        DATASET_UUID,
        conflict_strategy='newest_wins'  # Most recent modification wins
    )

    print(f"\n✅ Automated sync complete!")
    print(f"   Pulled: {len(results['pulled'])} files")
    print(f"   Pushed: {len(results['pushed'])} files")

    # Log conflicts for review
    if results['conflicts']:
        print(f"\n⚠️  Conflicts auto-resolved: {len(results['conflicts'])}")
        with open('sync_conflicts.log', 'a') as f:
            for item in results['conflicts']:
                f.write(f"{item['record']}: {item['action']}\n")


def example_workflow():
    """
    Example 5: Complete workflow for daily work
    This is how you'd use sync in practice
    """
    print("\n" + "="*60)
    print("EXAMPLE 5: Daily Workflow")
    print("="*60)

    client = ODRAPIClient(BASE_URL, USERNAME, PASSWORD)
    client.authenticate()

    sync = SCOBISyncManager(client, data_dir="data")

    # Step 1: Start of day - pull latest from ODR
    print("\n📥 Step 1: Pulling latest changes from ODR...")
    results = sync.sync_dataset(DATASET_UUID, conflict_strategy='odr_wins')
    print(f"   ✅ Pulled {len(results['pulled'])} files")

    # Step 2: User does work locally
    print("\n✏️  Step 2: You work on files locally...")
    print("   (Make your changes to data files)")
    input("   Press Enter when done with local work...")

    # Step 3: End of day - push local changes to ODR
    print("\n📤 Step 3: Pushing local changes to ODR...")
    results = sync.sync_dataset(DATASET_UUID, conflict_strategy='local_wins')
    print(f"   ✅ Pushed {len(results['pushed'])} files")

    # Step 4: Handle any conflicts
    if results['conflicts']:
        print(f"\n⚠️  Step 4: {len(results['conflicts'])} conflicts need attention")
        print("   Re-running sync with interactive resolution...")
        results = sync.sync_dataset(DATASET_UUID, conflict_strategy='ask')

    print("\n✅ Workflow complete! Your work is synced with ODR.")


def main():
    """Main function to run examples"""
    print("\n🔄 SCOBI Sync Manager - Usage Examples")
    print("="*60)

    if len(sys.argv) > 1:
        example = sys.argv[1]

        if example == "initial":
            example_initial_sync()
        elif example == "regular":
            example_regular_sync()
        elif example == "push":
            example_push_local_changes()
        elif example == "auto":
            example_newest_wins_sync()
        elif example == "workflow":
            example_workflow()
        else:
            print(f"❌ Unknown example: {example}")
            print_usage()
    else:
        print_usage()


def print_usage():
    """Print usage instructions"""
    print("\nUsage: python example_sync.py [example]")
    print("\nAvailable examples:")
    print("  initial   - Initial sync (download from ODR)")
    print("  regular   - Regular bidirectional sync")
    print("  push      - Push local changes to ODR")
    print("  auto      - Automated sync (newest wins)")
    print("  workflow  - Complete daily workflow")
    print("\nExample:")
    print("  python example_sync.py initial")


if __name__ == "__main__":
    main()
