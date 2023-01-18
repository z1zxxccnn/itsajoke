# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

import platform

if platform.system() == 'Windows':
    from twisted.internet import iocpreactor

    try:
        iocpreactor.install()
        print(f'iocpreactor install succeed')
    except:
        pass
elif platform.system() == 'Darwin':
    from twisted.internet import kqreactor

    try:
        kqreactor.install()
        print(f'kqreactor install succeed')
    except:
        pass
elif platform.system() == 'Linux':
    from twisted.internet import epollreactor

    try:
        epollreactor.install()
        print(f'epollreactor install succeed')
    except:
        pass

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from twisted.internet import reactor, protocol, error
from twisted.protocols import basic
from twisted.logger import formatEvent, ILogObserver, globalLogBeginner
from twisted.python import failure
from zope.interface import implementer
from enum import IntEnum, unique
import weakref
import random
import struct
import base64
import os
import inspect

JOKE_RANDOM_LEN = 0
JOKE_RANDOM_KEY = b''

JOKE_PASSWORD_LEN = 0
JOKE_PASSWORD_KEY = b''

JOKE_SALT = b''

JOKE_CALL_STOP = False


def MsgWithFrameInfo(msg):
    frame = inspect.stack()[1].frame
    inst = frame.f_locals.get('self')
    func_name = frame.f_code.co_name
    if inst and hasattr(inst, '__class__') and hasattr(inst.__class__, '__name__'):
        func_name = f'{inst.__class__.__name__}.{func_name}'
    return f'[{os.path.basename(frame.f_code.co_filename)}:' \
           f'{frame.f_lineno}:{func_name}]{msg}'


class UniqueIdGenerator:

    def __init__(self):
        self.pos = 1
        self.free_lst = []

    def generate(self):
        if self.free_lst:
            return self.free_lst.pop()

        unique_id = self.pos
        self.pos += 1
        return unique_id

    def release(self, unique_id):
        self.free_lst.append(unique_id)


def ReactorStop(reason):
    global JOKE_CALL_STOP
    print(f'call reactor stop, already call: {JOKE_CALL_STOP}, reason: {reason}')
    if not JOKE_CALL_STOP:
        JOKE_CALL_STOP = True
        reactor.stop()


@implementer(ILogObserver)
class MyLogObserver:

    def __call__(self, event):
        if isinstance(event['failure'], failure.Failure):
            print(formatEvent(event))


@unique
class JokePacketType(IntEnum):
    NONE = 0
    VERIFY_SUCCEED = 1
    MODIFY_PASSWORD = 2
    CREATE_PROXY_REQ = 3
    CREATE_PROXY_RES = 4
    DELETE_PROXY_REQ = 5
    DELETE_PROXY_RES = 6
    TRANSFER_DATA = 7


