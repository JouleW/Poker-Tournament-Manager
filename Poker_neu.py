import tkinter as tk
from tkinter import messagebox, simpledialog, Toplevel
import time
import threading
import random
import winsound
import math
from math import ceil

LEVELS = [
    {"level": 1, "small_blind": 50, "big_blind": 100, "ante": 0, "duration": 300},
    {"level": 2, "small_blind": 100, "big_blind": 200, "ante": 0, "duration": 300},
    {"level": 3, "small_blind": 200, "big_blind": 400, "ante": 25, "duration": 300},
    {"level": 4, "small_blind": 400, "big_blind": 800, "ante": 50, "duration": 300},
    {"level": 5, "small_blind": 800, "big_blind": 1600, "ante": 100, "duration": 300},
]

MIN_PLAYERS_PER_TABLE = 2
MAX_PLAYERS_PER_TABLE = 9

class Player:
    def __init__(self, name):
        self.name = name
        self.eliminations = 0
        self.seat = None
        self.table = None

class Table:
    def __init__(self):
        self.players = []

    def add_player(self, player):
        if len(self.players) < MAX_PLAYERS_PER_TABLE:
            self.players.append(player)
            return True
        return False

class PokerGame:
    def __init__(self):
        self.tables = [Table()]

    def add_player(self, player):
        # Versuche, den Spieler an einen bestehenden Tisch zu setzen
        for table in self.tables:
            if table.add_player(player):
                return
        # Falls alle Tische voll sind, neuen Tisch erstellen
        new_table = Table()
        new_table.add_player(player)
        self.tables.append(new_table)

