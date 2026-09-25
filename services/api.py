import logging
from typing import Optional

import requests

from config import API_URL, BACKEND_API_KEY

logger = logging.getLogger(__name__)

# one connection pool for all calls + a timeout: without a timeout a single slow request
# blocks the whole bot for every user
_session = requests.Session()
TIMEOUT = 15


def _request(method: str, path: str, telegram_id=None, **kwargs) -> Optional[requests.Response]:
    headers = kwargs.pop("headers", {}) or {}
    if telegram_id is not None:
        headers["x-telegram-id"] = str(telegram_id)
    if BACKEND_API_KEY:
        headers["x-api-key"] = BACKEND_API_KEY
    try:
        return _session.request(method, f"{API_URL}{path}", headers=headers, timeout=TIMEOUT, **kwargs)
    except requests.RequestException:
        logger.exception("Backend request failed: %s %s", method, path)
        return None


def _json_or(response: Optional[requests.Response], default=None):
    if response is None or response.status_code != 200:
        return default
    try:
        return response.json()
    except ValueError:
        return default


def _error(response: Optional[requests.Response]) -> dict:
    detail = None
    if response is not None:
        try:
            detail = response.json().get("detail")
        except (ValueError, AttributeError):
            detail = None
    return {
        "error": True,
        "status_code": response.status_code if response is not None else None,
        "detail": detail,
    }


def verify_telegram(phone_number:str,telegram_id:int):
    response = _request("POST", "/agents/verify-telegram",
                        json={"phone_number": phone_number, "telegram_id": telegram_id})
    return _json_or(response)


def get_me(telegram_id: int):
    """Profile (id, role, names) of this Telegram user from the backend, or None."""
    return _json_or(_request("GET", "/agents/me", telegram_id))


def create_order(order,telegram_id):
    response = _request("POST", "/orders/", telegram_id, json=order)
    if response is not None and response.status_code == 200:
        return response.json()
    logger.error("❌ Order creation failed: %s", response.text if response is not None else "no response")
    return None


#getting orders
def get_new_orders(telegram_id:int):
    """List of existing orders, or None if the backend failed."""
    response = _request("GET", "/orders/", telegram_id)
    data = _json_or(response)
    if data is None:
        logger.error("❌ Order getting failed: %s", response.text if response is not None else "no response")
    return data

def calculating_new_orders_quantity():
    """{product: "qty unit"} or None."""
    return _json_or(_request("GET", "/orders/calculating-existing-orders"))

def get_order_by_id(order_id: int, telegram_id: int):
    response = _request("GET", f"/orders/{order_id}", telegram_id)
    data = _json_or(response)
    if data is None:
        logger.info("Order %s not available for %s: %s", order_id, telegram_id,
                    response.status_code if response is not None else "no response")
    return data


def update_order(order_id: int, telegram_id: int, order_data: dict):
    """Updated order dict, or {"error": True, "status_code": ..., "detail": ...}."""
    response = _request("PUT", f"/orders/{order_id}", telegram_id, json=order_data)
    if response is not None and response.status_code == 200:
        return response.json()
    return _error(response)


def patch_update_order(order_id: int, telegram_id: int, order_data: dict):
    response = _request("PATCH", f"/orders/patch/{order_id}", telegram_id, json=order_data)
    return _json_or(response, "Backendda xatolik bor!")



def delete_order(order_id: int, telegram_id: int):
    response = _request("DELETE", f"/orders/{order_id}", telegram_id)
    if response is not None and response.status_code == 200:
        try:
            return response.json()
        except ValueError:
            return {}
    return _error(response)



def approve_order(order_id: int, telegram_id: int):
    response = _request("POST", f"/orders/{order_id}/approve", telegram_id)
    if response is not None and response.status_code == 200:
        return response.json()
    return _error(response) if response is not None and response.status_code == 403 else None

def disapprove_order(order_id: int, telegram_id: int):
    response = _request("POST", f"/orders/{order_id}/disapprove", telegram_id)
    if response is not None and response.status_code == 200:
        return response.json()
    return _error(response) if response is not None and response.status_code == 403 else None

def delivered_order(order_id: int, is_delivered: bool, telegram_id: int):
    response = _request("POST", f"/orders/{order_id}/delivered", telegram_id,
                        params={"is_delivered": str(is_delivered).lower()})
    if response is not None and response.status_code == 200:
        try:
            return response.json()
        except ValueError:
            return {}
    return _error(response)


