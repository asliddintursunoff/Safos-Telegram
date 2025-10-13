import requests
from config import API_URL
import logging
def verify_telegram(phone_number:str,telegram_id:int):
    response = requests.post(url=f"{API_URL}/agents/verify-telegram",
                            json={
                                
                                "phone_number": phone_number,
                                "telegram_id": telegram_id
                                    
                            })
    if response.status_code == 200:
        return response.json()
    return None





def create_order(order,telegram_id):
    response = requests.post(url=f"{API_URL}/orders/",
                            json=order,
                            headers={
                                "x-telegram-id":f"{telegram_id}"
                            })

    if response.status_code == 200:
        return response.json()
    print("❌ Order creation failed:", response.text)
    return None


#getting orders
def get_new_orders(telegram_id:int):
    response = requests.get(url=f"{API_URL}/orders/",
                            headers={
                                "x-telegram-id":f"{telegram_id}"
                            })
    
    if response.status_code ==200:
        return response.json()
    print("❌ Order getting failed:", response.text)
    return "Getting order is failed!"

def calculating_new_orders_quantity():
    response = requests.get(url=f"{API_URL}/orders/calculating-existing-orders")
                            
    
    if response.status_code ==200:
        return response.json()
    print("❌ Order getting failed:", response.text)
    return "Yangi Zakaz mavjud emas"
    
def get_order_by_id(order_id: int, telegram_id: int):
    response = requests.get(
        url=f"{API_URL}/orders/{order_id}",
        headers={"x-telegram-id": f"{telegram_id}"}
    )
    if response.status_code == 200:
        data = response.json()
        logging.info(f"Order {order_id} data: {data}")
        return data
    logging.error(f"❌ Order getting failed: {response.text}")
    return None


def update_order(order_id: int, telegram_id: int, order_data: dict):
    response = requests.put(
        f"{API_URL}/orders/{order_id}",
        headers={"x-telegram-id": str(telegram_id)},
        json=order_data
    )
    return response.json() if response.status_code == 200 else None


def patch_update_order(order_id: int, telegram_id: int, order_data: dict):
    response = requests.patch(
        f"{API_URL}/orders/patch/{order_id}",
        headers={"x-telegram-id": str(telegram_id)},
        json=order_data
    )
    return response.json() if response.status_code == 200 else "Backendda xatolik bor!"



def delete_order(order_id: int, telegram_id: int):
    response = requests.delete(
        f"{API_URL}/orders/{order_id}",
        headers={"x-telegram-id": str(telegram_id)}
    )
    if response.status_code == 200:
        try:
            return response.json()
        except ValueError:
            return {}
    return {"error": True, "status_code": response.status_code}



def approve_order(order_id: int, telegram_id: int):
    response = requests.post(
        f"{API_URL}/orders/{order_id}/approve",
        headers={"x-telegram-id": str(telegram_id)}
    )
    return response.json() if response.status_code == 200 else None

def disapprove_order(order_id: int, telegram_id: int):
    response = requests.post(
        f"{API_URL}/orders/{order_id}/disapprove",
        headers={"x-telegram-id": str(telegram_id)}
    )
    return response.json() if response.status_code == 200 else None

def delivered_order(order_id: int, is_delivered: bool, telegram_id: int):
    response = requests.post(
        f"{API_URL}/orders/{order_id}/delivered",
        headers={"x-telegram-id": str(telegram_id)},
        params={"is_delivered": str(is_delivered).lower()}
    )
    return response.json() if response.status_code == 200 else None

    



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

    response = requests.get(
        f"{API_URL}/agents/my-orders-total-price",
        headers={"x-telegram-id": str(telegram_id)},
        params=payload
    )
    if response.status_code == 200:
        return response.json()
    return None


from typing import Optional
def remaining_salary(telegram_id: int,agents_id:Optional[int] = None):
    response = requests.get(
        f"{API_URL}/agents/salary/",
        headers={"x-telegram-id": str(telegram_id)},
        params={"agents_id": agents_id}
    )
    return response.json() if response.status_code == 200 else None




#################
#products API
def get_products(telegram_id: int):
    response = requests.get(
        url=f"{API_URL}/products/",
        headers={"x-telegram-id": f"{telegram_id}"}
    )
    if response.status_code == 200:
        products = response.json()
        logging.info(f"Products retrieved: {products}")
        return products
    logging.error(f"❌ Product retrieval failed: {response.text}")
    return []


