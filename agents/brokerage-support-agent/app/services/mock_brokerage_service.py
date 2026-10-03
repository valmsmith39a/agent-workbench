"""In-memory brokerage backed by the fixtures in mock_data.py.

Besides looking records up, this layer owns everything deterministic:
input validation, status explanations, and the pre-trade checks that decide
whether an order can be placed. The LLM only phrases what comes back.
"""

import re

from app.models.brokerage import (
    AccountRestrictionsResult,
    BlockingReason,
    Order,
    OrderSide,
    OrderStatus,
    ProposedOrderCheck,
    Restriction,
    TradeStatusResult,
    Transfer,
    TransferDirection,
    TransferStatus,
    TransferStatusResult,
)
from app.services import mock_data
from app.services.brokerage_service import AccountNotFoundError, InvalidRequestError

SYMBOL_RE = re.compile(r"^[A-Z]{1,5}$")
ORDER_ID_RE = re.compile(r"^ORD-[A-Z0-9]{4}-\d{4}$")
TRANSFER_ID_RE = re.compile(r"^TRF-[A-Z0-9]{4}-\d{4}$")

REASON_TEXT = {
    "INSUFFICIENT_BUYING_POWER": "the estimated cost exceeded your available buying power",
    "INSUFFICIENT_SETTLED_FUNDS": (
        "your cash account did not have enough settled funds; proceeds from recent "
        "sales were still unsettled"
    ),
    "ACCOUNT_RESTRICTED": "your account has a restriction that blocks this type of order",
    "LIMIT_PRICE_NOT_REACHED": "the market has not reached your limit price yet",
}


def _money(value: float) -> str:
    return f"${value:,.2f}"


