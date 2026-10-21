"""ORDERING category: place_order, get_order_status, modify_order, cancel_order. No payments."""

from .data import CUSTOMERS, MENU, ORDERS, order_ids


def _validate(items):
    """Return (normalized_items, total) or an error dict."""
    if not items:
        return {"error": "order has no items"}
    out, total = [], 0.0
    for it in items:
        name = (it.get("name") or "").lower().strip()
        d = MENU.get(name)
        if not d:
            return {"error": f"'{it.get('name')}' is not on the menu"}
        size = it.get("size") or ("one" if "one" in d["prices"] else "medium")
        if size not in d["prices"]:
            return {"error": f"{name} comes in {', '.join(d['prices'])}"}
        milk = it.get("milk")
        if milk and milk not in d["milks"]:
            return {"error": f"{name} milk options: {', '.join(d['milks']) or 'none'}"}
        qty = int(it.get("qty") or 1)
        if not 1 <= qty <= 10:
            return {"error": "qty must be 1-10"}
        out.append({"name": name, "size": size, "milk": milk, "qty": qty})
        total += d["prices"][size] * qty
    return out, round(total, 2)


def _eta(items):
    return 5 + 2 * sum(i["qty"] for i in items)


def place_order(customer_id: str, items: list[dict], pickup_time: str | None = None) -> dict:
    """Validate items [{name,size,milk,qty}] against the menu and create a pickup order. Pay at pickup."""
    if customer_id not in CUSTOMERS:
        return {"error": "unknown customer"}
    v = _validate(items)
    if isinstance(v, dict):
        return v
    norm, total = v
    oid = f"ORD-{next(order_ids)}"
    ORDERS[oid] = {"customer_id": customer_id, "items": norm, "pickup_time": pickup_time, "status": "received", "total": total}
    return {"order_id": oid, "items": norm, "total": total, "pickup_time": pickup_time or "ASAP",
            "eta_min": _eta(norm), "payment": "pay at pickup (mock, nothing charged)"}


def get_order_status(order_id: str) -> dict:
    """Status, items, pickup time, and total for an order."""
    o = ORDERS.get((order_id or "").upper())
    return {"order_id": order_id.upper(), **o} if o else {"error": f"No order '{order_id}'"}


def modify_order(order_id: str, items: list[dict] | None = None, pickup_time: str | None = None) -> dict:
    """Replace the items and/or change pickup time on an order that isn't cancelled or picked up."""
    oid = (order_id or "").upper()
    o = ORDERS.get(oid)
    if not o:
        return {"error": f"No order '{order_id}'"}
    if o["status"] in ("cancelled", "picked up"):
        return {"error": f"Order {oid} is {o['status']} and can't be changed"}
    if items:
        v = _validate(items)
        if isinstance(v, dict):
            return v
        o["items"], o["total"] = v
    if pickup_time:
        o["pickup_time"] = pickup_time
    return {"order_id": oid, "modified": True, **o}


def cancel_order(order_id: str) -> dict:
    """Cancel an order. Nothing was charged, so no refund is needed."""
    oid = (order_id or "").upper()
    o = ORDERS.get(oid)
    if not o:
        return {"error": f"No order '{order_id}'"}
    if o["status"] in ("cancelled", "picked up"):
        return {"error": f"Order {oid} is already {o['status']}"}
    o["status"] = "cancelled"
    return {"order_id": oid, "status": "cancelled"}


def register(mcp) -> None:
    for fn in (place_order, get_order_status, modify_order, cancel_order):
        mcp.tool()(fn)
