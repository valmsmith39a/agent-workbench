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


class Restriction(BaseModel):
    code: str
    symbol: str | None  # None means it applies to the whole account
    description: str
    resolution: str  # what the customer can do about it


class ProposedOrder(BaseModel):
    """An order the customer wants to place, priced with an indicative quote."""

    symbol: str
    side: OrderSide
    quantity: int
    estimated_price: float
    estimated_cost: float


class BlockingReason(BaseModel):
    code: str  # e.g. INSUFFICIENT_BUYING_POWER, UNSETTLED_FUNDS, ACCOUNT_RESTRICTION
    message: str


class AccountRestrictionsResult(BaseModel):
    account_id: str
    account_type: str  # CASH or MARGIN
    buying_power: float
    unsettled_funds: float
    unsettled_settlement_date: date | None
    restrictions: list[Restriction]
    proposed_order: ProposedOrder | None  # set when a specific order was checked
    can_place_order: bool | None  # None when no specific order was checked
    blocking_reasons: list[BlockingReason]
