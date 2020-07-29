import socket
import threading
import xml.etree.ElementTree as et

class dbgp_reader (threading.Thread):
    def __init__(self, server):
        threading.Thread.__init__(self)
        self.server_ = server

    def run(self):
        self.server_.log("dbgp_reader started...")
        while self.server_.valid():
            root = et.XML(self.server_.recv())
            if root.tag == '{urn:debugger_protocol_v1}response':
                self.response(root)
            elif root.tag == '{urn:debugger_protocol_v1}stream':
                self.stream(root)
            elif root.tag == '{urn:debugger_protocol_v1}notify':
                self.notify(root)
            elif root.tag == '{urn:debugger_protocol_v1}init':
                self.init(root)

    def response(self, root):
        message = root.find('{https://xdebug.org/dbgp/xdebug}message')
        if not message is None:
            filename = message.get('filename')
            lineno = message.get('lineno')
            if filename and lineno:
                self.server_.write("where: " + filename[7:] + ":" + lineno)

    def stream(self, root):
        pass

    def notify(self, root):
        pass

    def init(self, root):
        pass

class dbgp_writer (threading.Thread):
    def __init__(self, server):
        threading.Thread.__init__(self)
        self.server_ = server
        self.id_ = 0

    def run(self):
        self.server_.log("dbgp_writer started...")
        while self.server_.valid():
            [ cmd, *args ] = self.server_.read().split(" ", 1)
            self.command(cmd, args)

    def command(self, cmd, args):
        command = " ".join([cmd, "-i", self.next_id()] + args)
        self.server_.send(command);

    def next_id(self):
        self.id_ = self.id_ + 1
        return str(self.id_)

class dbgp_server:
    def __init__(self):
        self.sock_ = None
        self.valid_ = True

    def run(self):
        server = socket.socket()
        server.bind(('localhost', 9000))

        server.listen(1)
        self.log("Listenning on port 9000...")

        self.sock_, addr = server.accept()
        self.log("Connection from: " + str(addr))

        reader = dbgp_reader(self)
        writer = dbgp_writer(self)

        reader.start()
        writer.start()

        reader.join()
        writer.join()

        server.close()
        self.write('program_state: Exited')

    def valid(self):
        return self.valid_

    def recv(self):
        if self.valid_:
            try:
                pre = self.sock_.recv(10);
                pos = pre.find(0)
                cnt = int(pre[0:pos].decode())
                buf = bytearray(pre[pos + 1:])
                while len(buf) < cnt:
                    buf += self.sock_.recv(int(cnt - len(buf)))
                self.sock_.recv(1)     # read-out last NULL byte

                return buf.decode('utf-8')
            except:
                self.valid_ = False
                raise
        else:
            raise Exception("DBGP socket is invalid")

    def send(self, cmd):
        if self.valid_:
            try:
                self.sock_.send(cmd.encode('utf-8') + b'\x00')
            except:
                self.valid_ = False
                raise
        else:
            raise Exception("DBGP socket is invalid")

    def read(self):
        return input()

    def write(self, text):
        print(text)

    def log(self, message):
        print("dbgp: " + message)

if __name__ == '__main__':
    server = dbgp_server()
    server.run()

