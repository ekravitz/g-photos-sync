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
import itertools

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
	
	def __str__(self):
		return self.path

class GooglePhotos():
	def __init__(self, config):
		self.credentials = self.retreive_from_storage(config)
		self.pickleFile = config["pickleFile"]
		self.albumList = self.getAlbumList(self.pickleFile)
		
	def getAlbumList(self,pickleFileLocation):
		try:
			l = pickle.load(open(pickleFileLocation,mode='rb'))
		except IOError:
			l = {}
		print(l)
		return dict(l)
		
	def authenticateGoogle(self, config):
		flow = flow_from_clientsecrets(config['clientJSON'],
			scope=config['scope'],
			redirect_uri='urn:ietf:wg:oauth:2.0:oob')
			#redirect_uri='http://localhost')
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
	
	def getAlbum(self, albumTitle):
		
		if albumTitle.lower() not in self.albumList:
			#Add album
			h=Http()
			request_url="https://photoslibrary.googleapis.com/v1/albums"
			request_type="POST"
			headers={"Content-type": "application/json; charset=UTF-8"}

			body={"album": {"title": albumTitle}}

			self.credentials.authorize(h)
			formatted_body=json.dumps(body)
			# print(formatted_body)
			response, content = h.request(request_url, request_type, headers=headers, body=formatted_body)
			
			#Save album title and id information
			
			# UTF-8 is common and is specified in header, so assume it will stay the same. Better approach would be to follow what is in the header
			jsonContent = json.loads(content.decode("utf-8"))

			self.albumList[jsonContent["title"].lower()] = jsonContent["id"]
			pickle.dump(self.albumList, open(self.pickleFile, mode="wb"))
		
		return self.albumList[albumTitle.lower()]
	
	#Function not used since maintain list. Problem was this function was returning and empty set even for albums created by program.
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
		
	def uploadPhoto(self,albumID,fileList): #only first item in list for now
		h=Http()
		request_url="https://photoslibrary.googleapis.com/v1/uploads"
		request_type="POST"
		headers={"Content-type": "octet-stream", "X-Goog-Upload-File-Name": fileList[0].path, "X-Goog-Upload-Protocol": "raw"}
		self.credentials.authorize(h)
		
		# print(formatted_body)
		response, content = h.request(request_url, request_type, headers=headers, body=open(fileList[0].path, 'rb').read())
		print(response)
		print("______")
		print(content)
		
		#Need to create media item if this works until here.
		
def scan_for_changes(topdir=".",subfolders = True):

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
					yield db[fullpath]
		if not subfolders:
			break

	pickle.dump(db, open(pickle_file, mode="wb"))

	
def loadConfig(file):
	config = configparser.ConfigParser()
	config.read(file)
	return config



def loadArgParser():
	parser = argparse.ArgumentParser(description='Scan HD for changes and upload to GPhotos.')
	parser.add_argument('Folder', help='Folder location to scan and upload')
	parser.add_argument('-album', help='Specify name of album to save; defaults to albums in FIRST LEVEL SUBFOLDER (pics in top folder ignored)')
	parser.add_argument('-config', help='Location of config file; defaults to current directory', default="./config.ini")
	parser.add_argument('-subfolders', help='Include subfolders? CONFIRM Relevant only if album flag specified', default=True)
	return parser.parse_args()

if __name__ == "__main__":
	args = loadArgParser()
	
	print(args.Folder)
	print(args.album)

	config = loadConfig(args.config)
	
	gPhoto = GooglePhotos(config["Google"])
	
	if args.album:
		albumID = gPhoto.getAlbum(args.album)
		files = scan_for_changes(args.Folder,args.subfolders)
		print(list(itertools.islice(files, 10))[0])
		#gPhoto.uploadPhoto(albumID, fileList)