class JokePacket:

    def __init__(self):
        self.type = JokePacketType.NONE
        self.key = b''
        self.host = b''
        self.port = 0
        self.link_id = 0
        self.payload = b''

    def pack(self):
        data = b''
        data += struct.pack('<B', int(self.type.value))

        if self.type == JokePacketType.VERIFY_SUCCEED:
            pass

        elif self.type == JokePacketType.MODIFY_PASSWORD:
            data += struct.pack('<I', len(self.key))
            data += self.key

        elif self.type == JokePacketType.CREATE_PROXY_REQ:
            data += struct.pack('<I', self.link_id)
            data += struct.pack('<I', len(self.host))
            data += self.host
            data += struct.pack('<I', self.port)

        elif self.type == JokePacketType.CREATE_PROXY_RES:
            data += struct.pack('<I', self.link_id)

        elif self.type == JokePacketType.DELETE_PROXY_REQ:
            data += struct.pack('<I', self.link_id)

        elif self.type == JokePacketType.DELETE_PROXY_RES:
            data += struct.pack('<I', self.link_id)

        elif self.type == JokePacketType.TRANSFER_DATA:
            data += struct.pack('<I', self.link_id)
            data += struct.pack('<I', len(self.payload))
            data += self.payload

        return data

    def unpack(self, data):
        start_pos = 0
        self.type = JokePacketType(struct.unpack('<B', data[start_pos: 1])[0])
        start_pos += 1

        if self.type == JokePacketType.VERIFY_SUCCEED:
            pass

        elif self.type == JokePacketType.MODIFY_PASSWORD:
            byte_len = struct.unpack('<I', data[start_pos: start_pos + 4])[0]
            start_pos += 4
            self.key = data[start_pos: start_pos + byte_len]
            start_pos += byte_len

        elif self.type == JokePacketType.CREATE_PROXY_REQ:
            self.link_id = struct.unpack('<I', data[start_pos: start_pos + 4])[0]
            start_pos += 4
            byte_len = struct.unpack('<I', data[start_pos: start_pos + 4])[0]
            start_pos += 4
            self.host = data[start_pos: start_pos + byte_len]
            start_pos += byte_len
            self.port = struct.unpack('<I', data[start_pos: start_pos + 4])[0]
            start_pos += 4

        elif self.type == JokePacketType.CREATE_PROXY_RES:
            self.link_id = struct.unpack('<I', data[start_pos: start_pos + 4])[0]
            start_pos += 4

        elif self.type == JokePacketType.DELETE_PROXY_REQ:
            self.link_id = struct.unpack('<I', data[start_pos: start_pos + 4])[0]
            start_pos += 4

        elif self.type == JokePacketType.DELETE_PROXY_RES:
            self.link_id = struct.unpack('<I', data[start_pos: start_pos + 4])[0]
            start_pos += 4

        elif self.type == JokePacketType.TRANSFER_DATA:
            self.link_id = struct.unpack('<I', data[start_pos: start_pos + 4])[0]
            start_pos += 4
            byte_len = struct.unpack('<I', data[start_pos: start_pos + 4])[0]
            start_pos += 4
            self.payload = data[start_pos: start_pos + byte_len]
            start_pos += byte_len


class MyHttpProxyClient(protocol.Protocol):

    def __init__(self, requester_ref, host, port):
        super(MyHttpProxyClient, self).__init__()
        self.requester_ref = requester_ref
        self.host = host
        self.port = port

    def getRequester(self):
        if self.requester_ref is None:
            print(MsgWithFrameInfo(f'requester_ref is None'
                                   f', host: {self.host}, port: {self.port}'))
            self.transport.loseConnection()
            return None

        requester = self.requester_ref()
        if requester is None:
            print(MsgWithFrameInfo(f'requester is None'
                                   f', host: {self.host}, port: {self.port}'))
            self.transport.loseConnection()
            return None

        return requester

    def dataReceived(self, data):
        requester = self.getRequester()
        if not requester:
            return

        if not requester.resCallWrite(data):
            print(MsgWithFrameInfo(f'res call write failed'
                                   f', host: {self.host}, port: {self.port}'))
            self.transport.loseConnection()

    def connectionMade(self):
        print(MsgWithFrameInfo(f'connection made'
                               f', host: {self.host}, port: {self.port}'))

        requester = self.getRequester()
        if not requester:
            return

        requester.setResRef(weakref.ref(self))

        data = b'HTTP/1.1 200 Connection Established\r\n\r\n'

        if not requester.resCallWrite(data):
            print(MsgWithFrameInfo(f'res call write failed'
                                   f', host: {self.host}, port: {self.port}'))
            self.transport.loseConnection()

    def connectionLost(self, reason):
        if reason.type == error.ConnectionDone:
            print(MsgWithFrameInfo(f'close cleanly'
                                   f', host: {self.host}, port: {self.port}'))
        elif reason.type == error.ConnectionLost:
            print(MsgWithFrameInfo(f'close non-cleanly'
                                   f', host: {self.host}, port: {self.port}'))
        else:
            print(MsgWithFrameInfo(f'connection lost'
                                   f', host: {self.host}, port: {self.port}'))

        requester = self.getRequester()
        if not requester:
            return

        requester.resCallStop()

    def reqCallWrite(self, data):
        if self.transport is None:
            return False

        self.transport.write(data)
        return True

    def reqCallStop(self):
        print(MsgWithFrameInfo(f'req call stop'
                               f', has transport: {self.transport is not None}'
                               f', host: {self.host}, port: {self.port}'))

        if self.transport is None:
            return False

        self.transport.loseConnection()
        return True


