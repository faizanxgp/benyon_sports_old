# TODO:
# handle the case when user enters the absolute path - how to identify and prevent it from executing?

import os
# Set the working directory to the directory where this script is located
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# import sys
# import ctypes
# from ctypes import wintypes
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.files import files_router
from routers.keycloak import keycloak_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(files_router, prefix="/files", tags=["files"])
app.include_router(keycloak_router, prefix="/keycloak", tags=["keycloak"])

@app.get("/")
def get_items():
    return "root_endpoint"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=5000, reload=True)
