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

printVerbose = False


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

	def addGoogleID(self,picID):
		self.picID=picID

class GooglePhotos():
	def __init__(self, config):
		self.credentials = self.retreive_from_storage(config)
		self.pickleFile = config["pickleFileAlbums"]
		self.albumList = self.getAlbumList(self.pickleFile)
		
	def getAlbumList(self,pickleFileLocation):
		try:
			l = pickle.load(open(pickleFileLocation,mode='rb'))
		except IOError:
			l = {}
		printv("Album list loaded from file: ", end="")
		printv(l)
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
			credentials = self.authenticateGoogle(config)
			storage.put(credentials)
		else:
			printv("Obtained credentials from storage")
	
		return credentials
	
	def getAlbum(self, albumTitle):
		
		if (albumTitle.lower() not in self.albumList) or (not self.albumExistsOnline(self.albumList[albumTitle.lower()])):
			#Add album
			printv("Running getAlbum")
			h=Http()
			request_url="https://photoslibrary.googleapis.com/v1/albums"
			request_type="POST"
			headers={"Content-type": "application/json; charset=UTF-8"}

			body={"album": {"title": albumTitle}}

			self.credentials.authorize(h)
			formatted_body=json.dumps(body)
			printv("Submitting the following http body: " + formatted_body)
			response, content = h.request(request_url, request_type, headers=headers, body=formatted_body)
			printv("______GET ALBUM RESPONSE______")
			printv(response)
			printv(content)			
			#Save album title and id information
			
			# UTF-8 is common and is specified in header, so assume it will stay the same. Better approach would be to follow what is in the header
			jsonContent = json.loads(content.decode("utf-8"))
			
			
			self.albumList[jsonContent["title"].lower()] = jsonContent["id"]
			pickle.dump(self.albumList, open(self.pickleFile, mode="wb"))
		
		return self.albumList[albumTitle.lower()]
	
	def albumExistsOnline(self, albumID):
		printv("Checking album exists online")
		h=Http()
		request_url="https://photoslibrary.googleapis.com/v1/albums/" +  albumID
		request_type="GET"
		headers={"Content-type": "application/json; charset=UTF-8", "albumId":albumID}
		self.credentials.authorize(h)
		response, content = h.request(request_url, request_type, headers=headers, body='')
		# UTF-8 is common and is specified in header, so assume it will stay the same. Better approach would be to follow what is in the header
		printv("______ALBUM EXISTS RESPONSE______")
		printv(response)
		printv(content)
		jsonContent = json.loads(content.decode("utf-8"))
		if "title" in jsonContent:
			printv("Found album with the following title: " + jsonContent["title"])
			return True
		else:
			printv("Album in local storage but not online. Re-adding album.")
			return False
		
	def uploadPhoto(self,albumID,fileList):
		printv("Uploading list of photos")
		newItems =[]
		for filePath in fileList:
			h=Http()
			request_url="https://photoslibrary.googleapis.com/v1/uploads"
			request_type="POST"
			headers={"Content-type": "octet-stream", "X-Goog-Upload-File-Name": filePath.path, "X-Goog-Upload-Protocol": "raw"}
			self.credentials.authorize(h)
			printv("_____UPLOAD FILE______")
			print("Uploading file: " + filePath.path)
			printv(headers)

			response, content = h.request(request_url, request_type, headers=headers, body=open(filePath.path, 'rb').read())
			
			printv("______UPLOAD RESPONSE______")
			printv(response)
			printv(content)
			#HANDLE ERROR UPLOADING
			newItems.append({"description":filePath.path,"simpleMediaItem":{"uploadToken":content.decode("utf-8")}})
		
		
		#Need to create media item if this works until here.
		h=Http()
		request_url="https://photoslibrary.googleapis.com/v1/mediaItems:batchCreate"
		request_type="POST"
		headers={"Content-type": "octet-stream"}
		self.credentials.authorize(h)
		body={"albumId":albumID, "newMediaItems":newItems}
		formatted_body=json.dumps(body)
		printv("Body of media item request:")
		printv(formatted_body)
		
		response, content = h.request(request_url, request_type, headers=headers, body=formatted_body)
		
		printv("Response to media item request:")

		jsonContent = json.loads(content.decode("utf-8"))
		printv(response)
		printv(jsonContent)


		for result in jsonContent["newMediaItemResults"]:
			if "ok" in result["status"]["message"].lower():
				print("Good upload for file: " + result["mediaItem"]["filename"])
				self.db[result["mediaItem"]["filename"]].addGoogleID(result["mediaItem"]["id"])
			else:
				print("Upload failed")
				raise Exception("Upload failed!")

		pickle.dump(self.db, open(self.pickle_file, mode="wb"))


	def scan_for_changes(self,pickle_file="./db.pyPickle",topdir=".",subfolders = True):

		self.pickle_file=pickle_file

		try:
			l = pickle.load(open(pickle_file,mode='rb'))
		except IOError:
			l = []
		self.db = dict(l)

		for dirpath, dirnames, files in os.walk(topdir):
			for name in files:

				if name.lower().split(".")[-1] in extensions:
					fullpath=os.path.join(dirpath, name)

					if fullpath in self.db and self.db[fullpath].checkSame():
						printv(fullpath + " check passed")
					else:
						printv(fullpath + " check failed, adding file")
						self.db[fullpath]=MyFile(fullpath)
						yield self.db[fullpath]

			if not subfolders:
				break


def loadConfig(file):
	config = configparser.ConfigParser()
	config.read(file)
	return config



def loadArgParser():
	parser = argparse.ArgumentParser(description='Scan HD for changes and upload to GPhotos.')
	parser.add_argument('Folder', help='Folder location to scan and upload')
	parser.add_argument('-album', help='Specify name of album to save; defaults to albums in FIRST LEVEL SUBFOLDER (pics in top folder ignored)')
	parser.add_argument('-config', help='Location of config file; defaults to current directory', default="./config.ini")
	parser.add_argument('-subfolders', help='Include subfolders beneath album level?', default=True)
	parser.add_argument('-verbose', help='Verbose mode.', action='store_true')
	return parser.parse_args()

def printv(x, end=None):
	if printVerbose:
		print (x,end=end)

if __name__ == "__main__":
	args = loadArgParser()
	printVerbose = args.verbose
	
	printv("Folder location is: ", end="")
	printv(args.Folder)

	config = loadConfig(args.config)
	
	gPhoto = GooglePhotos(config["Google"])
	numList=int(config["General"]["Number_Files_to_Loop"])

	if args.album:
		albumID = gPhoto.getAlbum(args.album)
		fileListGenerator = gPhoto.scan_for_changes(config["General"]["pickleFileDB"],args.Folder,args.subfolders)
		while True:
			fileList = list(itertools.islice(fileListGenerator, numList))
			printv("File list is: ", end="")
			printv(fileList)
			if not fileList: 
				break
			gPhoto.uploadPhoto(albumID, fileList)
			printv("loop")
	else:
		dirpath, dirnames, files = next(os.walk(args.Folder))
		printv("Looping through dirnames: ", end='')
		printv(dirnames)
		
		for dirname in dirnames:
			albumID = dirname
			fileListGenerator = gPhoto.scan_for_changes(config["General"]["pickleFileDB"],
							     os.path.join(dirpath, dirname),args.subfolders)
			while True:
				fileList = list(itertools.islice(fileListGenerator, numList))
				printv("File list is: ", end="")
				printv(fileList)
				if not fileList: 
					break
				gPhoto.uploadPhoto(albumID, fileList)
				printv("loop")
