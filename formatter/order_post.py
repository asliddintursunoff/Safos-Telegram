from datetime import datetime

from datetime import datetime

def format_order_message(order: dict):
    status_approved = "" if order.get("is_approved") else "#Yaroqsiz❌"
    status_delivered = "#yetqazib berildi✅" if order.get("is_delivered") else "#yetqazilmagan❌"

    order_date = order.get("order_date")
  
    if order_date:
        order_date = datetime.fromisoformat(order_date).strftime("%d-%m-%Y %H:%M")
    else:
        order_date = "Noma'lum"

    agent = order.get("agent")
    if agent:
        agent_fullname = f"{agent.get('first_name','')} {agent.get('last_name','')}"
    else:
        agent_fullname = "Noma'lum agent"

    dostavchik = order.get("dostavchik")

    if dostavchik:
        dostavchik_name = f"{dostavchik.get('first_name','')} {agent.get('last_name','')}"
    else:
        dostavchik_name = None
    delivered_date = order.get("delivered_date")
    
    if delivered_date:
        delivered_date = datetime.fromisoformat(delivered_date).strftime("%d-%m-%Y %H:%M")
    else: 
        delivered_date = None
    text = f"{status_approved}\n{status_delivered}\n"
    text += f"🧾 <b>Buyurtma tafsilotlari:</b>\n\n"
    text += f"🧾 <b>Buyurtmani oldi:</b> {agent_fullname}\n"
    text += f"👤 <b>Buyurtma egasi:</b> {order.get('for_who','Noma\'lum')}\n"
    if dostavchik_name:
        text += f"🚚 <b>Yetqazib berdi:</b> {dostavchik_name}\n"
    text+="\n"
    text += f"⏰ <b>Buyurtma vaqti:</b> {order_date}\n"
    if delivered_date:
        text += f"🚚⏰ <b>Yetqazib berilgan vaqti:</b> {delivered_date}\n\n"
    
    items = order.get("items") or []
    for item in items:
        product = item.get("product") or {}
        text += (
            f"📦 {product.get('name','')} {product.get('unit','')} x {item.get('quantity',0)} × {product.get('price',0):,} = {item.get('total_price',0):,} so'm\n"
        )

    total_price = order.get("get_total_price", 0)
    text += f"\n🟢 <b>Umumiy narx:</b> {total_price:,} so'm ✅"
    return text
