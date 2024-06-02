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
        self.root.title("Fayl yuklovchi ilova")
        self.root.geometry("710x550")

        self.url = tk.StringVar()
        self.file_name = tk.StringVar()
        self.file_progress = tk.StringVar()
        self.download_percentage = tk.StringVar()
        self.net_speed = tk.StringVar()
        self.elapsed_time = tk.StringVar()

        self.file_progress.set("N/A")
        self.download_percentage.set("N/A")
        self.net_speed.set("0 Mb/s")
        self.elapsed_time.set("0 sekund")

        self.download_thread = None
        self.download_stop_event = threading.Event()
        self.download_resume_event = threading.Event()

        ######### File Url Frame #########
        self.file_url_frame = tk.LabelFrame(self.root, text="Fayl URL")
        self.file_url_frame.pack(fill="both", expand="yes", padx=10, pady=10)

        self.label = tk.Label(self.file_url_frame, text="URL kiriting:")
        # self.label.grid(row=0, column=0, padx=10, pady=10)
        self.label.place(x=10, y=13)

        self.entry = tk.Entry(self.file_url_frame, textvariable=self.url)
        # self.entry.grid(row=0, column=1, padx=10, pady=10)
        self.entry.place(x=100, y=10, width=500, height=30)

        self.download_image = tk.PhotoImage(file="/home/abdulaziz/Code/diplom/assets/download.png")
        self.download_button = tk.Button(self.file_url_frame, text="Yuklab olish", command=self.download_file, image=self.download_image, compound="left")
        # self.download_button.grid(row=0, column=0, padx=0, pady=10)
        self.download_button.place(x=10, y=60)

        self.stop_image = tk.PhotoImage(file="/home/abdulaziz/Code/diplom/assets/stop.png")
        self.stop_button = tk.Button(self.file_url_frame, text="To'xtatish", command=self.stop_download, image=self.stop_image, compound="left")
        # self.stop_button.grid(row=0, column=1, padx=0, pady=10)
        self.stop_button.place(x=170, y=60)

        self.play_image = tk.PhotoImage(file="/home/abdulaziz/Code/diplom/assets/play-button.png")
        self.resume_button = tk.Button(self.file_url_frame, text="Qayta boshlash", command=self.resume_download, image=self.play_image, compound="left")
        # self.resume_button.grid(row=0, column=2, padx=0, pady=10)
        self.resume_button.place(x=320, y=60)

        self.cancel_image = tk.PhotoImage(file="/home/abdulaziz/Code/diplom/assets/cancel.png")
        self.cancel_button = tk.Button(self.file_url_frame, text="Bekor qilish", command=self.cancel_download, image=self.cancel_image, compound="left")
        # self.cancel_button.grid(row=0, column=3, padx=10, pady=10)
        self.cancel_button.place(x=505, y=60)

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

        self.partial_file_path = file_name
        self.download_stop_event.clear()
        self.download_resume_event.set()
        self.downloaded_size = 0

        self.download_thread = threading.Thread(target=self.download_file_thread, args=(url, file_name))
        self.download_thread.start()

    def stop_download(self):
        if self.download_thread and self.download_thread.is_alive():
            self.download_stop_event.set()
            self.download_resume_event.clear()
            print(self.downloaded_size)

    def resume_download(self):
        if self.download_thread and not self.download_thread.is_alive():
            self.download_stop_event.clear()
            self.download_resume_event.set()
            url = self.entry.get()
            self.download_thread = threading.Thread(target=self.download_file_thread, args=(url, self.partial_file_path))
            self.download_thread.start()

    def cancel_download(self):
        if self.download_thread and self.download_thread.is_alive():
            self.download_stop_event.set()
            self.download_resume_event.clear()
            self.download_thread.join()  # Ensure the thread stops before proceeding
            if os.path.exists(self.partial_file_path):
                os.remove(self.partial_file_path)
            self.reset_download_info()

    def reset_download_info(self):
        self.file_name.set("")
        self.file_progress.set("Download cancelled")
        self.download_percentage.set("N/A")
        self.net_speed.set("0 Mb/s")
        self.elapsed_time.set("0 seconds")

    def download_file_thread(self, url, file_name):
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


if __name__ == "__main__":
    root = tk.Tk()
    app = FileDownloaderApp(root)
    root.mainloop()
