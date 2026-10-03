from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import BillingPlanController
from utils.schema_handler import SchemaHandler


class BillingPlanResource:
    @SchemaHandler.validate("post_billing_plan.json")
    def on_post(self, account_key: str, payload: dict) -> JSONResponse:
        billing_plan = BillingPlanController().create(account_key, payload)
        return JSONResponse(content=jsonable_encoder(billing_plan), status_code=http_status.HTTP_201_CREATED)

    def on_get_by_key(self, account_key: str, plan_key: str) -> JSONResponse:
        billing_plan = BillingPlanController().get_by_key(account_key, plan_key)
        return JSONResponse(content=jsonable_encoder(billing_plan), status_code=http_status.HTTP_200_OK)

    @SchemaHandler.validate("post_billing_plan_adjustment.json")
    def on_post_adjustment(self, account_key: str, plan_key: str, payload: dict) -> JSONResponse:
        adjustment = BillingPlanController().create_adjustment(account_key, plan_key, payload)
        return JSONResponse(content=jsonable_encoder(adjustment), status_code=http_status.HTTP_201_CREATED)