class MyHttpProxyClientFactory(protocol.ClientFactory):

    def __init__(self, requester_ref, host, port):
        super(MyHttpProxyClientFactory, self).__init__()
        self.requester_ref = requester_ref
        self.host = host
        self.port = port

    def buildProtocol(self, addr):
        print(MsgWithFrameInfo(f'build protocol'
                               f', host: {self.host}, port: {self.port}, addr: {addr}'))
        return MyHttpProxyClient(self.requester_ref, self.host, self.port)

    def clientConnectionFailed(self, connector, reason):
        print(MsgWithFrameInfo(f'connection failed'
                               f', host: {self.host}, port: {self.port}, reason: {reason.type}'))

        if self.requester_ref is None:
            print(MsgWithFrameInfo(f'requester_ref is None'
                                   f', host: {self.host}, port: {self.port}'))
            return

        requester = self.requester_ref()
        if requester is None:
            print(MsgWithFrameInfo(f'requester is None'
                                   f', host: {self.host}, port: {self.port}'))
            return

        requester.resCallStop()


class MyHttpConnectMethod(basic.LineReceiver):

    def __init__(self, joke_ref):
        super(MyHttpConnectMethod, self).__init__()
        self.joke_ref = joke_ref
        self.first_recv = True
        self.host = None
        self.port = None
        self.responser_ref = None

    def getResponser(self):
        if self.responser_ref is None:
            print(MsgWithFrameInfo(f'responser_ref is None'
                                   f', host: {self.host}, port: {self.port}'))
            self.transport.loseConnection()
            return None

        responser = self.responser_ref()
        if responser is None:
            print(MsgWithFrameInfo(f'responser is None'
                                   f', host: {self.host}, port: {self.port}'))
            self.transport.loseConnection()
            return None

        return responser

    def start(self):
        if self.host is None or self.port is None:
            print(MsgWithFrameInfo(f'http proxy start failed'
                                   f', host: {self.host}, port: {self.port}'))
            self.transport.loseConnection()
            return

        print(MsgWithFrameInfo(f'http proxy start'
                               f', host: {self.host}, port: {self.port}'))
        client_factory = MyHttpProxyClientFactory(weakref.ref(self), self.host, self.port)
        reactor.connectTCP(self.host, self.port, client_factory)

    def lineReceived(self, line):
        if self.first_recv:
            self.first_recv = False

            lst = line.split(b' ')
            if len(lst) != 3 or lst[0] != b'CONNECT' or not lst[2].startswith(b'HTTP/'):
                print(MsgWithFrameInfo(f'method parse error: {line}'))
                self.transport.loseConnection()
                return

            lst = lst[1].split(b':')
            if len(lst) != 2 or len(lst[0]) <= 0 or not lst[1].isdigit():
                print(MsgWithFrameInfo(f'host or port parse error: {line}'))
                self.transport.loseConnection()
                return

            self.host = lst[0]
            self.port = int(lst[1])

        elif len(line) <= 0:
            self.setRawMode()
            self.start()

    def rawDataReceived(self, data):
        responser = self.getResponser()
        if not responser:
            return

        if not responser.reqCallWrite(data):
            print(MsgWithFrameInfo(f'req call write failed'
                                   f', host: {self.host}, port: {self.port}'))
            self.transport.loseConnection()

    def connectionLost(self, reason):
        if reason.type == error.ConnectionDone:
            print(MsgWithFrameInfo(f'close cleanly'
                                   f', host: {self.host}, port: {self.port}'))
        elif reason.type == error.ConnectionLost:
            print(MsgWithFrameInfo(f'close non-cleanly'
                                   f', host: {self.host}, port: {self.port}'))
        else:
            print(MsgWithFrameInfo(f'connection lost'
                                   f', host: {self.host}, port: {self.port}'))

        responser = self.getResponser()
        if not responser:
            return

        responser.reqCallStop()

    def setResRef(self, responser_ref):
        self.responser_ref = responser_ref

    def resCallWrite(self, data):
        if self.transport is None:
            return False

        self.transport.write(data)
        return True

    def resCallStop(self):
        print(MsgWithFrameInfo(f'res call stop'
                               f', has transport: {self.transport is not None}'
                               f', host: {self.host}, port: {self.port}'))

        if self.transport is None:
            return False

        self.transport.loseConnection()
        return True


