"""
Script to delete all resources from the Keycloak client 'benyon_be' 
except for specific protected resources.

This script will:
1. Fetch all resources from the Keycloak client
2. Filter out protected resources that should not be deleted
3. Delete all remaining resources
"""

import asyncio
import sys
import os
import httpx
from typing import Dict, List, Tuple

# Add the parent directory to the path so we can import from routers
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routers.utils.misc_keycloak_utils import get_all_resources, delete_resource, obtain_headers
from routers.utils.keycloak_vars import *

# List of resource names that should NOT be deleted
PROTECTED_RESOURCES = [
    ".",
    "admin"
]

# Configuration for concurrent operations
DEFAULT_MAX_CONCURRENT = 10  # Maximum number of concurrent deletion operations


async def delete_resource_bulk(resource_id: str, resource_name: str, access_token: str = None) -> Tuple[str, bool, str]:
    """
    Delete a single resource and return the result.
    Returns: (resource_name, success, error_message)
    """
    try:
        headers, _ = await obtain_headers(access_token)
        async with httpx.AsyncClient() as client:
            response = await client.delete(base_url + ep_delete_resource + resource_id, headers=headers)
        
        if response.status_code in [200, 201, 204]:
            return resource_name, True, ""
        else:
            return resource_name, False, f"Status: {response.status_code}, Response: {response.text}"
    except Exception as e:
        return resource_name, False, str(e)


async def delete_resources_concurrently(resources_to_delete: Dict[str, str], max_concurrent: int = 10) -> Tuple[List[str], List[Tuple[str, str]]]:
    """
    Delete multiple resources concurrently using asyncio.gather().
    
    Args:
        resources_to_delete: Dictionary mapping resource names to resource IDs
        max_concurrent: Maximum number of concurrent deletion operations
    
    Returns:
        Tuple of (successful_deletions, failed_deletions_with_errors)
    """
    if len(resources_to_delete) == 0:
        return [], []
    
    successful_deletions = []
    failed_deletions = []
    
    # Get access token once for all operations
    access_token = None
    try:
        _, access_token = await obtain_headers()
    except Exception as e:
        print(f"Failed to obtain access token: {e}")
        return [], [(name, str(e)) for name in resources_to_delete.keys()]
    
    # Create semaphore to limit concurrent operations
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def delete_with_semaphore(resource_name: str, resource_id: str):
        async with semaphore:
            return await delete_resource_bulk(resource_id, resource_name, access_token)
    
    # Process resources in batches to avoid overwhelming the server
    resource_items = list(resources_to_delete.items())
    
    print(f"Deleting {len(resource_items)} resources concurrently (max {max_concurrent} at a time)...")
    
    # Create tasks for all deletions
    tasks = [delete_with_semaphore(name, resource_id) for name, resource_id in resource_items]
    
    # Execute all tasks concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    for i, result in enumerate(results):
        resource_name = resource_items[i][0]
        
        if isinstance(result, Exception):
            failed_deletions.append((resource_name, str(result)))
            print(f"  ✗ Error deleting {resource_name}: {result}")
        else:
            name, success, error_msg = result
            if success:
                successful_deletions.append(name)
                print(f"  ✓ Successfully deleted: {name}")
            else:
                failed_deletions.append((name, error_msg))
                print(f"  ✗ Failed to delete: {name} - {error_msg}")
    
    return successful_deletions, failed_deletions


async def list_all_resources():
    """
    List all resources without deleting them (for debugging/verification).
    """
    try:
        print("📋 LISTING RESOURCES (No deletion will occur)")
        print("-" * 50)
        
        # Get all resources from Keycloak
        all_resources = await get_all_resources()
        
        if not all_resources:
            print("No resources found in Keycloak client.")
            return
        
        print(f"\nFound {len(all_resources)} total resources:")
        print("=" * 80)
        print(f"{'Resource Name':<35} | {'Resource ID':<25} | {'Status'}")
        print("=" * 80)
        
        for resource_name, resource_id in all_resources.items():
            status = "🔒 PROTECTED" if resource_name in PROTECTED_RESOURCES else "🗑️  DELETABLE"
            print(f"{resource_name:<35} | {resource_id:<25} | {status}")
        
        print("=" * 80)
        
        protected_count = sum(1 for name in all_resources.keys() if name in PROTECTED_RESOURCES)
        deletable_count = len(all_resources) - protected_count
        
        print(f"\n📊 Summary:")
        print(f"  - Total resources: {len(all_resources)}")
        print(f"  - 🔒 Protected resources: {protected_count}")
        print(f"  - 🗑️  Deletable resources: {deletable_count}")
        
        if deletable_count > 0:
            print(f"\n⚠️  To actually DELETE the {deletable_count} deletable resources, run:")
            print(f"   python delete_resources.py delete")
        else:
            print(f"\n✅ All resources are protected - nothing would be deleted.")
        
    except Exception as e:
        print(f"Error listing resources: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")