class PokerTournamentManager(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Poker Turniermanager")
        self.geometry("1100x600")
        self.resizable(True, True)

        self.players = []
        # NEU: Liste für eliminierte Spieler mit Details
        self.eliminated_players = []  # List of dicts: {"name", "eliminations", "by", "time"}
        self.level_index = 0
        self.time_left = LEVELS[0]["duration"]
        self.timer_running = False
        self.num_tables = 1
        self.total_time_elapsed = 0  # Gesamtzeit
        self.one_minute_warning_played = False

        self.create_widgets()
        self.update_level_display()
        self.update_ranking()
        self.update_eliminated_display()

    def create_widgets(self):
        self.player_entry = tk.Entry(self)
        self.player_entry.place(x=20, y=20, width=200)
        tk.Button(self, text="Spieler hinzufügen", command=self.add_player).place(x=230, y=18)

        # tk.Label(self, text="Tische (automatisch):").place(x=350, y=20)
        # self.table_label = tk.Label(self, text="1")
        # self.table_label.place(x=480, y=20, width=40)

        tk.Button(self, text="Sitzplätze zuweisen", command=self.assign_seats).place(x=20, y=55)
        tk.Button(self, text="Level-Einstellungen", command=self.edit_levels).place(x=150, y=55)
        tk.Button(self, text="Einstellungen", command=self.open_settings).place(x=280, y=55)

        self.level_label = tk.Label(self, text="", font=("Arial", 16))
        self.level_label.place(x=20, y=100)
        self.timer_label = tk.Label(self, text="", font=("Arial", 24))
        self.timer_label.place(x=20, y=140)
        tk.Button(self, text="Timer Start", command=self.start_timer).place(x=20, y=200)
        tk.Button(self, text="Timer Pause", command=self.pause_timer).place(x=120, y=200)
        tk.Button(self, text="Nächstes Level", command=self.next_level).place(x=220, y=200)

        # Vorschau nächstes Level
        self.next_level_label = tk.Label(self, text="", font=("Arial", 12, "italic"))
        self.next_level_label.place(x=20, y=180)

        # Gesamtzeit-Anzeige
        self.total_time_label = tk.Label(self, text="Gesamtzeit: 00:00", font=("Arial", 12))
        self.total_time_label.place(x=20, y=240)

        self.ranking_label = tk.Label(self, text="Rangliste", font=("Arial", 14))
        self.ranking_label.place(x=500, y=20)
        self.ranking_listbox = tk.Listbox(self, width=40, height=20)
        self.ranking_listbox.place(x=500, y=50)

        tk.Button(self, text="Spieler eliminieren", command=self.eliminate_player).place(x=20, y=290)
        self.elim_entry = tk.Entry(self)
        self.elim_entry.place(x=150, y=292, width=100)
        tk.Label(self, text="durch").place(x=260, y=295)
        self.elim_by_entry = tk.Entry(self)
        self.elim_by_entry.place(x=300, y=292, width=100)

        self.seat_label = tk.Label(self, text="Sitzplan", font=("Arial", 14))
        self.seat_label.place(x=20, y=340)
        self.seat_listbox = tk.Listbox(self, width=60, height=10)
        self.seat_listbox.place(x=20, y=370)

        # Eliminierte Spieler
        self.eliminated_label = tk.Label(self, text="Eliminierte Spieler", font=("Arial", 14))
        self.eliminated_label.place(x=800, y=20)
        self.eliminated_listbox = tk.Listbox(self, width=45, height=20)
        self.eliminated_listbox.place(x=800, y=50)

    def add_player(self):
        name = self.player_entry.get().strip()
        if name and not any(p.name == name for p in self.players) and not any(p["name"] == name for p in self.eliminated_players):
            self.players.append(Player(name))
            self.player_entry.delete(0, tk.END)
            self.update_ranking()
            self.update_tables_auto()
        else:
            messagebox.showwarning("Fehler", "Ungültiger oder doppelter Name.")

    def update_tables_auto(self):
        n = len(self.players)
        if n == 0:
            self.num_tables = 1
        else:
            self.num_tables = max(1, math.ceil(n / MAX_PLAYERS_PER_TABLE))
        self.table_label.config(text=str(self.num_tables))

    def assign_seats(self):
        n = len(self.players)
        if n == 0:
            messagebox.showwarning("Fehler", "Keine Spieler vorhanden.")
            return

        # Merke die vorherige Tischanzahl (Standard: 1)
        old_num_tables = getattr(self, "last_num_tables", 1)

        # Berechne neue Tischanzahl
        self.num_tables = max(1, math.ceil(n / MAX_PLAYERS_PER_TABLE))
        self.table_label.config(text=str(self.num_tables))

        # Speichere die aktuelle Tischanzahl für das nächste Mal
        self.last_num_tables = self.num_tables

        # Prüfe, ob Tische zusammengelegt wurden
        if self.num_tables < old_num_tables:
            messagebox.showinfo(
                "Tische zusammengelegt",
                f"Die Anzahl der Tische wurde von {old_num_tables} auf {self.num_tables} reduziert. "
                "Bitte setzen Sie die Spieler neu um."
            )

        # Spieler mischen und auf Tische verteilen
        random.shuffle(self.players)
        tables = [[] for _ in range(self.num_tables)]
        for idx, player in enumerate(self.players):
            table_idx = idx % self.num_tables
            tables[table_idx].append(player)

        # Sitz- und Tischzuweisung
        for t_idx, table in enumerate(tables, 1):
            for s_idx, player in enumerate(table, 1):
                player.table = t_idx
                player.seat = s_idx

        self.update_seat_display()

    def update_seat_display(self):
        self.seat_listbox.delete(0, tk.END)
        sorted_players = sorted(self.players, key=lambda p: (p.table if p.table else 999, p.seat if p.seat else 999))
        for player in sorted_players:
            if player.table and player.seat:
                self.seat_listbox.insert(tk.END, f"Tisch {player.table}, Platz {player.seat}: {player.name}")

    def start_timer(self):
        if not self.timer_running:
            self.timer_running = True
            self.run_timer()

    def pause_timer(self):
        self.timer_running = False
        if self._timer_after_id is not None:
            self.after_cancel(self._timer_after_id)
            self._timer_after_id = None

    def run_timer(self):
        if self.timer_running and self.time_left > 0:
            self.time_left -= 1
            self.total_time_elapsed += 1  # Gesamtzeit hochzählen
            self.update_level_display()
            self.update_total_time_display()

            # 1-Minuten-Warnung
            if self.time_left == 60 and not self.one_minute_warning_played:
                try:
                    import winsound
                    winsound.Beep(1000, 300)
                except ImportError:
                    pass
                self.one_minute_warning_played = True

            # Timer-Callback speichern
            self._timer_after_id = self.after(1000, self.run_timer)
        elif self.time_left == 0:
            self.play_sound()
            self.next_level()
            self.one_minute_warning_played = False  # Reset für das nächste Level

    def next_level(self):
        self.timer_running = False
        if self._timer_after_id is not None:
            self.after_cancel(self._timer_after_id)
            self._timer_after_id = None
        self.level_index += 1
        if self.level_index >= len(LEVELS):
            messagebox.showinfo("Turnier", "Turnier beendet!")
            self.level_index = len(LEVELS) - 1
        else:
            self.time_left = LEVELS[self.level_index]["duration"]
            self.update_level_display()
            self.play_sound()
            self.one_minute_warning_played = False  # Reset für das nächste Level
            self.start_timer()

    def update_level_display(self):
        level = LEVELS[self.level_index]
        small_blind = level["small_blind"]
        big_blind = level["big_blind"]
        ante = level.get("ante", 0)
        # Aktuelles Level anzeigen (ohne Zeit)
        self.level_label.config(
            text=f"Aktuelles Level: SB {small_blind} / BB {big_blind} / Ante {ante}"
        )

        # Nächstes Level anzeigen
        if self.level_index + 1 < len(LEVELS):
            next_level = LEVELS[self.level_index + 1]
            next_sb = next_level["small_blind"]
            next_bb = next_level["big_blind"]
            next_ante = next_level.get("ante", 0)
            self.next_level_label.config(
                text=f"Nächstes Level: SB {next_sb} / BB {next_bb} / Ante {next_ante}"
            )
        else:
            self.next_level_label.config(text="Nächstes Level: ---")

        # Großer Timer bleibt wie gehabt
        mins, secs = divmod(self.time_left, 60)
        self.timer_label.config(text=f"{mins:02d}:{secs:02d}")

    def update_total_time_display(self):
        mins, secs = divmod(self.total_time_elapsed, 60)
        self.total_time_label.config(text=f"Gesamtzeit: {mins:02d}:{secs:02d}")

    def play_sound(self):
        try:
            winsound.Beep(1000, 500)
        except:
            pass

    def eliminate_player(self):
        elim_name = self.elim_entry.get().strip()
        by_name = self.elim_by_entry.get().strip()
        elim_player = next((p for p in self.players if p.name == elim_name), None)
        by_player = next((p for p in self.players if p.name == by_name), None)
        if elim_player and by_player and elim_player != by_player:
            self.players.remove(elim_player)
            by_player.eliminations += 1
            # Zeit des Ausscheidens berechnen
            mins, secs = divmod(self.total_time_elapsed, 60)
            time_str = f"{mins:02d}:{secs:02d}"
            # NEU: Details zum eliminierten Spieler speichern
            self.eliminated_players.append({
                "name": elim_player.name,
                "eliminations": elim_player.eliminations,
                "by": by_player.name,
                "time": time_str
            })
            self.elim_entry.delete(0, tk.END)
            self.elim_by_entry.delete(0, tk.END)
            self.update_ranking()
            self.update_tables_auto()
            self.assign_seats()
            self.update_eliminated_display()
        else:
            messagebox.showwarning("Fehler", "Ungültige Namen oder gleicher Spieler.")

    def update_ranking(self):
        self.ranking_listbox.delete(0, tk.END)
        sorted_players = sorted(self.players, key=lambda p: p.eliminations, reverse=True)
        for idx, player in enumerate(sorted_players, 1):
            self.ranking_listbox.insert(
                tk.END, f"{idx}. {player.name} - Eliminierungen: {player.eliminations}"
            )

    def update_eliminated_display(self):
        self.eliminated_listbox.delete(0, tk.END)
        for idx, info in enumerate(self.eliminated_players, 1):
            self.eliminated_listbox.insert(
                tk.END,
                f"{idx}. {info['name']} (eliminiert um {info['time']}, "
                f"Elims: {info['eliminations']}, durch: {info['by']})"
            )

    def edit_levels(self):
        LevelEditor(self)

    def open_settings(self):
        settings_win = Toplevel(self)
        settings_win.title("Einstellungen")

        # Tischlimit
        tk.Label(settings_win, text="Maximale Spieler pro Tisch:").grid(row=0, column=0, sticky="e")
        table_limit_var = tk.IntVar(value=MAX_PLAYERS_PER_TABLE)
        tk.Entry(settings_win, textvariable=table_limit_var).grid(row=0, column=1)

        def save_settings():
            global MAX_PLAYERS_PER_TABLE
            MAX_PLAYERS_PER_TABLE = table_limit_var.get()
            settings_win.destroy()
            messagebox.showinfo("Einstellungen", "Einstellungen gespeichert.")

        tk.Button(settings_win, text="Speichern", command=save_settings).grid(row=len(LEVELS)+1, column=0, columnspan=2)

class LevelEditor(Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Level-Einstellungen")
        self.parent = parent
        self.level_vars = []
        self.draw_levels()

    def draw_levels(self):
        for widget in self.winfo_children():
            widget.destroy()
        tk.Label(self, text="Level").grid(row=0, column=0)
        tk.Label(self, text="Small Blind").grid(row=0, column=1)
        tk.Label(self, text="Big Blind").grid(row=0, column=2)
        tk.Label(self, text="Ante").grid(row=0, column=3)
        tk.Label(self, text="Dauer (Sek)").grid(row=0, column=4)

        self.level_vars = []
        for i, level in enumerate(LEVELS):
            level_var = {
                "level": tk.IntVar(value=level["level"]),
                "small_blind": tk.IntVar(value=level["small_blind"]),
                "big_blind": tk.IntVar(value=level["big_blind"]),
                "ante": tk.IntVar(value=level.get("ante", 0)),
                "duration": tk.IntVar(value=level["duration"])
            }
            tk.Entry(self, textvariable=level_var["level"], width=5).grid(row=i+1, column=0)
            tk.Entry(self, textvariable=level_var["small_blind"], width=10).grid(row=i+1, column=1)
            tk.Entry(self, textvariable=level_var["big_blind"], width=10).grid(row=i+1, column=2)
            tk.Entry(self, textvariable=level_var["ante"], width=10).grid(row=i+1, column=3)
            tk.Entry(self, textvariable=level_var["duration"], width=10).grid(row=i+1, column=4)
            self.level_vars.append(level_var)

        tk.Button(self, text="Speichern", command=self.save_levels).grid(row=len(LEVELS)+1, column=0, columnspan=5)

    def save_levels(self):
        for i, vars in enumerate(self.level_vars):
            LEVELS[i]["level"] = vars["level"].get()
            LEVELS[i]["small_blind"] = vars["small_blind"].get()
            LEVELS[i]["big_blind"] = vars["big_blind"].get()
            LEVELS[i]["ante"] = vars["ante"].get()
            LEVELS[i]["duration"] = vars["duration"].get()
        self.destroy()
        messagebox.showinfo("Level-Einstellungen", "Levels gespeichert.")

if __name__ == "__main__":
    app = PokerTournamentManager()
    app.mainloop()