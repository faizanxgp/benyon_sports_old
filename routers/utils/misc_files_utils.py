import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import datetime


def _get_owner_windows(path: str) -> str:
    """
    Uses Win32 API calls (via ctypes) to resolve the owner of a file/folder.
    Returns "DOMAIN\\User" on success, or raises an exception on failure.
    """
    # Constants
    SE_FILE_OBJECT = 1
    OWNER_SECURITY_INFORMATION = 1

    # Prepare GetNamedSecurityInfoW
    advapi32 = ctypes.windll.advapi32
    GetNamedSecurityInfoW = advapi32.GetNamedSecurityInfoW
    GetNamedSecurityInfoW.restype = wintypes.DWORD
    GetNamedSecurityInfoW.argtypes = [
        wintypes.LPWSTR,    # pObjectName
        wintypes.DWORD,     # ObjectType
        wintypes.DWORD,     # SecurityInfo
        ctypes.POINTER(ctypes.c_void_p),  # ppsidOwner
        ctypes.POINTER(ctypes.c_void_p),  # ppsidGroup
        ctypes.POINTER(ctypes.c_void_p),  # ppDacl
        ctypes.POINTER(ctypes.c_void_p),  # ppSacl
        ctypes.POINTER(ctypes.c_void_p)   # ppSecurityDescriptor
    ]

    owner_sid = ctypes.c_void_p()
    # We don’t need group/pDacl/pSacl, so pass None for those pointers,
    # but we do need a place to store the returned SECURITY_DESCRIPTOR so we can free it later.
    pSecurityDescriptor = ctypes.c_void_p()

    # Call GetNamedSecurityInfoW to get an owner SID pointer
    result = GetNamedSecurityInfoW(
        ctypes.c_wchar_p(path),
        SE_FILE_OBJECT,
        OWNER_SECURITY_INFORMATION,
        ctypes.byref(owner_sid),
        None,
        None,
        None,
        ctypes.byref(pSecurityDescriptor)
    )
    if result != 0:
        # Non‐zero return code → Win32 error
        raise ctypes.WinError(result)

    try:
        # Now call LookupAccountSidW to turn that SID into a “DOMAIN\\Username” string
        LookupAccountSidW = advapi32.LookupAccountSidW
        LookupAccountSidW.restype = wintypes.BOOL
        LookupAccountSidW.argtypes = [
            wintypes.LPCWSTR,  # lpSystemName (None for local machine)
            wintypes.LPVOID,   # Sid
            wintypes.LPWSTR,   # Name buffer
            ctypes.POINTER(wintypes.DWORD),  # cchName
            wintypes.LPWSTR,   # Domain buffer
            ctypes.POINTER(wintypes.DWORD),  # cchDomain
            ctypes.POINTER(wintypes.DWORD)   # peUse
        ]

        # First call to get required buffer sizes
        name_len = wintypes.DWORD(0)
        domain_len = wintypes.DWORD(0)
        peUse = wintypes.DWORD()
        # This call is expected to fail with ERROR_INSUFFICIENT_BUFFER (122),
        # but it will fill in name_len and domain_len for us
        LookupAccountSidW(
            None,
            owner_sid,
            None,
            ctypes.byref(name_len),
            None,
            ctypes.byref(domain_len),
            ctypes.byref(peUse)
        )

        # Allocate buffers of the needed size:
        name_buf = ctypes.create_unicode_buffer(name_len.value)
        domain_buf = ctypes.create_unicode_buffer(domain_len.value)

        success = LookupAccountSidW(
            None,
            owner_sid,
            name_buf,
            ctypes.byref(name_len),
            domain_buf,
            ctypes.byref(domain_len),
            ctypes.byref(peUse)
        )
        if not success:
            raise ctypes.WinError(ctypes.get_last_error())

        return f"{domain_buf.value}\\{name_buf.value}"
    finally:
        # Free the SECURITY_DESCRIPTOR that GetNamedSecurityInfoW allocated
        if pSecurityDescriptor:
            # LocalFree is the correct way to free this pointer
            ctypes.windll.kernel32.LocalFree(pSecurityDescriptor)


def get_owner(path: str) -> str:
    """
    Cross‐platform owner lookup:
    - On Windows: try the Win32/ctypes routine above.
    - On Unix‐like: just call Path(path).owner().
    If anything fails, return "UNKNOWN".
    """
    try:
        if os.name == "nt":
            # On Windows:
            return _get_owner_windows(path)
        else:
            # On Unix‐like:
            return Path(path).owner()
    except Exception:
        return "UNKNOWN"


def search_files_and_folders(root, query, case_sensitive=False):
    """
    Recursively search under `root` for any file or folder whose name contains `query`.
    Returns a list of full paths to matching files/folders.
    
    - root:      string path where search begins (e.g. "." or "C:\\Users\\...")
    - query:     substring to look for in file/folder names
    - case_sensitive: if False (default), perform a case-insensitive match
    """
    matches = []
    if not case_sensitive:
        query_lower = query.lower()

    for dirpath, dirnames, filenames in os.walk(root):
        # check folders
        for dirname in dirnames:
            name_to_check = dirname if case_sensitive else dirname.lower()
            if (query in dirname) if case_sensitive else (query_lower in name_to_check):
                matches.append(os.path.join(dirpath, dirname))

        # check files
        for filename in filenames:
            name_to_check = filename if case_sensitive else filename.lower()
            if (query in filename) if case_sensitive else (query_lower in name_to_check):
                found_path = os.path.join(dirpath, filename)
                base_dir = os.path.normpath(os.path.join(os.getcwd(), "remote"))
                relative_path = os.path.relpath(found_path, base_dir)
                matches.append(relative_path)

    return matches


async def dir_contents_details(abs_path, permissions):
    try:
        # check permissions
        base_dir = os.path.normpath(os.path.join(os.getcwd(), "remote"))
        relative_path = os.path.relpath(abs_path, base_dir)
        if f"path_{relative_path}" not in permissions: raise Exception("no access")
        
        results = []
        for entry in os.listdir(abs_path):
            entry_path = os.path.join(abs_path, entry)
            p = Path(entry_path)
            try:
                st = p.stat()
                size_bytes = st.st_size

                # Cross‐platform owner lookup
                try:
                    owner_name = get_owner(abs_path)
                except Exception:
                    # Fallback if owner() fails
                    owner_name = "UNKNOWN"

                # Last‐modified as an ISO‐8601 string (UTC)
                last_mod = datetime.datetime.fromtimestamp(
                    st.st_mtime, tz=datetime.timezone.utc
                )
                last_mod_iso = last_mod.isoformat()
                
                num_files = 0
                num_subdirs = 0
                
                if p.is_dir():
                    try:
                        # Count only immediate children (non‐recursive)
                        for child in p.iterdir():
                            if child.is_file():
                                num_files += 1
                            elif child.is_dir():
                                num_subdirs += 1
                    except Exception as inner_err:
                        # If listing fails (permissions, etc.), log and leave counts at 0
                        print(f"    ❗ couldn’t list contents of {entry_path}: {inner_err}")

                results.append({
                    "name": entry,
                    "is_dir": p.is_dir(),
                    "size_bytes": size_bytes,
                    "owner": owner_name,
                    "last_modified": last_mod_iso,
                    "num_files": num_files,
                    "num_subdirs": num_subdirs
                })
            except Exception as file_err:
                # Skip entries that can’t be stat’d or owner() fails unexpectedly
                print(f"  ❗ couldn’t process {entry_path}: {file_err}")
                continue
        
        return results
    
    except Exception as e:
        raise e from e
