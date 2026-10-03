from fastapi import Request, status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import TransactionController
from errors import MissingIdempotencyKey
from utils.schema_handler import SchemaHandler


class TransactionResource:
    @SchemaHandler.validate("post_transaction.json")
    def on_post(self, account_key: str, payload: dict, request: Request) -> JSONResponse:
        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            raise MissingIdempotencyKey()

        execution = TransactionController().create(account_key, payload, idempotency_key)
        response = JSONResponse(
            content=jsonable_encoder(execution.body),
            status_code=http_status.HTTP_201_CREATED,
        )
        if execution.replayed:
            response.headers["Idempotent-Replayed"] = "true"
        return response
