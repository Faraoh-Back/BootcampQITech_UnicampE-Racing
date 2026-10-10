from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import PricingPolicyController
from utils.schema_handler import SchemaHandler


class PricingPolicyResource:
    @SchemaHandler.validate("post_pricing_policy.json")
    def on_post(self, payload: dict) -> JSONResponse:
        policy = PricingPolicyController().create(payload)
        return JSONResponse(content=jsonable_encoder(policy), status_code=http_status.HTTP_201_CREATED)
