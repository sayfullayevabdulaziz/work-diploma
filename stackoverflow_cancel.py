import tkinter as tk
from tkinter import filedialog
import threading
from urllib.parse import urlparse
import requests
import os
import time


class FileDownloaderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("File Downloader")
        self.root.geometry("550x400")
        self.root.resizable(False, False)

        self.url = tk.StringVar()
        self.file_name = tk.StringVar()
        self.file_progress = tk.StringVar()
        self.download_percentage = tk.StringVar()
        self.net_speed = tk.StringVar()
        self.elapsed_time = tk.StringVar()

        self.file_progress.set("N/A")
        self.download_percentage.set("N/A")
        self.net_speed.set("0 Mb/s")
        self.elapsed_time.set("0 seconds")

        self.download_thread = None
        self.download_cancel_event = threading.Event()

        ######### File Url Frame #########
        self.file_url_frame = tk.LabelFrame(self.root, text="File URL")
        self.file_url_frame.pack(fill="both", expand="yes", padx=10, pady=10)

        self.label = tk.Label(self.file_url_frame, text="URL kiriting:")
        self.label.grid(row=0, column=0, padx=10, pady=10)

        self.entry = tk.Entry(self.file_url_frame, textvariable=self.url)
        self.entry.grid(row=0, column=1, padx=5, pady=10)

        self.button = tk.Button(self.file_url_frame, text="Yuklab olish", command=self.download_file)
        self.button.grid(row=0, column=2, padx=5, pady=10)

        self.cancel_button = tk.Button(self.file_url_frame, text="Cancel", command=self.cancel_download)
        self.cancel_button.grid(row=0, column=3, padx=5, pady=10)

        ######### Download File Frame #########
        self.download_information_fram = tk.LabelFrame(self.root, text="Download Information")
        self.download_information_fram.pack(fill="both", expand="yes", padx=10, pady=10)

        self.file_name_label = tk.Label(self.download_information_fram, text="Fayl nomi:")
        self.file_name_label.grid(row=0, column=0, padx=10, pady=10)
        self.file_var = tk.Label(self.download_information_fram, textvariable=self.file_name)
        self.file_var.grid(row=0, column=1, padx=10, pady=10)

        self.file_progress_label = tk.Label(self.download_information_fram, text="Fayl yuklanmoqda:")
        self.file_progress_label.grid(row=1, column=0, padx=10, pady=10)
        self.file_progress_var = tk.Label(self.download_information_fram, textvariable=self.file_progress)
        self.file_progress_var.grid(row=1, column=1, padx=10, pady=10)

        self.file_down_percentage_label = tk.Label(self.download_information_fram, text="Yuklab olish foizi:")
        self.file_down_percentage_label.grid(row=2, column=0, padx=10, pady=10)
        self.file_down_percentage_var = tk.Label(self.download_information_fram, textvariable=self.download_percentage)
        self.file_down_percentage_var.grid(row=2, column=1, padx=10, pady=10)

        self.net_speed_label = tk.Label(self.download_information_fram, text="Internet tezligi:")
        self.net_speed_label.grid(row=3, column=0, padx=10, pady=10)
        self.net_speed_var = tk.Label(self.download_information_fram, textvariable=self.net_speed)
        self.net_speed_var.grid(row=3, column=1, padx=10, pady=10)

        self.file_down_time_label = tk.Label(self.download_information_fram, text="Ketgan vaqt:")
        self.file_down_time_label.grid(row=4, column=0, padx=10, pady=10)
        self.file_down_time_var = tk.Label(self.download_information_fram, textvariable=self.elapsed_time)
        self.file_down_time_var.grid(row=4, column=1, padx=10, pady=10)

    def format_file_size(self, size_in_bytes):
        if size_in_bytes < 1024:
            return f"{size_in_bytes} bytes"
        elif size_in_bytes < 1024 * 1024:
            return f"{size_in_bytes / 1024:.2f} KB"
        elif size_in_bytes < 1024 * 1024 * 1024:
            return f"{size_in_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_in_bytes / (1024 * 1024 * 1024):.2f} GB"

    def download_file(self):
        url = self.entry.get()
        if not url:
            return

        parsed_url = urlparse(url)

        if not parsed_url.scheme or parsed_url.scheme not in ("http", "https"):
            print("Invalid URL")
            return

        file_name_from_server = parsed_url.path.split('/')[-1]

        if "%20" in file_name_from_server:
            file_name_from_server = file_name_from_server.replace("%20", " ")

        file_type = url.split(".")[-1]
        file_name = filedialog.asksaveasfilename(filetypes=[(f"{file_type.upper()}", f"*.{file_type}"), ("All Files", "*.*")],
                                                 initialfile=f"{file_name_from_server}"
                                                 )
        self.file_name.set(os.path.basename(file_name))

        if not file_name:
            return

        self.download_cancel_event.clear()
        self.download_thread = threading.Thread(target=self.download_file_thread, args=(url, file_name))
        self.download_thread.start()

    def cancel_download(self):
        if self.download_thread and self.download_thread.is_alive():
            self.download_cancel_event.set()
            self.download_thread.join()
            self.download_thread = None
            self.file_progress.set("Download cancelled")
            self.download_percentage.set("N/A")
            self.net_speed.set("0 Mb/s")
            self.elapsed_time.set("0 seconds")

    def download_file_thread(self, url, file_name):
        response = requests.get(url, stream=True)

        try:
            total_size = int(response.headers["Content-Length"])
        except KeyError:
            total_size = len(response.content)

        downloaded_size = 0

        with open(file_name, "wb") as f:
            start = time.perf_counter()
            for chunk in response.iter_content(1024 * 5):
                if self.download_cancel_event.is_set():
                    break
                downloaded_size += len(chunk)
                f.write(chunk)
                perc = round(((downloaded_size / total_size) * 100), 2)
                self.file_progress.set(f"{self.format_file_size(downloaded_size)} / {self.format_file_size(total_size)}")
                self.download_percentage.set(f"{perc}%")
                self.net_speed.set(f"{downloaded_size // (time.perf_counter() - start) / 100000} Mb/s")

            if not self.download_cancel_event.is_set():
                self.elapsed_time.set(f"{round(time.perf_counter() - start)} seconds")
            else:
                os.remove(file_name)  # Remove partially downloaded file if cancelled

if __name__ == "__main__":
    root = tk.Tk()
    app = FileDownloaderApp(root)
    root.mainloop()
