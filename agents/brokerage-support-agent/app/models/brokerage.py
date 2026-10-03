"""Structured brokerage records returned by the service layer and MCP tools.

These models are the agent-facing contract. A real brokerage integration
should map its own API responses onto these shapes so the tools, prompts and
UI keep working unchanged.
"""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    PENDING = "PENDING"
    REJECTED = "REJECTED"
    CANCELED = "CANCELED"


class TransferDirection(str, Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"


class TransferStatus(str, Enum):
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Order(BaseModel):
    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    order_type: str  # MARKET or LIMIT
    limit_price: float | None = None
    status: OrderStatus
    filled_quantity: int
    average_fill_price: float | None = None
    submitted_at: datetime
    updated_at: datetime
    status_reason_code: str | None = None
    status_explanation: str


class TradeStatusResult(BaseModel):
    account_id: str
    filters: dict[str, str]
    match_count: int
    orders: list[Order]
    message: str | None = None


class Transfer(BaseModel):
    transfer_id: str
    amount: float
    direction: TransferDirection
    method: str  # ACH, WIRE
    external_account: str
    status: TransferStatus
    initiated_date: date
    expected_available_date: date | None = None
    completed_date: date | None = None
    failure_reason: str | None = None
    status_explanation: str


class TransferStatusResult(BaseModel):
    account_id: str
    filters: dict[str, str]
    match_count: int
    transfers: list[Transfer]
    message: str | None = None


class Restriction(BaseModel):
    code: str
    description: str
    blocks: list[OrderSide]
    resolution: str


class BlockingReason(BaseModel):
    code: str
    message: str


class ProposedOrderCheck(BaseModel):
    source: str  # CUSTOMER_REQUEST or MOST_RECENT_REJECTED_ORDER
    order_id: str | None = None
    symbol: str
    side: OrderSide
    quantity: int
    estimated_price: float
    estimated_cost: float


class AccountRestrictionsResult(BaseModel):
    account_id: str
    account_type: str  # CASH or MARGIN
    as_of: date
    buying_power: float
    settled_cash: float
    unsettled_funds: float
    unsettled_settlement_date: date | None = None
    restrictions: list[Restriction]
    proposed_order: ProposedOrderCheck | None = None
    can_trade: bool
    blocking_reasons: list[BlockingReason]
    notes: list[str]
