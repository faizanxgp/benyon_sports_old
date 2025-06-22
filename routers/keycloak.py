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
from routers.utils.api_keycloak_utils import *

keycloak_router = APIRouter()


@keycloak_router.delete("/delete_permission")
@jwt_token("all_endpoints")
async def api_delete_permission(request: Request):
    try:
        username = request.state.email
        response = await delete_permission(username)
        
        return response
    
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"delete_permission. error: {tb_str}")
        
        if isinstance (e, HTTPException):
            raise e
        else:
            raise HTTPException(status_code=500, detail=str(e))
        

@keycloak_router.post("/unassign_permission")
@jwt_token("all_endpoints")
async def api_unassign_permission(request: Request):
    try:
        payload = await request.json()
        resource_names, username = payload.get("resource_names"), payload.get("username")
        response = await unassign_permission(resource_names, username)
        
        return response
    
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"unassign_permission. error: {tb_str}")
        
        if isinstance (e, HTTPException):
            raise e
        else:
            raise HTTPException(status_code=500, detail=str(e))


@keycloak_router.post("/assign_permission")
@jwt_token("all_endpoints")
async def api_assign_permission(request: Request):
    try:
        payload = await request.json()
        resource_names, username = payload.get("resource_names"), payload.get("username")
        response = await assign_permission(resource_names, username)
        
        if response.status_code in [200, 201, 204]:
            return {"detail": "permission assigned successfully"}
        
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"assign_permission. error: {tb_str}")
        
        if isinstance (e, HTTPException):
            raise e
        else:
            raise HTTPException(status_code=500, detail=str(e))
        

@keycloak_router.post("/create_user")
@jwt_token("all_endpoints")
async def api_create_user(request: Request):
    try:
        payload = await request.json()
        response = await create_user(payload)
        
        if response.status_code in [200, 201, 204]:
            return {"detail": "user created successfully"}
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"create_user. error: {tb_str}")
        
        if isinstance (e, HTTPException):
            raise e
        else:
            raise HTTPException(status_code=500, detail=str(e))
        

@keycloak_router.delete("/delete_user")
@jwt_token("all_endpoints")
async def api_create_user(request: Request):
    try:
        data = await request.json()
        username = data.get("username")
        response = await delete_user(username)
        return {"detail": response}         
    
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"delete_user. error: {tb_str}")
        
        if isinstance (e, HTTPException):
            raise e
        else:
            raise HTTPException(status_code=500, detail=str(e))
        
        
@keycloak_router.post("/assign_role")
@jwt_token("")
async def api_assign_role(request: Request):
    try:
        data = await request.json()
        username, role = data.get("username"), data.get("role")
        user_details = (await retrieve_user_details(username)).json()
        if not user_details: return HTTPException(status_code=404, detail="user not found")
        user_id = user_details[0].get("id")
        role_id = (await get_client_role(role)).json().get("id")
        payload = [{
            "id": role_id,
            "name": role
            }]
        response = await assign_client_role(payload, user_id)
        
        if response.status_code in [200, 201, 204]:
            return {"detail": "role assigned successfully"}
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"assign_role. error: {tb_str}")
        
        if isinstance (e, HTTPException):
            raise e
        else:
            raise HTTPException(status_code=500, detail=str(e))


@keycloak_router.get("/get_user_roles")
@jwt_token("")
async def api_get_user_roles(request: Request):
    try:
        user_id = request.state.user_id
        role_names = await get_user_roles(user_id)
        return {"detail": role_names}
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"get_user_roles. error: {tb_str}")
        
        if isinstance (e, HTTPException):
            raise e
        else:
            raise HTTPException(status_code=500, detail=str(e))
        

@keycloak_router.delete("/remove_role")
@jwt_token("")
async def api_remove_role(request: Request):
    try:
        data = await request.json()
        username, role = data.get("username"), data.get("role")
        user_details = (await retrieve_user_details(username)).json()
        if not user_details: return HTTPException(status_code=404, detail="user not found")
        user_id = user_details[0].get("id")
        role_id = (await get_client_role(role)).json().get("id")
        payload = [{
            "id": role_id,
            "name": role
            }]
        response = await remove_client_role(payload, user_id)
        
        if response.status_code in [200, 201, 204]:
            return {"detail": "role removed successfully"}
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"remove_role. error: {tb_str}")
        
        if isinstance (e, HTTPException):
            raise e
        else:
            raise HTTPException(status_code=500, detail=str(e))
        

@keycloak_router.post("/retrieve_user_details")
async def api_retrieve_user_details(request: Request):
    try:
        data = await request.json()
        username = data.get("username")
        response:httpx.Response = await retrieve_user_details(username)
        
        if response.status_code in [200, 201, 204]:
            if response.json():
                return {"detail": response.json()[0]}
            else: 
                raise HTTPException(status_code=404, detail="no record found")
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"retrieve_user_details. error: {tb_str}")
        
        if isinstance (e, HTTPException):
            raise e
        else:
            raise HTTPException(status_code=500, detail=str(e))


# TODO: this approach needs to be changed - not secure
@keycloak_router.post("/reset_password")
@jwt_token("")
async def api_reset_password(request: Request):
    try:
        user_id = request.state.user_id # action carried out by concerned user (non-admin)
        payload = await request.json()
        response:httpx.Response = await reset_password(payload, user_id)
        
        if response.status_code in [200, 201, 204]:
            return {"detail": "password reset successfully"}
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"reset_password. error: {tb_str}")
        
        if isinstance (e, HTTPException):
            raise e
        else:
            raise HTTPException(status_code=500, detail=str(e))
        

@keycloak_router.post("/forgot_password")
@jwt_token("")
async def api_forgot_password(request: Request):
    try:
        user_id = request.state.user_id # action carried out by concerned user (non-admin)
        response:httpx.Response = await forgot_password(user_id)
        if response.status_code in [200, 201, 204]:
            return {"detail": "password reset link sent"}
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"forgot_password. error: {tb_str}")
        
        if isinstance (e, HTTPException):
            raise e
        else:
            raise HTTPException(status_code=500, detail=str(e))
        

# This action will carried out by concerned user (non-admin)
@keycloak_router.post("/update_user_details")
@jwt_token("")
async def api_update_user_details(request: Request):
    try:
        user_id = request.state.user_id
        payload = await request.json()
        response:httpx.Response = await update_user_details(payload, user_id)
        
        if response.status_code in [200, 201, 204]:
            return {"detail": "user details updated successfully"}
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"update_user_details. error: {tb_str}")
        
        if isinstance (e, HTTPException):
            raise e
        else:
            raise HTTPException(status_code=500, detail=str(e))
        

# This action will carried out by concerned user (non-admin)
@keycloak_router.get("/logout_user")
@jwt_token("")
async def api_logout_user(request: Request):
    try:
        user_id = request.state.user_id 
        response:httpx.Response = await logout_user(user_id)
        
        if response.status_code in [200, 201, 204]:
            return {"detail": "user logged out successfully"}
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"logout_user. error: {tb_str}")
        
        if isinstance (e, HTTPException):
            raise e
        else:
            raise HTTPException(status_code=500, detail=str(e))


@keycloak_router.get("/users_status")
@jwt_token("all_endpoints")
async def api_users_status(request: Request):
    try:
        details = await users_status()
        return {"detail": details}
    
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"logout_user. error: {tb_str}")
        
        if isinstance (e, HTTPException):
            raise e
        else:
            raise HTTPException(status_code=500, detail=str(e))