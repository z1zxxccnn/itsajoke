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

from twisted.internet import reactor, endpoints, protocol, error
from twisted.protocols import basic
from enum import Enum, unique
import weakref


def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    print(f'Hi, {name}')  # Press Ctrl+F8 to toggle the breakpoint.


@unique
class MyHttpConnectMethodStopReason(Enum):
    OK = 0,
    METHOD_PARSE_ERROR = 1
    HOST_OR_PORT_PARSE_ERROR = 2
    CONNECTION_NOT_ESTABLISHED = 3
    CONNECTION_HAVE_BEEN_LOST = 4
    HOST_OR_PORT_IS_NONE = 5
    PROXY_CONNECT_FAILED = 6
    PROXY_CONNECTION_DONE = 7


def MyHttpConnectMethodStopReasonToStr(reason):
    if reason == MyHttpConnectMethodStopReason.OK:
        return 'ok'
    elif reason == MyHttpConnectMethodStopReason.METHOD_PARSE_ERROR:
        return 'method parse error'
    elif reason == MyHttpConnectMethodStopReason.HOST_OR_PORT_PARSE_ERROR:
        return 'host or port parse error'
    elif reason == MyHttpConnectMethodStopReason.CONNECTION_NOT_ESTABLISHED:
        return 'connection not established'
    elif reason == MyHttpConnectMethodStopReason.CONNECTION_HAVE_BEEN_LOST:
        return 'connection have been lost'
    elif reason == MyHttpConnectMethodStopReason.HOST_OR_PORT_IS_NONE:
        return 'host or port is none'
    elif reason == MyHttpConnectMethodStopReason.PROXY_CONNECT_FAILED:
        return 'proxy connect failed'
    elif reason == MyHttpConnectMethodStopReason.PROXY_CONNECTION_DONE:
        return 'proxy connection done'
    else:
        return ''


class MyHttpProxyClient(protocol.Protocol):

    def __init__(self, requester, host, port):
        super(MyHttpProxyClient, self).__init__()
        self.requester = requester
        self.host = host
        self.port = port

    def dataReceived(self, data):
        if self.requester.transport is None:
            print(f'http proxy data received but requester is none'
                  f', host: {self.host}, port: {self.port}')
            self.transport.loseConnection()
            return

        self.requester.transport.write(data)

    def connectionMade(self):
        if self.requester.transport is None:
            print(f'http proxy connection made but requester is none'
                  f', host: {self.host}, port: {self.port}')
            self.transport.loseConnection()
            return

        print(f'http proxy connection made, host: {self.host}, port: {self.port}')
        self.requester.transport.write(b'HTTP/1.1 200 Connection Established\r\n\r\n')

    def connectionLost(self, reason):
        if reason.type == error.ConnectionDone:
            print(f'http proxy close cleanly'
                  f', host: {self.host}, port: {self.port}')
            self.requester.stop(MyHttpConnectMethodStopReason.PROXY_CONNECTION_DONE)
        elif reason.type == error.ConnectionLost:
            print(f'http proxy close non-cleanly'
                  f', host: {self.host}, port: {self.port}')
            self.requester.stop(MyHttpConnectMethodStopReason.PROXY_CONNECTION_DONE)
        else:
            print(f'http proxy connection lost, reason: {reason}'
                  f', host: {self.host}, port: {self.port}')
            self.requester.stop(MyHttpConnectMethodStopReason.PROXY_CONNECT_FAILED)


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
        if reason.type == error.ConnectionDone:
            print(f'close cleanly, cur num: {self.factory.numProtocols}'
                  f', host: {self.host}, port: {self.port}')
        elif reason.type == error.ConnectionLost:
            print(f'close non-cleanly, cur num: {self.factory.numProtocols}'
                  f', host: {self.host}, port: {self.port}')
        else:
            print(f'connection lost, cur num: {self.factory.numProtocols}, reason: {reason}'
                  f', host: {self.host}, port: {self.port}')

    def start(self):
        if self.host is None or self.port is None:
            self.stop(MyHttpConnectMethodStopReason.HOST_OR_PORT_IS_NONE)
            return

        print(f'http proxy client start, host: {self.host}, port: {self.port}')
        client = MyHttpProxyClient(self, self.host, self.port)
        self.clientRef = weakref.ref(client)
        point = endpoints.TCP4ClientEndpoint(reactor, self.host, self.port)
        endpoints.connectProtocol(point, client)

    def stop(self, reason):
        print(f'http connect stop, reason: {MyHttpConnectMethodStopReasonToStr(reason)}'
              f', host: {self.host}, port: {self.port}'
              f', has transport: {self.transport is not None}, has clientRef: {self.clientRef is not None}')

        if self.transport is not None:
            self.transport.loseConnection()

        if self.clientRef is not None:
            client = self.clientRef()
            if client is not None and client.transport is not None:
                client.transport.loseConnection()

    def lineReceived(self, line):
        if self.line_mode == 1:
            print(f'line received: {line}')

        if self.firstRecv:
            self.firstRecv = False

            lst = line.split(b' ')
            if len(lst) != 3 or lst[0] != b'CONNECT' or not lst[2].startswith(b'HTTP/'):
                self.stop(MyHttpConnectMethodStopReason.METHOD_PARSE_ERROR)
                return

            lst = lst[1].split(b':')
            if len(lst) != 2 or len(lst[0]) <= 0 or not lst[1].isdigit():
                self.stop(MyHttpConnectMethodStopReason.HOST_OR_PORT_PARSE_ERROR)
                return

            self.host = lst[0]
            self.port = int(lst[1])

        elif len(line) <= 0:
            print(f'set raw mode')
            self.setRawMode()
            self.start()

    def rawDataReceived(self, data):
        if self.clientRef is None:
            self.stop(MyHttpConnectMethodStopReason.CONNECTION_NOT_ESTABLISHED)
            return

        client = self.clientRef()
        if client is None or client.transport is None:
            self.stop(MyHttpConnectMethodStopReason.CONNECTION_HAVE_BEEN_LOST)
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
