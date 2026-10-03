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

    def on_get_by_key(self, account_key: str, transaction_key: str) -> JSONResponse:
        transaction = TransactionController().get_by_key(account_key, transaction_key)
        return JSONResponse(content=jsonable_encoder(transaction), status_code=http_status.HTTP_200_OK)

    @SchemaHandler.validate_query_params("get_transactions.json")
    def on_get_list(self, account_key: str, request: Request) -> JSONResponse:
        query_params = {key: request.query_params[key] for key in request.query_params.keys()}
        transactions = TransactionController().get_list(account_key, query_params)
        return JSONResponse(content=jsonable_encoder(transactions), status_code=http_status.HTTP_200_OK)
