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
    model_run_procs = {}
    model_run_signal_queues = {}
    recommendations_model = recommendations.Recommendations(
        DATASET, MODEL_RUN_SRC)
    recommendations_model.load_dataset()
    backend_signal_queue = multiprocessing.Queue(10)
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
                print('main received msg {}'.format(msg))
            if "main:recommendations-run" in msg:
                target_run_id = msg.split(":")[2]
                recommendations_model.generate_recommendations_proc_prepare(target_run_id)
                model_run_signal_queues[target_run_id] = multiprocessing.Queue(10)
                model_run_procs[target_run_id] = multiprocessing.Process(target=recommendations.generate_recommendations_proc_fork, args=(
                    str(target_run_id), str(MODEL_RUN_SRC), model_run_signal_queues[target_run_id]))
                model_run_procs[target_run_id].start()
            elif msg == "main:backend-done":
                break
            else:
                pass
            for run_id, model_run_signal_queue in model_run_signal_queues.items():
                msg = ''
                try:
                    msg = model_run_signal_queue.get(False)
                except queue.Empty:
                    msg = ''
                # if msg == 
    except Exception as e:
        # TODO: send msg to queues and join procs
        backend_signal_queue.put("backend:quit")
        backend_process.join()

# thread entry point
if __name__ == "__main__":
    main()
