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

# Import the new PDF functions explicitly
from routers.utils.api_files_utils import (
    get_pdf_info, 
    get_pdf_page, 
    get_pdf_pages_range, 
    search_pdf_text,
    get_pdf_page_with_text,
    get_pdf_text_layer,
    get_raw_pdf
)

# Import the new DOCX, XLSX, PPTX functions explicitly
from routers.utils.api_files_utils import (
    get_docx_info,
    get_docx_page,
    get_xlsx_info,
    get_xlsx_sheet,
    get_pptx_info,
    get_pptx_slide
)

# Import the new functions for newly added files
from routers.utils.api_files_utils import get_newly_added_files, get_newly_added_files_since_timestamp

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
    
    
@files_router.delete("/delete")
@jwt_token("admin")
async def api_delete_file_and_dir(request: Request):
    try:
        data = await request.form()
        path = data.get("path")
        return JSONResponse(content={"detail": await delete_file_and_dir(path)})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
@files_router.post("/create_dir")
@jwt_token("admin")
async def api_create_dir(request: Request):
    try:
        data = await request.form()
        path = data.get("path")
        relative_path = await create_dir(path)

        return JSONResponse(content={"detail": f"directory created: {relative_path}"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@files_router.post("/upload") # TODO: what if duplicate filenames?
@jwt_token("admin")
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
        # print(request.state.permissions)
        data = await request.form()
        path = data.get("path")
        results = await dir_contents(path, request.state.permissions, request.state.roles)

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
@jwt_token("admin")
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


@files_router.post("/pdf_info")
@jwt_token("")
async def api_pdf_info(request: Request):
    """Get PDF metadata like page count, dimensions, etc."""
    try:
        data = await request.form()
        path = data.get("path")
        pdf_info = await get_pdf_info(path)
        return JSONResponse(content={"detail": pdf_info})
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"Error getting PDF info for {path}: {tb_str}")
        raise HTTPException(status_code=500, detail=str(e))


@files_router.post("/pdf_page")
@jwt_token("")
async def api_pdf_page(request: Request):
    """Get a specific page from PDF as base64 image"""
    try:
        data = await request.form()
        path = data.get("path")
        page_num = int(data.get("page", 1))
        quality = data.get("quality", "medium")  # low, medium, high
        scale = float(data.get("scale", 1.0))
        
        page_data = await get_pdf_page(path, page_num, quality, scale)
        return JSONResponse(content={"detail": page_data})
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"Error getting PDF page {page_num} for {path}: {tb_str}")
        raise HTTPException(status_code=500, detail=str(e))


@files_router.post("/pdf_pages_range")
@jwt_token("")
async def api_pdf_pages_range(request: Request):
    """Get multiple PDF pages in a range"""
    try:
        data = await request.form()
        path = data.get("path")
        start_page = int(data.get("start_page", 1))
        end_page = int(data.get("end_page", start_page))
        quality = data.get("quality", "medium")
        scale = float(data.get("scale", 1.0))
        
        pages_data = await get_pdf_pages_range(path, start_page, end_page, quality, scale)
        return JSONResponse(content={"detail": pages_data})
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"Error getting PDF pages {start_page}-{end_page} for {path}: {tb_str}")
        raise HTTPException(status_code=500, detail=str(e))


@files_router.post("/pdf_search")
@jwt_token("")
async def api_pdf_search(request: Request):
    """Search for text within PDF and return page numbers and positions"""
    try:
        data = await request.form()
        path = data.get("path")
        search_text = data.get("search_text")
        
        search_results = await search_pdf_text(path, search_text)
        return JSONResponse(content={"detail": search_results})
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"Error searching PDF {path}: {tb_str}")
        raise HTTPException(status_code=500, detail=str(e))


@files_router.post("/pdf_page_with_text")
@jwt_token("")
async def api_pdf_page_with_text(request: Request):
    """Get a PDF page with both image and text layer for text selection"""
    try:
        data = await request.form()
        path = data.get("path")
        page_num = int(data.get("page", 1))
        quality = data.get("quality", "medium")
        scale = float(data.get("scale", 1.0))
        
        page_data = await get_pdf_page_with_text(path, page_num, quality, scale)
        return JSONResponse(content={"detail": page_data})
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"Error getting PDF page with text {page_num} for {path}: {tb_str}")
        raise HTTPException(status_code=500, detail=str(e))


@files_router.post("/pdf_text_layer")
@jwt_token("")
async def api_pdf_text_layer(request: Request):
    """Get just the text layer data for a PDF page"""
    try:
        data = await request.form()
        path = data.get("path")
        page_num = int(data.get("page", 1))
        scale = float(data.get("scale", 1.0))
        
        text_data = await get_pdf_text_layer(path, page_num, scale)
        return JSONResponse(content={"detail": text_data})
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"Error getting PDF text layer {page_num} for {path}: {tb_str}")
        raise HTTPException(status_code=500, detail=str(e))


