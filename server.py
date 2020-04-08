#
# Серверное приложение для соединений
#
""" Сервер заточен под PuTTY"""

import asyncio
from asyncio import transports
from typing import Optional

class ServerProtocol(asyncio.Protocol):
    login: str = None
    server: 'Server'
    transport: transports.Transport
    try_count: int = 2                      # количество попыток логина
    history_count: int = 10                 # количество отображаемых старых сообщений при логине

    def __init__(self, server: 'Server'):
        self.server = server

    def data_received(self, data: bytes):
#        print(data)
        decoded = data.decode().replace("\r\n", "")
        if decoded == "":                    # не реагируем на пустые строки
            return

        if self.login is not None:
            self.send_message(decoded)
        else:
            if decoded.startswith("login:"):
                new_login = decoded.replace("login:", "")
                check_login = ["false" for i in self.server.clients if i.login == new_login]
                if len(check_login) != 0:
                    self.try_count = self.try_count - 1
                    self.transport.write(
                        f"Привет, логин {new_login} занят! Выберите другой\r\nУ Вас {self.try_count} попытка\r\n".encode()
                    )

                    if self.try_count > 0:
                        self.transport.write(
                            f"Занятые логины:\r\n".encode()
                        )
                        for user in self.server.clients[:-1]:
                            self.transport.write(
                                f"{user.login}\r\n".encode()
                            )
                    else:
                        self.transport.close()

                    return

                self.login = new_login
                self.transport.write(
                    f"Привет, {self.login}!\r\nПоследние {self.history_count} сообщений:\r\n".encode()
                )
                self.server.send_history(self, self.history_count)
                self.transport.write("*****\r\n".encode())
            else:
                self.transport.write("Неправильный логин\r\n".encode())

    def connection_made(self, transport: transports.Transport):
        self.server.clients.append(self)
        self.transport = transport
        print("Пришел новый клиент")

    def connection_lost(self, exception):
        self.server.clients.remove(self)
        print("Клиент вышел")

    def send_message(self, content: str):
        message = f"{self.login}: {content}"
        self.server.history.append(message)

        for user in self.server.clients:
            if user.login != self.login:
                user.transport.write(
                    f"{message}\r\n".encode()
                )


class Server:
    clients: list
    history: list

    def __init__(self):
        self.clients = []
        self.history = []

    def build_protocol(self):
        return ServerProtocol(self)

    def send_history(self, user: ServerProtocol, history_count: int):
        for message in self.history[(history_count * (-1)):]:
            user.transport.write(
                f"{message}\r\n".encode()
            )

    async def start(self):
        loop = asyncio.get_running_loop()

        coroutine = await loop.create_server(
            self.build_protocol,
            "127.0.0.1",
            8888
        )

        print("Сервер запущен ...")

        await coroutine.serve_forever()

process = Server()

try:
    asyncio.run(process.start())
except KeyboardInterrupt:
    print("Сервер остановлен вручную")
