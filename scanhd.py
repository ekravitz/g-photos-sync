import os
import pickle
import hashlib
import sys

#Should be run in Python 3
extensions=['jpg','jpeg']
testing="this is a test"

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

	
if __name__ == "__main__":
	print(sys.argv[1])
	scan_for_changes(sys.argv[1])
