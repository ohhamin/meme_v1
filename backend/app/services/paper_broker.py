import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from backend.app.core.config import get_settings
from backend.app.models.schemas import (
    MarketInstrumentSnapshot,
    PaperOrderExecution,
    PaperPortfolio,
    PaperPosition,
)
from backend.app.services.audit import AuditLogger
from backend.app.services.push import PushService


class PaperBroker:
    """Local JSON-backed paper broker.

    Prices come from the supplied market snapshot.
    No external broker API is called.
    """

    def __init__(self):
        self.config = get_settings()
        self.tz = ZoneInfo(self.config.app_timezone)
        self.path: Path = self.config.data_path / "state" / "paper_portfolio.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.audit = AuditLogger()
        self.push = PushService()

    def reset(self, initial_cash: Decimal | None = None) -> PaperPortfolio:
        cash = initial_cash or Decimal(str(self.config.paper_initial_cash_krw))
        if cash <= 0:
            raise ValueError("initial_cash must be positive")

        today = datetime.now(self.tz).date().isoformat()
        state = {
            "date": today,
            "cash": str(cash),
            "initial_cash": str(cash),
            "day_start_equity": str(cash),
            "daily_order_count": 0,
            "positions": {},
        }
        self._write(state)
        self.audit.write(
            "system",
            {
                "event": "paper_portfolio_reset",
                "initial_cash": str(cash),
            },
        )
        return self.portfolio()

    def update_prices(
        self,
        instruments: list[MarketInstrumentSnapshot],
    ) -> None:
        state = self._load()
        positions = state["positions"]

        for instrument in instruments:
            key = self._key(instrument.market, instrument.symbol)
            if key in positions:
                positions[key]["last_price"] = str(instrument.price)
                positions[key]["last_price_at"] = datetime.now(self.tz).isoformat()
                positions[key]["last_market_open"] = instrument.market_open
                if instrument.name:
                    positions[key]["name"] = instrument.name

        self._write(state)

    def portfolio(self) -> PaperPortfolio:
        state = self._load()
        self._roll_day_if_needed(state)

        positions: list[PaperPosition] = []
        market_value_total = Decimal("0")
        realized_total = Decimal("0")

        for raw in state["positions"].values():
            quantity = Decimal(raw["quantity"])
            average_price = Decimal(raw["average_price"])
            last_price = Decimal(raw["last_price"])
            realized_pnl = Decimal(raw.get("realized_pnl", "0"))

            invested = quantity * average_price
            market_value = quantity * last_price
            market_value_total += market_value
            realized_total += realized_pnl

            if average_price > 0:
                return_rate = (
                    (last_price - average_price) / average_price
                ) * Decimal("100")
            else:
                return_rate = Decimal("0")

            last_price_at = None
            raw_last_price_at = raw.get("last_price_at")
            if raw_last_price_at:
                try:
                    last_price_at = datetime.fromisoformat(raw_last_price_at)
                except ValueError:
                    last_price_at = None

            positions.append(
                PaperPosition(
                    market=raw["market"],
                    symbol=raw["symbol"],
                    name=raw.get("name") or raw["symbol"],
                    quantity=quantity,
                    average_price=average_price,
                    last_price=last_price,
                    last_price_at=last_price_at,
                    last_market_open=bool(raw.get("last_market_open", True)),
                    invested_amount=invested,
                    market_value=market_value,
                    return_rate=return_rate,
                    realized_pnl=realized_pnl,
                    decision_score=raw.get("decision_score"),
                )
            )

        cash = Decimal(state["cash"])
        equity = cash + market_value_total
        day_start_equity = Decimal(state["day_start_equity"])
        daily_pnl = equity - day_start_equity

        daily_pnl_pct = (
            daily_pnl / day_start_equity * Decimal("100")
            if day_start_equity > 0
            else Decimal("0")
        )

        return PaperPortfolio(
            date=state["date"],
            cash=cash,
            initial_cash=Decimal(state["initial_cash"]),
            day_start_equity=day_start_equity,
            equity=max(equity, Decimal("0.00000001")),
            daily_pnl=daily_pnl,
            daily_pnl_pct=daily_pnl_pct,
            daily_order_count=int(state["daily_order_count"]),
            positions=sorted(
                positions,
                key=lambda p: (p.market, p.symbol),
            ),
        )

    def account_snapshot(self) -> dict:
        portfolio = self.portfolio()
        return {
            "mode": "paper",
            "date": portfolio.date,
            "cash": str(portfolio.cash),
            "equity": str(portfolio.equity),
            "daily_pnl": str(portfolio.daily_pnl),
            "daily_pnl_pct": str(portfolio.daily_pnl_pct),
            "daily_order_count": portfolio.daily_order_count,
            "positions": [
                {
                    "market": p.market,
                    "symbol": p.symbol,
                    "name": p.name,
                    "quantity": str(p.quantity),
                    "average_price": str(p.average_price),
                    "last_price": str(p.last_price),
                    "last_price_at": p.last_price_at.isoformat() if p.last_price_at else None,
                    "market_open": p.last_market_open,
                    "market_value": str(p.market_value),
                    "return_rate": str(p.return_rate),
                    "decision_score": p.decision_score,
                }
                for p in portfolio.positions
            ],
        }

    def market_exposure_value(self, market: str) -> Decimal:
        return sum(
            (
                p.market_value
                for p in self.portfolio().positions
                if p.market == market
            ),
            Decimal("0"),
        )

    def position(self, market: str, symbol: str) -> PaperPosition | None:
        return next(
            (
                p
                for p in self.portfolio().positions
                if p.market == market and p.symbol == symbol
            ),
            None,
        )

    def execute(
        self,
        *,
        market: str,
        symbol: str,
        name: str | None,
        side: str,
        quantity: Decimal,
        market_price: Decimal,
        decision_score: int | None = None,
    ) -> PaperOrderExecution:
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        if market_price <= 0:
            raise ValueError("market_price must be positive")
        if side not in {"buy", "sell"}:
            raise ValueError("side must be buy or sell")

        state = self._load()
        self._roll_day_if_needed(state)
        key = self._key(market, symbol)
        positions = state["positions"]

        slippage = Decimal(str(self.config.paper_slippage_bps)) / Decimal("10000")
        fill_price = (
            market_price * (Decimal("1") + slippage)
            if side == "buy"
            else market_price * (Decimal("1") - slippage)
        )
        notional = fill_price * quantity
        fee = (
            notional
            * Decimal(str(self.config.paper_fee_bps))
            / Decimal("10000")
        )

        cash = Decimal(state["cash"])
        existing = positions.get(key)

        if side == "buy":
            total_cost = notional + fee
            if total_cost > cash:
                raise ValueError("insufficient paper cash")

            if existing:
                old_qty = Decimal(existing["quantity"])
                old_avg = Decimal(existing["average_price"])
                new_qty = old_qty + quantity
                new_avg = (
                    (old_qty * old_avg) + (quantity * fill_price) + fee
                ) / new_qty
                existing["quantity"] = str(new_qty)
                existing["average_price"] = str(new_avg)
                existing["last_price"] = str(fill_price)
                existing["last_price_at"] = datetime.now(self.tz).isoformat()
                existing["name"] = name or existing.get("name") or symbol
                existing["decision_score"] = decision_score
            else:
                positions[key] = {
                    "market": market,
                    "symbol": symbol,
                    "name": name or symbol,
                    "quantity": str(quantity),
                    "average_price": str((notional + fee) / quantity),
                    "last_price": str(fill_price),
                    "last_price_at": datetime.now(self.tz).isoformat(),
                    "last_market_open": True,
                    "realized_pnl": "0",
                    "decision_score": decision_score,
                }

            state["cash"] = str(cash - total_cost)

        else:
            if not existing:
                raise ValueError("paper position not found")

            old_qty = Decimal(existing["quantity"])
            if quantity > old_qty:
                raise ValueError("sell quantity exceeds paper position")

            old_avg = Decimal(existing["average_price"])
            realized = Decimal(existing.get("realized_pnl", "0"))
            realized += ((fill_price - old_avg) * quantity) - fee

            remaining = old_qty - quantity
            state["cash"] = str(cash + notional - fee)

            if remaining <= 0:
                del positions[key]
            else:
                existing["quantity"] = str(remaining)
                existing["last_price"] = str(fill_price)
                existing["last_price_at"] = datetime.now(self.tz).isoformat()
                existing["realized_pnl"] = str(realized)
                existing["decision_score"] = decision_score

        state["daily_order_count"] = int(state["daily_order_count"]) + 1
        self._write(state)

        execution = PaperOrderExecution(
            order_id=f"paper-{uuid4().hex[:12]}",
            market=market,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=fill_price,
            notional=notional,
            fee=fee,
            status="paper_filled",
            created_at=datetime.now(self.tz),
        )

        self.audit.write(
            "orders",
            {
                "source": "auto",
                "mode": "paper",
                **execution.model_dump(mode="json"),
            },
        )
        self.push.send(
            title="Paper 자동 주문",
            body=f"{symbol} {side.upper()} {quantity}",
            data={
                "type": "paper_auto_order",
                "symbol": symbol,
                "side": side,
                "order_id": execution.order_id,
            },
        )
        return execution

    def _load(self) -> dict:
        if not self.path.exists():
            self.reset()

        try:
            state = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            self.reset()
            state = json.loads(self.path.read_text(encoding="utf-8"))

        self._roll_day_if_needed(state)
        return state

    def _roll_day_if_needed(self, state: dict) -> None:
        today = datetime.now(self.tz).date().isoformat()
        if state.get("date") == today:
            return

        # Mark-to-market equity at the start of a new local day.
        cash = Decimal(state["cash"])
        market_value = sum(
            (
                Decimal(raw["quantity"]) * Decimal(raw["last_price"])
                for raw in state["positions"].values()
            ),
            Decimal("0"),
        )
        state["date"] = today
        state["day_start_equity"] = str(cash + market_value)
        state["daily_order_count"] = 0
        self._write(state)

    def _write(self, state: dict) -> None:
        temp = self.path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp.replace(self.path)

    @staticmethod
    def _key(market: str, symbol: str) -> str:
        return f"{market}:{symbol}"
