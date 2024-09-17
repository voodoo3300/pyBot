from py_bot_server import PyBotServer

import asyncio

if __name__ == "__main__":
    server = PyBotServer()
    asyncio.run(server.start_server())