# TODO:
# handle the case when user enters the absolute path - how to identify and prevent it from executing?

import os
# Set the working directory to the directory where this script is located
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, Form, UploadFile, File, Request
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

from decorators.jwt import jwt_token

app = FastAPI()

@app.get("/")
def get_items():
    return "root_endpoint"


@app.post("/download")
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
    
    
@app.post("/delete")
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
    
    
@app.post("/create_dir")
@jwt_token("api_endpoint_create")
async def create_dir(path: str = Form(...)):
    try:
        base_dir = os.getcwd()  # Get the current working directory
        relative_path = path.lstrip("/\\")
        abs_path = os.path.normpath(os.path.join(base_dir, relative_path))
        os.makedirs(abs_path, exist_ok=False)
        return JSONResponse(content={"detail": f"directory created: {relative_path}"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload") # TODO: what if duplicate filenames?
@jwt_token("api_endpoint_upload")
async def upload_files(request: Request):
    try:
        data = await request.form()
        files, path = data.getlist("file"), data.get("path")
        print(files)
        base_dir = os.getcwd()
        relative_path = path.lstrip("/\\")
        abs_path = os.path.normpath(os.path.join(base_dir, relative_path))
        uploaded_files = []
        for file in files:
            file_path = os.path.join(abs_path, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            uploaded_files.append(file.filename)

        return JSONResponse(content={"detail": uploaded_files})
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/dir_contents")
def dir_contents(path: str = Form(...)):
    try:
        base_dir = os.getcwd()
        relative_path = path.lstrip("/\\")
        abs_path = os.path.normpath(os.path.join(base_dir, relative_path))
        print(f"Absolute path: {abs_path}")
        contents = os.listdir(abs_path)
        return {"detail": contents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/file_preview")
def file_preview(request: Request):
    path = request.form()
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




if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