def creating_product(telegram_id:int,name:str,price:float,unit:str):
    response = requests.post(
        f"{API_URL}/products/create",
        headers={"x-telegram-id": str(telegram_id)},
        json={"name": name,
              "price":int(price),
              "unit":unit.strip().lower()}
    )
    return response.json() if response.status_code == 200 else None
    


def update_product(telegram_id:int,products_id:int,name:str,price:float,unit:str):
    response = requests.put(
        f"{API_URL}/products/update/{products_id}",
        headers={"x-telegram-id": str(telegram_id)},
        json={"name": name,
              "price":price,
              "unit":unit}
    )
    return response.json() if response.status_code == 200 else None
    

def delete_product(telegram_id:int,product_id:int):
    response = requests.delete(
        f"{API_URL}/products/delete/{product_id}",
        headers={"x-telegram-id": str(telegram_id)},
        
    )
    return response.json() if response.status_code == 200 else None
    
#####


#####################
#agents apis

def getting_all_agents(telegram_id:int):
    response = requests.get(
        f"{API_URL}/agents/all",
        headers={"x-telegram-id": str(telegram_id)},
        
    )
    return response.json() if response.status_code == 200 else None

def getting_one_agent(telegram_id:int,agent_id:int):
    response = requests.get(
        f"{API_URL}/agents/{agent_id}",
        headers={"x-telegram-id": str(telegram_id)},
        
    )
    return response.json() if response.status_code == 200 else None
def deleting_agent(telegram_id:int,agent_id:int):
    response = requests.delete(
        f"{API_URL}/agents/delete/{agent_id}",
        headers={"x-telegram-id": str(telegram_id)},
        
    )
    return response.json() if response.status_code == 200 else None
def updating_agent(telegram_id:int,agent_id:int,first_name:str,last_name:str,phone_number:str,percentage:int,role:str):
    response = requests.put(
        f"{API_URL}/agents/update/{agent_id}",
        headers={"x-telegram-id": str(telegram_id)},
        json={
            "first_name":first_name,
            "last_name":last_name,
            "phone_number":phone_number,
            "percentage":float(percentage),
            "role":role
        }
        
    )
    return response.json() if response.status_code == 200 else None
def creating_agent(telegram_id:int,first_name:str,last_name:str,phone_number:str,percentage:int,role:str):
    response = requests.post(
        f"{API_URL}/agents/create",
        headers={"x-telegram-id": str(telegram_id)},
        json={
            "first_name":first_name,
            "last_name":last_name,
            "phone_number":phone_number,
            "percentage":float(percentage),
            "role":role
        }
        
    )
    return response.json() if response.status_code == 200 else None

def adding_salary(telegram_id:int,agent_id:int,salary_amount:int):
    response = requests.post(
        f"{API_URL}/agents/add-salary/{agent_id}",
        headers={"x-telegram-id": str(telegram_id)},
        json={
            "salary_amount":salary_amount,
            
        }
        
    )
    return response.json() if response.status_code == 200 else None


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

    response = requests.get(
        f"{API_URL}/agents/taking-users-price-with-id",
        headers={"x-telegram-id": str(telegram_id)},
        params=payload
    )
    if response.status_code == 200:
        return response.json()
    return None



### order hisobot


def get_total_orders_price_today(telegram_id):
    r = requests.get(
        f"{API_URL}/orders/total-price",
        params={"today_only": "true"},
        headers={"x-telegram-id": str(telegram_id)}
    )
    return r.json()

def get_total_orders_price_by_date(telegram_id, date_str):
    r = requests.get(
        f"{API_URL}/orders/total-price",
        params={"which_day": f"{date_str}T00:00:00"},
        headers={"x-telegram-id": str(telegram_id)}
    )
    return r.json()

def get_total_orders_price_between(telegram_id, start_str, end_str):
    r = requests.get(
        f"{API_URL}/orders/total-price",
        params={"start_date": f"{start_str}T00:00:00", "end_date": f"{end_str}T23:59:59"},
        headers={"x-telegram-id": str(telegram_id)}
    )
    return r.json()