class MyHttpConnectMethodFactory(protocol.Factory):

    def __init__(self, joke_ref):
        super(MyHttpConnectMethodFactory, self).__init__()
        self.joke_ref = joke_ref

    def buildProtocol(self, addr):
        return MyHttpConnectMethod(self.joke_ref)


class MyJokeDataHandler:

    def __init__(self):
        self.fernet = None
        self.buf_len = 0
        self.buf = b''

    def updateFernet(self, password):
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=JOKE_SALT,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        self.fernet = Fernet(key)

    def recv(self, data):
        ret = b''
        self.buf += data

        if self.buf_len == 0 and len(self.buf) >= 4:
            self.buf_len = struct.unpack('<I', self.buf[:4])[0]
            self.buf = self.buf[4:]

        if 0 < self.buf_len <= len(self.buf):
            ret = self.buf[:self.buf_len]
            self.buf = self.buf[self.buf_len:]
            self.buf_len = 0

        if ret and self.fernet:
            ret = self.fernet.decrypt(ret)
            packet = JokePacket()
            packet.unpack(ret)
            return packet

        return None

    def send(self, packet):
        if not self.fernet:
            return b''

        data = packet.pack()
        data = self.fernet.encrypt(data)
        buf = struct.pack('<I', len(data))
        buf += data
        return buf


class MyJokeServer(protocol.Protocol):

    def __init__(self, addr):
        super(MyJokeServer, self).__init__()
        self.addr = addr
        self.verify = False
        self.verify_data = b''

        print(f'joke server wait verify, addr: {self.addr}'
              f', random len: {JOKE_RANDOM_LEN}, random key: {JOKE_RANDOM_KEY}'
              f', password len: {JOKE_PASSWORD_LEN}, password key: {JOKE_PASSWORD_KEY}'
              f', salt: {JOKE_SALT}')

        self.data_handler = MyJokeDataHandler()
        self.data_handler.updateFernet(JOKE_PASSWORD_KEY)

    def dataReceived(self, data):
        if not self.verify:
            self.verify_data += data
            if len(self.verify_data) >= JOKE_RANDOM_LEN:
                if self.verify_data != JOKE_RANDOM_KEY:
                    self.transport.loseConnection()
                    ReactorStop('joke server verify failed')
                else:
                    print(f'joke server verify succeed, addr: {self.addr}')
                    self.verify = True
                    packet = JokePacket()
                    packet.type = JokePacketType.VERIFY_SUCCEED
                    self.transport.write(self.data_handler.send(packet))

        else:
            packet = self.data_handler.recv(data)
            while packet:
                if packet.type == JokePacketType.CREATE_PROXY_REQ:
                    pass
                elif packet.type == JokePacketType.DELETE_PROXY_REQ:
                    pass
                elif packet.type == JokePacketType.TRANSFER_DATA:
                    pass

                packet = self.data_handler.recv(b'')

    def connectionLost(self, reason):
        if reason.type == error.ConnectionDone:
            print(f'joke server connection close cleanly, addr: {self.addr}')
        elif reason.type == error.ConnectionLost:
            print(f'joke server connection close non-cleanly, addr: {self.addr}')
        else:
            print(f'joke server connection connection lost, addr: {self.addr}'
                  f', reason: {reason.type}')
        ReactorStop('joke server disconnect')


class MyJokeServerFactory(protocol.Factory):

    def __init__(self):
        super(MyJokeServerFactory, self).__init__()
        self.listen_port_ref = None

    def setListenPort(self, listen_port_ref):
        self.listen_port_ref = listen_port_ref

    def buildProtocol(self, addr):
        print(f'joke server factory build protocol, addr: {addr}')
        if self.listen_port_ref is None:
            ReactorStop('joke server factory build protocol but listen port ref is none')
            return None
        listen_port = self.listen_port_ref()
        if listen_port is None:
            ReactorStop('joke server factory build protocol but listen port is none')
            return None

        listen_port.stopListening()
        return MyJokeServer(addr)


