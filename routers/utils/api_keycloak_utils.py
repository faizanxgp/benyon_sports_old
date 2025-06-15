from fastapi import HTTPException

from routers.utils.misc_keycloak_utils import *
from routers.utils.keycloak_vars import *


async def delete_permission(username: str, access_token=None):
    try:
        headers, _ = await obtain_headers()

        permission_name = f"permission_user_{username}"
        all_permissions = (await get_all_permissions()).json()
        relevant_permission = None
        for permission in all_permissions:
            if permission.get("name") == permission_name:
                relevant_permission = permission
                break
        if not relevant_permission: raise Exception("no existing permission found for this user")
        permission_id = relevant_permission.get("id")

        async with httpx.AsyncClient() as client:
            response = await client.delete(
                base_url + ep_delete_permission.replace("[ENTER_PERMISSION_ID]", permission_id), 
                headers=headers
                )
        if response.status_code in [200, 201, 204]:
            return {"detail": "permission deleted"}
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    except Exception as e:
        raise e from e

async def unassign_permission(resource_names: str, username: str, access_token=None):
    try:
        rem_resource_ids = []
        rem_resource_dict = {} # to store resource name against each resource id
        for name in resource_names:
            resource_id = await retrieve_resource(name)
            if not resource_id: raise Exception(f"resource_id not found against the resource: {name}")
            rem_resource_ids.append(resource_id)
            rem_resource_dict[resource_id] = name
        print("rem_resource_ids:", rem_resource_ids)

        policy_id = (await retrieve_user_policy(username)).get("id")
        if not policy_id: raise Exception("policy_id not found against the given username")
        
        permission_name = f"permission_user_{username}"
        all_permissions = (await get_all_permissions()).json()
        relevant_permission = None
        for permission in all_permissions:
            if permission.get("name") == permission_name:
                relevant_permission = permission
                break
 
        if relevant_permission:
            permission_id = relevant_permission.get("id")
            resource_ids = []
            resources_in_permission = (await get_resources_in_permission(permission_id)).json()
            resource_ids = [resource.get("_id") for resource in resources_in_permission]
            print("resource_ids:", resource_ids)
            
            # check if all resources to be unassigned were earlier assigned or not?
            non_existent_permissions = []
            for rem_id in rem_resource_ids:
                if rem_id not in resource_ids: non_existent_permissions.append(rem_resource_dict[rem_id])
            
            updated_resource_ids = resource_ids.copy()
            for id in resource_ids:
                if id in rem_resource_ids: updated_resource_ids.remove(id)
            print("updated resource_ids:", updated_resource_ids)
            update_payload = (
                {
                    "id":permission_id,
                    "name":permission_name,
                    "description":"",
                    "type":"resource",
                    "logic":"POSITIVE",
                    "decisionStrategy":"UNANIMOUS",
                    "resources":updated_resource_ids,
                    "policies":[policy_id],
                    "scopes":[]
                }
            )
            response = await update_permission(permission_id, update_payload)
            if response.status_code in [200, 201, 204]:
                return_string = "permissions unassigned"
                if len(non_existent_permissions): return_string += f" (if existing). Following permissions did not exist: {non_existent_permissions}"
                return {"detail": return_string}
        else:
            return {"detail": "no existing permission found for this user"}

        return response

    except Exception as e:
        raise e from e
    

async def assign_permission(resource_names: str, username: str, access_token=None):
    try:
        new_resource_ids = []
        for resource in resource_names:
            resource_id = await retrieve_resource(resource)
            if not resource_id: raise Exception(f"resource_id not found against the resource: {resource}")
            new_resource_ids.append(resource_id)

        policy_id = (await retrieve_user_policy(username)).get("id")
        if not policy_id: raise Exception("policy_id not found against the given username")
        
        permission_name = f"permission_user_{username}"
        all_permissions = (await get_all_permissions()).json()
        relevant_permission = None
        for permission in all_permissions:
            if permission.get("name") == permission_name:
                relevant_permission = permission
                break

        if relevant_permission:
            permission_id = relevant_permission.get("id")
            resource_ids = []
            resources_in_permission = (await get_resources_in_permission(permission_id)).json()
            resource_ids = [resource.get("_id") for resource in resources_in_permission]
            resource_ids.extend(new_resource_ids)
            update_payload = (
                {
                    "id":permission_id,
                    "name":permission_name,
                    "description":"",
                    "type":"resource",
                    "logic":"POSITIVE",
                    "decisionStrategy":"UNANIMOUS",
                    "resources":resource_ids,
                    "policies":[policy_id],
                    "scopes":[]
                }
            )
            response = await update_permission(permission_id, update_payload)
        else:
            create_payload = (
                {
                    "resources":new_resource_ids,
                    "policies":[policy_id],
                    "name":permission_name,
                    "description":"",
                    "decisionStrategy":"UNANIMOUS"
                }
            )
            response = await create_permission(create_payload)

        return response

    except Exception as e:
        raise e from e


