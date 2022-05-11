import queue
import asyncio
import websockets
import websockets.exceptions


## SOCKETS CLASS ##
# websocket backend static class
class Sockets():

    ## WEBSOCKET SERVER ##

    ## class methods ##
    # socket server start
    @staticmethod
    def socket_run(production='False', host='localhost', port='3000', sockets_signal_queue=None):
        # arguments
        port = int(port)
        production = bool(production)

        # client list
        clients = {}

        # socket server event handler
        async def socket_handler(websocket):
            id = str(websocket.id)
            if id not in clients:
                clients[id] = {'watching_runs': [], 'complete_runs': []}
            while True:
                # check signal queue
                queue_msg = ''
                try:
                    queue_msg = sockets_signal_queue.get(block=False)
                except queue.Empty:
                    queue_msg = ''
                if queue_msg != '':
                    queue_msg = queue_msg.split(':')
                    if queue_msg[0] == 'notify':
                        target_run_id = queue_msg[1]
                        for c in clients.keys():
                            watching_runs = clients[c]['watching_runs']
                            for watching_run in watching_runs:
                                if watching_run == target_run_id:
                                    clients[c]['complete_runs'].append(target_run_id)
                                    clients[c]['watching_runs'].remove(target_run_id)

                # check sockets
                ws_msg = ''
                try:
                    if len(clients[id]['complete_runs']) > 0:
                        for run_id in clients[id]['complete_runs']:
                            await websocket.send(f"notify:{run_id}")
                        clients[id]['complete_runs'] = []
                    try:
                        ws_msg = await asyncio.wait_for(websocket.recv(), 0.2)
                    except asyncio.TimeoutError:
                        ws_msg = ''
                    if ws_msg != '':
                        print("[ws] socket received: {}".format(ws_msg))
                        ws_msg = ws_msg.split(":")
                        if ws_msg[0] == 'msg':
                            pass
                        elif ws_msg[0] == 'sub':
                            run_id = ws_msg[1]
                        clients[id]['watching_runs'].append(run_id)
                        print(clients)
                        # await websocket.send(message)  # echo server

                except (websockets.exceptions.ConnectionClosedOK, websockets.exceptions.ConnectionClosedError) as e:
                    print(f'[ws] client {id} disconnected')
                    del clients[id]
                    break

        # socket server event loop
        async def socket_serve(host, port):
            async with websockets.serve(socket_handler, host, port):
                await asyncio.Future()  # run forever

        # socket server start
        asyncio.run(socket_serve(host, port))

    # websocket send
    @staticmethod
    def socket_send(message):
        # not implemented yet
        # use self.socket_signal_queue to send data to websocket client
        pass
