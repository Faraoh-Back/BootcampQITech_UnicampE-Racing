from fastapi import Request, status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import AccountController
from utils.schema_handler import SchemaHandler
from utils.account_access import authorize_user_if_present


class AccountResource:
    @SchemaHandler.validate("post_account.json")
    def on_post(self, payload: dict) -> JSONResponse:
        account = AccountController().create(payload)
        return JSONResponse(content=jsonable_encoder(account), status_code=http_status.HTTP_201_CREATED)

    def on_get_by_key(self, account_key: str, request: Request) -> JSONResponse:
        authorize_user_if_present(request, account_key, {"OWNER", "OPERATOR", "VIEWER"})
        account = AccountController().get_by_key(account_key)
        return JSONResponse(content=jsonable_encoder(account), status_code=http_status.HTTP_200_OK)

    def on_put_block(self, account_key: str, request: Request) -> JSONResponse:
        authorize_user_if_present(request, account_key, {"OWNER"})
        account = AccountController().block(account_key)
        return JSONResponse(content=jsonable_encoder(account), status_code=http_status.HTTP_200_OK)

    def on_put_cancel(self, account_key: str, request: Request) -> JSONResponse:
        authorize_user_if_present(request, account_key, {"OWNER"})
        account = AccountController().cancel(account_key)
        return JSONResponse(content=jsonable_encoder(account), status_code=http_status.HTTP_200_OK)
