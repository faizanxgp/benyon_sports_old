import os
from pathlib import Path
import datetime
import shutil
import traceback
from fastapi import HTTPException
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
import base64
from io import BytesIO
import fitz
from PIL import Image

from routers.utils.misc_files_utils import *
from routers.utils.misc_keycloak_utils import *


async def file_preview(path):
    base_dir = os.path.normpath(os.path.join(os.getcwd(), "remote"))
    relative_path = path.lstrip("/\\")
    abs_path = os.path.normpath(os.path.join(base_dir, relative_path))
    # print(abs_path)
    if not os.path.isfile(abs_path):
        raise HTTPException(status_code=400, detail="Invalid file path")
    ext = os.path.splitext(abs_path)[1].lower()
    try:
        if ext == ".pdf":
            doc = fitz.open(abs_path)
            if doc.page_count < 1:
                raise HTTPException(status_code=500, detail="Could not render PDF")
            page = doc.load_page(0)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img_data = pix.tobytes("png")
            img = Image.open(BytesIO(img_data))
        elif ext in [".png", ".jpg", ".jpeg"]:
            img = Image.open(abs_path)
        else:
            raise HTTPException(status_code=415, detail="Preview not supported for this file type")

        img.thumbnail((100, 100))
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        preview_path = os.path.join(os.getcwd(), "preview/preview_output.png")
        img.save(preview_path, format="PNG") # save preview
        img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return img_b64
        
    except Exception as e:
        raise e from e
    

async def download_file(path: str):
    try:
        base_dir = os.path.normpath(os.path.join(os.getcwd(), "remote"))
        relative_path = path.lstrip("/\\")
        abs_path = os.path.normpath(os.path.join(base_dir, relative_path))
        download_file_path = Path(abs_path).resolve()
        if not download_file_path.is_file():
            raise HTTPException(status_code=404, detail=f"File not found: {download_file_path}")
        
        return FileResponse(
        path=download_file_path,
        filename=download_file_path.name
        )
    except Exception as e:
        raise e from e
    

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
        relative_path = str(Path(path.lstrip("/\\")).as_posix())
        abs_path = os.path.normpath(os.path.join(base_dir, relative_path))
        os.makedirs(abs_path, exist_ok=False)
        
        resource_payload = (                            
            {
                "name":relative_path,
                "displayName":relative_path,
                "type":"dir",
                "icon_uri":"",
                "ownerManagedAccess":False,
                "attributes":{},
                "scopes":[]
            }
        )
        await create_resource(resource_payload)
    
        return relative_path
    except Exception as e:
        raise e


async def delete_file_and_dir(path: str):
    try:
        base_dir = os.path.normpath(os.path.join(os.getcwd(), "remote"))
        relative_path = str(Path(path.lstrip("/\\")).as_posix())
        # print("relative_path:", relative_path)
        abs_path = os.path.normpath(os.path.join(base_dir, relative_path))
        all_resources = await get_all_resources()
        # print("all_resources:", all_resources)
        if os.path.isfile(abs_path):
            os.remove(abs_path)
        elif os.path.isdir(abs_path):
            shutil.rmtree(abs_path)
        else:
            raise HTTPException(status_code=400, detail="invalid path")
        for resource in all_resources:
                if relative_path in resource: await delete_resource(all_resources[resource])
        return f"deleted: {relative_path}"
    except Exception as e:
        raise e from e
    

async def upload_files(folder: str, files, path: str):
    try:
        base_dir = os.path.normpath(os.path.join(os.getcwd(), "remote"))
        relative_path = path.lstrip("/\\") if path else ""
        if folder:
            relative_path = os.path.join(relative_path, folder)
            # print("relative_path:", relative_path)
            await create_dir(relative_path)
        abs_path = os.path.normpath(os.path.join(base_dir, relative_path))
        uploaded_files = []
        for file in files:
            file_path = os.path.join(abs_path, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            relative_file_location = str(Path(os.path.join(relative_path, file.filename)).as_posix()) # e.g. docs/test_file.jpg
            resource_payload = (
                {
                    "name":relative_file_location,
                    "displayName":relative_file_location,
                    "type":"file",
                    "icon_uri":"",
                    "ownerManagedAccess":False,
                    "attributes":{},
                    "scopes":[]
                }
            )
            await create_resource(resource_payload)

            uploaded_files.append(file.filename)

        return uploaded_files
    
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"Error in upload_files: {tb_str}")
        raise e from e