def main():
    """
    Main function to handle command line arguments and run the appropriate action.
    
    Usage:
    python delete_resources.py [action] [--concurrent N]
    
    Actions:
    - list/ls/show: List all resources without deleting
    - delete/del/remove: Delete all resources except protected ones
    
    Options:
    - --concurrent N: Maximum number of concurrent deletion operations (default: 10)
    """
    action = "list"  # default action
    max_concurrent = DEFAULT_MAX_CONCURRENT
    
    # Parse command line arguments
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.lower() in ['list', 'ls', 'show']:
            action = "list"
        elif arg.lower() in ['delete', 'del', 'remove']:
            action = "delete"
        elif arg == '--concurrent' and i + 1 < len(args):
            try:
                max_concurrent = int(args[i + 1])
                if max_concurrent < 1:
                    print("Error: --concurrent value must be at least 1")
                    return
                i += 1  # Skip the next argument as it's the value
            except ValueError:
                print("Error: --concurrent value must be a number")
                return
        elif arg.startswith('--concurrent='):
            try:
                max_concurrent = int(arg.split('=')[1])
                if max_concurrent < 1:
                    print("Error: --concurrent value must be at least 1")
                    return
            except (ValueError, IndexError):
                print("Error: --concurrent value must be a number")
                return
        else:
            print(f"Unknown argument: {arg}")
            print("Usage:")
            print("  python delete_resources.py [list|delete] [--concurrent N]")
            print("  python delete_resources.py list               # List all resources without deleting")
            print("  python delete_resources.py delete             # Delete all resources except protected ones")
            print("  python delete_resources.py delete --concurrent 20  # Use 20 concurrent operations")
            return
        i += 1
    
    if action == "list":
        print("Mode: LIST RESOURCES ONLY")
        asyncio.run(list_all_resources())
    elif action == "delete":
        print(f"Mode: DELETE RESOURCES (max concurrent: {max_concurrent})")
        asyncio.run(delete_all_resources_except_protected_with_concurrency(max_concurrent))
    else:
        # Default action when no arguments provided - show usage
        print("=" * 70)
        print("KEYCLOAK RESOURCE DELETION TOOL")
        print("=" * 70)
        print("This script will delete ALL resources from the Keycloak client 'benyon_be'")
        print("EXCEPT for protected resources: " + str(PROTECTED_RESOURCES))
        print()
        print("Usage:")
        print("  python delete_resources.py list               # List all resources (safe)")
        print("  python delete_resources.py delete             # DELETE resources (destructive)")
        print("  python delete_resources.py delete --concurrent 20  # Use custom concurrency")
        print()
        print("Examples:")
        print("  python delete_resources.py list               # See what would be deleted")
        print("  python delete_resources.py delete             # Actually delete resources")
        print()
        print("⚠️  WARNING: The 'delete' action will permanently remove resources!")
        print("=" * 70)
        print()
        
        # Show current resources for convenience
        print("Current resources in your Keycloak client:")
        asyncio.run(list_all_resources())


async def delete_all_resources_except_protected_with_concurrency(max_concurrent: int = DEFAULT_MAX_CONCURRENT):
    """
    Delete all resources from the Keycloak client except for protected ones.
    Uses configurable concurrency level.
    """
    try:
        print("Starting resource deletion process...")
        print(f"Protected resources (will NOT be deleted): {PROTECTED_RESOURCES}")
        print(f"Maximum concurrent operations: {max_concurrent}")
        
        # Get all resources from Keycloak
        print("\nFetching all resources from Keycloak...")
        all_resources = await get_all_resources()
        
        if not all_resources:
            print("No resources found in Keycloak client.")
            return
        
        print(f"Found {len(all_resources)} total resources:")
        for resource_name, resource_id in all_resources.items():
            print(f"  - {resource_name} (ID: {resource_id})")
        
        # Filter out protected resources
        resources_to_delete = {}
        protected_found = []
        
        for resource_name, resource_id in all_resources.items():
            if resource_name in PROTECTED_RESOURCES:
                protected_found.append(resource_name)
                print(f"\nSkipping protected resource: {resource_name}")
            else:
                resources_to_delete[resource_name] = resource_id
        
        # Show summary
        print(f"\nSummary:")
        print(f"  - Total resources found: {len(all_resources)}")
        print(f"  - Protected resources found: {len(protected_found)} {protected_found}")
        print(f"  - Resources to delete: {len(resources_to_delete)}")
        
        if not resources_to_delete:
            print("\nNo resources to delete. All resources are protected.")
            return
        
        # Ask for confirmation
        print(f"\nResources that will be DELETED:")
        for resource_name, resource_id in resources_to_delete.items():
            print(f"  - {resource_name} (ID: {resource_id})")
        
        confirmation = input(f"\nAre you sure you want to delete {len(resources_to_delete)} resources? (yes/no): ").strip().lower()
        
        if confirmation not in ['yes', 'y']:
            print("Operation cancelled by user.")
            return
        
        # Delete resources using concurrent deletion
        print(f"\nStarting concurrent deletion process...")
        successful_deletions, failed_deletions = await delete_resources_concurrently(resources_to_delete, max_concurrent)
        
        # Final summary
        print(f"\nDeletion completed!")
        print(f"  - Successfully deleted: {len(successful_deletions)} resources")
        print(f"  - Failed to delete: {len(failed_deletions)} resources")
        print(f"  - Protected resources preserved: {len(protected_found)}")
        
        if successful_deletions:
            print(f"\nSuccessfully deleted resources:")
            for resource_name in successful_deletions:
                print(f"  ✓ {resource_name}")
        
        if failed_deletions:
            print(f"\nFailed to delete resources:")
            for resource_name, error_msg in failed_deletions:
                print(f"  ✗ {resource_name}: {error_msg}")
            print("\nSome resources failed to delete. Please check the error messages above.")
        else:
            print("\nAll non-protected resources have been successfully deleted!")
            
    except Exception as e:
        print(f"Error during resource deletion process: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    main()
