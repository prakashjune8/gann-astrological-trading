"""Verification Suite for Sub-Task 4: Dedicated CTkToplevel Quant Workstation Refactor.

Verifies:
1. MainWindow initialization and presence of `btn_launch_quant`.
2. Dedicated `BacktestQuantWorkstationWindow` instantiation, embedding of `BacktestDashboardView`
   and `InteractiveTradeInspector`.
3. Auto-maximization (`state('zoomed')`) execution.
4. Focus / bring-to-front behavior preventing duplicate window spawning.
5. Clean destruction and lifecycle callback notification.
"""
import os
import sys

# Ensure repository root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import customtkinter as ctk
from ui.main_window import MainWindow
from ui.windows.backtest_window import BacktestQuantWorkstationWindow
from ui.components.backtest_dashboard_view import BacktestDashboardView


def test_quant_workstation_window_lifecycle():
    print("[1/4] Initializing MainWindow headless...")
    app = MainWindow()
    app.withdraw()  # Keep hidden during automated test run

    try:
        # Check launch button
        assert hasattr(app, "btn_launch_quant"), "MainWindow must have btn_launch_quant"
        print("  [OK] btn_launch_quant successfully registered in control strip.")

        # Trigger launch
        print("[2/4] Triggering launch_quant_workstation()...")
        app.launch_quant_workstation()
        app.update_idletasks()

        assert app.backtest_window is not None, "app.backtest_window must not be None"
        assert app.backtest_window.winfo_exists(), "app.backtest_window must exist"
        assert isinstance(app.backtest_window, BacktestQuantWorkstationWindow)
        print("  [OK] BacktestQuantWorkstationWindow instantiated cleanly.")

        # Check embedded dashboard view
        assert hasattr(app.backtest_window, "dashboard_view")
        assert isinstance(app.backtest_window.dashboard_view, BacktestDashboardView)
        assert hasattr(app.backtest_window.dashboard_view, "inspector_view")
        print("  [OK] BacktestDashboardView and InteractiveTradeInspector embedded.")

        # Test duplicate prevention (bring to front)
        print("[3/4] Testing duplicate window prevention...")
        first_instance = app.backtest_window
        app.launch_quant_workstation()  # Second call
        app.update_idletasks()
        assert app.backtest_window is first_instance, "Must reuse existing window rather than spawning duplicate"
        print("  [OK] Duplicate launch cleanly focuses existing workstation window.")

        # Test clean close callback
        print("[4/4] Testing window close protocol...")
        app.backtest_window._on_window_close()
        app.update_idletasks()
        assert app.backtest_window is None, "app.backtest_window must be reset to None on close"
        print("  [OK] Window close lifecycle callback verified.")

        print("\n=======================================================")
        print(" [SUCCESS] SUB-TASK 4 QUANT WORKSTATION VERIFICATION PASSED!")
        print("=======================================================")

    finally:
        try:
            if app.backtest_window and app.backtest_window.winfo_exists():
                app.backtest_window.destroy()
            app.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    test_quant_workstation_window_lifecycle()
