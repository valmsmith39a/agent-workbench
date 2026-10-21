"""MENU category: list_menu, get_item_details, get_store_info."""

from .data import DEFAULT_STORE, MENU, STORES


def list_menu(category: str | None = None) -> dict:
    """List menu items, optionally filtered by category ('coffee' or 'dessert')."""
    if category and category not in ("coffee", "dessert"):
        return {"error": "category must be 'coffee' or 'dessert'"}
    items = [{"name": n, "category": d["category"], "from_price": min(d["prices"].values())}
             for n, d in MENU.items() if not category or d["category"] == category]
    return {"category": category or "all", "items": items}


def get_item_details(item_name: str) -> dict:
    """Prices per size, sizes, milk options, and allergens for one menu item."""
    d = MENU.get((item_name or "").lower().strip())
    if not d:
        return {"error": f"'{item_name}' is not on the menu", "items": sorted(MENU)}
    return {"name": item_name.lower().strip(), "category": d["category"], "prices": d["prices"],
            "sizes": list(d["prices"]), "milks": d["milks"], "allergens": d["allergens"]}


def get_store_info(store_id: str | None = None) -> dict:
    """Hours, address, and phone for a store (defaults to the main store)."""
    sid = store_id or DEFAULT_STORE
    s = STORES.get(sid)
    return {"store_id": sid, **s} if s else {"error": f"Unknown store '{store_id}'", "stores": sorted(STORES)}


def register(mcp) -> None:
    for fn in (list_menu, get_item_details, get_store_info):
        mcp.tool()(fn)