def getting_my_orders_price(
    telegram_id: int,
    which_day:str = None,
    start_date: str = None,  # format "YYYY-MM-DD"
    end_date: str = None,
    today_only: bool = False
):
    """
    Get total price for the current user (agent/admin/dostavchik).
    Can filter by today or a date range.
    """
    payload = {}
    if which_day:
        payload["which_day"] = which_day
    if start_date:
        payload["start_date"] = start_date
    if end_date:
        payload["end_date"] = end_date
    if today_only:
        payload["today_only"] = True

    return _json_or(_request("GET", "/agents/my-orders-total-price", telegram_id, params=payload))


def remaining_salary(telegram_id: int,agents_id:Optional[int] = None):
    params = {"agent_id": agents_id} if agents_id is not None else {}
    return _json_or(_request("GET", "/agents/salary", telegram_id, params=params))




#################
#products API
def get_products(telegram_id: int):
    response = _request("GET", "/products/", telegram_id)
    products = _json_or(response)
    if isinstance(products, list):
        return products
    logger.error("❌ Product retrieval failed: %s", response.text if response is not None else "no response")
    return []


def creating_product(telegram_id:int,name:str,price:float,unit:str):
    return _json_or(_request("POST", "/products/create", telegram_id,
                             json={"name": name, "price": int(price), "unit": unit.strip().lower()}))



def update_product(telegram_id:int,products_id:int,name:str,price:float,unit:str):
    return _json_or(_request("PUT", f"/products/update/{products_id}", telegram_id,
                             json={"name": name, "price": price, "unit": unit}))


def delete_product(telegram_id:int,product_id:int):
    return _json_or(_request("DELETE", f"/products/delete/{product_id}", telegram_id))

#####


#####################
#agents apis

def getting_all_agents(telegram_id:int):
    return _json_or(_request("GET", "/agents/all", telegram_id))

def getting_one_agent(telegram_id:int,agent_id:int):
    return _json_or(_request("GET", f"/agents/{agent_id}", telegram_id))

def deleting_agent(telegram_id:int,agent_id:int):
    return _json_or(_request("DELETE", f"/agents/delete/{agent_id}", telegram_id))

def updating_agent(telegram_id:int,agent_id:int,first_name:str,last_name:str,phone_number:str,percentage:int,role:str):
    return _json_or(_request("PUT", f"/agents/update/{agent_id}", telegram_id, json={
        "first_name":first_name,
        "last_name":last_name,
        "phone_number":phone_number,
        "percentage":float(percentage),
        "role":role
    }))

def creating_agent(telegram_id:int,first_name:str,last_name:str,phone_number:str,percentage:int,role:str):
    return _json_or(_request("POST", "/agents/create", telegram_id, json={
        "first_name":first_name,
        "last_name":last_name,
        "phone_number":phone_number,
        "percentage":float(percentage),
        "role":role
    }))

def adding_salary(telegram_id:int,agent_id:int,salary_amount:int):
    return _json_or(_request("POST", f"/agents/add-salary/{agent_id}", telegram_id,
                             json={"salary_amount": salary_amount}))


def get_users_salary(
    telegram_id: int,
    agent_id:int,
    which_day:str = None,
    start_date: str = None,  # format "YYYY-MM-DD"
    end_date: str = None,
    today_only: bool = False
):
    """
    Get total price for the current user (agent/admin/dostavchik).
    Can filter by today or a date range.
    """
    payload = {
        "agent_id":agent_id
    }
    if which_day:
        payload["which_day"] = which_day
    if start_date:
        payload["start_date"] = start_date
    if end_date:
        payload["end_date"] = end_date
    if today_only:
        payload["today_only"] = True

    return _json_or(_request("GET", "/agents/taking-users-price-with-id", telegram_id, params=payload))



### order hisobot


def get_total_orders_price_today(telegram_id):
    return _json_or(_request("GET", "/orders/total-price", telegram_id, params={"today_only": "true"}), {})

def get_total_orders_price_by_date(telegram_id, date_str):
    return _json_or(_request("GET", "/orders/total-price", telegram_id,
                             params={"which_day": f"{date_str}T00:00:00"}), {})

def get_total_orders_price_between(telegram_id, start_str, end_str):
    return _json_or(_request("GET", "/orders/total-price", telegram_id,
                             params={"start_date": f"{start_str}T00:00:00", "end_date": f"{end_str}T23:59:59"}), {})


### agent earnings (admin panel)

def get_agents_earnings(telegram_id, **params):
    return _json_or(_request("GET", "/agents/earnings", telegram_id, params=params), {})
