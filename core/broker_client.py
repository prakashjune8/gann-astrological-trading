"""Phase 2 Scaffolding: Live Broker Bridge & WebSocket Architecture.

Foundational architectural blueprint for low-latency Indian broker integration:
1. BrokerAuthManager: Authentication, API token lifecycle, session persistence (Zerodha Kite / Angel One SmartAPI).
2. WebSocketDataPump: Low-latency streaming tick receiver with strict bullion exclusion barriers.
3. OrderManagementSystem (OMS): Institutional order lifecycle state machine & pre-trade risk controls.
4. BracketOrderDispatcher: OCO bracket order submission with 18-point hard stop and multi-tier profit targets.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Dict, List, Optional, Set

from core.backtest_data import BULLION_BLACKLIST

logger = logging.getLogger("broker_client")


# ==============================================================================
# 1. BROKER STATE & EVENT DATA STRUCTURES
# ==============================================================================

class BrokerType(Enum):
    ZERODHA_KITE = "ZERODHA_KITE"
    ANGEL_ONE = "ANGEL_ONE"
    SIMULATED = "SIMULATED"


class OrderState(Enum):
    PENDING_SUBMIT = "PENDING_SUBMIT"
    OPEN = "OPEN"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class OrderType(Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP_LOSS_MARKET = "SL-M"
    STOP_LOSS_LIMIT = "SL-L"


@dataclass(frozen=True)
class LiveTick:
    """Real-time market quote tick emitted by broker WebSocket data pump."""
    instrument_token: int
    symbol: str
    timestamp: datetime
    last_price: float
    volume: int
    open: float
    high: float
    low: float
    close: float
    bid_price: float = 0.0
    ask_price: float = 0.0
    open_interest: int = 0


@dataclass
class BrokerOrder:
    """Live broker order lifecycle tracker."""
    order_id: str
    client_order_id: str
    symbol: str
    order_type: OrderType
    is_buy: bool
    qty: int
    price: float
    trigger_price: float = 0.0
    state: OrderState = OrderState.PENDING_SUBMIT
    filled_qty: int = 0
    avg_fill_price: float = 0.0
    rejection_reason: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class BracketOrderRequest:
    """Specification for atomic One-Cancels-Other (OCO) Triple Confluence trade execution."""
    symbol: str
    is_buy: bool
    qty: int
    entry_price: float
    hard_stop_price: float
    target1_price: float
    target2_price: float
    confluence_signal_id: str
    tag: str = "GANN_CONFLUENCE_RADAR"


# ==============================================================================
# 2. BROKER AUTHENTICATION MANAGER (PHASE 2 SCAFFOLDING)
# ==============================================================================

class BrokerAuthManager:
    """Manages secure credentials, TOTP generation, access token refreshes, and session persistence."""

    def __init__(self, broker: BrokerType = BrokerType.ZERODHA_KITE):
        self.broker = broker
        self.api_key: Optional[str] = None
        self.access_token: Optional[str] = None
        self.is_authenticated: bool = False

    def configure_credentials(self, api_key: str, api_secret: str, totp_secret: Optional[str] = None) -> None:
        """Configures API credentials for the target brokerage."""
        self.api_key = api_key
        logger.info(f"Configured credentials for {self.broker.value} (API Key: {api_key[:4]}****)")

    def authenticate_session(self, request_token: str) -> bool:
        """Phase 2 Stub: Exchanges request token for active 24-hour access token."""
        # Foundational authentication stub
        self.access_token = f"TOKEN_{self.broker.value}_{datetime.now().strftime('%Y%m%d')}"
        self.is_authenticated = True
        logger.info(f"Authenticated session for {self.broker.value}. Token generated.")
        return True


# ==============================================================================
# 3. WEBSOCKET DATA PUMP (PHASE 2 SCAFFOLDING)
# ==============================================================================

class WebSocketDataPump(ABC):
    """Abstract high-frequency WebSocket data client for streaming market ticks."""

    def __init__(self, auth_mgr: BrokerAuthManager):
        self.auth_mgr = auth_mgr
        self.is_connected: bool = False
        self.subscribed_symbols: Set[str] = set()
        self._listeners: List[Callable[[LiveTick], None]] = []

    def subscribe(self, symbols: List[str]) -> None:
        """Registers symbols for streaming ticks, enforcing strict zero bullion protection."""
        for sym in symbols:
            clean = sym.strip().upper()
            for b in BULLION_BLACKLIST:
                if b in clean:
                    raise ValueError(
                        f"CRITICAL REJECTION: Symbol '{sym}' matches blacklisted bullion token '{b}'. "
                        "Gold and Silver feeds are strictly prohibited by system mandate."
                    )
            self.subscribed_symbols.add(clean)

        logger.info(f"Subscribed {len(symbols)} instruments to WebSocket data pump.")

    def add_tick_listener(self, callback: Callable[[LiveTick], None]) -> None:
        """Registers a callback to receive incoming live market ticks."""
        self._listeners.append(callback)

    def _dispatch_tick(self, tick: LiveTick) -> None:
        """Dispatches an incoming tick to all registered listeners."""
        for cb in self._listeners:
            try:
                cb(tick)
            except Exception as e:
                logger.error(f"Error in tick listener: {e}")

    @abstractmethod
    def connect(self) -> None:
        """Initiates persistent WebSocket connection."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Safely closes WebSocket connection."""
        pass


