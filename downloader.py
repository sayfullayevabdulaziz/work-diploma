import os, sys, socket, json
import threading, ssl, select
from datetime import datetime
import time, re, tempfile
from urllib.parse import unquote
from itertools import cycle

from main import FileDownloaderApp

MAX_SOCKET_CHUNK_SIZE = 16 * 1024
MAX_IO_CHUNK_SIZE = 8 * 1024

MAX_CONNECTION = 16
MANUAL_MAX_CONNECTION = 64
CONNECTION_PER_BYTE = 1024 * 1024 * 5

class Response:
	def __init__(self, raw: bytes):
		header_body = raw.split(b"\r\n\r\n")
		
		self.body = b""

		if len(header_body) == 1:
			self.raw_header = header_body[0]
		else:
			self.raw_header, self.body = header_body

		header_split = self.raw_header.split(b"\r\n")
		self.log = header_split[0]


		log_split = self.log.decode().split(" ")
		if len(log_split) == 3:
			self.protocol, self.status, self.status_str = self.log.decode().split(" ")

		if len(log_split) > 3:
			self.protocol, self.status, self.status_str = log_split[0], log_split[1], " ".join(log_split[2:])

		self.headers = self.make_header()

		self.allow_multi_connection = False
		self.filename = None
		self.length = 0


		if l:=self.headers.get("content-length"):
			self.length = int(l)
		
		if "accept-ranges" in self.headers:
			self.allow_multi_connection = True

		if disposition:=self.headers.get("content-disposition"):
			groups = disposition.split(";")
			for group in map(lambda x: x.strip(), groups):
				sgroup = group.split("=")
				if len(sgroup) == 2:
					key, value = sgroup
					setattr(self, key, value)

	def __repr__(self):
		return f"<{self.__class__.__name__} status={self.status} length={self.length}>"

	def make_header(self):
		raw_split = self.raw_header.split(b"\r\n")[1:]
		_header = dict()
		for line in raw_split:
			if not line:
				continue
			broken_line = line.decode().split(":")
			_header[broken_line[0].lower()] = ":".join(broken_line[1:]).strip()

		return _header

class Url:
	def __init__(self, url:str):
		# url = unquote(url)
		search = re.search(r"(?P<scheme>\w+)://(?P<host>[\w\.-]+)(?P<path>.*)", url)

		assert search, "Invalid url"

		for key, value in search.groupdict().items():
			setattr(self, key, value)

		self.scheme = self.scheme.lower()

		if self.scheme == "http":
			self.port = 80

		if self.scheme == "https":
			self.port = 443


class Worker(threading.Thread):
	def __init__(self, init_data:dict, connection:object):
		super().__init__()
		self.init_data = init_data
		self.connection = connection
		self.file = tempfile.NamedTemporaryFile(delete=False)

	def run(self):
		data = self.connection.recv(MAX_SOCKET_CHUNK_SIZE)
		res = Response(data)

		if res.body:
			self.file.write(res.body)
			self.init_data["bytes_recv"] += len(res.body)

		while True:
			data = self.connection.recv(MAX_SOCKET_CHUNK_SIZE)
			if not data:
				break
			self.init_data["bytes_recv"] += len(data)
			self.file.write(data)
			# self.gui.update_download_info(self.init_data)

		if hasattr(self.connection, "pending"):
			left_bytes = self.connection.pending()
			data = self.connection.recv(left_bytes)
			self.init_data["bytes_recv"] += left_bytes
			self.file.write(data)

		self.file.seek(0)
		self.connection.close()

	def __del__(self):
		self.file.close()
		os.unlink(self.file.name)

