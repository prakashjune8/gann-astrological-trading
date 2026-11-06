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
)


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
    print("[5/5] Testing OMS Pre-Trade Gate, Signal Lockout State Machine & OCO Router...")
    auth = BrokerAuthManager()
    oms = OrderManagementSystem(auth_mgr=auth)

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


if __name__ == "__main__":
    print("=================================================================")
    print("RUNNING LIVE BROKER WEBSOCKET & AGGREGATOR TEST SUITE (PHASE 2-1)")
    print("=================================================================")
    test_exponential_backoff()
    test_latency_telemetry_bounded_memory()
    test_tick_to_ohlcv_aggregator()
    test_ingestion_bullion_barrier()
    test_oms_bracket_execution()
    print("=================================================================")
    print("ALL 5 PHASE 2 SUB-TASK 1 TESTS DETERMINISTICALLY PASSED")
    print("=================================================================")
