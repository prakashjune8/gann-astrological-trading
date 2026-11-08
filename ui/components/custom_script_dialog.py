"""Custom Add Script Dialog with Strict Bullion Validation."""
from __future__ import annotations

import customtkinter as ctk
from typing import Callable, Optional
from ui.theme import ThemeTokens


class CustomScriptDialog(ctk.CTkToplevel):
    """Modal dialog allowing users to add custom equity tickers with instant bullion filtering."""

    def __init__(self, master, theme: ThemeTokens, on_add_callback: Callable[[str, str], tuple[bool, str]]):
        super().__init__(master)
        self.theme = theme
        self.on_add_callback = on_add_callback

        self.title("Add Custom Script")
        self.geometry("420x280")
        self.resizable(False, False)
        self.configure(fg_color=theme.bg_primary)

        self.transient(master)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        title = ctk.CTkLabel(
            self,
            text="ADD CUSTOM EQUITY / INDEX",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.theme.accent_blue
        )
        title.pack(pady=(16, 4))

        sub = ctk.CTkLabel(
            self,
            text="Enter NSE/BSE ticker symbol (e.g., RELIANCE, HDFCBANK, TATACHEM).\nNote: Gold and Silver (bullion) instruments are strictly forbidden.",
            font=ctk.CTkFont(size=10),
            text_color=self.theme.text_muted,
            justify="center"
        )
        sub.pack(pady=(0, 14), padx=16)

        # Symbol Input
        ctk.CTkLabel(self, text="Symbol / Ticker:", font=ctk.CTkFont(size=11, weight="bold"), text_color=self.theme.text_primary).pack(anchor="w", padx=30)
        self.entry_symbol = ctk.CTkEntry(self, placeholder_text="e.g. RELIANCE", height=32)
        self.entry_symbol.pack(fill="x", padx=30, pady=(2, 10))

        # Display Name Input
        ctk.CTkLabel(self, text="Friendly Name (Optional):", font=ctk.CTkFont(size=11, weight="bold"), text_color=self.theme.text_primary).pack(anchor="w", padx=30)
        self.entry_name = ctk.CTkEntry(self, placeholder_text="e.g. Reliance Industries", height=32)
        self.entry_name.pack(fill="x", padx=30, pady=(2, 14))

        # Status / Feedback Label
        self.lbl_status = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=10))
        self.lbl_status.pack(pady=(0, 8))

        # Action Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=30)

        ctk.CTkButton(
            btn_frame, text="Cancel", fg_color=self.theme.bg_accent, text_color=self.theme.text_primary,
            command=self.destroy, width=100
        ).pack(side="left")

        ctk.CTkButton(
            btn_frame, text="Add Script", fg_color=self.theme.accent_blue, text_color="white",
            command=self._handle_add, width=120
        ).pack(side="right")

    def _handle_add(self):
        sym = self.entry_symbol.get().strip()
        name = self.entry_name.get().strip()
        if not sym:
            self.lbl_status.configure(text="Please enter a symbol.", text_color=self.theme.accent_red)
            return

        ok, msg = self.on_add_callback(sym, name)
        if ok:
            self.lbl_status.configure(text=msg, text_color=self.theme.accent_green)
            self.after(1200, self.destroy)
        else:
            self.lbl_status.configure(text=msg, text_color=self.theme.accent_red)
