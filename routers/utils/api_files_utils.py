import os
from pathlib import Path
import datetime
import shutil
import traceback
from fastapi import HTTPException

from routers.utils.misc_files_utils import get_owner, search_files_and_folders, dir_contents_details


async def search_files(search_str: str):
    try:
        base_dir = os.path.normpath(os.path.join(os.getcwd(), "remote"))
        results = search_files_and_folders(base_dir, search_str)
        return results
    except Exception as e:
        raise e


async def dir_contents(path: str, permissions):
    try:
        base_dir = os.path.normpath(os.path.join(os.getcwd(), "remote"))
        relative_path = path.lstrip("/\\")
        abs_path = os.path.normpath(os.path.join(base_dir, relative_path))
        p_abs_path = Path(abs_path)
        if not p_abs_path.is_dir(): raise HTTPException(status_code=404, detail="path does not exist")
        results = await dir_contents_details(abs_path, permissions)
        return results
    
    except Exception as e:
        raise e


async def create_dir(path: str):
    try:
        base_dir = os.path.normpath(os.path.join(os.getcwd(), "remote"))
        relative_path = path.lstrip("/\\")
        abs_path = os.path.normpath(os.path.join(base_dir, relative_path))
        os.makedirs(abs_path, exist_ok=False)
        return relative_path
    except Exception as e:
        raise e


async def upload_files(folder: str, files, path: str):
    try:
        base_dir = os.path.normpath(os.path.join(os.getcwd(), "remote"))
        relative_path = path.lstrip("/\\")
        if folder:
            relative_path = os.path.join(relative_path, folder)
            print("relative_path:", relative_path)
            await create_dir(relative_path)
        abs_path = os.path.normpath(os.path.join(base_dir, relative_path))
        uploaded_files = []
        for file in files:
            file_path = os.path.join(abs_path, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            uploaded_files.append(file.filename)

        return uploaded_files
    
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"Error in upload_files: {tb_str}")
        raise e