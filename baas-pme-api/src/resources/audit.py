from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers.audit_controller import AuditController


class AuditResource:
    def on_get(self) -> JSONResponse:
        events = AuditController().get_all()
        return JSONResponse(content=jsonable_encoder(events), status_code=http_status.HTTP_200_OK)

    def on_get_checkpoint(self) -> JSONResponse:
        checkpoint = AuditController().get_checkpoint()
        return JSONResponse(content=jsonable_encoder(checkpoint), status_code=http_status.HTTP_200_OK)