@files_router.get("/pdf_raw")
@jwt_token("")
async def api_pdf_raw(request: Request):
    """Serve raw PDF file for PDF.js viewer"""
    try:
        path = request.query_params.get("path")
        if not path:
            raise HTTPException(status_code=400, detail="Path parameter is required")
            
        raw_pdf = await get_raw_pdf(path)
        return raw_pdf
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"Error serving raw PDF {path}: {tb_str}")
        raise HTTPException(status_code=500, detail=str(e))


@files_router.post("/docx_info")
@jwt_token("")
async def api_docx_info(request: Request):
    """Get Word document metadata and page count (approximate)"""
    try:
        data = await request.form()
        path = data.get("path")
        info = await get_docx_info(path)
        return JSONResponse(content={"detail": info})
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"Error getting DOCX info for {path}: {tb_str}")
        raise HTTPException(status_code=500, detail=str(e))


@files_router.post("/docx_page")
@jwt_token("")
async def api_docx_page(request: Request):
    """Get a specific page (section) from a Word document as HTML"""
    try:
        data = await request.form()
        path = data.get("path")
        page_num = int(data.get("page", 1))
        page_data = await get_docx_page(path, page_num)
        return JSONResponse(content={"detail": page_data})
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"Error getting DOCX page {page_num} for {path}: {tb_str}")
        raise HTTPException(status_code=500, detail=str(e))


@files_router.post("/xlsx_info")
@jwt_token("")
async def api_xlsx_info(request: Request):
    """Get Excel file metadata and sheet names"""
    try:
        data = await request.form()
        path = data.get("path")
        info = await get_xlsx_info(path)
        return JSONResponse(content={"detail": info})
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"Error getting XLSX info for {path}: {tb_str}")
        raise HTTPException(status_code=500, detail=str(e))


@files_router.post("/xlsx_sheet")
@jwt_token("")
async def api_xlsx_sheet(request: Request):
    """Get a specific sheet from Excel as HTML table"""
    try:
        data = await request.form()
        path = data.get("path")
        sheet_name = data.get("sheet_name")
        sheet_data = await get_xlsx_sheet(path, sheet_name)
        return JSONResponse(content={"detail": sheet_data})
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"Error getting XLSX sheet {sheet_name} for {path}: {tb_str}")
        raise HTTPException(status_code=500, detail=str(e))


@files_router.post("/pptx_info")
@jwt_token("")
async def api_pptx_info(request: Request):
    """Get PowerPoint file metadata and slide count"""
    try:
        data = await request.form()
        path = data.get("path")
        info = await get_pptx_info(path)
        return JSONResponse(content={"detail": info})
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"Error getting PPTX info for {path}: {tb_str}")
        raise HTTPException(status_code=500, detail=str(e))


@files_router.post("/pptx_slide")
@jwt_token("")
async def api_pptx_slide(request: Request):
    """Get a specific slide from PowerPoint as HTML or image"""
    try:
        data = await request.form()
        path = data.get("path")
        slide_num = int(data.get("slide", 1))
        slide_data = await get_pptx_slide(path, slide_num)
        return JSONResponse(content={"detail": slide_data})
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"Error getting PPTX slide {slide_num} for {path}: {tb_str}")
        raise HTTPException(status_code=500, detail=str(e))


@files_router.post("/newly_added_files")
@jwt_token("")
async def api_newly_added_files(request: Request):
    """Get a list of newly added files since a given timestamp"""
    try:
        data = await request.form()
        timestamp = data.get("timestamp")
        
        if not timestamp:
            raise HTTPException(status_code=400, detail="timestamp field is required")
        
        # Convert timestamp to datetime object
        timestamp_dt = datetime.fromisoformat(timestamp)
        
        newly_added = await get_newly_added_files_since_timestamp(timestamp_dt)
        return JSONResponse(content={"detail": newly_added})
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"Error getting newly added files: {tb_str}")
        raise HTTPException(status_code=500, detail=str(e))


@files_router.get("/newly_added")
@jwt_token("")
async def api_newly_added_files(request: Request):
    """Get files that have been modified within the last 3 days"""
    try:
        # Get optional 'days' parameter from query params, default to 3
        days_param = request.query_params.get("days", "3")
        try:
            days = int(days_param)
            if days < 1:
                days = 3  # Default to 3 if invalid value
        except ValueError:
            days = 3  # Default to 3 if not a valid integer
        
        newly_added = await get_newly_added_files(days)
        return JSONResponse(content={"detail": newly_added})
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"Error getting newly added files: {tb_str}")
        raise HTTPException(status_code=500, detail=str(e))