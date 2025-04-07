import tkinter as tk
from tkinter import messagebox
import datetime
import time
import threading
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Custom selection dialog with a scrollable Listbox
class SelectionDialog(tk.Toplevel):
    def __init__(self, parent, title, prompt, items):
        super().__init__(parent)
        self.title(title)
        self.selection = None

        # Set a fixed window size so it doesn't extend beyond your monitor.
        self.geometry("400x300")
        self.resizable(True, True)

        label = tk.Label(self, text=prompt)
        label.pack(pady=5)

        # Frame for Listbox and Scrollbar
        frame = tk.Frame(self)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set, width=50, height=10)
        for item in items:
            self.listbox.insert(tk.END, item)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.listbox.yview)

        # Button to confirm selection
        button = tk.Button(self, text="Select", command=self.on_select)
        button.pack(pady=5)

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.grab_set()
        self.wait_window(self)

    def on_select(self):
        selection = self.listbox.curselection()
        if selection:
            self.selection = self.listbox.get(selection[0])
        self.destroy()

    def on_close(self):
        self.destroy()

# Spotify credentials and scope configuration
SPOTIPY_CLIENT_ID = 'CLIENT_ID'
SPOTIPY_CLIENT_SECRET = 'CLIENT_SECRET'
SPOTIPY_REDIRECT_URI = 'http://localhost:8888/callback'
SCOPE = "user-read-playback-state,user-modify-playback-state,playlist-read-private"

class SpotifyAlarmApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Spotify Alarm Clock")

        # Initialize Spotify client with OAuth
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=SPOTIPY_CLIENT_ID,
            client_secret=SPOTIPY_CLIENT_SECRET,
            redirect_uri=SPOTIPY_REDIRECT_URI,
            scope=SCOPE
        ))
        
        # Alarm time input
        self.time_label = tk.Label(root, text="Enter Alarm Time (HH:MM:SS):")
        self.time_label.pack(pady=5)
        self.time_entry = tk.Entry(root, width=15)
        self.time_entry.pack(pady=5)

        # Spotify track selection
        self.track_label = tk.Label(root, text="No track selected")
        self.track_label.pack(pady=5)
        self.track_button = tk.Button(root, text="Select Track from Playlist", command=self.select_track)
        self.track_button.pack(pady=5)

        # Set alarm button
        self.set_alarm_button = tk.Button(root, text="Set Alarm", command=self.set_alarm)
        self.set_alarm_button.pack(pady=10)

        # Stop alarm button
        self.stop_alarm_button = tk.Button(root, text="Stop Alarm", command=self.stop_alarm)
        self.stop_alarm_button.pack(pady=5)

        # Status label for messages
        self.status_label = tk.Label(root, text="", fg="green")
        self.status_label.pack(pady=5)

        self.alarm_datetime = None
        self.track_uri = None

    def select_track(self):
        try:
            # Retrieve user's playlists (limit to 50)
            playlists = self.sp.current_user_playlists(limit=50)
            playlist_dict = {p['name']: p['id'] for p in playlists['items']}
            if not playlist_dict:
                messagebox.showerror("Error", "No playlists found.")
                return

            # Use the custom selection dialog for playlist selection
            dialog = SelectionDialog(self.root, "Select Playlist", "Choose a playlist:", list(playlist_dict.keys()))
            playlist_name = dialog.selection
            if not playlist_name:
                messagebox.showerror("Error", "No playlist selected.")
                return

            # Fetch tracks from the selected playlist
            results = self.sp.playlist_tracks(playlist_dict[playlist_name])
            tracks = results['items']
            track_options = {}
            for t in tracks:
                track = t['track']
                if track is not None:
                    display_name = f"{track['name']} by {track['artists'][0]['name']}"
                    track_options[display_name] = track['uri']
            if not track_options:
                messagebox.showerror("Error", "No tracks found in this playlist.")
                return

            # Use the custom selection dialog for track selection
            dialog = SelectionDialog(self.root, "Select Track", "Choose a track:", list(track_options.keys()))
            track_choice = dialog.selection
            if not track_choice:
                messagebox.showerror("Error", "No track selected.")
                return

            self.track_uri = track_options[track_choice]
            self.track_label.config(text=f"Selected: {track_choice}")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")

    def set_alarm(self):
        alarm_time_str = self.time_entry.get()
        try:
            alarm_time_obj = datetime.datetime.strptime(alarm_time_str, "%H:%M:%S").time()
            today = datetime.date.today()
            self.alarm_datetime = datetime.datetime.combine(today, alarm_time_obj)
            if self.alarm_datetime < datetime.datetime.now():
                self.alarm_datetime += datetime.timedelta(days=1)
            self.status_label.config(text="Alarm Set!", fg="green")
            threading.Thread(target=self.wait_for_alarm, daemon=True).start()
        except ValueError:
            self.status_label.config(text="Invalid time format. Use HH:MM:SS", fg="red")

    def wait_for_alarm(self):
        while True:
            if datetime.datetime.now() >= self.alarm_datetime:
                self.play_alarm()
                break
            time.sleep(1)

    def play_alarm(self):
        self.status_label.config(text="Alarm! Playing track...", fg="blue")
        if self.track_uri:
            try:
                devices = self.sp.devices()
                if not devices['devices']:
                    self.status_label.config(text="No active device found. Please open Spotify and play something.", fg="red")
                    return
                device_id = devices['devices'][0]['id']
                self.sp.start_playback(device_id=device_id, uris=[self.track_uri])
            except Exception as e:
                self.status_label.config(text=f"Error playing track: {e}", fg="red")
        else:
            self.status_label.config(text="No track selected.", fg="red")

    def stop_alarm(self):
        try:
            self.sp.pause_playback()
            self.status_label.config(text="Alarm stopped", fg="red")
        except Exception as e:
            self.status_label.config(text=f"Error stopping track: {e}", fg="red")

if __name__ == "__main__":
    root = tk.Tk()
    app = SpotifyAlarmApp(root)
    root.mainloop()
