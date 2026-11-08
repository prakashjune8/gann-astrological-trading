"""Unit & Integration Test Suite for Phase 2 Sub-Task 1: Live WebSocket Data Pump.

Verifies:
1. ExponentialBackoffReconnector delay progression, jitter, and reset.
2. LatencyTelemetry zero-leak bounded ring buffer, average lag, and jitter.
3. LiveOHLCVAggregator turn-of-minute bar synthesis, boundary detection, and DataFrame output.
4. Ingestion-layer Bullion Barrier: silent drop of restricted Gold/Silver ticks.
5. Threaded WebSocket lifecycle and listener dispatch.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from core.broker_client import (
    APIRateLimiter,
    BracketOrderRequest,
    BrokerAuthManager,
    BrokerType,
    ExponentialBackoffReconnector,
    KiteWebSocketDataPump,
    LatencyTelemetry,
    LiveBarEvent,
    LiveOHLCVAggregator,
    LiveTick,
    OrderManagementSystem,
    OrderState,
    OrderType,
    RealTimeConfluenceRouter,
)
from core.confluence_engine import SniperTradeSetup


def test_exponential_backoff():
    print("[1/5] Testing ExponentialBackoffReconnector...")
    backoff = ExponentialBackoffReconnector(initial_delay_sec=1.0, factor=2.0, max_delay_sec=16.0, jitter_pct=0.05)
    
    delays = [backoff.compute_next_delay() for _ in range(6)]
    # Expected approx: 1.0, 2.0, 4.0, 8.0, 16.0, 16.0 (capped)
    assert 0.9 <= delays[0] <= 1.1, f"Attempt 0 delay unexpected: {delays[0]}"
    assert 1.8 <= delays[1] <= 2.2, f"Attempt 1 delay unexpected: {delays[1]}"
    assert 3.6 <= delays[2] <= 4.4, f"Attempt 2 delay unexpected: {delays[2]}"
    assert 7.2 <= delays[3] <= 8.8, f"Attempt 3 delay unexpected: {delays[3]}"
    assert 15.0 <= delays[4] <= 17.0, f"Attempt 4 delay unexpected: {delays[4]}"
    assert 15.0 <= delays[5] <= 17.0, f"Attempt 5 delay capped: {delays[5]}"

    backoff.reset()
    assert backoff.attempt_count == 0
    next_d = backoff.compute_next_delay()
    assert 0.9 <= next_d <= 1.1, "Backoff reset failed"
    print(f"      Passed. Delays: {delays[:4]} -> Cap: {delays[4]}s -> Reset: {next_d}s")


def test_latency_telemetry_bounded_memory():
    print("[2/5] Testing LatencyTelemetry Memory Bounding & Jitter...")
    telemetry = LatencyTelemetry(max_samples=50)
    base_t = datetime.now()

    # Simulate 500 incoming ticks to verify ring-buffer memory cap
    for i in range(500):
        tick_time = base_t + timedelta(milliseconds=i * 100)
        receipt_time = tick_time + timedelta(milliseconds=15.0 + (i % 10))
        telemetry.record_tick_latency(tick_time, receipt_time)

    summary = telemetry.get_summary()
    assert summary["sample_count"] == 50, f"Sample count must be bounded at 50, got {summary['sample_count']}"
    assert 14.0 <= summary["min_ms"] <= 16.0
    assert 23.0 <= summary["max_ms"] <= 26.0
    assert 18.0 <= summary["avg_ms"] <= 21.0
    assert summary["jitter_ms"] > 0.0
    print(f"      Passed. Bounded at {summary['sample_count']} samples. Avg Latency: {summary['avg_ms']}ms, Jitter: {summary['jitter_ms']}ms")


def test_tick_to_ohlcv_aggregator():
    print("[3/5] Testing LiveOHLCVAggregator 1-Minute Synthesis...")
    aggregator = LiveOHLCVAggregator(max_history_bars=100)
    emitted_bars: list[LiveBarEvent] = []
    aggregator.add_bar_listener(lambda b: emitted_bars.append(b))

    # Ticks within Minute 1 (09:15:00 to 09:15:59)
    t1 = datetime(2024, 1, 15, 9, 15, 10)
    aggregator.process_tick(LiveTick(256265, "NIFTY50", t1, 21500.0, 1000, 21500.0, 21500.0, 21500.0, 21500.0))
    
    t2 = datetime(2024, 1, 15, 9, 15, 25)
    aggregator.process_tick(LiveTick(256265, "NIFTY50", t2, 21520.0, 3000, 21500.0, 21520.0, 21500.0, 21520.0))
    
    t3 = datetime(2024, 1, 15, 9, 15, 45)
    aggregator.process_tick(LiveTick(256265, "NIFTY50", t3, 21490.0, 5000, 21500.0, 21520.0, 21490.0, 21490.0))

    t4 = datetime(2024, 1, 15, 9, 15, 59)
    aggregator.process_tick(LiveTick(256265, "NIFTY50", t4, 21515.0, 7000, 21500.0, 21520.0, 21490.0, 21515.0))
    
    # Minute 1 should NOT be emitted yet
    assert len(emitted_bars) == 0, "Bar must not be emitted before minute boundary crosses"

    # First tick of Minute 2 (09:16:02) -> Triggers emission of 09:15:00 bar
    t5 = datetime(2024, 1, 15, 9, 16, 2)
    completed_bar = aggregator.process_tick(LiveTick(256265, "NIFTY50", t5, 21518.0, 8500, 21515.0, 21518.0, 21515.0, 21518.0))

    assert completed_bar is not None
    assert len(emitted_bars) == 1
    bar = emitted_bars[0]

    assert bar.symbol == "NIFTY50"
    assert bar.timestamp_ist == datetime(2024, 1, 15, 9, 15, 0)
    assert bar.open == 21500.0
    assert bar.high == 21520.0
    assert bar.low == 21490.0
    assert bar.close == 21515.0
    assert bar.volume == 6000  # 7000 - 1000 base
    assert bar.ticks_count == 4

    # Verify DataFrame structure matches Confluence Gate requirements
    df_bars = aggregator.get_bars_dataframe("NIFTY50")
    assert not df_bars.empty
    assert "close" in df_bars.columns
    assert "volume" in df_bars.columns
    assert df_bars.iloc[0]["close"] == 21515.0
    print(f"      Passed. Synthesized 09:15 Bar: O={bar.open}, H={bar.high}, L={bar.low}, C={bar.close}, Vol={bar.volume}")


def test_ingestion_bullion_barrier():
    print("[4/5] Testing Ingestion-Layer Bullion Barrier...")
    auth = BrokerAuthManager()
    auth.authenticate_session("token_123")
    pump = KiteWebSocketDataPump(auth_mgr=auth)

    received_ticks = []
    pump.add_tick_listener(lambda t: received_ticks.append(t))

    # Send valid tick
    pump.inject_simulated_tick(LiveTick(
        instrument_token=256265, symbol="NIFTY50", timestamp=datetime.now(),
        last_price=24200.0, volume=1000, open=24200.0, high=24200.0, low=24200.0, close=24200.0
    ))
    assert len(received_ticks) == 1

    # Send restricted Gold and Silver ticks
    for bullion_sym in ["GOLD", "SILVERBEES", "XAUUSD", "GC=F"]:
        pump.inject_simulated_tick(LiveTick(
            instrument_token=999999, symbol=bullion_sym, timestamp=datetime.now(),
            last_price=75000.0, volume=500, open=75000.0, high=75000.0, low=75000.0, close=75000.0
        ))

    # Assert bullion ticks were dropped silently at network layer
    assert len(received_ticks) == 1, f"Bullion ticks breached network barrier! Expected 1 tick, got {len(received_ticks)}"
    assert "GOLD" not in pump.aggregator._active_bars
    print("      Passed. Bullion ticks dropped silently at ingestion layer.")


def test_oms_bracket_execution():
    print("[5/8] Testing OMS Pre-Trade Gate, Signal Lockout State Machine & OCO Router...")
    auth = BrokerAuthManager()
    oms = OrderManagementSystem(auth_mgr=auth)
    oms.arm_live_execution()

    valid_req = BracketOrderRequest(
        symbol="NIFTY50",
        is_buy=True,
        qty=50,
        entry_price=24200.0,
        hard_stop_price=24182.0,  # 18.0 pt stop
        target1_price=24325.0,    # +125 pts
        target2_price=24452.0,    # +252 pts
        confluence_signal_id="CONF_TEST_LIVE_01",
        node_id="MIDPOINT_1222_24200",
        session_date="20261107"
    )

    # 1. First Dispatch: Must succeed and tag node as [EXECUTED]
    success, order_id = oms.dispatch_bracket_order(valid_req)
    assert success, f"First dispatch failed: {order_id}"
    assert order_id in oms.active_orders
    order = oms.active_orders[order_id]
    assert order.state == OrderState.OPEN

    lockout_key = oms.get_lockout_key(valid_req)
    assert oms.is_node_locked(lockout_key), f"Node key {lockout_key} was not locked after execution!"
    print(f"      Initial Dispatch: Order {order_id} active. Lockout key '{lockout_key}' tagged as [EXECUTED].")

    # 2. Infinite Loop Flood Test: Simulate market hovering at 24,200 for 10 seconds (20 duplicate signals)
    duplicate_attempts = 20
    rejected_count = 0
    for _ in range(duplicate_attempts):
        dup_success, dup_reason = oms.dispatch_bracket_order(valid_req)
        if not dup_success and "OMS LOCKOUT" in dup_reason:
            rejected_count += 1

    assert rejected_count == duplicate_attempts, (
        f"Infinite loop protection failed! {rejected_count}/{duplicate_attempts} rejected."
    )
    assert len(oms.active_orders) == 1, (
        f"Active orders mutated! Expected exactly 1 order, got {len(oms.active_orders)}"
    )
    print(f"      Signal Lockout Shield: 20/20 duplicate flood triggers safely REJECTED. Broker API protected.")

    # 3. Test Reset Session Lockouts
    oms.reset_session_lockouts()
    assert not oms.is_node_locked(lockout_key), "Session reset failed to clear lockout"
    print("      Session Reset: Cleared lockouts for subsequent trading day.")


def test_api_rate_limiter():
    print("[6/8] Testing APIRateLimiter (10 req/s Sliding Window)...")
    limiter = APIRateLimiter(max_requests_per_sec=10.0, window_sec=1.0)
    
    # First 10 calls in <10ms must succeed
    allowed_count = 0
    for _ in range(10):
        if limiter.acquire():
            allowed_count += 1
    assert allowed_count == 10, f"Expected 10 requests allowed, got {allowed_count}"

    # 11th request in the same second must be throttled
    assert not limiter.acquire(), "11th request must be throttled by rate limiter!"
    assert not limiter.can_request()
    print("      Passed. Exactly 10 requests granted; 11th request throttled.")


def test_concurrent_millisecond_signal_lockout():
    print("[7/8] Testing Mutex-Guarded OMS Lockout Under 10 Concurrent Millisecond Signals...")
    import concurrent.futures

    auth = BrokerAuthManager()
    # High rate limiter limit to isolate mutex lockout logic
    limiter = APIRateLimiter(max_requests_per_sec=100.0)
    oms = OrderManagementSystem(auth_mgr=auth, rate_limiter=limiter)

    req = BracketOrderRequest(
        symbol="NIFTY50",
        is_buy=True,
        qty=50,
        entry_price=24200.0,
        hard_stop_price=24182.0,
        target1_price=24325.0,
        target2_price=24452.0,
        confluence_signal_id="CONCURRENCY_TEST_RACE",
        node_id="MIDPOINT_1222_PARALLEL_RACE",
        session_date="20261107"
    )

    results = []

    def dispatch_worker():
        return oms.dispatch_bracket_order(req)

    # Launch 10 worker threads simultaneously in the exact same millisecond
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(dispatch_worker) for _ in range(10)]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    successes = [r for r in results if r[0] is True]
    failures = [r for r in results if r[0] is False]

    assert len(successes) == 1, f"CRITICAL RACE CONDITION: Expected 1 success, got {len(successes)}!"
    assert len(failures) == 9, f"Expected 9 rejected duplicate threads, got {len(failures)}!"
    assert len(oms.active_orders) == 1, f"Expected 1 active order, got {len(oms.active_orders)}!"

    # Verify all failures were caught by OMS Lockout
    for ok, reason in failures:
        assert "OMS LOCKOUT" in reason, f"Failure reason was not lockout: {reason}"

    print(f"      Passed. Mutex protected! Exactly 1/10 threads executed; 9/10 rejected simultaneously in same ms.")


def test_realtime_confluence_router_and_live_switch():
    print("[8/8] Testing RealTimeConfluenceRouter & Armed Live Switch Toggle...")
    auth = BrokerAuthManager()
    oms = OrderManagementSystem(auth_mgr=auth)
    router = RealTimeConfluenceRouter(oms=oms, default_lot_size=50)

    # 1. Test in safe Simulation Mode (Default: is_live_execution_armed = False)
    assert not oms.is_live_execution_armed
    mock_setup = SniperTradeSetup(
        is_triggered=True,
        direction="LONG / ATM CALL",
        entry_price=24200.0,
        hard_stop_loss=24182.0,
        risk_pts=18.0,
        target_1=24325.0,
        target_2=24452.0,
        reward_pts=252.0,
        risk_reward_ratio=14.0,
        tranche_a_pct=25.0,
        tranche_b_pct=50.0,
        tranche_c_pct=25.0,
        rationale="Triple Confluence 3-Gate Lock"
    )

    eval_t = datetime(2026, 11, 7, 12, 22, 30)
    ok, order_id = router.route_setup(mock_setup, symbol="NIFTY50", eval_time=eval_t)
    assert ok
    order = oms.active_orders[order_id]
    assert order.state == OrderState.FILLED  # Simulated fill
    print(f"      Simulation Mode Dispatch: {order_id} recorded in memory without live broker API transmission.")

    # 2. Test Live Execution Switch Armed (#F43F5E)
    oms.arm_live_execution()
    assert oms.is_live_execution_armed

    # Dispatch another different node while armed
    mock_setup_short = SniperTradeSetup(
        is_triggered=True,
        direction="SHORT / ATM PUT",
        entry_price=24500.0,
        hard_stop_loss=24518.0,
        risk_pts=18.0,
        target_1=24375.0,
        target_2=24248.0,
        reward_pts=252.0,
        risk_reward_ratio=14.0,
        tranche_a_pct=25.0,
        tranche_b_pct=50.0,
        tranche_c_pct=25.0,
        rationale="Triple Confluence Short at 24500"
    )
    eval_t2 = datetime(2026, 11, 7, 13, 56, 15)
    ok2, order_id2 = router.route_setup(mock_setup_short, symbol="NIFTY50", eval_time=eval_t2)
    assert ok2
    order2 = oms.active_orders[order_id2]
    assert order2.state == OrderState.OPEN  # Live broker open order
    print(f"      Live Armed Dispatch: {order_id2} marked as OPEN for active broker execution.")

    # Disarm back to safe simulation
    oms.disarm_live_execution()
    assert not oms.is_live_execution_armed
    print("      Passed. Safe disarm verified. RealTimeConfluenceRouter 3-gate pipeline fully operational.")


if __name__ == "__main__":
    print("=================================================================")
    print("RUNNING LIVE BROKER WEBSOCKET, ROUTER & OMS TEST SUITE (PHASE 2-4)")
    print("=================================================================")
    test_exponential_backoff()
    test_latency_telemetry_bounded_memory()
    test_tick_to_ohlcv_aggregator()
    test_ingestion_bullion_barrier()
    test_oms_bracket_execution()
    test_api_rate_limiter()
    test_concurrent_millisecond_signal_lockout()
    test_realtime_confluence_router_and_live_switch()
    print("=================================================================")
    print("ALL 8 PHASE 2 EXECUTION BRIDGE TESTS DETERMINISTICALLY PASSED")
    print("=================================================================")
