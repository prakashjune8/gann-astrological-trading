"""Unit tests for core/broker_client.py (Phase 2 Scaffolding).

Verifies:
1. BrokerAuthManager credential handling and token lifecycle.
2. WebSocketDataPump strict bullion exclusion protection.
3. OrderManagementSystem (OMS) pre-trade risk controls and OCO bracket dispatch.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.broker_client import (
    BracketOrderRequest,
    BrokerAuthManager,
    BrokerType,
    KiteWebSocketDataPump,
    LiveTick,
    OrderManagementSystem,
    OrderState,
    OrderType,
)


def test_broker_auth_manager():
    print("[1/3] Testing BrokerAuthManager...")
    auth = BrokerAuthManager(broker=BrokerType.ZERODHA_KITE)
    auth.configure_credentials(api_key="kite_test_api_key_1234", api_secret="kite_test_secret_5678")
    assert auth.api_key == "kite_test_api_key_1234"
    assert not auth.is_authenticated

    success = auth.authenticate_session(request_token="dummy_request_token_abc")
    assert success
    assert auth.is_authenticated
    assert auth.access_token is not None
    print(f"      Passed. Authenticated {auth.broker.value} session with active token.")


def test_websocket_data_pump_bullion_barrier():
    print("[2/3] Testing WebSocketDataPump & Bullion Barrier...")
    auth = BrokerAuthManager()
    auth.authenticate_session("token")
    pump = KiteWebSocketDataPump(auth_mgr=auth)

    # Allowed instruments
    pump.subscribe(["NIFTY50", "BANKNIFTY", "CRUDEOIL", "NATURALGAS", "COPPER"])
    assert len(pump.subscribed_symbols) == 5

    # Strictly forbidden bullion symbols
    for bullion_sym in ["GOLD", "SILVERBEES", "XAUUSD", "GC=F"]:
        try:
            pump.subscribe([bullion_sym])
            assert False, f"Expected bullion rejection for {bullion_sym}"
        except ValueError:
            pass

    # Tick listener callback test
    ticks_received = []
    pump.add_tick_listener(lambda t: ticks_received.append(t))

    tick = LiveTick(
        instrument_token=256265,
        symbol="NIFTY50",
        timestamp=datetime.now(),
        last_price=24250.0,
        volume=15000,
        open=24200.0,
        high=24275.0,
        low=24190.0,
        close=24250.0
    )
    pump._dispatch_tick(tick)
    assert len(ticks_received) == 1
    assert ticks_received[0].last_price == 24250.0
    print("      Passed. Absolute bullion rejection verified on WebSocket subscriptions.")


def test_oms_and_bracket_order_dispatch():
    print("[3/3] Testing OrderManagementSystem & Bracket Dispatch...")
    auth = BrokerAuthManager()
    oms = OrderManagementSystem(auth_mgr=auth)

    # 1. Valid Triple Confluence Bracket Request (18-pt hard stop, multi-target)
    valid_req = BracketOrderRequest(
        symbol="NIFTY50",
        is_buy=True,
        qty=50,  # 1 lot
        entry_price=24200.0,
        hard_stop_price=24182.0,  # 18 pts
        target1_price=24325.0,    # +125 pts
        target2_price=24452.0,    # +252 pts
        confluence_signal_id="CONF_NIFTY_20240115_1222"
    )

    success, order_id = oms.dispatch_bracket_order(valid_req)
    assert success
    assert order_id in oms.active_orders
    order = oms.active_orders[order_id]
    assert order.state == OrderState.OPEN
    assert order.qty == 50

    # 2. Bullion rejection in OMS
    bullion_req = BracketOrderRequest(
        symbol="GOLDMINI",
        is_buy=True,
        qty=1,
        entry_price=75000.0,
        hard_stop_price=74800.0,
        target1_price=75500.0,
        target2_price=76000.0,
        confluence_signal_id="CONF_GOLD_FAIL"
    )
    try:
        oms.dispatch_bracket_order(bullion_req)
        assert False, "OMS must strictly reject bullion orders"
    except ValueError:
        pass

    # 3. Oversized order rejection
    oversized_req = BracketOrderRequest(
        symbol="NIFTY50",
        is_buy=True,
        qty=1000,  # Exceeds max 500
        entry_price=24200.0,
        hard_stop_price=24182.0,
        target1_price=24325.0,
        target2_price=24452.0,
        confluence_signal_id="CONF_OVERSIZE"
    )
    ok, msg = oms.dispatch_bracket_order(oversized_req)
    assert not ok, "Oversized order must be rejected"
    print(f"      Passed. Bracket order {order_id} created with valid 18pt risk check.")


if __name__ == "__main__":
    print("=================================================================")
    print("RUNNING LIVE BROKER BRIDGE & OMS TEST SUITE (PHASE 2 SCAFFOLDING)")
    print("=================================================================")
    test_broker_auth_manager()
    test_websocket_data_pump_bullion_barrier()
    test_oms_and_bracket_order_dispatch()
    print("=================================================================")
    print("ALL 3 BROKER BRIDGE TESTS DETERMINISTICALLY PASSED")
    print("=================================================================")
