import os
import pickle
import hashlib
import sys
import configparser
from google_auth_oauthlib.flow import InstalledAppFlow
from oauth2client.file import Storage
from httplib2 import Http
from urllib.parse import urlencode

#Should be run in Python 3
extensions=['jpg','jpeg']

configFile="./config.ini"

class MyFile():
#Auto-init and save file attributes that are relevant
	def __init__(self, path):
		self.path = path
		
		self.st_size = os.stat(path).st_size
		self.st_mtime= os.stat(path).st_mtime
		self.checksum = hashlib.md5(open(path,mode='rb').read()).hexdigest()

		
	def checkSame(self):
		#check file size and modification date
		if (self.st_size != os.stat(self.path).st_size) or (self.st_mtime != os.stat(self.path).st_mtime):
			if self.checksum != hashlib.md5(open(self.path,mode='rb').read().hexdigest()):
				return False
		
		return True
	
def scan_for_changes(topdir="."):

	pickle_file = os.path.join(topdir,"db")
	
	try:
		l = pickle.load(open(pickle_file,mode='rb'))
	except IOError:
		l = []
	db = dict(l)

	for dirpath, dirnames, files in os.walk(topdir):
		for name in files:
			if name.lower().split(".")[-1] in extensions:
				fullpath=os.path.join(dirpath, name)
				
				if fullpath in db and db[fullpath].checkSame():
					print(fullpath + " check passed")
				else:
					print (fullpath + " check failed, adding file")
					db[fullpath]=MyFile(fullpath)

	pickle.dump(db, open(pickle_file, mode="wb"))

def loadConfig(file=configFile):
	config = configparser.ConfigParser()
	config.read(file)
	return config

def authenticateGoogle(config):
	flow = InstalledAppFlow.from_client_secrets_file(config['Google']['clientJSON'],
		scopes=config['Google']['scope'])
	credentials =flow.run_console()
	
	return credentials

def retreive_from_storage(config):

	storage = Storage(config['Google']['credentialsFile'])
	credentials = storage.get()
	if credentials is None:
		credentials = authenticateGoogle(config)
#		storage.put(credentials)
	else:
		pass
		#print("Got from storage")

	return credentials

def createAlbum(credentials):
	
	h=Http()
	request_url="https://photoslibrary.googleapis.com/v1/albums"
	request_type="POST"
	headers={'Content-type': 'application/json'}
	body={"album": {"title": "Test Album Title"}}
	credentials.authorize(h)
	response, content = h.request(request_url, request_type, headers=headers, body=urlencode(body))
	print(response)
	print(content)


if __name__ == "__main__":
	if len(sys.argv)>1:
		scan_for_changes(sys.argv[1])
		sys.exit()

	config = loadConfig()
	credentials = retreive_from_storage(config)
	
	createAlbum(credentials)
