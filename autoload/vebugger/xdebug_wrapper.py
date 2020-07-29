import base64
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
        transaction_id = root.get('transaction_id')
        command = root.get('command')
        if command == 'breakpoint_set':
            self.server_.breakpoint_update(root.get('id'), transaction_id)
        else:
            message = root.find('{https://xdebug.org/dbgp/xdebug}message')
            if not message is None:
                filename = message.get('filename')
                lineno = message.get('lineno')
                if filename and lineno:
                    self.server_.location(filename[7:], lineno)
            else:
                self.server_.log(et.tostring(root))

    def stream(self, root):
        self.server_.log(et.tostring(root))
        pass

    def notify(self, root):
        self.server_.log(et.tostring(root))
        pass

    def init(self, root):
        self.server_.log(et.tostring(root))
        pass

class dbgp_writer (threading.Thread):
    def __init__(self, server):
        threading.Thread.__init__(self)
        self.server_ = server
        self.id_ = 0

    def run(self):
        self.server_.log("dbgp_writer started...")
        while self.server_.valid():
            cmdline, *data = self.server_.read().split(" -- ", 1)
            for i in range(len(data)):
                data[i] = base64.b64encode(data[i].encode('utf-8')).decode('utf-8')

            cmd, *args = cmdline.split(" ", 1)
            self.command(cmd, args, data, self.next_id())

    def command(self, cmd, args, data, transaction_id):
        if cmd == 'breakpoint_set':
            self.server_.breakpoint_queue(args[0], transaction_id)
        elif cmd == 'breakpoint_remove':
            breakpoint_id = self.server_.breakpoint_find(args[0])
            self.server_.breakpoint_remove(args[0])
            args = [ "-d " + breakpoint_id ]

        cmdlist = [ cmd, "-i", transaction_id ] + args
        if len(data) > 0:
            cmdlist.append("--")
            cmdlist += data

        self.server_.send(" ".join(cmdlist));

    def next_id(self):
        self.id_ = self.id_ + 1
        return str(self.id_)

class dbgp_server:
    def __init__(self):
        self.sock_ = None
        self.valid_ = True

        self.breakpoints_queue_ = { }
        self.breakpoints_ = { }

    def run(self):
        server = socket.socket()
        server.bind(('localhost', 9000))

        server.listen(1)
        self.log("Listenning on localhost:9000...")

        self.sock_, addr = server.accept()
        self.log("Connection from: " + str(addr))

        reader = dbgp_reader(self)
        writer = dbgp_writer(self)

        reader.start()
        writer.start()

        reader.join()
        writer.join()

        server.close()
        self.end("OK")

    def valid(self):
        return self.valid_

    def breakpoint_queue(self, spec, transaction_id):
        self.breakpoints_queue_[transaction_id] = spec

    def breakpoint_update(self, breakpoint_id, transaction_id):
        spec = self.breakpoints_queue_[transaction_id]
        if spec:
            self.breakpoints_[spec] = breakpoint_id
            del self.breakpoints_queue_[transaction_id]

    def breakpoint_find(self, spec):
        return self.breakpoints_[spec]

    def breakpoint_remove(self, spec):
        del self.breakpoints_[spec]

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
                self.log(cmd)
                self.sock_.send(cmd.encode('utf-8') + b'\x00')
            except:
                self.valid_ = False
                raise
        else:
            raise Exception("DBGP socket is invalid")

    def read(self):
        return input()

    def stdout(self, text):
        print("dbgp_out:" + text)

    def stderr(self, text):
        print("dbgp_err:" + text)

    def location(self, filename, lineno):
        print("dbgp_loc:" + filename + ":" + lineno)

    def log(self, message):
        print("dbgp_log: " + message)

    def end(self, status):
        print("dbgp_end:" + status)

if __name__ == '__main__':
    server = dbgp_server()
    server.run()

