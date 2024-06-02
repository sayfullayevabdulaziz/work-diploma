import tkinter as tk
from tkinter import filedialog, messagebox
import threading
from urllib.parse import urlparse
import requests
import os
import time

class FileDownloaderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("File Downloader")
        self.root.geometry("700x600")
        self.root.resizable(False, False)

        self.download_tasks = []

        ######### File Url Frame #########
        self.file_url_frame = tk.LabelFrame(self.root, text="File URL")
        self.file_url_frame.pack(fill="both", expand="yes", padx=10, pady=10)

        self.label = tk.Label(self.file_url_frame, text="Enter URLs (one per line):")
        self.label.grid(row=0, column=0, padx=10, pady=10)

        self.textbox = tk.Text(self.file_url_frame, height=5, width=80)
        self.textbox.grid(row=1, column=0, padx=10, pady=10)

        self.download_button = tk.Button(self.file_url_frame, text="Download", command=self.start_downloads)
        self.download_button.grid(row=2, column=0, padx=10, pady=10)

        ######### Download File Frame #########
        self.download_information_frame = tk.LabelFrame(self.root, text="Download Information")
        self.download_information_frame.pack(fill="both", expand="yes", padx=10, pady=10)

        self.download_listbox = tk.Listbox(self.download_information_frame, height=15, width=80)
        self.download_listbox.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        self.scrollbar = tk.Scrollbar(self.download_information_frame, orient="vertical", command=self.download_listbox.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.download_listbox.config(yscrollcommand=self.scrollbar.set)

        ######### Control Buttons #########
        self.control_frame = tk.Frame(self.root)
        self.control_frame.pack(fill="x", padx=10, pady=10)

        self.play_pause_button = tk.Button(self.control_frame, text="Play/Pause", command=self.toggle_download)
        self.play_pause_button.grid(row=0, column=0, padx=5)

        self.cancel_button = tk.Button(self.control_frame, text="Cancel", command=self.cancel_download)
        self.cancel_button.grid(row=0, column=1, padx=5)
        self.cancel_button.config(state=tk.DISABLED)

    def format_file_size(self, size_in_bytes):
        if size_in_bytes < 1024:
            return f"{size_in_bytes} bytes"
        elif size_in_bytes < 1024 * 1024:
            return f"{size_in_bytes / 1024:.2f} KB"
        elif size_in_bytes < 1024 * 1024 * 1024:
            return f"{size_in_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_in_bytes / (1024 * 1024 * 1024):.2f} GB"

    def start_downloads(self):
        urls = self.textbox.get("1.0", tk.END).strip().split("\n")

        for url in urls:
            if not self.validate_url(url):
                messagebox.showerror("Invalid URL", f"Invalid URL: {url}")
                continue

            parsed_url = urlparse(url)
            file_name_from_server = parsed_url.path.split('/')[-1]
            file_name_from_server = file_name_from_server.replace("%20", " ")

            file_type = file_name_from_server.split(".")[-1]
            file_name = filedialog.asksaveasfilename(
                filetypes=[(f"{file_type.upper()}", f"*.{file_type}"), ("All Files", "*.*")],
                initialfile=f"{file_name_from_server}"
            )

            if not file_name:
                continue

            download_info = {
                "url": url,
                "file_name": file_name,
                "file_progress": tk.StringVar(value="N/A"),
                "download_percentage": tk.StringVar(value="N/A"),
                "net_speed": tk.StringVar(value="0 Mb/s"),
                "elapsed_time": tk.StringVar(value="0 seconds"),
                "total_size": 0,
                "downloaded_size": 0,
                "stop_event": threading.Event(),
                "resume_event": threading.Event(),
                "cancel_event": threading.Event(),
                "paused": False,
                "index": len(self.download_tasks)
            }
            self.download_tasks.append(download_info)

            self.download_listbox.insert(tk.END, f"File: {os.path.basename(file_name)} | Progress: N/A | Speed: 0 Mb/s | Time: 0 seconds")
            download_info["listbox_index"] = self.download_listbox.size() - 1

            thread = threading.Thread(target=self.download_file_thread, args=(download_info,))
            thread.start()

    def validate_url(self, url):
        parsed_url = urlparse(url)
        return parsed_url.scheme in ("http", "https") and parsed_url.netloc

    def update_listbox(self, download_info):
        index = download_info["listbox_index"]
        progress = download_info["file_progress"].get()
        speed = download_info["net_speed"].get()
        time_elapsed = download_info["elapsed_time"].get()
        file_name = os.path.basename(download_info["file_name"])
        self.download_listbox.delete(index)
        self.download_listbox.insert(index, f"File: {file_name} | Progress: {progress} | Speed: {speed} | Time: {time_elapsed}")

    def toggle_download(self):
        selected = self.download_listbox.curselection()
        if not selected:
            return
        index = selected[0]
        download_info = self.download_tasks[index]
        if download_info["paused"]:
            download_info["paused"] = False
            download_info["resume_event"].set()
        else:
            download_info["paused"] = True
            download_info["resume_event"].clear()

    def cancel_download(self):
        selected = self.download_listbox.curselection()
        if not selected:
            return
        index = selected[0]
        download_info = self.download_tasks[index]
        download_info["cancel_event"].set()

    def download_file_thread(self, download_info):
        url = download_info["url"]
        file_name = download_info["file_name"]
        headers = {"Range": f"bytes={download_info['downloaded_size']}-"}

        try:
            response = requests.get(url, stream=True, headers=headers)
            if 'Content-Length' in response.headers:
                download_info["total_size"] = int(response.headers["Content-Length"]) + download_info["downloaded_size"]
            else:
                download_info["total_size"] = None

            chunk_size = 1024 * 5
            with open(file_name, "ab") as f:
                start = time.perf_counter()
                for chunk in response.iter_content(chunk_size):
                    if download_info["cancel_event"].is_set():
                        break
                    while download_info["paused"]:
                        download_info["resume_event"].wait()
                    f.write(chunk)
                    download_info["downloaded_size"] += len(chunk)

                    if download_info["total_size"]:
                        perc = round(((download_info["downloaded_size"] / download_info["total_size"]) * 100), 2)
                        download_info["file_progress"].set(f"{self.format_file_size(download_info['downloaded_size'])} / {self.format_file_size(download_info['total_size'])}")
                        download_info["download_percentage"].set(f"{perc}%")
                    else:
                        download_info["file_progress"].set(f"{self.format_file_size(download_info['downloaded_size'])} downloaded")

                    download_info["net_speed"].set(f"{download_info['downloaded_size'] // (time.perf_counter() - start) / 100000} Mb/s")
                    self.update_listbox(download_info)

                if not download_info["cancel_event"].is_set():
                    download_info["elapsed_time"].set(f"{round(time.perf_counter() - start)} seconds")
                    self.update_listbox(download_info)
                    messagebox.showinfo("Success", f"File {os.path.basename(file_name)} downloaded successfully.")
                else:
                    messagebox.showinfo("Cancelled", f"Download for {os.path.basename(file_name)} has been cancelled.")
                    os.remove(file_name)
                    self.download_listbox.delete(download_info["listbox_index"])
                    self.download_tasks.remove(download_info)

                self.cancel_button.config(state=tk.DISABLED)

        except requests.RequestException as e:
            messagebox.showerror("Download Error", f"An error occurred while downloading {os.path.basename(file_name)}: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = FileDownloaderApp(root)
    root.mainloop()
