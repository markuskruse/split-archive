#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import zipfile
import re

APP_TITLE = "STL Archiver"

def find_sevenz():
    """Try to find the 7z/7z.exe binary. Return absolute path or None."""
    # 1) PATH
    for name in ("7z", "7z.exe"):
        p = shutil.which(name)
        if p:
            return p

    # 2) Common Windows locations
    common_windows = [
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
    ]
    for p in common_windows:
        if os.path.isfile(p):
            return p

    # Not found
    return None

class STLArchiverApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("720x520")
        self.minsize(600, 420)

        self.current_folder = tk.StringVar(value="")
        self.sevenz_path = find_sevenz()
        self.file_names = []
        self.archived_counts = {}
        self.last_archive_path = None

        self._build_ui()
        self._bind_events()

        # Start by asking for a folder
        self.after(100, self.choose_folder)

    def _build_ui(self):
        # Top: folder chooser
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="Folder:").pack(side="left")
        self.folder_entry = ttk.Entry(top, textvariable=self.current_folder)
        self.folder_entry.pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(top, text="Browse…", command=self.choose_folder).pack(side="left")
        ttk.Button(top, text="Refresh", command=self.refresh_list).pack(side="left", padx=(6,0))

        # Middle: listbox with scrollbar
        mid = ttk.Frame(self, padding=(10, 0))
        mid.pack(fill="both", expand=True)

        self.files_list = tk.Listbox(
            mid,
            selectmode=tk.EXTENDED,
            activestyle="none",
            exportselection=False
        )
        self.files_list_scroll = ttk.Scrollbar(mid, orient="vertical", command=self.files_list.yview)
        self.files_list.configure(yscrollcommand=self.files_list_scroll.set)

        self.files_list.pack(side="left", fill="both", expand=True)
        self.files_list_scroll.pack(side="left", fill="y")

        # Bottom controls
        bot = ttk.Frame(self, padding=10)
        bot.pack(fill="x")

        self.count_label = ttk.Label(bot, text="0 files")
        self.count_label.pack(side="left")

        ttk.Button(bot, text="Select All", command=self.select_all).pack(side="right")
        ttk.Button(bot, text="Clear", command=self.clear_selection).pack(side="right", padx=(6, 6))
        self.archive_btn = ttk.Button(bot, text="Archive Selected…", command=self.archive_selected)
        self.archive_btn.pack(side="right", padx=(6, 6))

        # Status bar
        self.status = tk.StringVar(value="Ready.")
        status_bar = ttk.Label(self, textvariable=self.status, anchor="w", relief="sunken")
        status_bar.pack(side="bottom", fill="x")

        # Menu (to set 7z path manually)
        menubar = tk.Menu(self)
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Set 7-Zip executable…", command=self.set_sevenz_path)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        self.config(menu=menubar)

        # Themed style polish
        try:
            self.style = ttk.Style(self)
            if sys.platform == "win32":
                self.style.theme_use("vista")
            else:
                self.style.theme_use(self.style.theme_use())
        except Exception:
            pass

    def _bind_events(self):
        self.files_list.bind("<<ListboxSelect>>", lambda e: self.update_status_selection())

    def choose_folder(self):
        initial = self.current_folder.get() or os.path.expanduser("~")
        folder = filedialog.askdirectory(title="Select folder", initialdir=initial)
        if folder:
            self.current_folder.set(folder)
            self.refresh_list()

    def refresh_list(self):
        folder = self.current_folder.get()
        self.files_list.delete(0, tk.END)
        self.count_label.config(text="0 files")
        self.file_names = []
        if not folder or not os.path.isdir(folder):
            self.status.set("Choose a valid folder.")
            return

        try:
            names = [
                f for f in os.listdir(folder)
                if os.path.isfile(os.path.join(folder, f)) and f.lower().endswith(".stl")
            ]
            names.sort(key=lambda s: s.lower())
            self.file_names = names
            for name in names:
                self.files_list.insert(tk.END, self._format_display_name(name))
            self.count_label.config(text=f"{len(names)} files")
            self.status.set(f"Loaded {len(names)} STL file(s).")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to list files:\n{e}")
            self.status.set("Error listing files.")

    def select_all(self):
        self.files_list.select_set(0, tk.END)
        self.update_status_selection()

    def clear_selection(self):
        self.files_list.selection_clear(0, tk.END)
        self.update_status_selection()

    def update_status_selection(self):
        sel = len(self.files_list.curselection())
        self.status.set(f"{sel} selected.")

    def set_sevenz_path(self):
        path = filedialog.askopenfilename(
            title="Locate 7-Zip executable (7z/7z.exe)",
            filetypes=[("7-Zip", "7z 7z.exe *"), ("All files", "*.*")]
        )
        if path:
            self.sevenz_path = path
            self.status.set(f"7-Zip set to: {path}")

    def archive_selected(self):
        folder = self.current_folder.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showwarning("No folder", "Please choose a valid folder first.")
            return

        selection = [self.file_names[i] for i in self.files_list.curselection()]
        if not selection:
            messagebox.showwarning("No files selected", "Select one or more STL files to archive.")
            return

        already_archived = [name for name in selection if self.archived_counts.get(self._file_key(name), 0) > 0]
        if already_archived:
            formatted = "\n".join(already_archived)
            messagebox.showwarning(
                "Already archived",
                "The following files have been archived before:\n\n"
                f"{formatted}\n\nArchiving them again will create duplicates in the new archive."
            )

        # Ask for archive filename
        default_name = "stl_archive.zip"
        initialdir = (
            os.path.dirname(self.last_archive_path)
            if self.last_archive_path
            else (folder or os.path.expanduser("~"))
        )
        initialfile = self._suggest_next_archive_name(default_name)
        archive_path = filedialog.asksaveasfilename(
            title="Save archive as",
            defaultextension=".zip",
            initialdir=initialdir,
            initialfile=initialfile,
            filetypes=[("Zip archive", "*.zip"), ("7-Zip archive", "*.7z"), ("All files", "*.*")]
        )
        if not archive_path:
            return

        archive_ext = os.path.splitext(archive_path)[1].lower()
        use_zip = archive_ext in ("", ".zip")

        sevenz = None
        if not use_zip:
            sevenz = self.sevenz_path or find_sevenz()
            if not sevenz or not os.path.isfile(sevenz):
                if not messagebox.askyesno(
                    "7-Zip not found",
                    "7-Zip (7z/7z.exe) was not found. Do you want to locate it now?"
                ):
                    return
                self.set_sevenz_path()
                sevenz = self.sevenz_path

            if not sevenz or not os.path.isfile(sevenz):
                messagebox.showerror("7-Zip required", "Cannot proceed without a valid 7-Zip executable.")
                return

        # Run archive creation with UI feedback
        self.status.set("Archiving… please wait.")
        self.archive_btn.state(["disabled"])
        self.update_idletasks()

        try:
            # Ensure archive directory exists
            os.makedirs(os.path.dirname(archive_path) or ".", exist_ok=True)

            if use_zip:
                self._create_zip_archive(archive_path, folder, selection)
            else:
                self._create_sevenz_archive(sevenz, archive_path, folder, selection)

            messagebox.showinfo("Success", f"Created archive:\n{archive_path}")
            self.status.set("Archive created successfully.")
            self._mark_files_archived(selection)
            self.last_archive_path = archive_path
        except RuntimeError as e:
            messagebox.showerror("Archiving error", str(e))
            self.status.set("Archiving failed.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while archiving:\n{e}")
            self.status.set("Archiving failed.")
        finally:
            self.archive_btn.state(["!disabled"])

    def _file_key(self, name):
        folder = self.current_folder.get()
        return os.path.join(folder, name)

    def _suggest_next_archive_name(self, fallback_name):
        if not self.last_archive_path:
            return fallback_name

        base = os.path.basename(self.last_archive_path)
        name, ext = os.path.splitext(base)
        match = re.search(r"(.*?)(\d+)$", name)
        if match:
            prefix, digits = match.groups()
            incremented = str(int(digits) + 1).zfill(len(digits))
            return f"{prefix}{incremented}{ext}"
        return base

    def _format_display_name(self, name):
        count = self.archived_counts.get(self._file_key(name), 0)
        if count <= 0:
            return name
        if count == 1:
            return f"{name} (archived)"
        return f"{name} (archived ×{count})"

    def _mark_files_archived(self, names):
        current_selection = set(self.files_list.curselection())
        updated_indexes = set()
        for name in names:
            key = self._file_key(name)
            self.archived_counts[key] = self.archived_counts.get(key, 0) + 1
            for idx, listed_name in enumerate(self.file_names):
                if listed_name == name:
                    updated_indexes.add(idx)

        for idx in sorted(updated_indexes):
            display = self._format_display_name(self.file_names[idx])
            self.files_list.delete(idx)
            self.files_list.insert(idx, display)
            if idx in current_selection:
                self.files_list.selection_set(idx)

        if updated_indexes:
            self.update_status_selection()

    def _create_zip_archive(self, archive_path, folder, names):
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for name in names:
                zf.write(os.path.join(folder, name), arcname=name)

    def _create_sevenz_archive(self, sevenz, archive_path, folder, names):
        cmd = [sevenz, "a", archive_path] + names
        proc = subprocess.run(
            cmd,
            cwd=folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        if proc.returncode != 0:
            raise RuntimeError(f"7-Zip returned code {proc.returncode}.\n\nOutput:\n{proc.stdout}")

def main():
    app = STLArchiverApp()
    app.mainloop()

if __name__ == "__main__":
    main()
