# AUDIU
# main.py

import multiprocessing

# local imports
import queue
import backend
import recommendations

HOST = '0.0.0.0'
PORT = 8001
DATASET = 'dataset.json'
DB_NAME = 'audiu'
DB_HOST = 'localhost'
DB_PORT = 27017
MODEL_RUN_SRC = 'data/runs'
PROD = True

## MAIN ##
# main entry point
def main():
    recommendations_model = recommendations.Recommendations(
        DATASET, MODEL_RUN_SRC)
    recommendations_model.load_dataset()
    model_run_procs = {}
    model_run_signal_queues = {}
    backend_signal_queue = multiprocessing.Queue(20)
    backend_process = multiprocessing.Process(
        target=backend.web_run, args=(str(DATASET), str(HOST), str(PORT), str(DB_HOST), str(DB_PORT), str(DB_NAME), str(MODEL_RUN_SRC), str(PROD), backend_signal_queue))
    backend_process.start()
    try:
        while True:
            msg = ''
            try:
                msg = backend_signal_queue.get(False)
            except queue.Empty:
                msg = ''
            if msg != '':
                print('main received msg from backend: {}'.format(msg))
            if "main:recommendations-run" in msg:
                target_run_id = msg.split(":")[2]
                recommendations_model.recommendations_prepare_input(target_run_id)
                model_run_signal_queues[target_run_id] = multiprocessing.Queue(10)
                model_run_procs[target_run_id] = multiprocessing.Process(target=recommendations.Recommendations.recommendations_run, args=(
                    str(target_run_id), str(MODEL_RUN_SRC), model_run_signal_queues[target_run_id]))
                model_run_procs[target_run_id].start()
            elif msg == "main:backend-done":
                break
            else:
                pass
            for run_id, model_run_signal_queue in model_run_signal_queues.items():
                if model_run_signal_queue != None:
                    msg = ''
                    try:
                        msg = model_run_signal_queue.get(False)
                    except queue.Empty:
                        msg = ''
                    if msg != '':
                        print('main received msg from model run {}: {}'.format(run_id, msg))
                    if "main:run-start" in msg:
                        target_run_id = msg.split(":")[2]
                        print("model run processes:")
                        print(model_run_procs)
                    elif "main:run-done" in msg:
                        target_run_id = msg.split(":")[2]
                        model_run_procs[target_run_id] = None
                        model_run_signal_queues[target_run_id] = None
                        print("model run processes:")
                        print(model_run_procs)
            for k in list(model_run_signal_queues.keys()):
                if model_run_signal_queues[k] == None:
                    del model_run_signal_queues[k]
                if model_run_procs[k] == None:
                    del model_run_procs[k]
                    print(model_run_procs)
            
    except Exception as e:
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
