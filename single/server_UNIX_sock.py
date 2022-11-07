from socketserver import UnixStreamServer, StreamRequestHandler, ThreadingMixIn
import os, socket, array


def recv_fds(sock, msglen, maxfds):
    fds = array.array("i")   # Array of ints
    msg, ancdata, flags, addr = sock.recvmsg(msglen, socket.CMSG_LEN(maxfds * fds.itemsize))
    for cmsg_level, cmsg_type, cmsg_data in ancdata:
        if cmsg_level == socket.SOL_SOCKET and cmsg_type == socket.SCM_RIGHTS:
            # Append data, ignoring any truncated integers at the end.
            fds.frombytes(cmsg_data[:len(cmsg_data) - (len(cmsg_data) % fds.itemsize)])
    return msg, list(fds)

os.unlink("/tmp/test")

class Handler(StreamRequestHandler):
    def handle(self):
        while True:
            msg = self.rfile.readline().strip()
            print(type(self.rfile))
            #msg2, fds_arr = recv_fds(self.rfile, len(msg), 3)
            #print(fds_arr)
            if msg:
                print("Data Recieved from client is: {}".format(msg))
            else:
                return

class ThreadedUnixStreamServer(ThreadingMixIn, UnixStreamServer):
    pass

with ThreadedUnixStreamServer('/tmp/test', Handler) as server:
    server.serve_forever()