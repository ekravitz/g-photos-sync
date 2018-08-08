import os
import pickle
import md5

#Python 3

def scan_for_changes(topdir=".")
	try:
		l = pickle.load(open(topdir+"\db"))
	except IOError:
		l = []
	db = dict(l)

	for dirpath, dirnames, files in os.walk(topdir):
		for name in files:
			if name.lower().endswith(exten):
				print(os.path.join(dirpath, name))
	
	checksum = md5.md5(open(path).read())
	
	if db.get(path, None) != checksum:
		print "file changed"
		db[path] = checksum
	pickle.dump(db.items(), open("db", "w")
