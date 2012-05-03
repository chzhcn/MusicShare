import pickle
import myclass
import socket


if __name__ == '__main__' :
    obj = myclass.myclass()

    with open('pfile', 'wb') as f:
        pickle.dump(obj, f)

    address = ('128.237.120.95', 30001)
    s = socket.create_connection(address)

    with open('pfile', 'rb') as f :
        s.sendall(f.read())
