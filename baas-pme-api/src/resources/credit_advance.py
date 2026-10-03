from fastapi import Request, status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import CreditAdvanceController
from errors import InvalidSchema, MissingIdempotencyKey
from utils.schema_handler import SchemaHandler


class CreditAdvanceResource:
    @SchemaHandler.validate("post_credit_advance.json")
    def on_post(self, account_key: str, payload: dict, request: Request) -> JSONResponse:
        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            raise MissingIdempotencyKey()
        if len(idempotency_key) > 64:
            raise InvalidSchema("Idempotency-Key must contain at most 64 characters.")

        credit_advance, replayed = CreditAdvanceController().create(
            account_key, payload, idempotency_key
        )
        response = JSONResponse(content=jsonable_encoder(credit_advance), status_code=http_status.HTTP_201_CREATED)
        if replayed:
            response.headers["Idempotent-Replayed"] = "true"
        return response
