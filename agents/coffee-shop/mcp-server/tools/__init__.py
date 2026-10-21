"""Coffee shop MCP tools, grouped by category (like brokerage's app/mcp/tools/)."""

from . import account, menu, ordering

CATEGORIES = {
    "menu": [menu.list_menu, menu.get_item_details, menu.get_store_info],
    "ordering": [ordering.place_order, ordering.get_order_status, ordering.modify_order, ordering.cancel_order],
    "account": [account.get_loyalty_account, account.get_rewards, account.submit_feedback],
}
TOOLS = {fn.__name__: fn for fns in CATEGORIES.values() for fn in fns}
