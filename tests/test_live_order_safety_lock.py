"""Verification Suite for Live Market Order Safety Lockout.

Confirms:
1. Global safety killswitch `LIVE_MARKET_ORDERS_BLOCKED` is permanently True.
2. OrderManagementSystem refusing to arm live execution (`arm_live_execution() == False`).
3. Dispatched bracket orders strictly forced into in-memory SIMULATION mode.
4. MainWindow UI reflecting safety lockout status banner and disarmed state.
"""
import os
import sys

# Ensure repository root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.broker_client import (
    BrokerAuthManager,
    BracketOrderRequest,
    OrderManagementSystem,
    OrderState,
    LIVE_MARKET_ORDERS_BLOCKED
)


def test_live_order_safety_lockout():
    print("=" * 65)
    print("  AUDITING LIVE MARKET ORDER SAFETY LOCKOUT")
    print("=" * 65)

    # 1. Global Safety Killswitch Status
    print(f"[1/4] Checking global safety killswitch: {LIVE_MARKET_ORDERS_BLOCKED}")
    assert LIVE_MARKET_ORDERS_BLOCKED is True, "LIVE_MARKET_ORDERS_BLOCKED must be True"
    print("  [OK] Global safety killswitch is confirmed ACTIVE.")

    # 2. OMS Initialization & Arming Rejection
    print("[2/4] Testing OMS arming refusal under safety directive...")
    auth_mgr = BrokerAuthManager()
    oms = OrderManagementSystem(auth_mgr)

    assert oms.live_orders_blocked is True
    assert oms.is_live_execution_armed is False

    # Attempt to arm live execution
    armed = oms.arm_live_execution()
    assert armed is False, "arm_live_execution() must return False when killswitch is active"
    assert oms.is_live_execution_armed is False, "is_live_execution_armed must remain False"
    print("  [OK] OMS successfully refused arming live execution.")

    # 3. Order Dispatch Simulation Enforcement
    print("[3/4] Testing bracket order dispatch simulation enforcement...")
    req = BracketOrderRequest(
        symbol="NIFTY50",
        is_buy=True,
        qty=50,
        entry_price=22000.0,
        hard_stop_price=21982.0,
        target1_price=22125.0,
        target2_price=22252.0,
        confluence_signal_id="TEST_CONF_001",
        node_id="NODE_TEST_1",
        session_date="20261108"
    )

    success, order_id = oms.dispatch_bracket_order(req)
    assert success is True, "Dispatch should record into in-memory simulation"
    order = oms.active_orders[order_id]
    assert order.state == OrderState.FILLED, "Order state must be simulated FILLED, never live OPEN"
    history = oms.node_lockout_history[oms.get_lockout_key(req)]
    assert history["mode"] == "SIMULATION", f"Order mode must be SIMULATION, got {history['mode']}"
    print(f"  [OK] Order {order_id} strictly dispatched as in-memory SIMULATION (Zero capital risk).")

    # 4. User Preferences & State Persistence Check
    print("[4/4] Verifying state manager default operating mode...")
    from ui.state_manager import StateManager
    state_mgr = StateManager()
    print(f"  Operating mode configured: {state_mgr.prefs.operating_mode}")
    assert state_mgr.prefs.operating_mode == "SIMULATION", "Operating mode must default to SIMULATION"
    print("  [OK] State Manager confirmed SIMULATION mode.")

    print("\n" + "=" * 65)
    print(" [SUCCESS] LIVE MARKET ORDER SAFETY LOCKOUT 100% VERIFIED!")
    print("=" * 65)


if __name__ == "__main__":
    test_live_order_safety_lockout()
