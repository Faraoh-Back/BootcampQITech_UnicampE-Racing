from fastapi import Header, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import PolicyChangeRequestController
from utils.schema_handler import SchemaHandler


class PolicyChangeRequestResource:
    @SchemaHandler.validate("post_policy_change_request.json")
    def on_post(self, payload: dict, authorization: str | None = Header(default=None)):
        return JSONResponse(jsonable_encoder(PolicyChangeRequestController().create(payload, authorization)), status_code=status.HTTP_201_CREATED)

    def on_submit(self, request_key: str, authorization: str | None = Header(default=None)):
        return JSONResponse(jsonable_encoder(PolicyChangeRequestController().submit(request_key, authorization)))

    def on_approve(self, request_key: str, authorization: str | None = Header(default=None)):
        return JSONResponse(jsonable_encoder(PolicyChangeRequestController().approve(request_key, authorization)))
