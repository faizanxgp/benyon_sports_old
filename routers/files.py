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
        return await download_file(path)
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