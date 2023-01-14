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

JOKE_RANDOM_LEN = 0
JOKE_RANDOM_KEY = b''

JOKE_PASSWORD_LEN = 0
JOKE_PASSWORD_KEY = b''

JOKE_SALT = b''

JOKE_CALL_STOP = False


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
class MyHttpConnectMethodStopReason(IntEnum):
    OK = 0
    METHOD_PARSE_ERROR = 1
    HOST_OR_PORT_PARSE_ERROR = 2
    HOST_OR_PORT_IS_NONE = 3
    HTTP_CONNECTION_DONE = 4
    HTTP_CONNECTION_LOST = 5
    PROXY_CONNECTION_NOT_ESTABLISHED = 6
    PROXY_CONNECTION_HAVE_BEEN_LOST = 7
    PROXY_CONNECTION_DONE = 8
    PROXY_CONNECTION_LOST = 9
    PROXY_CONNECTION_FAILED = 10


def MyHttpConnectMethodStopReasonToStr(reason):
    if reason == MyHttpConnectMethodStopReason.OK:
        return 'ok'
    elif reason == MyHttpConnectMethodStopReason.METHOD_PARSE_ERROR:
        return 'method parse error'
    elif reason == MyHttpConnectMethodStopReason.HOST_OR_PORT_PARSE_ERROR:
        return 'host or port parse error'
    elif reason == MyHttpConnectMethodStopReason.HOST_OR_PORT_IS_NONE:
        return 'host or port is none'
    elif reason == MyHttpConnectMethodStopReason.HTTP_CONNECTION_DONE:
        return 'http connection done'
    elif reason == MyHttpConnectMethodStopReason.HTTP_CONNECTION_LOST:
        return 'http connection lost'
    elif reason == MyHttpConnectMethodStopReason.PROXY_CONNECTION_NOT_ESTABLISHED:
        return 'proxy connection not established'
    elif reason == MyHttpConnectMethodStopReason.PROXY_CONNECTION_HAVE_BEEN_LOST:
        return 'proxy connection have been lost'
    elif reason == MyHttpConnectMethodStopReason.PROXY_CONNECTION_DONE:
        return 'proxy connection done'
    elif reason == MyHttpConnectMethodStopReason.PROXY_CONNECTION_LOST:
        return 'proxy connection lost'
    elif reason == MyHttpConnectMethodStopReason.PROXY_CONNECTION_FAILED:
        return 'proxy connection failed'
    else:
        return ''


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

    def dataReceived(self, data):
        if self.requester_ref is None:
            print(f'http proxy data received buf requester ref is none'
                  f', host: {self.host}, port: {self.port}')
            self.transport.loseConnection()
            return

        requester = self.requester_ref()
        if requester is None:
            print(f'http proxy data received buf requester is none'
                  f', host: {self.host}, port: {self.port}')
            self.transport.loseConnection()
            return

        if requester.transport is None:
            print(f'http proxy data received but transport of requester is none'
                  f', host: {self.host}, port: {self.port}')
            self.transport.loseConnection()
            return

        requester.transport.write(data)

    def connectionMade(self):
        if self.requester_ref is None:
            print(f'http proxy connection made buf requester ref is none'
                  f', host: {self.host}, port: {self.port}')
            self.transport.loseConnection()
            return

        requester = self.requester_ref()
        if requester is None:
            print(f'http proxy connection made buf requester is none'
                  f', host: {self.host}, port: {self.port}')
            self.transport.loseConnection()
            return

        if requester.transport is None:
            print(f'http proxy connection made but transport of requester is none'
                  f', host: {self.host}, port: {self.port}')
            self.transport.loseConnection()
            return

        print(f'http proxy connection made, host: {self.host}, port: {self.port}')
        requester.setHttpProxyClient(self)
        requester.transport.write(b'HTTP/1.1 200 Connection Established\r\n\r\n')

    def connectionLost(self, reason):
        if self.requester_ref is None:
            print(f'http proxy connection lost buf requester ref is none'
                  f', host: {self.host}, port: {self.port}')
            return

        requester = self.requester_ref()
        if requester is None:
            print(f'http proxy connection lost buf requester is none'
                  f', host: {self.host}, port: {self.port}')
            return

        if reason.type == error.ConnectionDone:
            print(f'http proxy close cleanly'
                  f', host: {self.host}, port: {self.port}')
            requester.stop(MyHttpConnectMethodStopReason.PROXY_CONNECTION_DONE)
        elif reason.type == error.ConnectionLost:
            print(f'http proxy close non-cleanly'
                  f', host: {self.host}, port: {self.port}')
            requester.stop(MyHttpConnectMethodStopReason.PROXY_CONNECTION_DONE)
        else:
            print(f'http proxy connection lost'
                  f', host: {self.host}, port: {self.port}, reason: {reason.type}')
            requester.stop(MyHttpConnectMethodStopReason.PROXY_CONNECTION_LOST)


