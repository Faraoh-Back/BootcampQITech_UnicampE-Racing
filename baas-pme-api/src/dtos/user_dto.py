from models import User


class UserDTO:
    @staticmethod
    def obj_to_created_dict(user: User, customer_key: str, role: str) -> dict:
        return {
            "user_key": user.user_key,
            "customer_key": customer_key,
            "role": role,
            "created_at": user.created_at.isoformat(),
        }
