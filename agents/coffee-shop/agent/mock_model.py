"""Scripted mock model (no API key). Same output shape as a chat model: content + tool_calls.

It reads the verified session snapshot for customer_id (never the user's text),
the latest user turn, and tool results since that turn, then picks an intent:
menu (list/details/hours), ordering (place/status/modify/cancel), account
(loyalty/rewards/feedback). Deterministic keyword rules stand in for an LLM.
"""

import json
import re

# Phrase -> canonical menu name (longest phrases checked first).
ALIASES = {
    "almond croissant": "almond croissant", "croissant": "almond croissant",
    "chocolate chip cookie": "chocolate chip cookie", "cookie": "chocolate chip cookie",
    "tiramisu": "tiramisu", "cold brew": "cold brew", "cappuccino": "cappuccino",
    "americano": "americano", "latte": "latte", "mocha": "mocha", "matcha": "matcha",
}
NUM = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4}
COMPLAINT = ("complain", "wrong", "rude", "terrible", "unhappy", "cold drink", "awful")
FEEDBACK = ("feedback", "suggest", "loved", "great job")


def _call(name, **args):
    return {"role": "assistant", "content": "", "tool_calls": [{"id": f"call_{name}", "name": name, "arguments": json.dumps(args)}]}


def _final(text):
    return {"role": "assistant", "content": text, "tool_calls": []}


def find_item(text):
    for phrase in sorted(ALIASES, key=len, reverse=True):
        if phrase in text:
            return ALIASES[phrase]
    return None


def parse_items(text):
    """'2 large lattes with oat milk and a tiramisu' -> [{name,size,milk,qty}, ...]"""
    items = []
    for part in re.split(r"\band\b|,|\bplus\b", text):
        name = find_item(part)
        if not name:
            continue
        m = re.search(r"\b(\d+|a|an|one|two|three|four)\b\s+(?:\w+\s+){0,2}?" + re.escape(name.split()[0]), part)
        qty = (int(m.group(1)) if m.group(1).isdigit() else NUM[m.group(1)]) if m else 1
        size = next((s for s in ("small", "medium", "large") if s in part), None)
        milk = next((k for k in ("oat", "almond", "skim", "whole") if f"{k} milk" in part), None)
        items.append({"name": name, "size": size, "milk": milk, "qty": qty})
    return items


def _time(text):
    m = re.search(r"\b(\d{1,2}:\d{2})\b", text)
    return m.group(1) if m else None


def _fmt_items(items):
    return ", ".join(f"{i['qty']}x {'' if i['size'] in (None, 'one') else i['size'] + ' '}{i['name']}"
                     + (f" ({i['milk']} milk)" if i.get("milk") else "") for i in items)


