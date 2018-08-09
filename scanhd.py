import os
import pickle
import hashlib
import sys

#Python 3
extensions=['jpg','jpeg']


class MyFile():
#Auto-init and save file attributes that are relevant
	def __init__(self, path):
		self.path = path
		self.stat = os.stat(path)
		self.checksum = hashlib.md5(open(path,mode='rb').read())

	def checkSame():
		#check file size and modification date
		if (self.stat.st_size != os.stat(self.path).st_size) or (self.stat.st_mtime != os.stat(self.path).st_mtime):
			if self.checksum != hashlib.md5(open(path,mode='rb').read()):
				return False
		
		return True
	
def scan_for_changes(topdir="."):

	pickle_file = os.path.join(topdir,"db").encode()
	
	try:
		l = pickle.load(open(pickle_file,mode='r'))
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

	pickle.dump(db.items(), open(pickle_file, mode="w"))

	
if __name__ == "__main__":
	print(sys.argv[1])
	scan_for_changes(sys.argv[1])
