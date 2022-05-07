import asyncio
import websockets

## WEBSOCKET SERVER ##
# socket server start
def socket_run(production='False', host='localhost', port='3000', signal_queue=None):
    port = int(port)
    production = bool(production)
    # socket server event handler

    async def socket_handler(websocket):
        async for message in websocket:
            print("[ws] socket received: {}".format(message))
            # await websocket.send(message)  # echo server
    # socket server event loop

    async def socket_serve(host, port):
        async with websockets.serve(socket_handler, host, port):
            await asyncio.Future()  # run forever
    # socket server start
    asyncio.run(socket_serve(host, port))
# websocket send
def socket_send(self, message):
    # not implemented yet
    # use self.socket_signal_queue to send data to websocket client
    pass
