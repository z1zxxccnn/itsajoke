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
import gc


def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    print(f'Hi, {name}')  # Press Ctrl+F8 to toggle the breakpoint.


@unique
class MyHttpConnectMethodStopReason(Enum):
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
        return 'http_connection lost'
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


class MyHttpProxyClient(protocol.Protocol):

    def __init__(self, requester_ref, host, port):
        super(MyHttpProxyClient, self).__init__()
        self.requester_ref = requester_ref
        self.host = host
        self.port = port

    def __del__(self):
        print(f'MyHttpProxyClient __del__ call'
              f', host: {self.host}, port: {self.port}')

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


class MyHttpProxyClientFactory(protocol.ClientFactory):

    def __init__(self, requester_ref, host, port):
        super(MyHttpProxyClientFactory, self).__init__()
        self.requester_ref = requester_ref
        self.host = host
        self.port = port

    def __del__(self):
        print(f'MyHttpProxyClientFactory __del__ call'
              f', host: {self.host}, port: {self.port}')

    def startedConnecting(self, connector):
        print(f'http proxy client factory started to connect'
              f', host: {self.host}, port: {self.port}, connector: {connector}')

    def buildProtocol(self, addr):
        print(f'http proxy client factory connected'
              f', host: {self.host}, port: {self.port}, addr: {addr}')

        return MyHttpProxyClient(self.requester_ref, self.host, self.port)

    def clientConnectionLost(self, connector, reason):
        if self.requester_ref is None:
            print(f'http proxy client factory connection failed buf requester ref is none'
                  f', host: {self.host}, port: {self.port}')
            return

        requester = self.requester_ref()
        if requester is None:
            print(f'http proxy client factory connection failed buf requester is none'
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
                  f', host: {self.host}, port: {self.port}, reason: {reason}')
            requester.stop(MyHttpConnectMethodStopReason.PROXY_CONNECTION_LOST)

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

        requester.stop(MyHttpConnectMethodStopReason.PROXY_CONNECTION_FAILED)


class MyHttpConnectMethod(basic.LineReceiver):

    def __init__(self, factory):
        super(MyHttpConnectMethod, self).__init__()
        self.factory = factory
        self.first_recv = True
        self.host = None
        self.port = None
        self.client_ref = None

    def __del__(self):
        print(f'MyHttpConnectMethod __del__ call'
              f', host: {self.host}, port: {self.port}')

    def connectionMade(self):
        super(MyHttpConnectMethod, self).connectionMade()
        self.factory.num_protocols += 1
        print(f'connection made, cur num: {self.factory.num_protocols}')

    def connectionLost(self, reason):
        super(MyHttpConnectMethod, self).connectionLost(reason)
        self.factory.num_protocols -= 1
        if reason.type == error.ConnectionDone:
            print(f'close cleanly, cur num: {self.factory.num_protocols}'
                  f', host: {self.host}, port: {self.port}')
            self.stop(MyHttpConnectMethodStopReason.HTTP_CONNECTION_DONE)
        elif reason.type == error.ConnectionLost:
            print(f'close non-cleanly, cur num: {self.factory.num_protocols}'
                  f', host: {self.host}, port: {self.port}')
            self.stop(MyHttpConnectMethodStopReason.HTTP_CONNECTION_DONE)
        else:
            print(f'connection lost, cur num: {self.factory.num_protocols}, reason: {reason}'
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
              f', has transport: {self.transport is not None}, has client_ref: {self.client_ref is not None}')

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
            print(f'set raw mode')
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

    def __del__(self):
        print(f'MyHttpConnectMethodFactory __del__ call')

    def buildProtocol(self, addr):
        return MyHttpConnectMethod(self)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    print_hi('PyCharm')

    endpoint = endpoints.TCP4ServerEndpoint(reactor, 1080)
    endpoint.listen(MyHttpConnectMethodFactory())
    reactor.run()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/

