"""The shapes of the brokerage data the agent will work with.

These Pydantic models are the contract between the data layer and everything
built on top of it (MCP tools, the agent, the UI). A real brokerage API would
be mapped onto these same shapes.
"""

from datetime import date, datetime
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


class TransferDirection(str, Enum):
    DEPOSIT = "DEPOSIT"  # bank -> brokerage
    WITHDRAWAL = "WITHDRAWAL"  # brokerage -> bank


class TransferStatus(str, Enum):
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Transfer(BaseModel):
    transfer_id: str
    amount: float
    direction: TransferDirection
    external_account: str  # the linked bank account, masked
    status: TransferStatus
    initiated_date: date
    expected_available_date: date | None = None  # when the money can be used (not set if failed)
    failure_reason: str | None = None


class TransferStatusResult(BaseModel):
    account_id: str
    amount: float | None  # filters that were applied, if any
    direction: TransferDirection | None
    transfers: list[Transfer]
