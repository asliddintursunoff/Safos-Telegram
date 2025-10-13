import urllib.parse
from datetime import datetime
import urllib.parse
from datetime import datetime

def get_order_print_url(order):
    ESC = "\x1B"
    GS = "\x1D"

    bold_on = ESC + "E" + "\x01"
    bold_off = ESC + "E" + "\x00"
    center = ESC + "a" + "\x01"
    left = ESC + "a" + "\x00"
    big_on = GS + "!" + "\x33"   # very big SAFOS
    big_off = GS + "!" + "\x00"

    line_width = 48  # Standard for 80mm printer
    sep_line = "█" * line_width  # bold line

    # Adjust column widths
    name_w = 16    # was 18
    price_w = 10
    qty_w = 12     # was 10
    sum_w = 10

    lines = []

    # ===== HEADER =====
    lines.append(center + bold_on + big_on + "SAFOS\n" + big_off + bold_off)
    lines.append(center + "Sof mahsulot\n")
    lines.append(sep_line + "\n")

    # ===== INFO SECTION =====
    agent = order.get("agent")
    if agent:
        agent_name = f"{agent.get('first_name','')} {agent.get('last_name','')}".strip()
        lines.append(left + bold_on + "Agent: " + bold_off + f"{agent_name}\n")

    dostavchik = order.get("dostavchik")
    if dostavchik:
        d_name = f"{dostavchik.get('first_name','')} {dostavchik.get('last_name','')}".strip()
        lines.append(bold_on + "Dostavchik: " + bold_off + f"{d_name}\n")

    lines.append("\n")  # spacing between humans and time

    for_who = order.get("for_who", "Noma’lum")
    lines.append(bold_on + "Buyurtma egasi: " + bold_off + f"{for_who}\n")

    if order.get("order_date"):
        time_taken = datetime.fromisoformat(order["order_date"]).strftime("%d-%m-%Y %H:%M")
        lines.append(bold_on + "Olingan vaqt: " + bold_off + f"{time_taken}\n")

    if order.get("delivered_date"):
        delivered_time = datetime.fromisoformat(order["delivered_date"]).strftime("%d-%m-%Y %H:%M")
        lines.append(bold_on + "Yetkazilgan: " + bold_off + f"{delivered_time}\n")

    lines.append(sep_line + "\n")

    # ===== PRODUCT TABLE HEADER =====
    lines.append(
        bold_on +
        f"{'Nomi':<{name_w}}{'Narx':<{price_w}}{'Soni':<{qty_w}}{'Summa':>{sum_w}}\n" +
        bold_off
    )
    lines.append(sep_line + "\n")

    # ===== PRODUCT ROWS =====
    total = 0
    for item in order.get("items", []):
        product_name = item["product"]["name"][:name_w]
        price = int(item["product"]["price"])
        qty = int(item["quantity"])
        unit = item["product"]["unit"]
        line_total = qty * price
        total += line_total

        price_str = f"{price:,}"
        qty_str = f"{qty:,} {unit}"
        total_str = f"{line_total:,}"

        lines.append(
            f"{product_name:<{name_w}}{price_str:<{price_w}}{qty_str:<{qty_w}}{total_str:>{sum_w}}\n"
        )
        lines.append(sep_line + "\n")

    # ===== TOTAL =====
    total_str = f"{total:,}"
    lines.append(bold_on + f"{'Jami:':<{name_w+price_w+qty_w}}{total_str:>{sum_w}}\n" + bold_off)

    # ===== SIGN LINE =====
    lines.append("\n")
    lines.append("\n")
    sign_line = "IMZO:  "
    lines.append(sign_line + "\n")
    lines.append("       "+"█" * line_width-len(sign_line))

    # ===== FOOTER =====
    lines.append(center + bold_on + "Rahmat! Yana kutib qolamiz!\n" + bold_off)
    lines.append(center + "\n\n\n")

    receipt_text = "".join(lines)
    encoded = urllib.parse.quote(receipt_text)

    return f"https://asliddintursunoff.github.io/url-redirect/print.html?data={encoded}"