class MyHttpProxyClientFactory(protocol.ClientFactory):

    def __init__(self, requester_ref, host, port):
        super(MyHttpProxyClientFactory, self).__init__()
        self.requester_ref = requester_ref
        self.host = host
        self.port = port

    def buildProtocol(self, addr):
        print(f'http proxy client factory build protocol'
              f', host: {self.host}, port: {self.port}, addr: {addr}')

        return MyHttpProxyClient(self.requester_ref, self.host, self.port)

    def clientConnectionFailed(self, connector, reason):
        if self.requester_ref is None:
            print(f'http proxy client factory connection failed buf requester ref is none'
                  f', host: {self.host}, port: {self.port}')
            return

        requester = self.requester_ref()
        if requester is None:
            print(f'http proxy client factory connection failed buf requester is none'
                  f', host: {self.host}, port: {self.port}')
            return

        print(f'http proxy client factory connection failed'
              f', host: {self.host}, port: {self.port}, reason: {reason.type}')
        requester.stop(MyHttpConnectMethodStopReason.PROXY_CONNECTION_FAILED)


class MyHttpConnectMethod(basic.LineReceiver):

    def __init__(self, factory_ref):
        super(MyHttpConnectMethod, self).__init__()
        self.factory_ref = factory_ref
        self.first_recv = True
        self.host = None
        self.port = None
        self.client_ref = None

    def connectionMade(self):
        super(MyHttpConnectMethod, self).connectionMade()
        if self.factory_ref is None:
            return
        factory = self.factory_ref()
        if factory is None:
            return

        factory.num_protocols += 1
        print(f'connection made, cur num: {factory.num_protocols}')

    def connectionLost(self, reason):
        super(MyHttpConnectMethod, self).connectionLost(reason)
        if self.factory_ref is None:
            return
        factory = self.factory_ref()
        if factory is None:
            return

        factory.num_protocols -= 1
        if reason.type == error.ConnectionDone:
            print(f'close cleanly, cur num: {factory.num_protocols}'
                  f', host: {self.host}, port: {self.port}')
            self.stop(MyHttpConnectMethodStopReason.HTTP_CONNECTION_DONE)
        elif reason.type == error.ConnectionLost:
            print(f'close non-cleanly, cur num: {factory.num_protocols}'
                  f', host: {self.host}, port: {self.port}')
            self.stop(MyHttpConnectMethodStopReason.HTTP_CONNECTION_DONE)
        else:
            print(f'connection lost, cur num: {factory.num_protocols}, reason: {reason.type}'
                  f', host: {self.host}, port: {self.port}')
            self.stop(MyHttpConnectMethodStopReason.HTTP_CONNECTION_LOST)

    def setHttpProxyClient(self, client):
        self.client_ref = weakref.ref(client)

    def start(self):
        if self.host is None or self.port is None:
            self.stop(MyHttpConnectMethodStopReason.HOST_OR_PORT_IS_NONE)
            return

        print(f'http proxy start, host: {self.host}, port: {self.port}')
        client_factory = MyHttpProxyClientFactory(weakref.ref(self), self.host, self.port)
        reactor.connectTCP(self.host, self.port, client_factory)

    def stop(self, reason):
        print(f'http connect stop, reason: {MyHttpConnectMethodStopReasonToStr(reason)}'
              f', host: {self.host}, port: {self.port}'
              f', has transport: {self.transport is not None}'
              f', has client_ref: {self.client_ref is not None}')

        if self.transport is not None:
            self.transport.loseConnection()

        if self.client_ref is not None:
            client = self.client_ref()
            if client is not None and client.transport is not None:
                client.transport.loseConnection()

    def lineReceived(self, line):
        if self.first_recv:
            self.first_recv = False

            lst = line.split(b' ')
            if len(lst) != 3 or lst[0] != b'CONNECT' or not lst[2].startswith(b'HTTP/'):
                print(f'line received but method parse error: {line}')
                self.stop(MyHttpConnectMethodStopReason.METHOD_PARSE_ERROR)
                return

            lst = lst[1].split(b':')
            if len(lst) != 2 or len(lst[0]) <= 0 or not lst[1].isdigit():
                print(f'line received but host or port parse error: {line}')
                self.stop(MyHttpConnectMethodStopReason.HOST_OR_PORT_PARSE_ERROR)
                return

            self.host = lst[0]
            self.port = int(lst[1])

        elif len(line) <= 0:
            self.setRawMode()
            self.start()

    def rawDataReceived(self, data):
        if self.client_ref is None:
            self.stop(MyHttpConnectMethodStopReason.PROXY_CONNECTION_NOT_ESTABLISHED)
            return

        client = self.client_ref()
        if client is None or client.transport is None:
            self.stop(MyHttpConnectMethodStopReason.PROXY_CONNECTION_HAVE_BEEN_LOST)
            return

        client.transport.write(data)


class MyHttpConnectMethodFactory(protocol.Factory):

    def __init__(self):
        super(MyHttpConnectMethodFactory, self).__init__()
        self.num_protocols = 0

    def buildProtocol(self, addr):
        return MyHttpConnectMethod(self)


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

    def dataReceived(self, data):
        packet = self.data_handler.recv(data)
        while packet:
            if packet.type == JokePacketType.VERIFY_SUCCEED:
                print(f'joke client confirm verify, addr: {self.addr}')
            elif packet.type == JokePacketType.MODIFY_PASSWORD:
                pass
            elif packet.type == JokePacketType.CREATE_PROXY_RES:
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

    http_connect_method_ret = reactor.listenTCP(1080, MyHttpConnectMethodFactory(), 512)
    print(f'http connect method listen: {http_connect_method_ret.getHost()}')

    reactor.run()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/

