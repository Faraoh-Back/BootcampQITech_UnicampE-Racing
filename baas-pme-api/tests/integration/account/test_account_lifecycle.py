from uuid import uuid4

from tests.utils.requisition import ClientRequisition
from tests.utils.request_generator import RequestGenerator


class TestAccountLifecycle:
    def test_blocks_approved_account_and_appends_immutable_event(self, make_account):
        account_key = make_account()["response"]["account_key"]

        status, blocked = RequestGenerator.PUT_account_block(account_key)

        assert status == 200
        assert set(blocked) == {"account_key", "status", "updated_at"}
        assert blocked["account_key"] == account_key
        assert blocked["status"] == "BLOCKED"

        status, account = RequestGenerator.GET_account(account_key)
        assert status == 200
        assert account["status"] == "BLOCKED"
        assert [event["status"] for event in account["status_events"]] == [
            "PENDING", "APPROVED", "BLOCKED"
        ]

        status, error = RequestGenerator.PUT_account_block(account_key)
        assert status == 409
        assert error["code"] == "QIT001019"

    def test_cancels_from_approved_or_blocked_and_never_leaves_cancelled(self, make_account):
        approved_account_key = make_account()["response"]["account_key"]
        blocked_account_key = make_account()["response"]["account_key"]

        status, cancelled = RequestGenerator.PUT_account_cancel(approved_account_key)
        assert status == 200
        assert cancelled["status"] == "CANCELLED"

        status, _ = RequestGenerator.PUT_account_block(blocked_account_key)
        assert status == 200
        status, cancelled = RequestGenerator.PUT_account_cancel(blocked_account_key)
        assert status == 200
        assert cancelled["status"] == "CANCELLED"

        status, account = RequestGenerator.GET_account(blocked_account_key)
        assert status == 200
        assert [event["status"] for event in account["status_events"]] == [
            "PENDING", "APPROVED", "BLOCKED", "CANCELLED"
        ]

        status, error = RequestGenerator.PUT_account_cancel(blocked_account_key)
        assert status == 409
        assert error["code"] == "QIT001019"

        status, error = RequestGenerator.PUT_account_block(blocked_account_key)
        assert status == 409
        assert error["code"] == "QIT001019"

    def test_returns_not_found_and_requires_internal_token(self):
        missing_account_key = str(uuid4())

        status, error = RequestGenerator.PUT_account_block(missing_account_key)
        assert status == 404
        assert error["code"] == "QIT001002"

        status, error = RequestGenerator.PUT_account_cancel(missing_account_key)
        assert status == 404
        assert error["code"] == "QIT001002"

        response = ClientRequisition.send("PUT", f"/account/{missing_account_key}/block")
        assert response.response_status == 403
        assert response.response_json["code"] == "QIT000002"

        response = ClientRequisition.send("PUT", f"/account/{missing_account_key}/cancel")
        assert response.response_status == 403
        assert response.response_json["code"] == "QIT000002"