async def create_user(payload, access_token=None):
    try:
        headers, _ = await obtain_headers(access_token)
        if role := payload.get("role"):
            del payload["role"]
        async with httpx.AsyncClient() as client:
            response = await client.post(base_url + ep_create_user, json=payload, headers=headers)
        
        if response.status_code not in [200, 201, 204]:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        
        if not role: return response
        
        username = payload.get("username")
        user_id = (await retrieve_user_details(username)).json()[0].get("id")
        role_id = (await get_client_role(role)).json().get("id")
        role_payload = [{
            "id": role_id,
            "name": role
            }]
        role_response = await assign_client_role(role_payload, user_id)
        policy_payload = (
            {
                "name":f"policy_user_{payload.get('username')}",
                "description":"",
                "users":[(await retrieve_user_details(username)).json()[0].get("id")],
                "logic":"POSITIVE"
            }
        )
        await create_user_policy(policy_payload)
        return role_response
    except Exception as e:
        raise e from e


async def assign_client_role(payload, user_id: str, access_token=None):
    try:
        headers, _ = await obtain_headers()
        async with httpx.AsyncClient() as client:
            response = await client.post(
                base_url + ep_assign_client_role.replace("[ENTER_USER_ID]", user_id), 
                json=payload, headers=headers
                )

        return response
    except Exception as e:
        raise e from e


async def remove_client_role(payload, user_id: str, access_token=None):
    headers, _ = await obtain_headers()
    async with httpx.AsyncClient() as client:
        response = await client.request("DELETE",
            base_url + ep_assign_client_role.replace("[ENTER_USER_ID]", user_id), 
            json=payload, headers=headers
            )

    return response


async def get_user_roles(user_id: str, access_token=None):
    try:
        headers, _ = await obtain_headers()
        roles = (await get_user_role_details(user_id)).json()
        role_names = [role.get("name") for role in roles]
        print("role_names:", role_names)
        return role_names
    except Exception as e:
        raise e from e


async def retrieve_user_details(username, access_token=None):
    try:
        headers, _ = await obtain_headers(access_token)
        query_params = {
        "username": username,
        "exact": True
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(base_url + ep_retrieve_user, params=query_params, headers=headers)
        return response
    except Exception as e:
        raise e from e


async def reset_password(payload, user_id, access_token=None):
    headers, _ = await obtain_headers(access_token)
    async with httpx.AsyncClient() as client:
        response = await client.put(
            base_url + ep_reset_password.replace("[ENTER_USER_ID]", user_id), 
            json=payload, headers=headers
            )

    return response


async def forgot_password(user_id, access_token=None):
    headers, _ = await obtain_headers(access_token)
    payload = ["UPDATE_PASSWORD"]
    async with httpx.AsyncClient() as client:
        response = await client.put(
            base_url + ep_forgot_password.replace("[ENTER_USER_ID]", user_id), 
            json=payload, headers=headers
            )

    return response


async def update_user_details(payload, user_id, access_token=None):
    headers, _ = await obtain_headers(access_token)
    async with httpx.AsyncClient() as client:
        response = await client.put(
            base_url + ep_update_user_details.replace("[ENTER_USER_ID]", user_id), 
            json=payload, headers=headers
            )

    return response


async def logout_user(user_id, access_token=None):
    headers, _ = await obtain_headers(access_token)
    async with httpx.AsyncClient() as client:
        response = await client.post(
            base_url + ep_logout_user.replace("[ENTER_USER_ID]", user_id), 
            headers=headers
            )

    return response


async def users_status(access_token=None):
    all_users = (await get_all_users()).json()
    print("all_users:", all_users)
    user_ids = [user.get("id") for user in all_users]
    usernames = [user.get("firstName") + " " + user.get("lastName") for user in all_users]
    emails = [user.get("email") for user in all_users]
    
    details = {}
    for i, id in enumerate(user_ids):
        active_sessions = (await check_user_active(id)).json()
        status = "active" if (len(active_sessions)>0) else "inactive"
        user_roles = await get_user_roles(id)
        role_name = user_roles[0] if user_roles else ""
        details[usernames[i]] = [emails[i], role_name, status]
    
    return details ##