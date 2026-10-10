from fastapi import Request, status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import QuoteController
from utils.schema_handler import SchemaHandler
from utils.account_access import authorize_user_if_present


class QuoteResource:
    @SchemaHandler.validate("post_quote.json")
    def on_post(self, account_key: str, payload: dict, request: Request) -> JSONResponse:
        authorize_user_if_present(request, account_key, {"OWNER", "OPERATOR", "VIEWER"})
        quote = QuoteController().create(account_key, payload)
        return JSONResponse(content=jsonable_encoder(quote), status_code=http_status.HTTP_201_CREATED)
