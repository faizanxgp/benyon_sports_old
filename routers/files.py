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
from datetime import datetime
import csv

from decorators.jwt import jwt_token
from routers.utils.api_files_utils import *
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
    

@files_router.post("/download_file")
@jwt_token("")
async def api_download_file(request: Request):
    try:
        data = await request.form()
        path = data.get("path")
        username = request.state.email
        user_id = request.state.user_id
        
        file_response = await download_file(path, user_id, username)
        
        return file_response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
@files_router.post("/delete")
@jwt_token("all_endpoints")
async def api_delete_file_and_dir(request: Request):
    try:
        data = await request.form()
        path = data.get("path")
        return JSONResponse(content={"detail": await delete_file_and_dir(path)})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
@files_router.post("/create_dir")
@jwt_token("all_endpoints")
async def api_create_dir(request: Request):
    try:
        data = await request.form()
        path = data.get("path")
        relative_path = await create_dir(path)

        return JSONResponse(content={"detail": f"directory created: {relative_path}"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@files_router.post("/upload") # TODO: what if duplicate filenames?
@jwt_token("all_endpoints")
async def api_upload_files(request: Request):
    try:
        data = await request.form()
        folder, files, path = data.get("folder"), data.getlist("file"), data.get("path")
        uploaded_files = await upload_files(folder, files, path)   
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
        tb_str = traceback.format_exc()
        print(f"Error retrieving dir contents of {path}: {tb_str}")
        raise HTTPException(status_code=500, detail=str(e))


@files_router.post("/file_preview")
@jwt_token("")
async def api_file_preview(request: Request):
    try:
        data = await request.form()
        path = data.get("path")
        preview_img = await file_preview(path)
        return JSONResponse(content={"detail": preview_img})
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"Error processing file {path}: {tb_str}")
        raise HTTPException(status_code=500, detail=str(e))


@files_router.post("/upload_multiple")
@jwt_token("all_endpoints")
async def api_upload_multiple_folders(request: Request):
    """
    Upload multiple folders with complex directory structures.
    
    Expects:
    - Multiple files attached via form-data
    - A 'directory_structure' field containing a serialized JSON object
      describing the intended directory structure
    
    Example directory_structure JSON:
    {
        "folders": {
            "documents": {
                "folders": {
                    "pdfs": {
                        "files": ["doc1.pdf", "doc2.pdf"]
                    },
                    "images": {
                        "files": ["img1.jpg", "img2.png"]
                    }
                },
                "files": ["readme.txt"]
            },
            "media": {
                "files": ["video1.mp4", "audio1.mp3"]
            }
        },
        "files": ["root_file.txt"]
    }
    """
    try:
        data = await request.form()
        directory_structure = data.get("directory_structure")
        
        files = data.getlist("file")
        
        if not directory_structure:
            raise HTTPException(status_code=400, detail="directory_structure field is required")
        
        if not files:
            raise HTTPException(status_code=400, detail="No files uploaded")
        
        result = await upload_multiple_folders(files, directory_structure)
        return JSONResponse(content={"detail": result})
    
    except HTTPException as he:
        print(f"Error in upload_multiple endpoint: {he}")
        raise he
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"Error in upload_multiple endpoint: {tb_str}")
        raise HTTPException(status_code=500, detail=str(e))