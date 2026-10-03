"""The shapes of the brokerage data the agent will work with.

These Pydantic models are the contract between the data layer and everything
built on top of it (MCP tools, the agent, the UI). A real brokerage API would
be mapped onto these same shapes.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    FILLED = "FILLED"
    PENDING = "PENDING"
    REJECTED = "REJECTED"


class Order(BaseModel):
    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    status: OrderStatus
    filled_quantity: int
    average_fill_price: float | None = None  # only set once shares have filled
    submitted_at: datetime
    status_reason: str | None = None  # why an order is pending or rejected


class TradeStatusResult(BaseModel):
    account_id: str
    symbol: str | None  # the filter that was applied, if any
    orders: list[Order]
