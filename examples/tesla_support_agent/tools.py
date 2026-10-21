"""Mock, read-only Tesla support tools over fake data. No network, no real bookings."""

from datetime import date, timedelta

# Fake customers (not real people, VINs, or orders).
CUSTOMERS = {
    "CUST-1001": {"name": "Ada Park", "email": "ada@example.com", "vins": ["5YJ3E1EA0PF000001"], "orders": ["RN100001"]},
    "CUST-1002": {"name": "Ben Ortiz", "email": "ben@example.com", "vins": ["7SAYGDEE1PA000002"], "orders": ["RN100002"]},
    "CUST-1003": {"name": "Chloe Ng", "email": "chloe@example.com", "vins": [], "orders": ["RN100003"]},
}

ORDERS = {
    "RN100001": {"customer_id": "CUST-1001", "model": "Model 3 Long Range", "status": "Delivered", "eta": "2026-03-14", "delivery_center": "Fremont, CA"},
    "RN100002": {"customer_id": "CUST-1002", "model": "Model Y Performance", "status": "Delivered", "eta": "2026-06-02", "delivery_center": "Austin, TX"},
    "RN100003": {"customer_id": "CUST-1003", "model": "Model S Plaid", "status": "In Transit", "eta": "2026-11-04", "delivery_center": "Seattle, WA"},
}

VEHICLES = {
    "5YJ3E1EA0PF000001": {"customer_id": "CUST-1001", "model": "Model 3 Long Range", "year": 2026, "software_version": "2026.32.5", "odometer_mi": 7120,
                          "warranty": {"basic": "4 yr / 50,000 mi", "battery_drive_unit": "8 yr / 120,000 mi", "basic_expires": "2030-03-14"}},
    "7SAYGDEE1PA000002": {"customer_id": "CUST-1002", "model": "Model Y Performance", "year": 2026, "software_version": "2026.26.3", "odometer_mi": 4380,
                          "warranty": {"basic": "4 yr / 50,000 mi", "battery_drive_unit": "8 yr / 120,000 mi", "basic_expires": "2030-06-02"}},
}

FAQ = [
    {"id": "faq-charging", "keywords": ["charge", "charging", "home", "wall connector", "range"],
     "answer": "For daily driving, set the charge limit to about 80-90% in the Charging screen; charge to 100% before long trips. A Wall Connector is the recommended home setup."},
    {"id": "faq-supercharger", "keywords": ["supercharger", "supercharging", "idle fee", "fast charge"],
     "answer": "Find Superchargers in the vehicle's navigation or the Tesla app. Idle fees may apply if the car stays plugged in after charging finishes; current rates are shown in the app."},
    {"id": "faq-fsd", "keywords": ["fsd", "full self-driving", "autopilot", "self driving"],
     "answer": "Full Self-Driving (Supervised) requires an attentive driver with hands on the wheel at all times. It does not make the vehicle autonomous."},
    {"id": "faq-warranty", "keywords": ["warranty", "covered", "coverage", "battery warranty"],
     "answer": "The Basic Vehicle Limited Warranty covers 4 years or 50,000 miles; the Battery and Drive Unit warranty covers 8 years with a model-specific mileage limit."},
    {"id": "faq-returns", "keywords": ["return", "returns", "refund", "cancel"],
     "answer": "Return and refund eligibility depends on your purchase agreement and region. A Tesla advisor must review any return or refund request."},
]

FAQ += [
    {"id": "faq-tire-service", "keywords": ["tire", "tyre", "flat", "puncture"],
     "answer": "Tire repair and replacement are handled by Tesla Service, at a Service Center or via Mobile Service. Do not attempt a roadside tire change yourself; request service in the Tesla app, or Roadside Assistance if you are stranded."},
    {"id": "faq-tire-cost", "keywords": ["tire cost", "cost", "covered", "pay", "price"],
     "answer": "Tire damage from road hazards is generally not covered by the Basic Vehicle Limited Warranty. Your advisor will share an estimate in the Tesla app before any work; you approve it before it starts."},
    {"id": "faq-tire-duration", "keywords": ["how long", "duration", "take"],
     "answer": "A typical tire repair or replacement takes about 1 hour once the technician arrives or the car is in the bay."},
    {"id": "faq-mobile-service", "keywords": ["mobile", "come to me", "my house"],
     "answer": "Tesla Mobile Service can perform many repairs, including most tire work, at your home or office where available."},
]

SERVICE_CENTERS = ["Fremont Service Center", "Austin Service Center", "Seattle Service Center"]
_BASE_DAY = date(2026, 10, 26)  # fixed so output is deterministic


def lookup_order(order_id: str = None, customer_id: str = None) -> dict:
    """Delivery status / ETA by order id or by customer id."""
    if order_id:
        order = ORDERS.get(order_id.upper())
        return {"order_id": order_id.upper(), **order} if order else {"error": f"No order '{order_id}'"}
    if customer_id in CUSTOMERS:
        return {"orders": [{"order_id": o, **ORDERS[o]} for o in CUSTOMERS[customer_id]["orders"]]}
    return {"error": "Provide an order_id or a valid customer_id"}


def get_vehicle_info(vin: str) -> dict:
    v = VEHICLES.get((vin or "").upper())
    return {"vin": vin.upper(), **v} if v else {"error": f"No vehicle with VIN '{vin}'"}


def get_available_service_slots(vin: str, days: int = 3) -> dict:
    if (vin or "").upper() not in VEHICLES:
        return {"error": f"No vehicle with VIN '{vin}'"}
    slots = [f"{(_BASE_DAY + timedelta(days=i)).isoformat()} {t}" for i in range(days) for t in ("09:00", "14:00")]
    return {"vin": vin.upper(), "slots": slots}


def schedule_service(vin: str, issue: str, preferred_date: str = None, mobile: bool = False) -> dict:
    """Returns a PROPOSED appointment. Nothing is booked."""
    slots = get_available_service_slots(vin)
    if "error" in slots:
        return slots
    pick = next((s for s in slots["slots"] if preferred_date and s.startswith(preferred_date)), slots["slots"][0])
    return {"status": "proposed (not booked)", "vin": vin.upper(), "issue": issue, "slot": pick,
            "location": "Mobile Service (customer address on file)" if mobile else SERVICE_CENTERS[0], "note": "Customer must confirm in the Tesla app."}


def search_faq(query: str, k: int = 2) -> dict:
    """Tiny keyword retrieval: score = number of keyword hits in the query."""
    q = query.lower()
    scored = sorted(((sum(kw in q for kw in f["keywords"]), f) for f in FAQ), key=lambda x: -x[0])
    hits = [{"id": f["id"], "answer": f["answer"]} for s, f in scored[:k] if s > 0]
    return {"query": query, "results": hits}


TOOLS = {
    "lookup_order": lookup_order,
    "get_vehicle_info": get_vehicle_info,
    "get_available_service_slots": get_available_service_slots,
    "schedule_service": schedule_service,
    "search_faq": search_faq,
}
