"""ACCOUNT category: get_loyalty_account, get_rewards, submit_feedback."""

from .data import CUSTOMERS, FEEDBACK, REWARDS, ticket_ids


def get_loyalty_account(customer_id: str) -> dict:
    """Loyalty tier and points balance."""
    c = CUSTOMERS.get(customer_id)
    if not c:
        return {"error": "unknown customer"}
    return {"customer_id": customer_id, "enrolled": False} if not c["loyalty"] else {"customer_id": customer_id, "enrolled": True, **c["loyalty"]}


def get_rewards(customer_id: str) -> dict:
    """Rewards the customer can redeem now, and the next one to unlock."""
    acct = get_loyalty_account(customer_id)
    if "error" in acct or not acct["enrolled"]:
        return {**acct, "redeemable": []}
    pts = acct["points"]
    nxt = next((r for r in REWARDS if r["points"] > pts), None)
    return {"customer_id": customer_id, "points": pts, "redeemable": [r for r in REWARDS if r["points"] <= pts],
            "next_reward": nxt and {**nxt, "points_needed": nxt["points"] - pts}}


def submit_feedback(customer_id: str, message: str, order_id: str | None = None, type: str = "feedback") -> dict:
    """Log feedback or a complaint ('feedback' | 'complaint') and return a ticket id."""
    if customer_id not in CUSTOMERS:
        return {"error": "unknown customer"}
    if type not in ("feedback", "complaint"):
        return {"error": "type must be 'feedback' or 'complaint'"}
    tid = f"TKT-{next(ticket_ids)}"
    FEEDBACK[tid] = {"customer_id": customer_id, "message": message, "order_id": order_id, "type": type}
    return {"ticket_id": tid, "type": type, "order_id": order_id, "status": "logged"}


def register(mcp) -> None:
    for fn in (get_loyalty_account, get_rewards, submit_feedback):
        mcp.tool()(fn)