class ProcessBar(threading.Thread):
	def __init__(self, init_data:dict):
		super().__init__()
		self.init_data = init_data
		self.len = 50
		self.prefix, self.block, self.suffix = ("[", "■", "]")
		self.empty_space = " "
		self.loading = cycle("\\/-")

		self.time_interval = 0.10

		self._block_len = 0
		self._last_bytes = 0

		self.processbar = self.init_data.get("processbar")

	def run(self):
		block_len = 0
		last_bytes = 0
		while self.len != self._block_len:

			self._block_len = (self.init_data["bytes_recv"]*self.len)//self.init_data["length"]

			download_bytes_in_second = ((self.init_data["bytes_recv"]-self._last_bytes) * (1//self.time_interval))
			self.download_bytes_in_second = download_bytes_in_second if download_bytes_in_second else 1
			self.download_bytes_in_second_str = f"{download_bytes_in_second}bytes/second"
			
			self.eta = f"{self.init_data['length']//self.download_bytes_in_second}s"
			self.eta_str = f" {next(self.loading)} ETA {self.eta:<20}"

			self.percentage = self._block_len*(100//self.len)

			animated_suff = f" {next(self.loading)} [{self.percentage}/100]"

			if self.processbar:
				print("\r", end="")
				print("downloading "+self.prefix + self.block * self._block_len + self.empty_space * (self.len-self._block_len)  + self.suffix + animated_suff, end="")

			last_bytes = self.init_data["bytes_recv"]
			time.sleep(self.time_interval)

		if self.processbar:
			print("")


class Download:
	def __init__(self, url:str, gui: FileDownloaderApp, connection:int=None, filename:str=None, headers:dict=dict(), processbar:bool=True):
		self.url = url
		self.gui = gui
		self.url_obj = Url(self.url)
		self.filename = filename
		self.connection = connection
		self.processbar = None
	
		self.data = dict(bytes_recv=0, url=self.url_obj, connection=connection, 
			filename=filename, processbar=processbar)

		self.master_payload = self.make_payload(headers=headers)

	def make_payload(self, bytes_range: list = None, headers: dict = None):
		headers = headers or {
			"user-agent": "MayankFawkes/Bot"
		}
		headers.update({"connection": "close"})

		payload = f'GET {self.url_obj.path} HTTP/1.1\r\nhost: {self.url_obj.host}\r\n'

		if bytes_range:
			bytes_range = list(map(str, bytes_range))
			payload += f"range: bytes={'-'.join(bytes_range)}\r\n"

		print("PayPayload", payload)
		for key, value in headers.items():
			payload += f"{key}: {value}\r\n"

		payload += "\r\n" 
		print("Last Payload", payload)
		return payload.encode()

	def create_connection(self):
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.connect((self.url_obj.host, self.url_obj.port))
		if self.url_obj.scheme == "https":
			ssl_cxt = ssl.create_default_context()
			sock = ssl_cxt.wrap_socket(sock, server_hostname=self.url_obj.host)

		return sock

	def proces(self):
		sock = self.create_connection()
		sock.send(self.master_payload)
		rawres = sock.recv(MAX_SOCKET_CHUNK_SIZE)

		print("RAWRES", rawres)

		res = Response(rawres)

		self.data["length"] = res.length

		if res.status.startswith("3"):
			down = Download(url=res.headers["location"])
			down.proces()
			return

		connection = self.predict_conn(res)
		bytes_ranges = self.get_range(length=res.length, connection=connection)
		
		workers = []

		self.start_time = time.perf_counter()
		self.data["start_time"] = self.start_time

		for bytes_range in bytes_ranges:
			payload = self.make_payload(bytes_range=bytes_range)

			worker_sock = self.create_connection()
			worker_sock.send(payload)

			w = Worker(init_data=self.data, connection=worker_sock)
			w.start()

			workers.append(w)

		# self.processbar = ProcessBar(init_data=self.data)
		# self.processbar.start()

		[worker.join() for worker in workers]

		filename = self.get_filename(response=res)

		with open(filename, "wb") as fp:
			for worker in workers:
				while True:
					chunk = worker.file.read(MAX_IO_CHUNK_SIZE)
					self.gui.update_download_info(self.data)
					if not chunk:
						break

					fp.write(chunk)
					
		# print(self.data["bytes_recv"])
	# def update_download_info(self, workers):
	# 	self.data["bytes_recv"] = sum([worker.init_data["bytes_recv"] for worker in workers])

	def get_filename(self, response:object):
		if self.filename:
			return self.filename

		if filename:=response.filename:
			return filename

		return unquote(self.url.split("/")[-1].split("?")[0])


	def get_range(self, length: int, connection: int):
		steps = length//connection
		ranges = []
		for n in range(connection):
			if connection == (n+1):
				ranges.append([n*steps, length])
				continue
			ranges.append([n*steps, (n*steps)+steps-1])
		return ranges

	def predict_conn(self, response:object):
		if self.connection:
			if self.connection > MANUAL_MAX_CONNECTION:
				self.connection = MANUAL_MAX_CONNECTION

		if not response.allow_multi_connection:
			return self.connection or 1

		if self.connection:
			return self.connection

		conn = response.length // CONNECTION_PER_BYTE

		if conn > MAX_CONNECTION:
			return MAX_CONNECTION
		
		if not conn:
			return 1

		return conn
		

# if __name__ == '__main__':
# 	link = input("Enter url -->")
# 	down = Download(url=link)
# 	down.proces()
