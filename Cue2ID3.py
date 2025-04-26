import subprocess
import sys
import os
import tkinter as tk
from tkinter import filedialog, messagebox

# Check for the mutagen module and prompt user for installation.
try:
    from mutagen.id3 import ID3, TIT2, CHAP, CTOC, CTOCFlags, ID3NoHeaderError
    from mutagen.mp3 import MP3
except ImportError:
    answer = input("Mutagen module not found. Do you want it to be installed now? (y/n): ").strip().lower()
    if answer.startswith("y"):
        print("Installing mutagen...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "mutagen"])
        except subprocess.CalledProcessError as e:
            print("Installation failed:", e)
            sys.exit(1)
        try:
            from mutagen.id3 import ID3, TIT2, CHAP, CTOC, CTOCFlags, ID3NoHeaderError
            from mutagen.mp3 import MP3
        except ImportError:
            print("Mutagen installation appears to have failed. Exiting.")
            sys.exit(1)
    else:
        print("Mutagen is required to run this script. Exiting.")
        sys.exit(1)

# Static settings
input_file_encoding = "cp1252"  # Default encoding for CUE files.


def parse_cue_file(cue_path):
    """
    Parses a CUE file (assumed to be encoded in 'input_file_encoding')
    and returns a list of (title, start_time_ms) tuples.
    """
    chapters = []
    current_title = None
    current_time = None

    with open(cue_path, "r", encoding=input_file_encoding) as f:
        for line in f:
            line = line.strip()
            if line.upper().startswith("TRACK"):
                if current_title is not None and current_time is not None:
                    chapters.append((current_title, current_time))
                current_title = None
                current_time = None
            elif line.upper().startswith("TITLE"):
                if '"' in line:
                    current_title = line.split('"')[1]
            elif "INDEX 01" in line.upper():
                try:
                    parts = line.split()
                    time_str = parts[-1]
                    m, s, f = time_str.split(":")
                    m = int(m)
                    s = int(s)
                    f = int(f)
                    current_time = int((m * 60 + s + f / 75.0) * 1000)
                except Exception as e:
                    print("Error parsing time from line:", line, e)
        if current_title is not None and current_time is not None:
            chapters.append((current_title, current_time))
    return chapters

def embed_chapters(mp3_path, chapters):
    """
    Embeds chapter markers into the MP3 as ID3 tags using Mutagen.
    Creates a CTOC frame and then one CHAP frame for each chapter.
    Also creates a backup of the original file (if not already present).
    """
    try:
        tags = ID3(mp3_path)
    except ID3NoHeaderError:
        tags = ID3()

    # Remove existing CHAP/CTOC frames to avoid conflicts.
    for key in list(tags.keys()):
        if key.startswith("CHAP") or key.startswith("CTOC"):
            del tags[key]

    mp3_info = MP3(mp3_path)
    total_duration_ms = int(mp3_info.info.length * 1000)

    child_ids = []
    for idx, (title, start_time) in enumerate(chapters):
        element_id = f"chp{idx+1:02d}"  # Zero-padded (e.g., chp01, chp02)
        child_ids.append(element_id)

    ctoc = CTOC(
        element_id="toc",
        flags=CTOCFlags.TOP_LEVEL | CTOCFlags.ORDERED,
        child_element_ids=child_ids,
        sub_frames=[TIT2(encoding=3, text=["I'm a TOC"])]
    )
    print(f"Added CTOC frame: {ctoc}")
    tags.add(ctoc)
    print(f"Tags after adding CTOC: {tags}")

    for idx, (title, start_time) in enumerate(chapters):
        element_id = f"chp{idx+1:02d}"
        if idx < len(chapters) - 1:
            end_time = chapters[idx+1][1]
        else:
            end_time = total_duration_ms

        chap = CHAP(
            element_id=element_id,
            start_time=start_time,
            end_time=end_time,
            start_offset=0,
            end_offset=0,
            sub_frames=[TIT2(encoding=3, text=title)]
        )
        tags.add(chap)
        print(f"Added CHAP frame: {chap}")

    # Create backup before saving.
    backup_file = mp3_path + ".bak"
    if not os.path.exists(backup_file):
        try:
            with open(mp3_path, "rb") as orig, open(backup_file, "wb") as bak:
                bak.write(orig.read())
            print(f"Backup created: {backup_file}")
        except Exception as e:
            print("Error creating backup:", e)

    # Try to save the modified tags.
    try:
        tags.save(mp3_path, v2_version=4)
        print("Chapters successfully embedded into the MP3 file.")
    except Exception as save_err:
        print("Error saving ID3 tags:", save_err)
        # Restore backup to revert modifications.
        try:
            with open(backup_file, "rb") as bak, open(mp3_path, "wb") as orig:
                orig.write(bak.read())
            print("Original file restored from backup due to save error.")
        except Exception as resex:
            print("Error restoring backup:", resex)
        raise save_err  # Re-raise to indicate processing failure.
    
    print(f"Final tags: {tags}")
    return backup_file  # Return the backup file name for further processing.


def process_files(cue_path, mp3_path):
    """
    Processes a single pair of CUE and MP3 files.
    """
    try:
        chapters = parse_cue_file(cue_path)
        if not chapters:
            raise ValueError("No chapters found in the CUE file.")
        print(f"Found {len(chapters)} chapters in the CUE file.")
        embed_chapters(mp3_path, chapters)
        return True
    except Exception as e:
        print("Error during processing:", e)
        return False


def process_folder(folder_path):
    """
    Processes all MP3 files in a folder (each with a corresponding .cue file).
    """
    processed_any = False
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".mp3"):
            mp3_full = os.path.join(folder_path, filename)
            cue_full = mp3_full + ".cue"
            if os.path.exists(cue_full):
                print(f"Processing:\n  MP3: {mp3_full}\n  CUE: {cue_full}")
                process_files(cue_full, mp3_full)
                processed_any = True
            else:
                print(f"Warning: No CUE file for {mp3_full}")
    if not processed_any:
        print("No suitable MP3/CUE pairs found in folder.")


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MP3 CUE-sheet to ID3 Chapter Writer")
        self.geometry("750x500")
        self.resizable(False, False)
        self.create_widgets()

    def create_widgets(self):
        # A description message for end users.
        self.description = tk.Message(self, 
                                      text=(
                                          "This program merges an MP3 file with its corresponding CUE file to embed chapter markers into ID3V2 tags. "
                                          "In Single Mode, choose an individual MP3 and CUE pair (the CUE field is auto-filled based on the MP3 filename). "
                                          "In Folder Mode, all MP3/CUE pairs (e.g. 'name.mp3' and 'name.mp3.cue') in the chosen folder will be processed."
                                          "You'll get such a pair for example from a CD ripper like foobar2000 with it's 'Generate multi-track files' option. "
                                          "Once processing is successful, the original CUE and backup mp3 files are automatically deleted."
                                          ),
                                          width=480  # controls the wrap length of the text
                                    )
        self.description.grid(row=5, column=0, columnspan=3, pady=10)

        # Mode switch (Single or Folder).
        mode_frame = tk.Frame(self)
        mode_frame.grid(row=0, column=0, columnspan=3, pady=10)
        tk.Label(mode_frame, text="Processing Mode: ").pack(side=tk.LEFT)
        self.mode_option = tk.StringVar(value="single")
        tk.Radiobutton(mode_frame, text="Single Mode", variable=self.mode_option,
                       value="single", command=self.update_mode).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(mode_frame, text="Folder Mode", variable=self.mode_option,
                       value="folder", command=self.update_mode).pack(side=tk.LEFT, padx=5)

        # Widgets for Single Mode.
        self.label_mp3 = tk.Label(self, text="MP3 File:")
        self.label_mp3.grid(row=1, column=0, padx=10, pady=10, sticky="e")
        self.entry_mp3 = tk.Entry(self, width=50)
        self.entry_mp3.grid(row=1, column=1, padx=10, pady=10)
        self.btn_mp3 = tk.Button(self, text="Browse...", command=self.browse_mp3)
        self.btn_mp3.grid(row=1, column=2, padx=10, pady=10)

        self.label_cue = tk.Label(self, text="CUE File:")
        self.label_cue.grid(row=2, column=0, padx=10, pady=10, sticky="e")
        self.entry_cue = tk.Entry(self, width=50)
        self.entry_cue.grid(row=2, column=1, padx=10, pady=10)
        self.btn_cue = tk.Button(self, text="Browse...", command=self.browse_cue)
        self.btn_cue.grid(row=2, column=2, padx=10, pady=10)

        # Widgets for Folder Mode.
        self.label_folder = tk.Label(self, text="Folder:")
        self.entry_folder = tk.Entry(self, width=50)
        self.btn_folder = tk.Button(self, text="Browse...", command=self.browse_folder)
        # Place them in a row (row 3) but hide initially.
        self.label_folder.grid(row=3, column=0, padx=10, pady=10, sticky="e")
        self.entry_folder.grid(row=3, column=1, padx=10, pady=10)
        self.btn_folder.grid(row=3, column=2, padx=10, pady=10)
        self.label_folder.grid_remove()
        self.entry_folder.grid_remove()
        self.btn_folder.grid_remove()

        # Start button.
        self.btn_start = tk.Button(self, text="Start Processing", width=20, command=self.start_processing)
        self.btn_start.grid(row=4, column=1, pady=20)


    def update_mode(self):
        """
        Toggles visibility of single-file and folder controls depending on selected mode.
        """
        mode = self.mode_option.get()
        if mode == "single":
            # Show single mode widgets.
            self.label_mp3.grid()
            self.entry_mp3.grid()
            self.btn_mp3.grid()
            self.label_cue.grid()
            self.entry_cue.grid()
            self.btn_cue.grid()
            # Hide folder mode widgets.
            self.label_folder.grid_remove()
            self.entry_folder.grid_remove()
            self.btn_folder.grid_remove()
        else:
            # Hide single mode widgets.
            self.label_mp3.grid_remove()
            self.entry_mp3.grid_remove()
            self.btn_mp3.grid_remove()
            self.label_cue.grid_remove()
            self.entry_cue.grid_remove()
            self.btn_cue.grid_remove()
            # Show folder mode widgets.
            self.label_folder.grid()
            self.entry_folder.grid()
            self.btn_folder.grid()

    def browse_cue(self):
        path = filedialog.askopenfilename(title="Select CUE File",
                                          filetypes=[("CUE Files", "*.cue"), ("All Files", "*.*")])
        if path:
            self.entry_cue.delete(0, tk.END)
            self.entry_cue.insert(0, path)

    def browse_mp3(self):
        path = filedialog.askopenfilename(title="Select MP3 File",
                                          filetypes=[("MP3 Files", "*.mp3"), ("All Files", "*.*")])
        if path:
            self.entry_mp3.delete(0, tk.END)
            self.entry_mp3.insert(0, path)
            # Automatically pre-fill CUE field based on the MP3 file's base name.
            cue_default = path + ".cue"
            self.entry_cue.delete(0, tk.END)
            self.entry_cue.insert(0, cue_default)

    def browse_folder(self):
        folder = filedialog.askdirectory(title="Select Folder")
        if folder:
            self.entry_folder.delete(0, tk.END)
            self.entry_folder.insert(0, folder)

    def start_processing(self):
        mode = self.mode_option.get()
        if mode == "single":
            cue_path = self.entry_cue.get().strip()
            mp3_path = self.entry_mp3.get().strip()
            if not cue_path or not mp3_path:
                messagebox.showwarning("Missing Files", "Please select both a CUE file and an MP3 file.")
                return
            if process_files(cue_path, mp3_path):
                messagebox.showinfo("Success", "Chapter information has been written to the MP3 file.")
            else:
                messagebox.showerror("Processing Error", "An error occurred during processing. Check the console for details.")
        else:
            folder_path = self.entry_folder.get().strip()
            if not folder_path:
                messagebox.showwarning("Missing Folder", "Please select a folder.")
                return
            # Process all MP3/CUE pairs in the selected folder.
            process_folder(folder_path)
            messagebox.showinfo("Success", "Processing of folder complete.")

