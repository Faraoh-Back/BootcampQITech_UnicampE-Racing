from fastapi import Request, status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response

from controllers import AuthController
from utils.schema_handler import SchemaHandler


class AuthResource:
    @SchemaHandler.validate("post_user.json")
    def on_post_user(self, payload: dict) -> JSONResponse:
        user = AuthController().register(payload)
        return JSONResponse(content=jsonable_encoder(user), status_code=http_status.HTTP_201_CREATED)

    @SchemaHandler.validate("post_auth_login.json")
    def on_post_login(self, payload: dict) -> JSONResponse:
        tokens = AuthController().login(payload)
        return JSONResponse(content=jsonable_encoder(tokens), status_code=http_status.HTTP_201_CREATED)

    @SchemaHandler.validate("post_auth_refresh.json")
    def on_post_refresh(self, payload: dict) -> JSONResponse:
        tokens = AuthController().refresh(payload["refresh_token"])
        return JSONResponse(content=jsonable_encoder(tokens), status_code=http_status.HTTP_201_CREATED)

    def on_post_logout(self, request: Request) -> Response:
        AuthController().logout(request.headers.get("Authorization"))
        return Response(status_code=http_status.HTTP_204_NO_CONTENT)
