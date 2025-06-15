import jwt
import json
import time

from functools import wraps
from decouple import Config, RepositoryEnv
from fastapi import HTTPException, Request, WebSocket
from keycloak import KeycloakOpenID
from jwcrypto.jwt import JWTExpired
from jwcrypto.jws import InvalidJWSObject, InvalidJWSSignature
from datetime import datetime

KEYCLOAK_URL = 'http://localhost:8080'
KEYCLOAK_REALM_NAME = 'team_online'
KEYCLOAK_BACKEND_CLIENT_ID = "benyon_be"
KEYCLOAK_BACKEND_CLIENT_SECRET = "YTAI2YEwh3B81zSVlUmLPPJppOtF96VL"


async def keycloak_verif(token:str):
    keycloak_openid = KeycloakOpenID(server_url=KEYCLOAK_URL,
                                    client_id=KEYCLOAK_BACKEND_CLIENT_ID,
                                    realm_name=KEYCLOAK_REALM_NAME,
                                    client_secret_key=KEYCLOAK_BACKEND_CLIENT_SECRET
                                    )

    dec_tok = await keycloak_openid.a_decode_token(token, validate=True)
    intr_tok = await keycloak_openid.a_introspect(token)
    if intr_tok.get("active"): 
        if time.time()>intr_tok.get('exp'): raise Exception("auth token expired")
    else:
        raise Exception("inactive auth token")
    
    auth_status = keycloak_openid.uma_permissions(token)
    permissions = [permissions_dict[i] for permissions_dict in auth_status for i in permissions_dict if i=="rsname"]
    
    return intr_tok, permissions


def jwt_token(required_permission: str):
    def decorator(fn):
        @wraps(fn)
        async def decorated(request: Request, *args, **kwargs):

            headers = request.headers

            try:
                if "Authorization" in headers:
                    token_from_request = headers.get('Authorization').split(" ")[1]
                else:
                    raise HTTPException(status_code = 401, detail = "An error occurred: missing authorization token")
            except:
                raise HTTPException(status_code = 401, detail = "An error occurred: missing authorization token")
        
            try:
                intr_tok, permissions = await keycloak_verif(token_from_request)                
                if required_permission:
                    if (required_permission not in permissions) and ("api_all_endpoints" not in permissions):
                        print("required permission:", required_permission)
                        print("permissions:", permissions)
                        raise Exception("auth token: insufficient permission(s)")
                else:
                    request.state.permissions = permissions
            
                user_id, user_name, user_email = intr_tok.get("sub"), intr_tok.get("name"), intr_tok.get("email")

                request.state.user_id = user_id
                request.state.username = user_name
                request.state.email = user_email

            except Exception as e:
                print(f"\n{datetime.now()} jwt_token. error: type: {type(e)}, details: {str(e)}\n")
                if isinstance(e, (InvalidJWSObject, InvalidJWSSignature)):
                    raise HTTPException(status_code = 401, detail = "error: invalid auth token")
                elif isinstance(e, (JWTExpired)):
                    raise HTTPException(status_code = 401, detail = "error: auth token expired")
                elif isinstance(e, (Exception)):
                    raise HTTPException(status_code = 401, detail = str(e))
                else:
                    raise e

            return await fn(request)

        return decorated
    return decorator