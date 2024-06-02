import tkinter as tk
from tkinter import filedialog, messagebox
import threading
from urllib.parse import urlparse
import requests
import os
import time


class DownloadManager:
    def __init__(self):
        self.downloads = []

    def add_download(self, url, file_name):
        download = FileDownloader(url, file_name)
        self.downloads.append(download)
        return download

    def get_downloads(self):
        return self.downloads


class FileDownloader:
    def __init__(self, url, file_name):
        self.url = url
        self.file_name = file_name
        self.file_progress = tk.StringVar()
        self.download_percentage = tk.StringVar()
        self.net_speed = tk.StringVar()
        self.elapsed_time = tk.StringVar()

        self.file_progress.set("N/A")
        self.download_percentage.set("N/A")
        self.net_speed.set("0 Mb/s")
        self.elapsed_time.set("0 seconds")

        self.download_thread = None
        self.download_stop_event = threading.Event()
        self.download_resume_event = threading.Event()

        self.partial_file_path = None
        self.total_size = 0
        self.downloaded_size = 0

    def format_file_size(self, size_in_bytes):
        if size_in_bytes < 1024:
            return f"{size_in_bytes} bytes"
        elif size_in_bytes < 1024 * 1024:
            return f"{size_in_bytes / 1024:.2f} KB"
        elif size_in_bytes < 1024 * 1024 * 1024:
            return f"{size_in_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_in_bytes / (1024 * 1024 * 1024):.2f} GB"

    def download_file(self, on_complete):
        parsed_url = urlparse(self.url)

        if not parsed_url.scheme or parsed_url.scheme not in ("http", "https"):
            print("Invalid URL")
            return

        self.partial_file_path = self.file_name
        self.download_stop_event.clear()
        self.download_resume_event.set()
        self.downloaded_size = 0

        self.download_thread = threading.Thread(target=self.download_file_thread, args=(self.url, self.file_name, on_complete))
        self.download_thread.start()

    def stop_download(self):
        if self.download_thread and self.download_thread.is_alive():
            self.download_stop_event.set()
            self.download_resume_event.clear()

    def resume_download(self, on_complete):
        if self.download_stop_event.is_set():
            self.download_stop_event.clear()
            self.download_resume_event.set()
            self.download_thread = threading.Thread(target=self.download_file_thread, args=(self.url, self.partial_file_path, on_complete))
            self.download_thread.start()

    def cancel_download(self):
        self.download_stop_event.set()
        self.download_resume_event.clear()
        if self.download_thread and self.download_thread.is_alive():
            self.download_thread.join()  # Ensure the thread stops before proceeding
        if os.path.exists(self.partial_file_path):
            os.remove(self.partial_file_path)
        self.reset_download_info()

    def reset_download_info(self):
        self.file_progress.set("Download cancelled")
        self.download_percentage.set("N/A")
        self.net_speed.set("0 Mb/s")
        self.elapsed_time.set("0 seconds")

    def download_file_thread(self, url, file_name, on_complete):
        headers = {"Range": f"bytes={self.downloaded_size}-"} if self.downloaded_size else {}
        response = requests.get(url, stream=True, headers=headers)

        if "Content-Range" in response.headers:
            content_range = response.headers["Content-Range"]
            self.total_size = int(content_range.split("/")[-1])
        elif "Content-Length" in response.headers:
            self.total_size = int(response.headers.get("Content-Length", 0))
        else:
            self.total_size = len(response.content)

        with open(file_name, "ab") as f:
            start = time.perf_counter()
            for chunk in response.iter_content(1024 * 16):
                if self.download_stop_event.is_set():
                    break
                self.downloaded_size += len(chunk)
                f.write(chunk)
                perc = round(((self.downloaded_size / self.total_size) * 100), 2)
                self.file_progress.set(f"{self.format_file_size(self.downloaded_size)} / {self.format_file_size(self.total_size)}")
                self.download_percentage.set(f"{perc}%")
                self.net_speed.set(f"{self.downloaded_size // (time.perf_counter() - start) / 100000} Mb/s")

            if not self.download_stop_event.is_set():
                self.elapsed_time.set(f"{round(time.perf_counter() - start)} seconds")
                on_complete()


class FileDownloaderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Fayl yuklovchi ilova")
        self.root.geometry("710x550")

        self.url = tk.StringVar()
        self.file_name = tk.StringVar()
        self.download_manager = DownloadManager()

        ######### File Url Frame #########
        self.file_url_frame = tk.LabelFrame(self.root, text="Fayl URL")
        self.file_url_frame.pack(fill="both", expand="yes", padx=10, pady=10)

        self.label = tk.Label(self.file_url_frame, text="URL kiriting:")
        # self.label.place(x=10, y=13)
        self.label.grid(row=0, column=0, padx=10, pady=10)

        self.entry = tk.Entry(self.file_url_frame, textvariable=self.url, width=40)
        # self.entry.place(x=100, y=10, width=500, height=30)
        self.entry.grid(row=0, column=1, padx=10, pady=10)

        self.download_image = tk.PhotoImage(file="/home/abdulaziz/Code/diplom/assets/download.png")
        self.download_button = tk.Button(self.file_url_frame, text="Yuklab olish", command=self.download_file, image=self.download_image, compound="left")
        # self.download_button.place(x=10, y=60)
        self.download_button.grid(row=0, column=2, padx=10, pady=10)

        ######### Download Information Frame with Scrollbar #########
        self.download_information_frame = tk.LabelFrame(self.root, text="Jarayon")
        self.download_information_frame.pack(fill="both", expand="yes", padx=10, pady=10)
        self.canvas = tk.Canvas(self.download_information_frame)
        self.scrollbar = tk.Scrollbar(self.download_information_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

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

        if not file_name:
            return

        downloader = self.download_manager.add_download(url, file_name)
        self.add_download_frame(downloader)
        downloader.download_file(lambda: self.on_download_complete(downloader))

    def add_download_frame(self, downloader):
        frame = tk.LabelFrame(self.scrollable_frame, text=f"Fayl nomi: {os.path.basename(downloader.file_name)}")
        frame.pack(fill="both", expand="yes", padx=10, pady=10)

        file_progress_label = tk.Label(frame, text="Fayl yuklanmoqda:")
        file_progress_label.grid(row=0, column=0, padx=10, pady=10)
        file_progress_var = tk.Label(frame, textvariable=downloader.file_progress)
        file_progress_var.grid(row=0, column=1, padx=10, pady=10)

        file_down_percentage_label = tk.Label(frame, text="Yuklab olish foizi:")
        file_down_percentage_label.grid(row=1, column=0, padx=10, pady=10)
        file_down_percentage_var = tk.Label(frame, textvariable=downloader.download_percentage)
        file_down_percentage_var.grid(row=1, column=1, padx=10, pady=10)

        net_speed_label = tk.Label(frame, text="Internet tezligi:")
        net_speed_label.grid(row=2, column=0, padx=10, pady=10)
        net_speed_var = tk.Label(frame, textvariable=downloader.net_speed)
        net_speed_var.grid(row=2, column=1, padx=10, pady=10)

        file_down_time_label = tk.Label(frame, text="Ketgan vaqt:")
        file_down_time_label.grid(row=3, column=0, padx=10, pady=10)
        file_down_time_var = tk.Label(frame, textvariable=downloader.elapsed_time)
        file_down_time_var.grid(row=3, column=1, padx=10, pady=10)

        stop_button = tk.Button(frame, text="To'xtatish", command=downloader.stop_download)
        stop_button.grid(row=4, column=0, padx=10, pady=10)

        resume_button = tk.Button(frame, text="Qayta boshlash", command=lambda: downloader.resume_download(lambda: self.on_download_complete(downloader)))
        resume_button.grid(row=4, column=1, padx=10, pady=10)

        cancel_button = tk.Button(frame, text="Bekor qilish", command=lambda: self.cancel_download(downloader, frame))
        cancel_button.grid(row=4, column=2, padx=10, pady=10)

        downloader.stop_button = stop_button
        downloader.resume_button = resume_button
        downloader.cancel_button = cancel_button

    def on_download_complete(self, downloader):
        downloader.stop_button.config(state=tk.DISABLED)
        downloader.resume_button.config(state=tk.DISABLED)
        downloader.cancel_button.config(state=tk.DISABLED)
        messagebox.showinfo("Download Complete", f"File {os.path.basename(downloader.file_name)} downloaded successfully!")

    def cancel_download(self, downloader, frame):
        downloader.cancel_download()
        downloader.stop_button.config(state=tk.DISABLED)
        downloader.resume_button.config(state=tk.DISABLED)
        downloader.cancel_button.config(state=tk.DISABLED)
        # frame.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = FileDownloaderApp(root)
    root.mainloop()
