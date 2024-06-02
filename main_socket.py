import tkinter as tk
from tkinter import filedialog
import threading
import socket
import os
import time

from urllib.parse import urlparse

class FileDownloaderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("File Downloader")
        self.root.geometry("450x400")
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

        ######### File Url Frame #########    
        self.file_url_frame = tk.LabelFrame(self.root, text="File URL")
        self.file_url_frame.pack(fill="both", expand="yes", padx=10, pady=10)

        self.label = tk.Label(self.file_url_frame, text="Enter File URL:")
        self.label.grid(row=0, column=0, padx=10, pady=10)

        self.entry = tk.Entry(self.file_url_frame, textvariable=self.url)
        self.entry.grid(row=0, column=1, padx=5, pady=10)

        self.button = tk.Button(self.file_url_frame, text="Download", command=self.download_file)
        self.button.grid(row=0, column=2, padx=5, pady=10)

        ######### Download File Frame #########
        self.download_information_fram = tk.LabelFrame(self.root, text="Download Information")
        self.download_information_fram.pack(fill="both", expand="yes", padx=10, pady=10)

        self.file_name_label = tk.Label(self.download_information_fram, text="File Name:")
        self.file_name_label.grid(row=0, column=0, padx=10, pady=10)
        self.file_var = tk.Label(self.download_information_fram, textvariable=self.file_name)
        self.file_var.grid(row=0, column=1, padx=10, pady=10)

        self.file_progress_label = tk.Label(self.download_information_fram, text="File Progress:")
        self.file_progress_label.grid(row=1, column=0, padx=10, pady=10)
        self.file_progress_var = tk.Label(self.download_information_fram, textvariable=self.file_progress)
        self.file_progress_var.grid(row=1, column=1, padx=10, pady=10)

        self.file_down_percentage_label = tk.Label(self.download_information_fram, text="Download Percentage:")
        self.file_down_percentage_label.grid(row=2, column=0, padx=10, pady=10)
        self.file_down_percentage_var = tk.Label(self.download_information_fram, textvariable=self.download_percentage)
        self.file_down_percentage_var.grid(row=2, column=1, padx=10, pady=10)

        self.net_speed_label = tk.Label(self.download_information_fram, text="Speed:")
        self.net_speed_label.grid(row=3, column=0, padx=10, pady=10)
        self.net_speed_var = tk.Label(self.download_information_fram, textvariable=self.net_speed)
        self.net_speed_var.grid(row=3, column=1, padx=10, pady=10)

        self.file_down_time_label = tk.Label(self.download_information_fram, text="Time:")
        self.file_down_time_label.grid(row=4, column=0, padx=10, pady=10)
        self.file_down_time_var = tk.Label(self.download_information_fram, textvariable=self.elapsed_time)
        self.file_down_time_var.grid(row=4, column=1, padx=10, pady=10)
        # ... (rest of the __init__ method remains the same)

    def format_file_size(self, size_in_bytes: int) -> str:
        # ... (rest of the format_file_size method remains the same)
        if size_in_bytes < 1024:
            return f"{size_in_bytes} bytes"
        elif size_in_bytes < 1024 * 1024:
            return f"{size_in_bytes / 1024:.2f} KB"
        elif size_in_bytes < 1024 * 1024 * 1024:
            return f"{size_in_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_in_bytes / (1024 * 1024 * 1024):.2f} GB"
        
    def download_file(self) -> None:
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

        download_thread = threading.Thread(target=self.download_file_thread, args=(url, file_name))
        download_thread.start()

    def download_file_thread(self, url: str, file_name: str) -> None:
        print(url.split("://")[-1].split("/", 1)[0].split(":"))
        host, port = url.split("://")[-1].split("/", 1)[0].split(":")
        port = int(port) if port else 80

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))

        request = f"GET /{url.split('/', 3)[3]} HTTP/1.1\r\nHost: {host}\r\n\r\n"
        sock.sendall(request.encode())

        response = b""
        while True:
            chunk = sock.recv(1024)
            if not chunk:
                break
            response += chunk

        response = response.decode().split("\r\n\r\n")[1]
        total_size = len(response)

        downloaded_size = 0
        start = time.perf_counter()

        with open(file_name, "wb") as f:
            for chunk in [response[i:i+1024*5] for i in range(0, len(response), 1024*5)]:
                downloaded_size += len(chunk)
                f.write(chunk.encode())
                perc = round(((downloaded_size / total_size) * 100), 2)
                self.file_progress.set(f"{self.format_file_size(downloaded_size)} / {self.format_file_size(total_size)}")
                self.download_percentage.set(f"{perc}%")
                self.net_speed.set(f"{downloaded_size//(time.perf_counter() - start) / 100000} Mb/s")

        self.elapsed_time.set(f"{round(time.perf_counter() - start)} seconds")

if __name__ == "__main__":
    root = tk.Tk()
    app = FileDownloaderApp(root)
    root.mainloop()