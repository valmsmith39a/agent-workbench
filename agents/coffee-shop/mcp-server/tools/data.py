"""Fake data and in-memory mock state shared by all tool modules."""

import itertools

CUSTOMERS = {
    "CUST-201": {"name": "Maya Lin", "loyalty": {"tier": "Gold", "points": 240}},
    "CUST-202": {"name": "Omar Haddad", "loyalty": {"tier": "Green", "points": 45}},
    "CUST-203": {"name": "Priya Rao", "loyalty": None},
}

MENU = {
    # coffee
    "latte": {"category": "coffee", "prices": {"small": 4.25, "medium": 4.95, "large": 5.45}, "milks": ["whole", "oat", "almond", "skim"], "allergens": ["milk"]},
    "cappuccino": {"category": "coffee", "prices": {"small": 4.15, "medium": 4.75}, "milks": ["whole", "oat", "skim"], "allergens": ["milk"]},
    "americano": {"category": "coffee", "prices": {"small": 3.25, "medium": 3.75, "large": 4.25}, "milks": ["none", "whole", "oat"], "allergens": []},
    "cold brew": {"category": "coffee", "prices": {"medium": 4.45, "large": 4.95}, "milks": ["none", "oat", "whole"], "allergens": []},
    "mocha": {"category": "coffee", "prices": {"small": 4.65, "medium": 5.25, "large": 5.75}, "milks": ["whole", "oat", "almond"], "allergens": ["milk", "soy"]},
    # dessert
    "almond croissant": {"category": "dessert", "prices": {"one": 3.95}, "milks": [], "allergens": ["wheat", "tree nuts", "milk", "egg"]},
    "chocolate chip cookie": {"category": "dessert", "prices": {"one": 2.75}, "milks": [], "allergens": ["wheat", "milk", "egg", "soy"]},
    "tiramisu": {"category": "dessert", "prices": {"one": 5.50}, "milks": [], "allergens": ["wheat", "milk", "egg"]},
}

STORES = {
    "STORE-1": {"name": "Bean There (Main St)", "address": "123 Main St, Springfield", "phone": "555-0142",
                "hours": {"Mon-Fri": "6:30-19:00", "Sat": "7:00-18:00", "Sun": "8:00-16:00"}},
    "STORE-2": {"name": "Bean There (Harbor)", "address": "9 Pier Rd, Springfield", "phone": "555-0177",
                "hours": {"Mon-Sun": "7:00-17:00"}},
}
DEFAULT_STORE = "STORE-1"

REWARDS = [
    {"reward": "Free pastry", "points": 100},
    {"reward": "Free drink (any size)", "points": 200},
    {"reward": "Free drink + dessert", "points": 300},
]

# In-memory mock state. Seeded so status/modify/cancel can be demoed deterministically.
ORDERS = {
    "ORD-0900": {"customer_id": "CUST-202", "items": [{"name": "latte", "size": "medium", "milk": "oat", "qty": 1}],
                 "pickup_time": "08:15", "status": "preparing", "total": 4.95},
}
FEEDBACK = {}
order_ids = itertools.count(1001)
ticket_ids = itertools.count(501)
