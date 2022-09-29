# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

import platform
if platform.system() == 'Windows':
    from twisted.internet import iocpreactor
    try:
        iocpreactor.install()
    except:
        pass
elif platform.system() == 'Darwin':
    from twisted.internet import kqreactor
    try:
        kqreactor.install()
    except:
        pass
elif platform.system() == 'Linux':
    from twisted.internet import epollreactor
    try:
        epollreactor.install()
    except:
        pass

from twisted.internet import reactor, endpoints, protocol
from twisted.protocols import basic
from enum import Enum, unique
import weakref


def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    print(f'Hi, {name}')  # Press Ctrl+F8 to toggle the breakpoint.


@unique
class MyHttpConnectMethodStopReason(Enum):
    OK = 0,
    PARSE_ERROR = 1
    CONNECT_FAILED = 2
    CONNECT_NOT_ESTABLISHED = 3
    CONNECT_HAVE_BEEN_LOST = 4


class MyHttpProxyClient(protocol.Protocol):

    def __init__(self, requester):
        super(MyHttpProxyClient, self).__init__()
        self.requester = requester

    def dataReceived(self, data):
        if self.requester.transport is None:
            self.transport.loseConnection()
            return

        self.requester.transport.write(data)

    def connectionMade(self):
        if self.requester.transport is None:
            self.transport.loseConnection()
            return

        self.requester.transport.write(b'HTTP/1.1 200 Connection Established\r\n\r\n')

    def connectionLost(self, reason):
        self.requester.stop(MyHttpConnectMethodStopReason.CONNECT_FAILED)


class MyHttpConnectMethod(basic.LineReceiver):

    def __init__(self, factory):
        super(MyHttpConnectMethod, self).__init__()
        self.factory = factory
        self.firstRecv = True
        self.host = None
        self.port = None
        self.clientRef = None
        
    def connectionMade(self):
        super(MyHttpConnectMethod, self).connectionMade()
        self.factory.numProtocols += 1
        print(f'connection made, cur num: {self.factory.numProtocols}')
        
    def connectionLost(self, reason):
        super(MyHttpConnectMethod, self).connectionLost(reason)
        self.factory.numProtocols -= 1
        print(f'connection lost, cur num: {self.factory.numProtocols}, reason: {reason}')

    def start(self):
        if self.host is None or self.port is None:
            return

        client = MyHttpProxyClient(self)
        self.clientRef = weakref.ref(client)
        point = endpoints.TCP4ClientEndpoint(reactor, self.host, self.port)
        endpoints.connectProtocol(point, client)

    def stop(self, reason):
        if self.transport is not None:
            if reason == MyHttpConnectMethodStopReason.PARSE_ERROR:
                self.transport.write(b'HTTP/1.1 403 Forbidden\r\n\r\n')
            elif reason == MyHttpConnectMethodStopReason.CONNECT_FAILED:
                self.transport.write(b'HTTP/1.1 502 Bad Gateway\r\n\r\n')
            self.transport.loseConnection()

        if self.clientRef is not None:
            client = self.clientRef.ref()
            if client is not None and client.transport is not None:
                client.transport.loseConnection()

    def lineReceived(self, line):
        if self.firstRecv:
            self.firstRecv = False

            lst = line.split(b' ')
            if len(lst) != 3 or lst[0] != 'CONNECT' or not lst[2].startswith(b'HTTP/'):
                self.stop(MyHttpConnectMethodStopReason.PARSE_ERROR)
                return

            lst = lst[1].split(b':')
            if len(lst) != 2 or len(lst[0]) <= 0 or not lst[1].isdigit():
                self.stop(MyHttpConnectMethodStopReason.PARSE_ERROR)
                return

            self.host = lst[0]
            self.port = int(lst[1])

        elif len(line) <= 0:
            self.setRawMode()

    def rawDataReceived(self, data):
        if self.clientRef is None:
            self.stop(MyHttpConnectMethodStopReason.CONNECT_NOT_ESTABLISHED)
            return

        client = self.clientRef()
        if client is None or client.transport is None:
            self.stop(MyHttpConnectMethodStopReason.CONNECT_HAVE_BEEN_LOST)
            return

        client.transport.write(data)


class MyHttpConnectMethodFactory(protocol.Factory):

    def __init__(self):
        super(MyHttpConnectMethodFactory, self).__init__()
        self.numProtocols = 0

    def buildProtocol(self, addr):
        return MyHttpConnectMethod(self)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    print_hi('PyCharm')

    endpoint = endpoints.TCP4ServerEndpoint(reactor, 1080)
    endpoint.listen(MyHttpConnectMethodFactory())
    reactor.run()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
