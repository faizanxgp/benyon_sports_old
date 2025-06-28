import jwt
import json
import time
import httpx

from functools import wraps
from decouple import Config, RepositoryEnv
from fastapi import HTTPException, Request, WebSocket
from keycloak import KeycloakOpenID
from jwcrypto.jwt import JWTExpired
from jwcrypto.jws import InvalidJWSObject, InvalidJWSSignature
from datetime import datetime

from routers.utils.keycloak_vars import *


async def get_resources_in_permission(permission_id: str, access_token=None):
    headers, _ = await obtain_headers()
    async with httpx.AsyncClient() as client:
        response = await client.get(
            base_url + ep_resources_in_permission.replace("[ENTER_PERMISSION_ID]", permission_id), 
            headers=headers
            )

    return response


async def create_permission(payload: dict, access_token=None):
    headers, _ = await obtain_headers()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            base_url + ep_create_permission, 
            json=payload, headers=headers
            )

    return response


async def update_permission(permission_id: str, payload: dict, access_token=None):
    headers, _ = await obtain_headers()
    async with httpx.AsyncClient() as client:
        response = await client.put(
            base_url + ep_update_permission.replace("[ENTER_PERMISSION_ID]", permission_id), 
            json=payload, headers=headers
            )

    return response


async def get_all_permissions(access_token=None):
    headers, _ = await obtain_headers()
    async with httpx.AsyncClient() as client:
        response = await client.get(
            base_url + ep_get_all_permissions, 
            headers=headers
            )

    return response


async def obtain_access_token():
    access_token_payload = {
        "grant_type":"client_credentials",
        "client_id":backend_client_name,
        "scope":"openid",
        "client_secret":backend_client_secret
    }
    token_url = base_url + ep_access_token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(token_url, data=access_token_payload)
        token_response.raise_for_status()  # Optional: raises exception for HTTP 4xx/5xx
        
    access_token = token_response.json()["access_token"]
    return access_token


async def obtain_headers(access_token=None):
    if not access_token: access_token = await obtain_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    return headers, access_token


async def check_user_active(user_id, access_token=None):
    headers, _ = await obtain_headers(access_token)
    async with httpx.AsyncClient() as client:
        response = await client.get(
            base_url + ep_check_user_active.replace("[ENTER_USER_ID]", user_id), 
            headers=headers
            )

    return response


async def get_all_users(access_token=None):
    headers, _ = await obtain_headers(access_token)
    async with httpx.AsyncClient() as client:
        response = await client.get(
            base_url + ep_get_all_users, 
            headers=headers
            )

    return response


async def get_client_role(role: str, access_token=None): # get complete details against a given role name
    try:
        headers, _ = await obtain_headers(access_token)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                base_url + ep_get_client_role.replace("[ENTER_ROLE]", role), 
                headers=headers
                )

        return response
    except Exception as e:
        raise e from e


async def get_user_role_details(user_id, access_token=None):
    try:
        headers, _ = await obtain_headers(access_token)
        async with httpx.AsyncClient() as client:
            response = await client.get(base_url + ep_get_user_roles.replace("[ENTER_USER_ID]", user_id), headers=headers)
        if response.status_code not in [200, 201, 204]:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response
    except Exception as e:
        raise e from e


async def create_user_policy(payload, access_token=None):
    headers, _ = await obtain_headers(access_token)
    async with httpx.AsyncClient() as client:
        response = await client.post(base_url + ep_create_user_policy, json=payload, headers=headers)

    return response


async def retrieve_user_policy(username, access_token=None):
    headers, _ = await obtain_headers(access_token)
    async with httpx.AsyncClient() as client:
        response = await client.get(base_url + ep_retrieve_policy, headers=headers)

    policy = None
    details = response.json()
    for detail in details:
        if detail["name"] == f"policy_user_{username}":
            policy = detail
            break
    return policy


async def delete_user_policy(policy_id, access_token=None):
    headers, _ = await obtain_headers(access_token)
    async with httpx.AsyncClient() as client:
        response = await client.delete(base_url + ep_delete_user_policy + policy_id, headers=headers)

    return response


async def create_resource(payload, access_token=None):
    headers, _ = await obtain_headers(access_token)
    async with httpx.AsyncClient() as client:
        response = await client.post(base_url + ep_create_resource_url, json=payload, headers=headers)

    return response


async def retrieve_resource(resource_name, access_token=None):
    headers, _ = await obtain_headers(access_token)
    query_params = {
    "name": resource_name,
    "exact": True
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(base_url + ep_retrieve_resource, params=query_params, headers=headers)

    resource_id = response.json()
    return resource_id[0] if resource_id else None


async def get_all_resources(access_token=None):
    try:
        headers, _ = await obtain_headers(access_token)
        async with httpx.AsyncClient() as client:
            response = await client.get(base_url + ep_get_all_resources, headers=headers)

        resource_details = response.json()
        resources_summary = {}
        for resource in resource_details:
            resources_summary[resource.get("name")] = resource.get("_id")
        return resources_summary
    except Exception as e:
        raise e from e


async def delete_resource(resource_id, access_token=None):
    headers, _ = await obtain_headers(access_token)
    async with httpx.AsyncClient() as client:
        response = await client.delete(base_url + ep_delete_resource + resource_id, headers=headers)

    return response


async def get_events(user_id=None, event_type=None, access_token=None):
    """
    Retrieve events from Keycloak with optional filtering by user_id and event_type.
    
    Args:
        user_id (str, optional): Filter events by user ID
        event_type (str, optional): Filter events by event type (e.g., "LOGIN")
        access_token (str, optional): Access token for authentication
        
    Returns:
        httpx.Response: Response containing the events data
    """
    try:
        headers, _ = await obtain_headers(access_token)
        
        # Build query parameters
        params = {}
        if user_id:
            params["user"] = user_id  # Changed from "userId" to "user"
        if event_type:
            params["type"] = event_type
            
        async with httpx.AsyncClient() as client:
            response = await client.get(
                base_url + ep_events, 
                params=params, 
                headers=headers
            )

        return response
    except Exception as e:
        raise e from e
