import pickle
import md5

try:
    l = pickle.load(open("db"))
except IOError:
    l = []
db = dict(l)
path = "/etc/hosts"
checksum = md5.md5(open(path).read())
if db.get(path, None) != checksum:
    print "file changed"
    db[path] = checksum
pickle.dump(db.items(), open("db", "w")
