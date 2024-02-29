from urllib.parse import urlparse
import re
import socket
import textual.app
import textual.widgets
import textual.containers
import sys

class GopherProtocolHandler():
	server_file_links = {}

	def get_url_components(self, location):
		# hacky way to get urllib.urlparse to recognize 
		# domains ending with .pub, else recognizes those
		# as params
		if not location.startswith('gopher://'):
			location = f'gopher://{location}'

		url_parts = urlparse(location)

		server = url_parts.hostname
		port = 70 if url_parts.port is None else url_parts.port 
		selector = '/'
		
		# split gopher:// out again since we appended it for the workaround above
		location = location.split('gopher://', 1)[1]
		if location.endswith(url_parts.netloc):
			selector = '/'
		else:
			selector = location.split(url_parts.netloc, 1)[1]

		return server, port, selector 

	def request(self, location):
		server, port, selector = self.get_url_components(location)
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.settimeout(5)
		s.connect((server, port))
		s.send(f'{selector}\r\n'.encode())
		
		response = s.recv(1024)
		while True:
			chunk = s.recv(1024)
			if chunk == b'':
				break
			response += chunk
		s.close()
	
		# if we are on a new server, create an entry
		# used to cache file links later to control formatting
		if server not in self.server_file_links:
			self.server_file_links[server] = set()

		return self.format_response(server, selector, response)
	
	def format_response(self, server, selector, response):
		response = response.decode('utf-8').split('\n')
		response_text = ''
		sep = '  '

		# {2,3} marked for link string since some sites omit the root / for other sites, hence the expectation of 2 chunks
		# though the standard dictates there should be 3
		file_link_regex = re.compile(r'0([a-zA-Z0-9 ~`!@#$%^&\*()-_=+\[\]{}\|\'";:,./?<>]+(\t)+){2,3}(\d)+(\r)?(\n)?')
		dir_link_regex = re.compile(r'1([a-zA-Z0-9 ~`!@#$%^&\*()-_=+\[\]{}\|\'";:,./?<>]+(\t)+){2,3}(\d)+(\r)?(\n)?')

		for line in response:
			if file_link_regex.match(line): # we have found a file link. format text and add to cache
				self.server_file_links[server].add(line[1:].split('\t')[1])
				c = line[1:].replace('\t', ' ')
				response_text += f'<file> {c}\n'
			elif dir_link_regex.match(line): # we have found dir, format text
				c = line[1:].replace('\t', ' ')
				response_text += f'<dir>  {c}\n'
			# if line starts with 'i' and is not a link to a file, then we need to format
			# some sites use 'i' at the start of ascii art 
			# if it is a link to a file, display as-is
			elif line.startswith('i') and selector not in self.server_file_links[server]:
				response_text += f'{sep}{line[1:]}'.replace('error.host\t1', '').replace('null.host\t1', '')
				response_text += '\n'
			else:
				response_text += line + '\n'
		
		# debug
		# response_text += f'server:{server} selector:{selector} !! set: {self.server_file_links}\n'
		return response_text

class Pypher(textual.app.App):
	handler = GopherProtocolHandler()
	BINDINGS = [('u', 'newurl', 'type in new URL')]
	CSS_PATH = "mycss.css"

	def focus_input(self, scroll_visible):
		self.query_one(textual.widgets.Input).focus(scroll_visible=scroll_visible)

	def write_to_static(self, text):
		self.query_one(textual.widgets.Static).update(text)
	
	def on_mount(self, event):
		self.write_to_static('Welcome to Pypher: a Gopher-space browser\nPress "u" to get started.')

	def action_newurl(self):
		self.focus_input(scroll_visible=False)

	def compose(self):
		yield textual.widgets.Header()					
		yield textual.widgets.Input(id="input", placeholder='Enter a gopher url')
		yield textual.widgets.Static(id="static", expand=True, markup=False)
		yield textual.widgets.Footer()
	
	def on_input_submitted(self, event):
		self.screen.set_focus(None)
		try:
			response_text = self.handler.request(event.value)
			self.write_to_static(response_text)
			self.query_one(textual.widgets.Input).scroll_visible()
		except Exception as e:
			self.write_to_static(f'Something went wrong: {str(e)}')

if __name__ == '__main__':
	Pypher().run()