def process_files(cue_path, mp3_path):
    """
    Processes a single pair of CUE and MP3 files.
    After success, deletes both the .cue file and the backup file.
    """
    try:
        chapters = parse_cue_file(cue_path)
        if not chapters:
            raise ValueError("No chapters found in the CUE file.")
        print(f"Found {len(chapters)} chapters in the CUE file.")
        backup_file = embed_chapters(mp3_path, chapters)
        
        # If everything was processed successfully, delete the backup and cue file.
        if os.path.exists(backup_file):
            os.remove(backup_file)
            print(f"Backup file '{backup_file}' deleted.")
        if os.path.exists(cue_path):
            os.remove(cue_path)
            print(f"CUE file '{cue_path}' deleted.")
        return True
    except Exception as e:
        print("Error during processing:", e)
        return False

def process_folder(folder_path):
    """
    Processes all MP3 files in a given folder.
    For each MP3, it expects a corresponding CUE file with the same base name.
    """
    processed_any = False
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".mp3"):
            mp3_full = os.path.join(folder_path, filename)
            cue_full = mp3_full + ".cue"
            if os.path.exists(cue_full):
                print(f"Processing:\n  MP3: {mp3_full}\n  CUE: {cue_full}")
                process_files(cue_full, mp3_full)
                processed_any = True
            else:
                print(f"Warning: No CUE file for {mp3_full}")
    if not processed_any:
        print("No suitable MP3/CUE pairs found in folder.")


if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
