REM Run the Keycloak container with the volume mounted
docker run -d ^
  --name keycloak ^
  -p 8080:8080 ^
  -e KEYCLOAK_ADMIN=admin ^
  -e KEYCLOAK_ADMIN_PASSWORD=admin ^
  -v keycloak_data:/opt/keycloak/data ^
  quay.io/keycloak/keycloak:26.2.5 ^
  start-dev