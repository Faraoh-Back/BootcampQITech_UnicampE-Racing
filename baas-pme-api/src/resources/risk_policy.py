from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import RiskPolicyController
from utils.schema_handler import SchemaHandler


class RiskPolicyResource:
    @SchemaHandler.validate("post_risk_policy.json")
    def on_post(self, payload: dict) -> JSONResponse:
        policy = RiskPolicyController().create(payload)
        return JSONResponse(content=jsonable_encoder(policy), status_code=http_status.HTTP_201_CREATED)