class KiteWebSocketDataPump(WebSocketDataPump):
    """Zerodha Kite Connect WebSocket binary tick protocol client (Phase 2 Stub)."""

    def connect(self) -> None:
        self.is_connected = True
        logger.info("Connected to Zerodha Kite WebSocket tick stream (Phase 2 Stub).")

    def disconnect(self) -> None:
        self.is_connected = False
        logger.info("Disconnected from Zerodha Kite WebSocket.")


# ==============================================================================
# 4. ORDER MANAGEMENT SYSTEM (OMS) & BRACKET DISPATCHER
# ==============================================================================

class OrderManagementSystem:
    """Pre-trade risk gateway, order tracking state machine, and broker order router."""

    def __init__(self, auth_mgr: BrokerAuthManager):
        self.auth_mgr = auth_mgr
        self.active_orders: Dict[str, BrokerOrder] = {}
        self.max_order_qty: int = 500  # Max 10 lots Nifty
        self.max_slippage_pts: float = 3.0

    def validate_pre_trade_risk(self, req: BracketOrderRequest) -> bool:
        """Pre-trade compliance check (sizing, bullion exclusion, risk limit)."""
        # 1. Bullion check
        clean = req.symbol.strip().upper()
        for b in BULLION_BLACKLIST:
            if b in clean:
                raise ValueError(f"OMS REJECTION: Bullion symbol '{req.symbol}' is forbidden.")

        # 2. Sizing check
        if req.qty <= 0 or req.qty > self.max_order_qty:
            logger.warning(f"OMS REJECTION: Order quantity {req.qty} exceeds limit {self.max_order_qty}")
            return False

        # 3. Stop loss tightness check (Must be >= 15 pts and <= 25 pts)
        stop_dist = abs(req.entry_price - req.hard_stop_price)
        if stop_dist < 15.0 or stop_dist > 25.0:
            logger.warning(f"OMS WARNING: Stop distance {stop_dist:.1f}pts deviates from 18.0pt Gann baseline")

        return True

    def dispatch_bracket_order(self, req: BracketOrderRequest) -> Tuple[bool, str]:
        """Dispatches an atomic OCO bracket order to the broker (Phase 2 Stub)."""
        if not self.validate_pre_trade_risk(req):
            return False, "Pre-trade risk check failed."

        order_id = f"ORD_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self.active_orders)+1:03d}"
        broker_order = BrokerOrder(
            order_id=order_id,
            client_order_id=f"CL_{req.confluence_signal_id}",
            symbol=req.symbol,
            order_type=OrderType.LIMIT,
            is_buy=req.is_buy,
            qty=req.qty,
            price=req.entry_price,
            state=OrderState.OPEN
        )
        self.active_orders[order_id] = broker_order
        logger.info(
            f"OMS DISPATCH SUCCESS: Bracket Order {order_id} ({req.symbol} Qty={req.qty} "
            f"Entry={req.entry_price} Stop={req.hard_stop_price} T1={req.target1_price} T2={req.target2_price})"
        )
        return True, order_id
