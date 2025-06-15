from fastapi import FastAPI, HTTPException, Form, UploadFile, File, Request, APIRouter
from typing import List
import os
from fastapi.responses import JSONResponse, FileResponse
import base64
from io import BytesIO
import traceback
import fitz
from PIL import Image
import shutil
from pathlib import Path
import datetime

from decorators.jwt import jwt_token
from routers.utils.api_files_utils import dir_contents, create_dir, upload_files, search_files
from routers.utils.misc_keycloak_utils import *

files_router = APIRouter()


@files_router.post("/search_files")
async def api_search_files(request: Request):
    try:
        data = await request.form()
        search_str = data.get("search_str")
        results = await search_files(search_str)

        return {"detail": results}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@files_router.post("/download")
async def download_files(path: str = Form(...)):
    try:
        base_dir = os.getcwd()
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
        raise HTTPException(status_code=500, detail=str(e))
    
    
@files_router.post("/delete")
@jwt_token("api_endpoint_delete")
async def delete_file_dir(path: str = Form(...)):
    try:
        base_dir = os.getcwd()  # Get the current working directory
        relative_path = path.lstrip("/\\")
        abs_path = os.path.normpath(os.path.join(base_dir, relative_path))
        
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)
        else:
            raise HTTPException(status_code=400, detail="invalid path")
        
        return JSONResponse(content={"detail": f"deleted: {relative_path}"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
@files_router.post("/create_dir")
@jwt_token("api_endpoint_create")
async def api_create_dir(request: Request):
    try:
        data = await request.form()
        path = data.get("path")
        relative_path = await create_dir(path)
        return JSONResponse(content={"detail": f"directory created: {relative_path}"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@files_router.post("/upload") # TODO: what if duplicate filenames?
@jwt_token("api_endpoint_upload")
async def api_upload_files(request: Request):
    try:
        data = await request.form()
        folder, files, path = data.get("folder"), data.getlist("file"), data.get("path")
        uploaded_files = await upload_files(folder, files, path)
        
        for file in files:
            filename = file.filename
            resource_payload = (
                {
                    "name":f"{path}/{folder}/{filename}",
                    "displayName":f"{path}/{folder}/{filename}",
                    "type":"file",
                    "icon_uri":"",
                    "ownerManagedAccess":False,
                    "attributes":{},
                    "scopes":[]
                }
            )
            await create_resource(resource_payload)
   
        return JSONResponse(content={"detail": uploaded_files})
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@files_router.post("/dir_contents")
@jwt_token("")
async def api_dir_contents(request: Request):
    try:
        print(request.state.permissions)
        data = await request.form()
        path = data.get("path")
        results = await dir_contents(path, request.state.permissions)

        return {"detail": results}
    
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@files_router.post("/file_preview")
async def file_preview(request: Request):
    data = await request.form()
    path = data.get("path")
    base_dir = os.getcwd()
    relative_path = path.lstrip("/\\")
    abs_path = os.path.normpath(os.path.join(base_dir, relative_path))
    print(abs_path)
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
        return JSONResponse(content={"detail": img_b64})
        
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"Error processing file {abs_path}: {tb_str}")
        raise HTTPException(status_code=500, detail=str(e))