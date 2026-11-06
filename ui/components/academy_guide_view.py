"""Educational Academy & Institutional Master Textbook Reader for Gann Celestial Tracker Pro."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Optional
import customtkinter as ctk

from ui.theme import ThemeTokens

# Resolve path to the master textbook
TEXTBOOK_PATH = Path(__file__).resolve().parent.parent.parent / "GANN_ACADEMY_TEXTBOOK.md"


class AcademyGuideView(ctk.CTkFrame):
    """Institutional educational academy reader and interactive curriculum browser."""

    def __init__(self, master, theme: ThemeTokens, **kwargs):
        super().__init__(master, fg_color=theme.bg_primary, **kwargs)
        self.theme = theme
        self.chapters: List[Dict[str, any]] = []
        self.active_index = 0
        self.active_level_filter = "All Chapters"

        # Load and parse textbook
        self._load_chapters()

        # Build UI layout
        self._build_header_ribbon()
        self._build_content_viewer()
        self._build_footer_ribbon()

        # Display initial chapter
        self._display_chapter(self.active_index)

    def _load_chapters(self):
        """Parse GANN_ACADEMY_TEXTBOOK.md into discrete chapters."""
        content = ""
        if TEXTBOOK_PATH.exists():
            try:
                with open(TEXTBOOK_PATH, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                content = f"# Error Loading Textbook\n\nFailed to read {TEXTBOOK_PATH}: {e}"
        else:
            content = "# Gann Celestial Tracker Pro Master Guide\n\nTextbook file not found on disk."

        # Split into chapters by '# CHAPTER XX:' or overview
        raw_chunks = re.split(r"\n(?=# CHAPTER \d+:)", content)
        
        self.chapters = []
        for idx, chunk in enumerate(raw_chunks):
            lines = chunk.strip().split("\n")
            raw_title = lines[0].strip("# ").strip() if lines else f"Chapter {idx}"
            
            if idx == 0:
                num = 0
                title = "00. Master Curriculum & Table of Contents"
                level = "Overview"
                short_label = "Curriculum Overview"
            else:
                num = idx
                # Extract clean title after '# CHAPTER XX: '
                match = re.match(r"CHAPTER (\d+):\s*(.*)", raw_title, re.IGNORECASE)
                clean_name = match.group(2) if match else raw_title
                short_label = f"Ch {num:02d}: {clean_name[:40]}..." if len(clean_name) > 40 else f"Ch {num:02d}: {clean_name}"
                title = f"Chapter {num:02d}: {clean_name}"

                if 1 <= num <= 6:
                    level = "Level 1: Beginner"
                elif 7 <= num <= 12:
                    level = "Level 2: Intermediate"
                else:
                    level = "Level 3: Master"

            self.chapters.append({
                "num": num,
                "title": title,
                "short_label": short_label,
                "level": level,
                "content": chunk.strip()
            })

    def _build_header_ribbon(self):
        """Build top control and navigation bar."""
        header = ctk.CTkFrame(self, fg_color=self.theme.bg_card, corner_radius=8)
        header.pack(fill="x", padx=16, pady=(16, 8))

        # Top row: Title and Action Buttons
        top_row = ctk.CTkFrame(header, fg_color="transparent")
        top_row.pack(fill="x", padx=16, pady=(12, 6))

        title_lbl = ctk.CTkLabel(
            top_row,
            text="🏛️ GANN CELESTIAL QUANTITATIVE ACADEMY (16-CHAPTER MASTER SPECIFICATION)",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=self.theme.accent_blue
        )
        title_lbl.pack(side="left")

        btn_copy = ctk.CTkButton(
            top_row,
            text="📋 Copy Chapter",
            width=110,
            height=28,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=self.theme.bg_accent,
            hover_color=self.theme.border_color,
            text_color=self.theme.text_primary,
            command=self._copy_current_chapter
        )
        btn_copy.pack(side="right", padx=(6, 0))

        btn_open = ctk.CTkButton(
            top_row,
            text="📖 Open Markdown",
            width=120,
            height=28,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=self.theme.accent_blue,
            hover_color=self.theme.bg_accent,
            text_color="#ffffff",
            command=self._open_textbook_file
        )
        btn_open.pack(side="right", padx=(6, 0))

        # Bottom row: Level Filter, Chapter Selector, Search
        nav_row = ctk.CTkFrame(header, fg_color="transparent")
        nav_row.pack(fill="x", padx=16, pady=(0, 12))

        # Level Segmented Filter
        self.seg_level = ctk.CTkSegmentedButton(
            nav_row,
            values=["All Chapters", "Level 1: Beginner", "Level 2: Intermediate", "Level 3: Master"],
            font=ctk.CTkFont(family="Segoe UI", size=11),
            selected_color=self.theme.accent_blue,
            command=self._on_level_filter_change
        )
        self.seg_level.set("All Chapters")
        self.seg_level.pack(side="left", padx=(0, 12))

        # Chapter Dropdown
        self.chapter_options = [ch["short_label"] for ch in self.chapters]
        self.om_chapter = ctk.CTkOptionMenu(
            nav_row,
            values=self.chapter_options,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            width=260,
            fg_color=self.theme.bg_secondary,
            button_color=self.theme.accent_blue,
            text_color=self.theme.text_primary,
            command=self._on_chapter_selected
        )
        self.om_chapter.pack(side="left", padx=(0, 12))

        # Search Bar
        self.ent_search = ctk.CTkEntry(
            nav_row,
            placeholder_text="🔍 Search textbook concepts (e.g. Spencer, Parallax, 1x1)...",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            width=280,
            fg_color=self.theme.bg_secondary,
            text_color=self.theme.text_primary
        )
        self.ent_search.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.ent_search.bind("<Return>", lambda e: self._on_search())

        btn_search = ctk.CTkButton(
            nav_row,
            text="Search",
            width=65,
            height=28,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=self.theme.accent_blue,
            hover_color=self.theme.bg_accent,
            text_color="#ffffff",
            command=self._on_search
        )
        btn_search.pack(side="left")

    def _build_content_viewer(self):
        """Build center reading textbox pane."""
        viewer_frame = ctk.CTkFrame(self, fg_color=self.theme.bg_card, corner_radius=8)
        viewer_frame.pack(fill="both", expand=True, padx=16, pady=4)

        self.txt_content = ctk.CTkTextbox(
            viewer_frame,
            wrap="word",
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=self.theme.bg_card,
            text_color=self.theme.text_primary,
            activate_scrollbars=True
        )
        self.txt_content.pack(fill="both", expand=True, padx=16, pady=16)

    def _build_footer_ribbon(self):
        """Build bottom pagination and quick jump bar."""
        footer = ctk.CTkFrame(self, fg_color=self.theme.bg_card, corner_radius=8)
        footer.pack(fill="x", padx=16, pady=(8, 16))

        inner = ctk.CTkFrame(footer, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=10)

        self.btn_prev = ctk.CTkButton(
            inner,
            text="◀ Previous Chapter",
            width=140,
            height=28,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=self.theme.bg_accent,
            hover_color=self.theme.border_color,
            text_color=self.theme.text_primary,
            command=self._go_prev_chapter
        )
        self.btn_prev.pack(side="left")

        self.lbl_progress = ctk.CTkLabel(
            inner,
            text="Chapter 0 of 16 | Overview",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=self.theme.text_secondary
        )
        self.lbl_progress.pack(side="left", fill="x", expand=True)

        self.btn_next = ctk.CTkButton(
            inner,
            text="Next Chapter ▶",
            width=140,
            height=28,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=self.theme.accent_blue,
            hover_color=self.theme.bg_accent,
            text_color="#ffffff",
            command=self._go_next_chapter
        )
        self.btn_next.pack(side="right")

    def _display_chapter(self, index: int):
        """Render the selected chapter into the textbox."""
        if not (0 <= index < len(self.chapters)):
            return

        self.active_index = index
        chapter = self.chapters[index]

        # Update text viewer
        self.txt_content.configure(state="normal")
        self.txt_content.delete("1.0", "end")
        self.txt_content.insert("1.0", chapter["content"])
        self.txt_content.configure(state="disabled")
        self.txt_content.see("1.0")

        # Update Dropdown OptionMenu selection
        if chapter["short_label"] in self.chapter_options:
            self.om_chapter.set(chapter["short_label"])

        # Update Footer Progress Label
        if chapter["num"] == 0:
            prog_text = "Master Curriculum Overview & Index"
        else:
            prog_text = f"Chapter {chapter['num']:02d} of 16  •  {chapter['level']}"
        self.lbl_progress.configure(text=prog_text)

        # Update Prev/Next button states
        self.btn_prev.configure(state="normal" if index > 0 else "disabled")
        self.btn_next.configure(state="normal" if index < len(self.chapters) - 1 else "disabled")

    def _on_level_filter_change(self, value: str):
        """Filter chapter list by selected educational level."""
        self.active_level_filter = value
        
        filtered = []
        for ch in self.chapters:
            if value == "All Chapters":
                filtered.append(ch)
            elif value.startswith("Level 1") and ch["level"] == "Level 1: Beginner":
                filtered.append(ch)
            elif value.startswith("Level 2") and ch["level"] == "Level 2: Intermediate":
                filtered.append(ch)
            elif value.startswith("Level 3") and ch["level"] == "Level 3: Master":
                filtered.append(ch)

        if not filtered:
            return

        self.chapter_options = [ch["short_label"] for ch in filtered]
        self.om_chapter.configure(values=self.chapter_options)
        
        # Switch to first chapter in filtered set
        target_idx = self.chapters.index(filtered[0])
        self._display_chapter(target_idx)

    def _on_chapter_selected(self, choice: str):
        """User selected a chapter from the dropdown menu."""
        for idx, ch in enumerate(self.chapters):
            if ch["short_label"] == choice:
                self._display_chapter(idx)
                break

    def _go_prev_chapter(self):
        """Navigate to the previous chapter."""
        if self.active_index > 0:
            self._display_chapter(self.active_index - 1)

    def _go_next_chapter(self):
        """Navigate to the next chapter."""
        if self.active_index < len(self.chapters) - 1:
            self._display_chapter(self.active_index + 1)

    def _copy_current_chapter(self):
        """Copy active chapter text to system clipboard."""
        if 0 <= self.active_index < len(self.chapters):
            content = self.chapters[self.active_index]["content"]
            self.clipboard_clear()
            self.clipboard_append(content)

    def _open_textbook_file(self):
        """Open GANN_ACADEMY_TEXTBOOK.md using the default system application."""
        if TEXTBOOK_PATH.exists():
            try:
                os.startfile(str(TEXTBOOK_PATH))
            except Exception:
                pass

    def _on_search(self):
        """Search for keyword across current chapter or all chapters."""
        query = self.ent_search.get().strip().lower()
        if not query:
            return

        # First search inside current chapter
        current_content = self.chapters[self.active_index]["content"].lower()
        if query in current_content:
            # Found in current chapter - highlight or scroll
            idx_pos = current_content.find(query)
            # Rough line estimate
            line_num = current_content[:idx_pos].count("\n") + 1
            self.txt_content.see(f"{line_num}.0")
            return

        # Otherwise find first chapter containing the query
        for idx, ch in enumerate(self.chapters):
            if query in ch["content"].lower():
                self._display_chapter(idx)
                # Scroll to match
                content_lower = ch["content"].lower()
                idx_pos = content_lower.find(query)
                line_num = content_lower[:idx_pos].count("\n") + 1
                self.txt_content.see(f"{line_num}.0")
                return
