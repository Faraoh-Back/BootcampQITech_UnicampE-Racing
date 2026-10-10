from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import QuoteController
from utils.schema_handler import SchemaHandler


class QuoteResource:
    @SchemaHandler.validate("post_quote.json")
    def on_post(self, account_key: str, payload: dict) -> JSONResponse:
        quote = QuoteController().create(account_key, payload)
        return JSONResponse(content=jsonable_encoder(quote), status_code=http_status.HTTP_201_CREATED)
