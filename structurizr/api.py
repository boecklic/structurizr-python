import requests
import base64
import hmac
import hashlib
import time
import json
import logging
import inspect
from enum import Enum


DEBUG = False
VERIFY_CERTS = False

# proxies = {
#  	"http": "http://127.0.0.1:8118",
#  	"https": "http://127.0.0.1:8118",
# }
proxies = {
 	"http": "http://127.0.0.1:8080",
 	"https": "http://127.0.0.1:8080",
}

# certificate verification fails for
# structurizr, use verify=False and disable warnings
if not VERIFY_CERTS:
	import urllib3
	urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)



# Check: https://stackoverflow.com/a/16630836
# These two lines enable debugging at httplib level (requests->urllib3->http.client)
# You will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
# The only thing missing will be the response.body which is not logged.
if DEBUG:
	try:
	    import http.client as http_client
	except ImportError:
	    # Python 2
	    import httplib as http_client
	http_client.HTTPConnection.debuglevel = 1
	# You must initialize logging, otherwise you'll not see debug output.
	logging.basicConfig()
	logging.getLogger().setLevel(logging.DEBUG)
	requests_log = logging.getLogger("requests.packages.urllib3")
	requests_log.setLevel(logging.DEBUG)
	requests_log.propagate = True


class Method(Enum):
	GET = 1
	PUT = 2
	POST = 3

class StructurizrMessage:
	def __init__(self, method:Method, uri, content, content_type, nonce):
		self.method = method
		self.uri = uri
		self.content = content
		self._md5 = hashlib.md5(self.content.encode('utf-8'))
		self.content_type = content_type
		self.nonce = nonce

	def digest(self):
		message = '\n'.join([
			self.method.name.upper(), 
			self.uri, 
			self._md5.hexdigest().lower(),
			self.content_type,
			self.nonce
		])
		message += '\n'
		return message

	@property
	def md5(self):
		return self._md5

	def __str__(self):
		return self.digest()

class StructurizrAPI:
	# cloud
	apikey = 'a7cb6f93-4ca3-407d-bee6-5faa6ddbbd40'
	apisecret = '8cc19ca8-9021-4fb4-93ea-9df0ebcd6409'
	baseurl = 'https://api.structurizr.com'

	# docker0
	# apikey = '860a6098-5c77-462e-af41-dccf1b724ff1'
	# apisecret = '79e27dda-d376-4959-8144-fa5b38e2198b'
	# baseurl = 'https://ltboc.infra.bgdi.ch/api'

	@classmethod
	def _hmac(cls, message):
		return hmac.new(
			cls.apisecret.encode('utf-8'), 
			message.encode('utf-8'), 
			digestmod=hashlib.sha256
		)

	@classmethod
	def _b64encode(cls, hashed):
		# Note: the secret to the following line can only be found in
		# https://github.com/structurizr/java/blob/master/structurizr-client/src/com/structurizr/api/HashBasedMessageAuthenticationCode.java#L25
		# having simple base64.b64encode(hashed.digest()) doesn't work, the lower() is not mentioned in docs
		# https://structurizr.com/help/web-api
		secret = base64.b64encode(hashed.hexdigest().lower().encode('utf-8'))
		return secret

	@classmethod
	def call(cls, method: Method, uri: str, content, nonce=None):
		if nonce is None:
			nonce = str(int(time.time()*1000))
		
		# set content_type, '' for GET calls
		if method == Method.GET:
			content_type = ''
		else:
			content_type = 'application/json; charset=UTF-8'
		
		sm = StructurizrMessage(
			method=method,
			uri=uri,
			content=content,
			content_type=content_type,
			nonce=nonce
		)

		secret = cls._b64encode(cls._hmac(message=sm.digest()))

		# set http headers
		headers = {}
		headers['X-Authorization'] = "{apikey}:{secret}".format(
			apikey=cls.apikey, 
			secret=secret.decode('utf-8')
		)
		headers['Nonce'] = nonce
		if method != Method.GET:
			headers['Content-Type'] = content_type
			headers['Content-MD5'] = base64.b64encode(
				sm.md5.hexdigest().encode('utf-8')
			).decode('utf-8')
		
		print(f"HTTP {method.name}: {cls.baseurl}{uri}")
		request_method = getattr(requests, method.name.lower())
		response = request_method(f"{cls.baseurl}{uri}",
			data=content,
			headers=headers,
			verify=VERIFY_CERTS,
			proxies=proxies
		)
		return response

