from tests.utils.auth import user_payload
from tests.utils.request_generator import RequestGenerator


def test_password_limit_is_measured_in_utf8_bytes(make_customer):
    customer = make_customer()["response"]["customer_key"]
    user = {**user_payload(customer), "password": "é" * 37}
    status, error = RequestGenerator.POST_user(user)
    assert status == 400
    assert error["code"] == "QIT000001"
    # O mesmo e-mail continua disponível: o cadastro recusado não foi salvo.
    user["password"] = "é" * 36
    assert RequestGenerator.POST_user(user)[0] == 201
    assert RequestGenerator.POST_auth_login({"email": user["email"], "password": user["password"]})[0] == 201
    status, error = RequestGenerator.POST_auth_login({"email": user["email"], "password": "é" * 37})
    assert status == 401
    assert error["code"] == "QIT001021"