class MyJokeClient(protocol.Protocol):

    def __init__(self, addr):
        super(MyJokeClient, self).__init__()
        self.addr = addr
        self.verify = False

        print(f'joke client ready to verify, addr: {self.addr}'
              f', random len: {JOKE_RANDOM_LEN}, random key: {JOKE_RANDOM_KEY}'
              f', password len: {JOKE_PASSWORD_LEN}, password key: {JOKE_PASSWORD_KEY}'
              f', salt: {JOKE_SALT}')

        self.data_handler = MyJokeDataHandler()
        self.data_handler.updateFernet(JOKE_PASSWORD_KEY)

    def listenConnectMethod(self):
        http_connect_method_ret = reactor.listenTCP(1080, MyHttpConnectMethodFactory(weakref.ref(self)), 512)
        print(f'http connect method listen: {http_connect_method_ret.getHost()}')

    def dataReceived(self, data):
        packet = self.data_handler.recv(data)
        while packet:
            if packet.type == JokePacketType.VERIFY_SUCCEED:
                print(f'joke client confirm verify, addr: {self.addr}')
                self.listenConnectMethod()
            elif packet.type == JokePacketType.MODIFY_PASSWORD:
                pass
            elif packet.type == JokePacketType.CREATE_PROXY_RES:
                pass
            elif packet.type == JokePacketType.DELETE_PROXY_RES:
                pass
            elif packet.type == JokePacketType.TRANSFER_DATA:
                pass

            packet = self.data_handler.recv(b'')

    def connectionMade(self):
        print(f'joke client send verify')
        self.transport.write(JOKE_RANDOM_KEY)

    def connectionLost(self, reason):
        if reason.type == error.ConnectionDone:
            print(f'joke client connection close cleanly, addr: {self.addr}')
        elif reason.type == error.ConnectionLost:
            print(f'joke client connection close non-cleanly, addr: {self.addr}')
        else:
            print(f'joke client connection connection lost, addr: {self.addr}'
                  f', reason: {reason.type}')
        ReactorStop('joke client disconnect')


class MyJokeClientFactory(protocol.ClientFactory):

    def __init__(self):
        super(MyJokeClientFactory, self).__init__()

    def buildProtocol(self, addr):
        print(f'joke client factory build protocol, addr: {addr}')
        return MyJokeClient(addr)

    def clientConnectionFailed(self, connector, reason):
        print(f'joke client factory connection failed, reason: {reason.type}')
        ReactorStop('joke client connection failed')


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    observers = [MyLogObserver()]
    globalLogBeginner.beginLoggingTo(observers, True, False)

    choice_str = '01234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'

    JOKE_RANDOM_LEN = random.randint(2048, 4096)
    print(f'joke random len: {JOKE_RANDOM_LEN}')
    JOKE_RANDOM_KEY = ''.join([random.choice(choice_str) for i in range(JOKE_RANDOM_LEN)]).encode('UTF-8')
    print(f'joke random key: {JOKE_RANDOM_KEY}')

    JOKE_PASSWORD_LEN = random.randint(32, 64)
    print(f'joke password len: {JOKE_PASSWORD_LEN}')
    JOKE_PASSWORD_KEY = ''.join([random.choice(choice_str) for i in range(JOKE_PASSWORD_LEN)]).encode('UTF-8')
    print(f'joke password key: {JOKE_PASSWORD_KEY}')

    JOKE_SALT = os.urandom(16)
    print(f'joke salt: {JOKE_SALT}')

    joke_server_factory = MyJokeServerFactory()
    joke_server_ret = reactor.listenTCP(0, joke_server_factory, 512)
    joke_host = joke_server_ret.getHost()
    print(f'joke server listen: {joke_host}')
    joke_server_factory.setListenPort(weakref.ref(joke_server_ret))

    joke_client_factory = MyJokeClientFactory()
    reactor.connectTCP('127.0.0.1', joke_host.port, joke_client_factory)

    reactor.run()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/

