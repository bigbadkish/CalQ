"""
Tkinter UI module for CalQ.

Contains:
- DatabaseManager: SQLite3 database handler.
- CalQApp: main Tkinter GUI application.
- run_app(): convenience function to start the app.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import List, Tuple, Optional

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

from models import UserLog
# calculator is available if you want to plug in serving-size math:
# from calculator import calculate_calories_for_serving


class DatabaseManager:
    """Manages SQLite database operations for CalQ application."""

    def __init__(self, db_name: str = "calq_database.db") -> None:
        """Initialize database connection and create tables if needed."""
        self.db_name = db_name
        self.connection: Optional[sqlite3.Connection] = None
        self.initialize_database()

    def initialize_database(self) -> None:
        """Create database tables if they don't exist."""
        try:
            self.connection = sqlite3.connect(self.db_name)
            cursor = self.connection.cursor()

            # Create meals table with all necessary fields
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS meals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    meal_type TEXT NOT NULL,
                    food_name TEXT NOT NULL,
                    calories REAL NOT NULL,
                    serving_size TEXT,
                    notes TEXT,
                    timestamp TEXT NOT NULL
                )
                """
            )

            # Create users table for settings
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    target_calories INTEGER DEFAULT 2000
                )
                """
            )

            # Insert default user if not exists
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    "INSERT INTO users (name, target_calories) VALUES (?, ?)",
                    ("User", 2000),
                )

            self.connection.commit()
            print("Database initialized successfully!")

        except sqlite3.Error as error:
            print(f"Database error: {error}")
            messagebox.showerror(
                "Database Error", f"Failed to initialize database: {error}"
            )

    def create_meal(
        self,
        date: str,
        meal_type: str,
        food_name: str,
        calories: float,
        serving_size: str = "",
        notes: str = "",
    ) -> bool:
        """CREATE operation - Add a new meal entry."""
        try:
            cursor = self.connection.cursor()
            timestamp = datetime.now().isoformat()

            cursor.execute(
                """
                INSERT INTO meals (date, meal_type, food_name, calories,
                                   serving_size, notes, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (date, meal_type, food_name, calories, serving_size, notes, timestamp),
            )

            self.connection.commit()
            return True
        except sqlite3.Error as error:
            print(f"Error creating meal: {error}")
            messagebox.showerror("Error", f"Failed to create meal entry: {error}")
            return False

    def read_meals_by_date(self, date: str) -> List[Tuple]:
        """READ operation - Get all meals for a specific date."""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                SELECT id, meal_type, food_name, calories,
                       serving_size, notes, timestamp
                FROM meals
                WHERE date = ?
                ORDER BY timestamp ASC
                """,
                (date,),
            )
            return cursor.fetchall()
        except sqlite3.Error as error:
            print(f"Error reading meals: {error}")
            return []

    def read_all_meals(self) -> List[Tuple]:
        """READ operation - Get all meals from database."""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                SELECT id, date, meal_type, food_name, calories,
                       serving_size, notes, timestamp
                FROM meals
                ORDER BY date DESC, timestamp DESC
                """
            )
            return cursor.fetchall()
        except sqlite3.Error as error:
            print(f"Error reading all meals: {error}")
            return []

    def update_meal(
        self,
        meal_id: int,
        meal_type: str,
        food_name: str,
        calories: float,
        serving_size: str = "",
        notes: str = "",
    ) -> bool:
        """UPDATE operation - Modify an existing meal entry."""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                UPDATE meals
                SET meal_type = ?, food_name = ?, calories = ?,
                    serving_size = ?, notes = ?
                WHERE id = ?
                """,
                (meal_type, food_name, calories, serving_size, notes, meal_id),
            )

            self.connection.commit()
            return True
        except sqlite3.Error as error:
            print(f"Error updating meal: {error}")
            messagebox.showerror("Error", f"Failed to update meal: {error}")
            return False

    def delete_meal(self, meal_id: int) -> bool:
        """DELETE operation - Remove a meal entry."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM meals WHERE id = ?", (meal_id,))
            self.connection.commit()
            return True
        except sqlite3.Error as error:
            print(f"Error deleting meal: {error}")
            messagebox.showerror("Error", f"Failed to delete meal: {error}")
            return False

    def get_daily_calories(self, date: str) -> float:
        """Calculate total calories for a specific date."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT SUM(calories) FROM meals WHERE date = ?", (date,))
            result = cursor.fetchone()[0]
            return float(result) if result else 0.0
        except sqlite3.Error as error:
            print(f"Error calculating calories: {error}")
            return 0.0

    def get_weekly_data(self) -> List[Tuple[str, float]]:
        """Get calorie data for the last 7 days."""
        weekly_data: List[Tuple[str, float]] = []
        for i in range(6, -1, -1):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            calories = self.get_daily_calories(date)
            weekly_data.append((date, calories))
        return weekly_data

    def get_target_calories(self) -> int:
        """Get user's target calorie goal."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT target_calories FROM users WHERE id = 1")
            result = cursor.fetchone()
            return int(result[0]) if result else 2000
        except sqlite3.Error as error:
            print(f"Error getting target calories: {error}")
            return 2000

    def close(self) -> None:
        """Close database connection."""
        if self.connection:
            self.connection.close()


class CalQApp:
    """Main application class for CalQ Food & Calorie Tracker."""

    def __init__(self, root: tk.Tk) -> None:
        """Initialize the application."""
        self.root = root
        self.root.title("CalQ - Daily Food & Calorie Tracker")
        self.root.geometry("1100x750")
        self.root.configure(bg="#f5f7fa")

        # Initialize database
        self.db = DatabaseManager()

        # Application state
        self.selected_date: str = datetime.now().strftime("%Y-%m-%d")
        self.editing_meal_id: Optional[int] = None

        # Placeholders for some widgets (to avoid type checker noise)
        self.main_container: tk.Frame
        self.btn_dashboard: tk.Button
        self.btn_add_meal: tk.Button
        self.btn_all_logs: tk.Button
        self.date_entry: tk.Entry

        # Form entries in add/edit view
        self.entry_date: tk.Entry
        self.entry_meal_type: ttk.Combobox
        self.entry_food_name: tk.Entry
        self.entry_calories: tk.Entry
        self.entry_serving_size: tk.Entry
        self.entry_notes: scrolledtext.ScrolledText

        # Create GUI
        self.create_header()
        self.create_main_container()
        self.show_dashboard()

    # ------------------------------------------------------------------ Header

    def create_header(self) -> None:
        """Create application header with modern gradient design."""
        header_frame = tk.Frame(self.root, bg="#1e88e5", height=120)
        header_frame.pack(fill="x", padx=0, pady=0)
        header_frame.pack_propagate(False)

        gradient_frame = tk.Frame(header_frame, bg="#1976d2")
        gradient_frame.place(x=0, y=0, relwidth=1, relheight=1)

        # Title
        title_frame = tk.Frame(gradient_frame, bg="#1976d2")
        title_frame.pack(side="left", padx=25, pady=15)

        title_label = tk.Label(
            title_frame,
            text="🍽️ CalQ",
            font=("Segoe UI", 32, "bold"),
            bg="#1976d2",
            fg="white",
        )
        title_label.pack(anchor="w")

        subtitle_label = tk.Label(
            title_frame,
            text="Daily Food & Calorie Tracker",
            font=("Segoe UI", 13),
            bg="#1976d2",
            fg="#bbdefb",
        )
        subtitle_label.pack(anchor="w")

        # SDG info
        sdg_frame = tk.Frame(gradient_frame, bg="#0d47a1", relief="flat")
        sdg_frame.pack(side="right", padx=25, pady=20)

        sdg_label = tk.Label(
            sdg_frame,
            text="  SDG 3: Good Health & Well-Being  \n  Promoting Healthy Eating Habits  ",
            font=("Segoe UI", 11, "bold"),
            bg="#0d47a1",
            fg="#ffffff",
            justify="center",
            padx=15,
            pady=10,
        )
        sdg_label.pack()

        # Navigation bar
        nav_frame = tk.Frame(self.root, bg="#ffffff", height=60)
        nav_frame.pack(fill="x", padx=0, pady=0)
        nav_frame.pack_propagate(False)

        shadow_frame = tk.Frame(self.root, bg="#e0e0e0", height=2)
        shadow_frame.pack(fill="x")

        btn_style = {
            "font": ("Segoe UI", 12, "bold"),
            "bd": 0,
            "padx": 25,
            "pady": 12,
            "cursor": "hand2",
            "relief": "flat",
            "activebackground": "#2196f3",
            "activeforeground": "white",
        }

        self.btn_dashboard = tk.Button(
            nav_frame,
            text="📊 Dashboard",
            command=self.show_dashboard,
            bg="#2196f3",
            fg="white",
            **btn_style,
        )
        self.btn_dashboard.pack(side="left", padx=8, pady=10)

        self.btn_add_meal = tk.Button(
            nav_frame,
            text="➕ Add Meal",
            command=self.show_add_meal,
            bg="#f5f5f5",
            fg="#424242",
            **btn_style,
        )
        self.btn_add_meal.pack(side="left", padx=8, pady=10)

        self.btn_all_logs = tk.Button(
            nav_frame,
            text="📋 All Logs",
            command=self.show_all_logs,
            bg="#f5f5f5",
            fg="#424242",
            **btn_style,
        )
        self.btn_all_logs.pack(side="left", padx=8, pady=10)

    # ----------------------------------------------------------------- Layout

    def create_main_container(self) -> None:
        """Create main content container."""
        self.main_container = tk.Frame(self.root, bg="#f5f7fa")
        self.main_container.pack(fill="both", expand=True, padx=0, pady=0)

    def clear_main_container(self) -> None:
        """Clear all widgets from main container."""
        for widget in self.main_container.winfo_children():
            widget.destroy()

    def update_nav_buttons(self, active_button: str) -> None:
        """Update navigation button styles."""
        buttons = {
            "dashboard": self.btn_dashboard,
            "add_meal": self.btn_add_meal,
            "all_logs": self.btn_all_logs,
        }

        for name, button in buttons.items():
            if name == active_button:
                button.config(bg="#2196f3", fg="white")
            else:
                button.config(bg="#f5f5f5", fg="#424242")

    # -------------------------------------------------------------- Dashboard

    def show_dashboard(self) -> None:
        """Display main dashboard view."""
        self.clear_main_container()
        self.update_nav_buttons("dashboard")
        self.editing_meal_id = None

        canvas = tk.Canvas(self.main_container, bg="#f5f7fa", highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            self.main_container, orient="vertical", command=canvas.yview
        )
        scrollable_frame = tk.Frame(canvas, bg="#f5f7fa")

        scrollable_frame.bind(
            "<Configure>",
            lambda event: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfig(window_id, width=event.width),
        )
        canvas.configure(yscrollcommand=scrollbar.set)

        content_wrapper = tk.Frame(scrollable_frame, bg="#f5f7fa")
        content_wrapper.pack(fill="both", expand=True, padx=10, pady=10)

        left_col = tk.Frame(content_wrapper, bg="#f5f7fa")
        left_col.pack(side="left", fill="both", expand=True)

        right_col = tk.Frame(content_wrapper, bg="#f5f7fa", width=420)
        right_col.pack(side="right", fill="y", padx=(10, 20))

        self.create_date_selector(left_col)
        self.create_daily_summary(left_col)
        self.create_meals_breakdown(left_col)
        self.create_weekly_chart(right_col)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def create_date_selector(self, parent: tk.Frame) -> None:
        """Create date selection widget with modern design."""
        frame = tk.Frame(parent, bg="white", relief="flat", bd=0)
        frame.pack(fill="x", padx=20, pady=15)

        shadow = tk.Frame(frame, bg="#e0e0e0", height=1)
        shadow.pack(side="bottom", fill="x")

        content_frame = tk.Frame(frame, bg="white")
        content_frame.pack(fill="x", padx=20, pady=15)

        tk.Label(
            content_frame,
            text="📅 Select Date:",
            font=("Segoe UI", 12, "bold"),
            bg="white",
            fg="#424242",
        ).pack(side="left", padx=10)

        self.date_entry = tk.Entry(
            content_frame,
            font=("Segoe UI", 12),
            width=18,
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightcolor="#2196f3",
            highlightbackground="#e0e0e0",
        )
        self.date_entry.insert(0, self.selected_date)
        self.date_entry.pack(side="left", padx=10, ipady=5)

        tk.Button(
            content_frame,
            text="Go ➜",
            command=self.update_selected_date,
            bg="#2196f3",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            cursor="hand2",
            padx=20,
            pady=6,
            relief="flat",
            bd=0,
            activebackground="#1976d2",
            activeforeground="white",
        ).pack(side="left", padx=5)

        tk.Label(
            content_frame,
            text="(Format: YYYY-MM-DD)",
            font=("Segoe UI", 10),
            bg="white",
            fg="#9e9e9e",
        ).pack(side="left", padx=15)

    def update_selected_date(self) -> None:
        """Update selected date and refresh dashboard."""
        try:
            date_str = self.date_entry.get()
            datetime.strptime(date_str, "%Y-%m-%d")
            self.selected_date = date_str
            self.show_dashboard()
        except ValueError:
            messagebox.showerror(
                "Invalid Date", "Please enter date in YYYY-MM-DD format"
            )

    def create_daily_summary(self, parent: tk.Frame) -> None:
        """Create daily calorie summary card with gradient design."""
        frame = tk.Frame(parent, bg="white", relief="flat", bd=0)
        frame.pack(fill="x", padx=20, pady=15)

        gradient_frame = tk.Frame(frame, bg="#4caf50")
        gradient_frame.pack(fill="both", expand=True)

        shadow = tk.Frame(frame, bg="#e0e0e0", height=2)
        shadow.pack(side="bottom", fill="x")

        daily_calories = self.db.get_daily_calories(self.selected_date)
        target_calories = self.db.get_target_calories()
        percentage = (daily_calories / target_calories * 100) if target_calories > 0 else 0

        tk.Label(
            gradient_frame,
            text="📈 Today's Calorie Summary",
            font=("Segoe UI", 18, "bold"),
            bg="#4caf50",
            fg="white",
        ).pack(anchor="w", padx=25, pady=(20, 10))

        calories_frame = tk.Frame(gradient_frame, bg="#4caf50")
        calories_frame.pack(fill="x", padx=25, pady=10)

        tk.Label(
            calories_frame,
            text=f"{int(daily_calories)}",
            font=("Segoe UI", 48, "bold"),
            bg="#4caf50",
            fg="white",
        ).pack(side="left")

        details_frame = tk.Frame(calories_frame, bg="#4caf50")
        details_frame.pack(side="left", padx=15)

        tk.Label(
            details_frame,
            text=f"of {target_calories} calories",
            font=("Segoe UI", 14),
            bg="#4caf50",
            fg="#e8f5e9",
        ).pack(anchor="w")

        tk.Label(
            details_frame,
            text=f"{int(percentage)}% of daily goal",
            font=("Segoe UI", 12),
            bg="#4caf50",
            fg="#c8e6c9",
        ).pack(anchor="w")

        progress_container = tk.Frame(gradient_frame, bg="#81c784", height=30)
        progress_container.pack(fill="x", padx=25, pady=(10, 5))
        progress_container.pack_propagate(False)

        progress_width = min(percentage, 100)
        progress_bar = tk.Frame(progress_container, bg="white", height=30)
        progress_bar.place(x=0, y=0, relwidth=progress_width / 100, relheight=1)

        progress_label = tk.Label(
            progress_container,
            text=f"{int(percentage)}%",
            font=("Segoe UI", 11, "bold"),
            bg="#81c784",
            fg="white",
        )
        progress_label.place(relx=0.5, rely=0.5, anchor="center")

        if percentage > 100:
            status_text = f"⚠️ {int(percentage - 100)}% over target"
            status_color = "#ffeb3b"
        elif percentage >= 80:
            status_text = f"✓ {int(100 - percentage)}% remaining"
            status_color = "#e8f5e9"
        else:
            status_text = f"💪 {int(100 - percentage)}% remaining - Keep going!"
            status_color = "#c8e6c9"

        tk.Label(
            gradient_frame,
            text=status_text,
            font=("Segoe UI", 11, "bold"),
            bg="#4caf50",
            fg=status_color,
        ).pack(anchor="w", padx=25, pady=(5, 20))

    def create_weekly_chart(self, parent: tk.Frame) -> None:
        """Create weekly calorie chart with modern design."""
        frame = tk.Frame(parent, bg="white", relief="flat", bd=0)
        frame.pack(fill="both", expand=True, padx=10, pady=15)

        shadow = tk.Frame(frame, bg="#e0e0e0", height=2)
        shadow.pack(side="bottom", fill="x")

        tk.Label(
            frame,
            text="📊 Weekly Overview",
            font=("Segoe UI", 16, "bold"),
            bg="white",
            fg="#424242",
        ).pack(anchor="w", padx=20, pady=(15, 10))

        try:
            weekly_data = self.db.get_weekly_data()
        except Exception:
            weekly_data = []

        max_calories = 1
        if weekly_data:
            max_calories = max(
                [cal for _, cal in weekly_data] + [self.db.get_target_calories()]
            )

        chart_frame = tk.Frame(frame, bg="white")
        chart_frame.pack(fill="both", expand=True, padx=10, pady=10)
        chart_frame.update_idletasks()

        bar_width = 60
        spacing = 20
        chart_height = 220

        for date, calories in weekly_data:
            bar_frame = tk.Frame(
                chart_frame, bg="white", width=bar_width, height=chart_height
            )
            bar_frame.pack(side="left", padx=(0, spacing), pady=0)
            bar_frame.pack_propagate(False)

            bar_container = tk.Frame(bar_frame, bg="#f5f5f5", height=chart_height - 60)
            bar_container.pack(fill="x", expand=True)
            bar_container.pack_propagate(False)

            bar_height = (
                int(calories / max_calories * (chart_height - 60))
                if max_calories > 0
                else 0
            )
            bar_color = "#2196f3" if date == self.selected_date else "#64b5f6"

            bar = tk.Frame(bar_container, bg=bar_color)
            bar.place(x=0, rely=1, relwidth=1, height=bar_height, anchor="sw")

            if date == self.selected_date:
                highlight = tk.Frame(bar, bg="#1976d2", height=4)
                highlight.pack(side="top", fill="x")

            day_name = datetime.strptime(date, "%Y-%m-%d").strftime("%a")
            label_bg = "#2196f3" if date == self.selected_date else "white"
            label_fg = "white" if date == self.selected_date else "#424242"

            tk.Label(
                bar_frame,
                text=day_name,
                font=("Segoe UI", 10, "bold"),
                bg=label_bg,
                fg=label_fg,
                padx=5,
                pady=3,
            ).pack(pady=(8, 2))

            tk.Label(
                bar_frame,
                text=f"{int(calories)} cal",
                font=("Segoe UI", 9),
                bg="white",
                fg="#757575",
            ).pack()

    def create_meals_breakdown(self, parent: tk.Frame) -> None:
        """Create today's meals breakdown with modern cards."""
        frame = tk.Frame(parent, bg="white", relief="flat", bd=0)
        frame.pack(fill="both", expand=True, padx=20, pady=15)

        shadow = tk.Frame(frame, bg="#e0e0e0", height=2)
        shadow.pack(side="bottom", fill="x")

        header_frame = tk.Frame(frame, bg="white")
        header_frame.pack(fill="x", padx=20, pady=15)

        tk.Label(
            header_frame,
            text="🍴 Today's Meals",
            font=("Segoe UI", 16, "bold"),
            bg="white",
            fg="#424242",
        ).pack(side="left")

        tk.Button(
            header_frame,
            text="➕ Add Meal",
            command=self.show_add_meal,
            bg="#4caf50",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            cursor="hand2",
            padx=20,
            pady=8,
            relief="flat",
            bd=0,
            activebackground="#388e3c",
            activeforeground="white",
        ).pack(side="right")

        meals = self.db.read_meals_by_date(self.selected_date)

        if not meals:
            empty_frame = tk.Frame(frame, bg="#f5f5f5")
            empty_frame.pack(fill="x", padx=20, pady=30)

            tk.Label(empty_frame, text="🍽️", font=("Segoe UI", 48), bg="#f5f5f5").pack(
                pady=10
            )

            tk.Label(
                empty_frame,
                text="No meals logged yet today",
                font=("Segoe UI", 14),
                bg="#f5f5f5",
                fg="#9e9e9e",
            ).pack()

            tk.Label(
                empty_frame,
                text="Start tracking your nutrition by adding your first meal!",
                font=("Segoe UI", 11),
                bg="#f5f5f5",
                fg="#bdbdbd",
            ).pack(pady=(5, 20))
        else:
            meal_types = ["Breakfast", "Lunch", "Dinner", "Snacks"]
            meal_icons = {
                "Breakfast": "🌅",
                "Lunch": "🌞",
                "Dinner": "🌙",
                "Snacks": "🍿",
            }

            for meal_type in meal_types:
                type_meals = [meal for meal in meals if meal[1] == meal_type]
                if type_meals:
                    self.create_meal_type_section(
                        frame, meal_type, type_meals, meal_icons.get(meal_type, "🍴")
                    )

    def create_meal_type_section(
        self,
        parent: tk.Frame,
        meal_type: str,
        meals: List[Tuple],
        icon: str,
    ) -> None:
        """Create section for specific meal type with modern design."""
        section_frame = tk.Frame(parent, bg="#fafafa", relief="flat", bd=0)
        section_frame.pack(fill="x", padx=20, pady=8)

        total_calories = sum(meal[3] for meal in meals)

        header = tk.Frame(section_frame, bg="#fafafa")
        header.pack(fill="x", padx=15, pady=12)

        title_frame = tk.Frame(header, bg="#fafafa")
        title_frame.pack(side="left")

        tk.Label(
            title_frame,
            text=f"{icon} {meal_type}",
            font=("Segoe UI", 14, "bold"),
            bg="#fafafa",
            fg="#424242",
        ).pack(side="left")

        tk.Label(
            title_frame,
            text=f"  •  {len(meals)} item{'s' if len(meals) > 1 else ''}",
            font=("Segoe UI", 11),
            bg="#fafafa",
            fg="#9e9e9e",
        ).pack(side="left")

        cal_label = tk.Label(
            header,
            text=f"{int(total_calories)} cal",
            font=("Segoe UI", 14, "bold"),
            bg="#fafafa",
            fg="#4caf50",
        )
        cal_label.pack(side="right")

        for meal in meals:
            self.create_meal_item(section_frame, meal)

    def create_meal_item(self, parent: tk.Frame, meal: Tuple) -> None:
        """Create individual meal item with modern card design."""
        meal_id, meal_type, food_name, calories, serving_size, notes, timestamp = meal

        item_frame = tk.Frame(parent, bg="white", relief="flat", bd=0)
        item_frame.pack(fill="x", padx=15, pady=4)

        border = tk.Frame(item_frame, bg="#2196f3", width=4)
        border.pack(side="left", fill="y")

        content_frame = tk.Frame(item_frame, bg="white")
        content_frame.pack(side="left", fill="both", expand=True, padx=15, pady=12)

        tk.Label(
            content_frame,
            text=food_name,
            font=("Segoe UI", 12, "bold"),
            bg="white",
            fg="#212121",
            anchor="w",
        ).pack(fill="x")

        if serving_size:
            tk.Label(
                content_frame,
                text=f"📏 {serving_size}",
                font=("Segoe UI", 10),
                bg="white",
                fg="#757575",
                anchor="w",
            ).pack(fill="x", pady=(2, 0))

        if notes:
            tk.Label(
                content_frame,
                text=f"💭 {notes}",
                font=("Segoe UI", 10, "italic"),
                bg="white",
                fg="#9e9e9e",
                anchor="w",
            ).pack(fill="x", pady=(2, 0))

        actions_frame = tk.Frame(item_frame, bg="white")
        actions_frame.pack(side="right", padx=15, pady=12)

        cal_frame = tk.Frame(actions_frame, bg="#e8f5e9", padx=12, pady=6)
        cal_frame.pack(side="left", padx=(0, 10))

        tk.Label(
            cal_frame,
            text=f"{int(calories)} cal",
            font=("Segoe UI", 12, "bold"),
            bg="#e8f5e9",
            fg="#2e7d32",
        ).pack()

        tk.Button(
            actions_frame,
            text="✏️ Edit",
            command=lambda: self.edit_meal(meal_id),
            bg="#2196f3",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
            padx=12,
            pady=5,
            relief="flat",
            bd=0,
            activebackground="#1976d2",
            activeforeground="white",
        ).pack(side="left", padx=3)

        tk.Button(
            actions_frame,
            text="🗑️ Delete",
            command=lambda: self.delete_meal_confirm(meal_id),
            bg="#f44336",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
            padx=12,
            pady=5,
            relief="flat",
            bd=0,
            activebackground="#d32f2f",
            activeforeground="white",
        ).pack(side="left", padx=3)

    # ------------------------------------------------------------ Add/Edit view

    def show_add_meal(self) -> None:
        """Display add meal form with modern design."""
        self.clear_main_container()
        self.update_nav_buttons("add_meal")

        outer_frame = tk.Frame(self.main_container, bg="#f5f7fa")
        outer_frame.pack(fill="both", expand=True)

        form_frame = tk.Frame(outer_frame, bg="white", relief="flat", bd=0)
        form_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.72, relheight=0.85)

        shadow = tk.Frame(form_frame, bg="#e0e0e0", height=2)
        shadow.pack(side="bottom", fill="x")

        title_text = "✏️ Edit Meal Entry" if self.editing_meal_id else "➕ Log New Meal"
        title_frame = tk.Frame(form_frame, bg="#2196f3")
        title_frame.pack(fill="x")

        tk.Label(
            title_frame,
            text=title_text,
            font=("Segoe UI", 20, "bold"),
            bg="#2196f3",
            fg="white",
            pady=20,
        ).pack()

        canvas = tk.Canvas(form_frame, bg="white", highlightthickness=0, height=450)
        scrollbar = ttk.Scrollbar(form_frame, orient="vertical", command=canvas.yview)
        fields_frame = tk.Frame(canvas, bg="white")

        fields_frame.bind(
            "<Configure>",
            lambda event: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        window_id_fields = canvas.create_window((0, 0), window=fields_frame, anchor="nw")
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfig(window_id_fields, width=event.width),
        )
        canvas.configure(yscrollcommand=scrollbar.set)

        inner_fields = tk.Frame(fields_frame, bg="white")
        inner_fields.pack(fill="both", expand=True, padx=40, pady=20)

        self.create_form_field(inner_fields, "Date", 0, is_date=True, required=True)
        self.create_form_field(
            inner_fields,
            "Meal Type",
            1,
            options=["Breakfast", "Lunch", "Dinner", "Snacks"],
            required=True,
        )
        self.create_form_field(inner_fields, "Food Name", 2, required=True)
        self.create_form_field(inner_fields, "Calories", 3, required=True)
        self.create_form_field(inner_fields, "Serving Size", 4)
        self.create_form_field(inner_fields, "Notes", 5, multiline=True)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        btn_frame = tk.Frame(form_frame, bg="white")
        btn_frame.pack(fill="x", pady=20)

        if self.editing_meal_id:
            self.load_meal_data()

            tk.Button(
                btn_frame,
                text="✓ Update Meal",
                command=self.update_meal_submit,
                bg="#2196f3",
                fg="white",
                font=("Segoe UI", 13, "bold"),
                cursor="hand2",
                width=18,
                pady=12,
                relief="flat",
                bd=0,
                activebackground="#1976d2",
                activeforeground="white",
            ).pack(side="left", padx=(150, 10))

            tk.Button(
                btn_frame,
                text="✕ Cancel",
                command=self.cancel_edit,
                bg="#757575",
                fg="white",
                font=("Segoe UI", 13, "bold"),
                cursor="hand2",
                width=12,
                pady=12,
                relief="flat",
                bd=0,
                activebackground="#616161",
                activeforeground="white",
            ).pack(side="left", padx=10)
        else:
            tk.Button(
                btn_frame,
                text="✓ Log Meal",
                command=self.create_meal_submit,
                bg="#4caf50",
                fg="white",
                font=("Segoe UI", 13, "bold"),
                cursor="hand2",
                width=18,
                pady=12,
                relief="flat",
                bd=0,
                activebackground="#388e3c",
                activeforeground="white",
            ).pack(side="left", padx=(150, 10))

            tk.Button(
                btn_frame,
                text="← Back",
                command=self.show_dashboard,
                bg="#757575",
                fg="white",
                font=("Segoe UI", 13, "bold"),
                cursor="hand2",
                width=12,
                pady=12,
                relief="flat",
                bd=0,
                activebackground="#616161",
                activeforeground="white",
            ).pack(side="left", padx=10)

    def create_form_field(
        self,
        parent: tk.Frame,
        label: str,
        row: int,
        required: bool = False,
        is_date: bool = False,
        options: Optional[List[str]] = None,
        multiline: bool = False,
    ) -> None:
        """Create form field with label and input - modern design."""
        field_frame = tk.Frame(parent, bg="white")
        field_frame.pack(fill="x", pady=10)

        label_text = label
        if required:
            label_text += " *"

        tk.Label(
            field_frame,
            text=label_text,
            font=("Segoe UI", 11, "bold"),
            bg="white",
            fg="#424242",
            anchor="w",
        ).pack(fill="x", pady=(0, 6))

        if multiline:
            widget: tk.Widget = scrolledtext.ScrolledText(
                field_frame,
                font=("Segoe UI", 11),
                height=4,
                wrap="word",
                relief="solid",
                bd=1,
                highlightthickness=1,
                highlightcolor="#2196f3",
                highlightbackground="#e0e0e0",
            )
        elif options:
            combo = ttk.Combobox(
                field_frame,
                font=("Segoe UI", 11),
                values=options,
                state="readonly",
            )
            combo.current(0)
            widget = combo
        else:
            widget = tk.Entry(
                field_frame,
                font=("Segoe UI", 11),
                relief="solid",
                bd=1,
                highlightthickness=1,
                highlightcolor="#2196f3",
                highlightbackground="#e0e0e0",
            )

        widget.pack(fill="x", ipady=8)

        field_name = label.lower().replace(" ", "_")
        setattr(self, f"entry_{field_name}", widget)

        if is_date and not self.editing_meal_id and isinstance(widget, tk.Entry):
            widget.insert(0, self.selected_date)

    def load_meal_data(self) -> None:
        """Load meal data for editing."""
        meals = self.db.read_all_meals()
        meal_data = next(
            (meal for meal in meals if meal[0] == self.editing_meal_id), None
        )

        if meal_data is None:
            return

        _, date, meal_type, food_name, calories, serving_size, notes, _ = meal_data

        self.entry_date.delete(0, "end")
        self.entry_date.insert(0, date)

        self.entry_meal_type.set(meal_type)

        self.entry_food_name.delete(0, "end")
        self.entry_food_name.insert(0, food_name)

        self.entry_calories.delete(0, "end")
        self.entry_calories.insert(0, str(calories))

        self.entry_serving_size.delete(0, "end")
        self.entry_serving_size.insert(0, serving_size or "")

        self.entry_notes.delete("1.0", "end")
        self.entry_notes.insert("1.0", notes or "")

    def create_meal_submit(self) -> None:
        """Handle meal creation form submission."""
        try:
            date = self.entry_date.get().strip()
            meal_type = self.entry_meal_type.get()
            food_name = self.entry_food_name.get().strip()
            calories_str = self.entry_calories.get().strip()
            serving_size = self.entry_serving_size.get().strip()
            notes = self.entry_notes.get("1.0", "end").strip()

            if not food_name or not calories_str:
                messagebox.showerror(
                    "Error", "Please fill in food name and calories"
                )
                return

            try:
                calories = float(calories_str)
                if calories < 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror(
                    "Error", "Please enter a valid number for calories"
                )
                return

            if self.db.create_meal(
                date, meal_type, food_name, calories, serving_size, notes
            ):
                messagebox.showinfo("Success", "✓ Meal logged successfully!")
                self.show_dashboard()

        except Exception as error:
            messagebox.showerror("Error", f"Failed to create meal: {error}")

    def update_meal_submit(self) -> None:
        """Handle meal update form submission."""
        try:
            meal_type = self.entry_meal_type.get()
            food_name = self.entry_food_name.get().strip()
            calories_str = self.entry_calories.get().strip()
            serving_size = self.entry_serving_size.get().strip()
            notes = self.entry_notes.get("1.0", "end").strip()

            if not food_name or not calories_str:
                messagebox.showerror(
                    "Error", "Please fill in food name and calories"
                )
                return

            try:
                calories = float(calories_str)
                if calories < 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror(
                    "Error", "Please enter a valid number for calories"
                )
                return

            if self.db.update_meal(
                self.editing_meal_id, meal_type, food_name, calories, serving_size, notes
            ):
                messagebox.showinfo("Success", "✓ Meal updated successfully!")
                self.editing_meal_id = None
                self.show_dashboard()

        except Exception as error:
            messagebox.showerror("Error", f"Failed to update meal: {error}")

    def edit_meal(self, meal_id: int) -> None:
        """Start editing a meal."""
        self.editing_meal_id = meal_id
        self.show_add_meal()

    def cancel_edit(self) -> None:
        """Cancel meal editing."""
        self.editing_meal_id = None
        self.show_dashboard()

    def delete_meal_confirm(self, meal_id: int) -> None:
        """Confirm and delete meal."""
        if messagebox.askyesno(
            "Confirm Delete", "Are you sure you want to delete this meal entry?"
        ):
            if self.db.delete_meal(meal_id):
                messagebox.showinfo("Success", "✓ Meal deleted successfully!")
                self.show_dashboard()

    # -------------------------------------------------------------- All logs

    def show_all_logs(self) -> None:
        """Display all meal logs with modern design."""
        self.clear_main_container()
        self.update_nav_buttons("all_logs")

        canvas = tk.Canvas(self.main_container, bg="#f5f7fa", highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            self.main_container, orient="vertical", command=canvas.yview
        )
        scrollable_frame = tk.Frame(canvas, bg="#f5f7fa")

        scrollable_frame.bind(
            "<Configure>",
            lambda event: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfig(window_id, width=event.width),
        )
        canvas.configure(yscrollcommand=scrollbar.set)

        header_frame = tk.Frame(scrollable_frame, bg="white", relief="flat")
        header_frame.pack(fill="x", padx=20, pady=15)

        shadow = tk.Frame(header_frame, bg="#e0e0e0", height=2)
        shadow.pack(side="bottom", fill="x")

        content_header = tk.Frame(header_frame, bg="white")
        content_header.pack(fill="x", padx=20, pady=15)

        tk.Label(
            content_header,
            text="📋 All Meal Logs",
            font=("Segoe UI", 20, "bold"),
            bg="white",
            fg="#424242",
        ).pack(side="left")

        tk.Button(
            content_header,
            text="← Back to Dashboard",
            command=self.show_dashboard,
            bg="#757575",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            cursor="hand2",
            padx=20,
            pady=8,
            relief="flat",
            bd=0,
            activebackground="#616161",
            activeforeground="white",
        ).pack(side="right")

        all_meals = self.db.read_all_meals()

        if not all_meals:
            empty_frame = tk.Frame(scrollable_frame, bg="white")
            empty_frame.pack(fill="both", expand=True, padx=20, pady=50)

            tk.Label(
                empty_frame, text="📭", font=("Segoe UI", 64), bg="white"
            ).pack(pady=20)

            tk.Label(
                empty_frame,
                text="No meals logged yet",
                font=("Segoe UI", 18, "bold"),
                bg="white",
                fg="#9e9e9e",
            ).pack()

            tk.Label(
                empty_frame,
                text="Start your health journey by logging your first meal!",
                font=("Segoe UI", 12),
                bg="white",
                fg="#bdbdbd",
            ).pack(pady=(10, 30))
        else:
            meals_by_date = {}
            for meal in all_meals:
                date = meal[1]
                meals_by_date.setdefault(date, []).append(meal)

            for date in sorted(meals_by_date.keys(), reverse=True):
                self.create_date_log_section(scrollable_frame, date, meals_by_date[date])

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def create_date_log_section(
        self,
        parent: tk.Frame,
        date: str,
        meals: List[Tuple],
    ) -> None:
        """Create log section for specific date with modern design."""
        section_frame = tk.Frame(parent, bg="white", relief="flat", bd=0)
        section_frame.pack(fill="x", padx=20, pady=10)

        shadow = tk.Frame(section_frame, bg="#e0e0e0", height=2)
        shadow.pack(side="bottom", fill="x")

        total_calories = sum(meal[4] for meal in meals)
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%A, %B %d, %Y")

        header_frame = tk.Frame(section_frame, bg="#f5f5f5")
        header_frame.pack(fill="x", padx=0, pady=0)

        header_content = tk.Frame(header_frame, bg="#f5f5f5")
        header_content.pack(fill="x", padx=20, pady=15)

        tk.Label(
            header_content,
            text=f"📅 {formatted_date}",
            font=("Segoe UI", 15, "bold"),
            bg="#f5f5f5",
            fg="#424242",
        ).pack(side="left")

        cal_badge = tk.Frame(header_content, bg="#e8f5e9", padx=15, pady=8)
        cal_badge.pack(side="right")

        tk.Label(
            cal_badge,
            text=f"{int(total_calories)} calories",
            font=("Segoe UI", 13, "bold"),
            bg="#e8f5e9",
            fg="#2e7d32",
        ).pack()

        for meal in meals:
            meal_id, _, meal_type, food_name, calories, serving_size, notes, _ = meal

            meal_frame = tk.Frame(section_frame, bg="white", relief="flat", bd=0)
            meal_frame.pack(fill="x", padx=20, pady=5)

            meal_colors = {
                "Breakfast": "#ff9800",
                "Lunch": "#4caf50",
                "Dinner": "#2196f3",
                "Snacks": "#9c27b0",
            }

            border = tk.Frame(
                meal_frame, bg=meal_colors.get(meal_type, "#757575"), width=5
            )
            border.pack(side="left", fill="y")

            content_frame = tk.Frame(meal_frame, bg="white")
            content_frame.pack(side="left", fill="both", expand=True, padx=15, pady=12)

            badge_colors = {
                "Breakfast": "#fff3e0",
                "Lunch": "#e8f5e9",
                "Dinner": "#e3f2fd",
                "Snacks": "#f3e5f5",
            }
            badge_text_colors = {
                "Breakfast": "#e65100",
                "Lunch": "#1b5e20",
                "Dinner": "#0d47a1",
                "Snacks": "#4a148c",
            }

            badge_frame = tk.Frame(
                content_frame,
                bg=badge_colors.get(meal_type, "#f5f5f5"),
                padx=10,
                pady=4,
            )
            badge_frame.pack(side="left", padx=(0, 12))

            meal_icons = {
                "Breakfast": "🌅",
                "Lunch": "🌞",
                "Dinner": "🌙",
                "Snacks": "🍿",
            }

            tk.Label(
                badge_frame,
                text=f"{meal_icons.get(meal_type, '🍴')} {meal_type}",
                font=("Segoe UI", 9, "bold"),
                bg=badge_colors.get(meal_type, "#f5f5f5"),
                fg=badge_text_colors.get(meal_type, "#424242"),
            ).pack()

            details_frame = tk.Frame(content_frame, bg="white")
            details_frame.pack(side="left", fill="both", expand=True)

            tk.Label(
                details_frame,
                text=food_name,
                font=("Segoe UI", 12, "bold"),
                bg="white",
                fg="#212121",
                anchor="w",
            ).pack(fill="x")

            if serving_size:
                tk.Label(
                    details_frame,
                    text=f"📏 {serving_size}",
                    font=("Segoe UI", 10),
                    bg="white",
                    fg="#757575",
                    anchor="w",
                ).pack(fill="x", pady=(2, 0))

            if notes:
                tk.Label(
                    details_frame,
                    text=f"💭 {notes}",
                    font=("Segoe UI", 10, "italic"),
                    bg="white",
                    fg="#9e9e9e",
                    anchor="w",
                ).pack(fill="x", pady=(2, 0))

            actions_frame = tk.Frame(meal_frame, bg="white")
            actions_frame.pack(side="right", padx=15, pady=12)

            cal_display = tk.Frame(actions_frame, bg="#e8f5e9", padx=12, pady=6)
            cal_display.pack(side="left", padx=(0, 10))

            tk.Label(
                cal_display,
                text=f"{int(calories)} cal",
                font=("Segoe UI", 11, "bold"),
                bg="#e8f5e9",
                fg="#2e7d32",
            ).pack()

            tk.Button(
                actions_frame,
                text="✏️ Edit",
                command=(lambda m_id=meal_id: self.edit_meal(m_id)),
                bg="#2196f3",
                fg="white",
                font=("Segoe UI", 10, "bold"),
                cursor="hand2",
                padx=12,
                pady=5,
                width=10,
                relief="flat",
                bd=0,
                activebackground="#1976d2",
                activeforeground="white",
            ).pack(side="left", padx=4)

            tk.Button(
                actions_frame,
                text="🗑️ Delete",
                command=(lambda m_id=meal_id: self.delete_meal_confirm(m_id)),
                bg="#f44336",
                fg="white",
                font=("Segoe UI", 10, "bold"),
                cursor="hand2",
                padx=12,
                pady=5,
                width=10,
                relief="flat",
                bd=0,
                activebackground="#d32f2f",
                activeforeground="white",
            ).pack(side="left", padx=4)

    # --------------------------------------------------------------- Lifecycle

    def on_closing(self) -> None:
        """Handle application closing."""
        self.db.close()
        self.root.destroy()


def run_app() -> None:
    """Convenience function to run the Tkinter app."""
    root = tk.Tk()
    app = CalQApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()