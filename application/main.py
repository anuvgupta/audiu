# AUDIU
# main.py

import os
import queue
import shutil
import pathlib
import multiprocessing

# local imports
import backend
import recommendations

# constants
HOST = '0.0.0.0'
PORT = 8001
HOST_PORT = f'{HOST}:{PORT}'
CONFIG = 'config.json'
DATASET = 'dataset.json'
DB_NAME = 'audiu'
DB_HOST = 'localhost'
DB_PORT = 27017
MODEL_RUN_SRC = 'data/runs'
MP_QUEUE_SIZE = 15
DEL_FS_REC = True
PROD = True


## MAIN ##
# main entry point
def main():
    # paths
    package_dir_path = os.path.dirname(os.path.abspath(__file__))
    model_run_dir_path = os.path.join(package_dir_path, MODEL_RUN_SRC)
    dataset_src = os.path.join(package_dir_path, DATASET)
    # ml model
    recommendations_model = recommendations.Recommendations(DATASET, MODEL_RUN_SRC)
    recommendations_model.load_dataset()
    # process management
    model_run_procs = {}
    model_run_signal_queues = {}
    backend_signal_queue = multiprocessing.Queue(MP_QUEUE_SIZE)
    # backend process
    backend_process = multiprocessing.Process(target=backend.Backend.web_run,
                                              args=(str(DATASET), str(HOST), str(PORT), str(DB_HOST), str(DB_PORT), str(DB_NAME), str(MODEL_RUN_SRC), str(MP_QUEUE_SIZE), str(PROD),
                                                    backend_signal_queue))
    backend_process.start()
    # queue event loop
    try:
        while True:
            msg = ''
            try:
                msg = backend_signal_queue.get(block=False)
            except queue.Empty:
                msg = ''
            if msg != '':
                print('[main] received msg from backend: {}'.format(msg))
            if "main:recommendations-run" in msg:
                target_run_id = msg.split(":")[2]
                recommendations_model.recommendations_prepare_input(target_run_id)
                model_run_signal_queues[target_run_id] = multiprocessing.Queue(MP_QUEUE_SIZE)
                model_run_procs[target_run_id] = multiprocessing.Process(target=recommendations.Recommendations.recommendations_run,
                                                                         args=(str(target_run_id), str(MODEL_RUN_SRC), str(CONFIG), model_run_signal_queues[target_run_id]))
                model_run_procs[target_run_id].start()
            elif msg == "main:backend-done":
                break
            else:
                pass
            for run_id, model_run_signal_queue in model_run_signal_queues.items():
                if model_run_signal_queue != None:
                    msg = ''
                    try:
                        msg = model_run_signal_queue.get(block=False)
                    except queue.Empty:
                        msg = ''
                    if msg != '':
                        print('[main] received msg from model run {}: {}'.format(run_id, msg))
                    if "main:run-start" in msg:
                        target_run_id = msg.split(":")[2]
                        if not backend.Backend.update_model_run_record(target_run_id, "running", target_host_port=HOST_PORT):
                            print("[main] failed to update model run record through local put request")
                        print("[main] model run processes:")
                        print(model_run_procs)
                    elif "main:run-done" in msg:
                        target_run_id = msg.split(":")[2]
                        model_run_procs[target_run_id].join()
                        if not backend.Backend.update_model_run_record(target_run_id, "complete", target_host_port=HOST_PORT, update_inference_output=True, model_run_src=MODEL_RUN_SRC):
                            print("[main] failed to update model run record through local put request")
                        model_run_procs[target_run_id] = None
                        model_run_signal_queues[target_run_id] = None
                        print("[main] model run processes:")
                        print(model_run_procs)
                        if DEL_FS_REC:
                            model_run_path = pathlib.Path(os.path.join(model_run_dir_path, target_run_id))
                            model_run_path.mkdir(parents=True, exist_ok=True)
                            try:
                                shutil.rmtree(model_run_path)
                            except Exception as e:
                                print("[main] error removing model run data from local filesystem")
                                print(e)

            for k in list(model_run_signal_queues.keys()):
                if model_run_signal_queues[k] == None:
                    del model_run_signal_queues[k]
                if model_run_procs[k] == None:
                    del model_run_procs[k]
                    print("[main] model run processes:")
                    print(model_run_procs)

    except Exception as e:
        print("[main] error in main queue event loop")
        print(e)
        pass

    for run_id, model_run_signal_queue in model_run_signal_queues.items():
        if model_run_signal_queue != None:
            model_run_signal_queue.put("run:quit")
    for run_id, model_run_proc in model_run_procs.items():
        if model_run_proc != None:
            model_run_proc.join()
    backend_signal_queue.put("backend:quit")
    backend_process.join()


# thread entry point
if __name__ == "__main__":
    main()
