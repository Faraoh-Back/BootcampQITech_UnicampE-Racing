from models import Customer


class CustomerDTO:
    @staticmethod
    def only_obj_key(customer: Customer) -> dict:
        return {"customer_key": customer.customer_key}

    @staticmethod
    def obj_to_dict(customer: Customer) -> dict:
        return {
            "customer_key": customer.customer_key,
            "name": customer.name,
            "email": customer.email,
            "document_number": customer.document_number,
            "created_at": customer.created_at.isoformat(),
        }