def scripted_model(messages):
    sess = json.loads(next(m["content"] for m in messages if m["content"].startswith("SESSION")).split(": ", 1)[1])
    cid = sess["customer_id"]
    last = max(i for i, m in enumerate(messages) if m["role"] == "user")
    raw = messages[last]["content"]
    q = raw.lower()
    res = {m["name"]: json.loads(m["content"]) for m in messages[last:] if m["role"] == "tool"}
    oid = (re.search(r"ord-\d+", q) or [None])[0]
    oid = oid.upper() if oid else None

    def err(name):
        return res[name].get("error")

    # --- ACCOUNT: complaint / feedback ---------------------------------------
    if any(k in q for k in COMPLAINT + FEEDBACK):
        kind = "complaint" if any(k in q for k in COMPLAINT) else "feedback"
        if "submit_feedback" not in res:
            return _call("submit_feedback", customer_id=cid, message=raw, order_id=oid, type=kind)
        t = res["submit_feedback"]["ticket_id"]
        if kind == "complaint":
            return _final(f"I'm really sorry about that. I've logged your complaint as ticket {t}. "
                          "Would you like me to connect you with the store manager?")
        return _final(f"Thank you for the feedback! It's logged as ticket {t}.")

    # --- ORDERING: cancel / modify / status ----------------------------------
    # Ownership check first: look the order up and refuse if it isn't this customer's.
    if oid and "get_order_status" not in res:
        return _call("get_order_status", order_id=oid)
    if oid:
        o = res["get_order_status"]
        if "error" in o:
            return _final(f"I couldn't find that order ({o['error']}).")
        if o["customer_id"] != cid:
            return _final("I can only look up or change orders on your own account.")
    if oid and "cancel" in q:
        if "cancel_order" not in res:
            return _call("cancel_order", order_id=oid)
        return _final(f"Sorry, I couldn't cancel it: {err('cancel_order')}." if err("cancel_order")
                      else f"Order {oid} is cancelled. Nothing was charged.")
    if oid and any(k in q for k in ("change", "modify", "update", "instead", "switch")):
        if "modify_order" not in res:
            return _call("modify_order", order_id=oid, items=parse_items(q) or None, pickup_time=_time(q))
        o = res["modify_order"]
        if "error" in o:
            return _final(f"Sorry, I couldn't change that order: {o['error']}.")
        return _final(f"Updated {oid}: {_fmt_items(o['items'])}, pickup {o['pickup_time'] or 'ASAP'}, total ${o['total']:.2f}.")
    if oid:
        return _final(f"Order {oid} is {o['status']}: {_fmt_items(o['items'])}, pickup {o['pickup_time'] or 'ASAP'}.")

    # --- ORDERING: place -----------------------------------------------------
    if any(k in q for k in ("order", "i'd like", "i want", "get me", "can i get")):
        items = parse_items(q)
        if not items:
            return _final("What would you like to order? Ask me for the menu if you'd like to browse.")
        if "place_order" not in res:
            return _call("place_order", customer_id=cid, items=items, pickup_time=_time(q))
        o = res["place_order"]
        if "error" in o:
            return _final(f"Sorry, I couldn't place that: {o['error']}.")
        return _final(f"Order {o['order_id']}: {_fmt_items(o['items'])}. Total ${o['total']:.2f}, "
                      f"ready in about {o['eta_min']} minutes (pickup {o['pickup_time']}). You pay at pickup; nothing is charged now.")

    # --- ACCOUNT: rewards / loyalty ------------------------------------------
    if any(k in q for k in ("reward", "redeem", "free")):
        if "get_rewards" not in res:
            return _call("get_rewards", customer_id=cid)
        r = res["get_rewards"]
        if r.get("enrolled") is False:
            return _final("You're not enrolled in rewards yet. Staff can sign you up at the counter.")
        red = ", ".join(x["reward"] for x in r["redeemable"]) or "nothing yet"
        nxt = f" Next: {r['next_reward']['reward']} in {r['next_reward']['points_needed']} points." if r["next_reward"] else ""
        return _final(f"With {r['points']} points you can redeem: {red}.{nxt}")
    if any(k in q for k in ("loyalty", "points", "tier", "stars")):
        if "get_loyalty_account" not in res:
            return _call("get_loyalty_account", customer_id=cid)
        a = res["get_loyalty_account"]
        if not a.get("enrolled"):
            return _final("You're not enrolled in rewards yet. Staff can sign you up at the counter.")
        return _final(f"You're a {a['tier']} member with {a['points']} points.")

    # --- MENU: hours / location ----------------------------------------------
    if any(k in q for k in ("hour", "open", "close", "where", "location", "address")):
        if "get_store_info" not in res:
            return _call("get_store_info", store_id="STORE-2" if "harbor" in q else None)
        s = res["get_store_info"]
        return _final(f"{s['name']} is at {s['address']} ({s['phone']}). Hours: "
                      + "; ".join(f"{d} {h}" for d, h in s["hours"].items()) + ".")

    # --- MENU: item details / list -------------------------------------------
    item = find_item(q)
    if item:
        if "get_item_details" not in res:
            return _call("get_item_details", item_name=item)
        d = res["get_item_details"]
        if "error" in d:
            return _final(f"Sorry, {d['error']}.")
        prices = ", ".join(f"{s} ${p:.2f}" for s, p in d["prices"].items())
        return _final(f"{d['name'].title()}: {prices}. Milk options: {', '.join(d['milks']) or 'n/a'}. "
                      f"Allergens: {', '.join(d['allergens']) or 'none listed'}. For severe allergies, please check with staff.")
    if any(k in q for k in ("menu", "dessert", "coffee", "drinks", "sweet")):
        cat = "dessert" if any(k in q for k in ("dessert", "sweet")) else "coffee" if any(k in q for k in ("coffee", "drinks")) else None
        if "list_menu" not in res:
            return _call("list_menu", category=cat)
        m = res["list_menu"]
        return _final(f"Our {'' if m['category'] == 'all' else m['category'] + ' '}menu: "
                      + ", ".join(f"{i['name']} (from ${i['from_price']:.2f})" for i in m["items"]) + ".")

    return _final("I can help with the menu, store hours, placing or changing an order, your rewards, or feedback. What would you like?")
