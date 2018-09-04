import os
import pickle
import hashlib
import sys
import configparser
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from httplib2 import Http
from urllib.parse import quote
import json
import argparse

#Should be run in Python 3
extensions=['jpg','jpeg']

pickle_file="./db.pyPickle"

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

class GooglePhotos():
	def __init__(self, config):
		self.credentials = self.retreive_from_storage(config)
		self.pickleFile = config["pickleFile"]
		self.albumList = self.getAlbumList(self.pickleFile)
		
	def getAlbumList(self,pickleFileLocation):
		try:
			l = pickle.load(open(pickleFileLocation,mode='rb'))
		except IOError:
			l = set()
		print(l)
		return l
		
	def authenticateGoogle(self, config):
		flow = flow_from_clientsecrets(config['clientJSON'],
			scope=config['scope'],
			redirect_uri='http://localhost')
		auth_uri = flow.step1_get_authorize_url()
		print("Please go to the following URL: " + auth_uri)
		gToken=input("Please enter the code from Google: ")
		
		credentials = flow.step2_exchange(gToken)
		return credentials
	
	def retreive_from_storage(self, config):
	
		storage = Storage(config['credentialsFile'])
		credentials = storage.get()
		if credentials is None:
			credentials = authenticateGoogle(config)
			storage.put(credentials)
		else:
			pass
			print("Got from storage")
	
		return credentials
	
	def createAlbum(self, album):
		
		h=Http()
		request_url="https://photoslibrary.googleapis.com/v1/albums"
		request_type="POST"
		headers={"Content-type": "application/json; charset=UTF-8"}
	
		if album:
			body={"album": {"title": album}}
		else:
			body={"album": {"title": "Test album for none specified"}}
			
		self.credentials.authorize(h)
		formatted_body=json.dumps(body)
		# print(formatted_body)
		response, content = h.request(request_url, request_type, headers=headers, body=formatted_body)

		# UTF-8 is common and is specified in header, so assume it will stay the same. Better approach would be to follow what is in the header
		self.albumList.add(json.loads(content.decode("utf-8"))["id"])
	
	def checkAlbum(self, album):
		h=Http()
		request_url="https://photoslibrary.googleapis.com/v1/albums"
		request_type="GET"
		headers={"Content-type": "application/json; charset=UTF-8"}
		self.credentials.authorize(h)
		body=''
		# print(formatted_body)
		response, content = h.request(request_url, request_type, headers=headers, body=body)
		print(response)
		print("______")
		print(content)
	
	def cleanup(self):
		pickle.dump(self.albumList, open(self.pickleFile, mode="wb"))
		
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

def loadConfig(file):
	config = configparser.ConfigParser()
	config.read(file)
	return config



def loadArgParser():
	parser = argparse.ArgumentParser(description='Scan HD for changes and upload to GPhotos.')
	parser.add_argument('Folder', help='Folder location to scan and upload')
	parser.add_argument('-album', help='Specify name of album to save; defaults to first level directory name')
	parser.add_argument('-config', help='Location of config file; defaults to current directory', default="./config.ini")
	
	return parser.parse_args()

if __name__ == "__main__":
	args = loadArgParser()
	
	print(args.Folder)
	print(args.album)

	config = loadConfig(args.config)
	
	gPhoto = GooglePhotos(config["Google"])
	
	if args.album:
		gPhoto.createAlbum(args.album)
		gPhoto.checkAlbum(args.album)
		
	gPhoto.cleanup()

	if False:
		scan_for_changes(sys.argv[1])
		sys.exit()