class MockBrokerageService:
    def __init__(
        self,
        accounts=mock_data.ACCOUNTS,
        orders=mock_data.ORDERS,
        transfers=mock_data.TRANSFERS,
        quotes=mock_data.QUOTES,
        as_of=mock_data.AS_OF,
    ):
        self._accounts = accounts
        self._orders = orders
        self._transfers = transfers
        self._quotes = quotes
        self._as_of = as_of

    # -- trades ---------------------------------------------------------------

    def get_trade_status(self, account_id, symbol=None, order_id=None):
        self._require_account(account_id)
        filters = {}
        if symbol:
            symbol = self._clean_symbol(symbol)
            filters["symbol"] = symbol
        if order_id:
            order_id = order_id.strip().upper()
            if not ORDER_ID_RE.match(order_id):
                raise InvalidRequestError(f"'{order_id}' is not a valid order ID (expected ORD-XXXX-0000).")
            filters["order_id"] = order_id

        orders = []
        for raw in self._orders.get(account_id, []):
            if symbol and raw["symbol"] != symbol:
                continue
            if order_id and raw["order_id"] != order_id:
                continue
            orders.append(Order(**raw, status_explanation=self._explain_order(raw)))

        message = None
        if not orders:
            message = "No orders match these filters." if filters else "No recent orders on this account."
        return TradeStatusResult(
            account_id=account_id, filters=filters, match_count=len(orders), orders=orders, message=message
        )

    @staticmethod
    def _explain_order(o):
        what = f"{o['side'].lower()} order for {o['quantity']} shares of {o['symbol']} ({o['order_id']})"
        reason = REASON_TEXT.get(o.get("status_reason_code"), "")
        status = OrderStatus(o["status"])
        if status == OrderStatus.FILLED:
            return f"Your {what} filled completely at an average price of {_money(o['average_fill_price'])}."
        if status == OrderStatus.PARTIALLY_FILLED:
            remaining = o["quantity"] - o["filled_quantity"]
            return (
                f"Your {what} is partially filled: {o['filled_quantity']} shares at an average of "
                f"{_money(o['average_fill_price'])}. The remaining {remaining} shares are still open "
                f"because {reason}."
            )
        if status == OrderStatus.PENDING:
            limit = f" (limit {_money(o['limit_price'])})" if o.get("limit_price") else ""
            return f"Your {what}{limit} is open and has not filled yet because {reason}."
        if status == OrderStatus.REJECTED:
            return f"Your {what} was rejected and did not execute because {reason}."
        return f"Your {what} was canceled."

    # -- transfers ------------------------------------------------------------

    def get_transfer_status(self, account_id, transfer_id=None, amount=None, direction=None):
        self._require_account(account_id)
        filters = {}
        if transfer_id:
            transfer_id = transfer_id.strip().upper()
            if not TRANSFER_ID_RE.match(transfer_id):
                raise InvalidRequestError(f"'{transfer_id}' is not a valid transfer ID (expected TRF-XXXX-0000).")
            filters["transfer_id"] = transfer_id
        if amount is not None:
            if amount <= 0:
                raise InvalidRequestError("Transfer amount must be greater than zero.")
            filters["amount"] = f"{amount:.2f}"
        if direction:
            try:
                direction = TransferDirection(direction.strip().upper()).value
            except ValueError:
                raise InvalidRequestError("Direction must be DEPOSIT or WITHDRAWAL.") from None
            filters["direction"] = direction

        transfers = []
        for raw in self._transfers.get(account_id, []):
            if transfer_id and raw["transfer_id"] != transfer_id:
                continue
            if amount is not None and abs(raw["amount"] - amount) >= 0.005:
                continue
            if direction and raw["direction"] != direction:
                continue
            transfers.append(Transfer(**raw, status_explanation=self._explain_transfer(raw)))

        message = None
        if not transfers:
            message = "No transfers match these filters." if filters else "No recent transfers on this account."
        return TransferStatusResult(
            account_id=account_id, filters=filters, match_count=len(transfers), transfers=transfers, message=message
        )

    @staticmethod
    def _explain_transfer(t):
        preposition = "from" if t["direction"] == "DEPOSIT" else "to"
        what = (
            f"{_money(t['amount'])} {t['method']} {t['direction'].lower()} {preposition} "
            f"{t['external_account']} ({t['transfer_id']}), initiated {t['initiated_date']},"
        )
        status = TransferStatus(t["status"])
        if status == TransferStatus.COMPLETED:
            return f"Your {what} completed on {t['completed_date']}."
        if status == TransferStatus.PROCESSING:
            return f"Your {what} is still processing. Funds are expected to be available on {t['expected_available_date']}."
        return f"Your {what} failed. {t['failure_reason']}"

    # -- restrictions / buying power -----------------------------------------

    def get_account_restrictions(self, account_id, symbol=None, side=None, quantity=None):
        acct = self._require_account(account_id)
        restrictions = [Restriction(**r) for r in acct["restrictions"]]
        blocking: list[BlockingReason] = []
        notes: list[str] = []

        if symbol or side or quantity:
            proposed = self._build_proposed_order(symbol, side, quantity)
        else:
            # No order specified: the customer most likely means the order that
            # was just rejected, so re-check that one if there is one.
            proposed = self._most_recent_rejected_order(account_id)

        if proposed is None:
            for r in restrictions:
                blocking.append(BlockingReason(code=r.code, message=r.description))
            notes.append(
                f"Available buying power is {_money(acct['buying_power'])}. Buy orders with an "
                "estimated cost above this amount will be rejected."
            )
            notes.append("Provide a symbol, side and quantity to check a specific order.")
        else:
            if proposed.source == "MOST_RECENT_REJECTED_ORDER":
                notes.append(
                    f"No order was specified, so this checks the most recent rejected order "
                    f"({proposed.order_id}: {proposed.side.value} {proposed.quantity} {proposed.symbol})."
                )
            for r in restrictions:
                if proposed.side in r.blocks:
                    blocking.append(BlockingReason(code=r.code, message=r.description))
            if proposed.side == OrderSide.BUY and proposed.estimated_cost > acct["buying_power"]:
                blocking.append(self._funds_reason(acct, proposed.estimated_cost))
            if proposed.side == OrderSide.SELL:
                held = acct["positions"].get(proposed.symbol, 0)
                if proposed.quantity > held:
                    blocking.append(
                        BlockingReason(
                            code="INSUFFICIENT_SHARES",
                            message=f"You hold {held} shares of {proposed.symbol}, fewer than the {proposed.quantity} you want to sell.",
                        )
                    )

        if acct["unsettled_funds"] > 0:
            notes.append(
                f"{_money(acct['unsettled_funds'])} from recent sales is unsettled and becomes "
                f"available on {acct['unsettled_settlement_date']}."
            )
        if proposed is not None:
            notes.append("Estimated cost uses an indicative quote; the final price is set at execution.")

        return AccountRestrictionsResult(
            account_id=account_id,
            account_type=acct["account_type"],
            as_of=self._as_of,
            buying_power=acct["buying_power"],
            settled_cash=acct["settled_cash"],
            unsettled_funds=acct["unsettled_funds"],
            unsettled_settlement_date=acct["unsettled_settlement_date"],
            restrictions=restrictions,
            proposed_order=proposed,
            can_trade=not blocking,
            blocking_reasons=blocking,
            notes=notes,
        )

    def _most_recent_rejected_order(self, account_id):
        for o in self._orders.get(account_id, []):
            if o["status"] == OrderStatus.REJECTED.value and o["symbol"] in self._quotes:
                check = self._build_proposed_order(o["symbol"], o["side"], o["quantity"])
                return check.model_copy(update={"source": "MOST_RECENT_REJECTED_ORDER", "order_id": o["order_id"]})
        return None

    def _build_proposed_order(self, symbol, side, quantity):
        if not (symbol and side and quantity):
            raise InvalidRequestError("To check a specific order, provide symbol, side and quantity together.")
        symbol = self._clean_symbol(symbol)
        try:
            side = OrderSide(side.strip().upper())
        except ValueError:
            raise InvalidRequestError("Side must be BUY or SELL.") from None
        if not isinstance(quantity, int) or not 0 < quantity <= 1_000_000:
            raise InvalidRequestError("Quantity must be a whole number of shares between 1 and 1,000,000.")
        if symbol not in self._quotes:
            raise InvalidRequestError(f"No quote is available for {symbol}.")
        price = self._quotes[symbol]
        return ProposedOrderCheck(
            source="CUSTOMER_REQUEST",
            symbol=symbol,
            side=side,
            quantity=quantity,
            estimated_price=price,
            estimated_cost=round(price * quantity, 2),
        )

    @staticmethod
    def _funds_reason(acct, cost):
        unsettled = acct["unsettled_funds"]
        if unsettled > 0 and cost <= acct["buying_power"] + unsettled:
            return BlockingReason(
                code="UNSETTLED_FUNDS",
                message=(
                    f"The estimated cost of {_money(cost)} exceeds your settled buying power of "
                    f"{_money(acct['buying_power'])}. {_money(unsettled)} from recent sales settles on "
                    f"{acct['unsettled_settlement_date']}, after which this order would be covered."
                ),
            )
        return BlockingReason(
            code="INSUFFICIENT_BUYING_POWER",
            message=(
                f"The estimated cost of {_money(cost)} exceeds your available buying power of "
                f"{_money(acct['buying_power'])}."
            ),
        )

    # -- helpers --------------------------------------------------------------

    def _require_account(self, account_id):
        acct = self._accounts.get(account_id)
        if acct is None:
            raise AccountNotFoundError(f"Account '{account_id}' was not found.")
        return acct

    @staticmethod
    def _clean_symbol(symbol):
        symbol = symbol.strip().upper().lstrip("$")
        if not SYMBOL_RE.match(symbol):
            raise InvalidRequestError(f"'{symbol}' is not a valid ticker symbol.")
        return symbol
