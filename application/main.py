# AUDIU
# main.py

# local imports
from backend import Backend
from recommendations import Recommendations

HOST = '0.0.0.0'
PORT = 8001
DATASET = 'dataset.json'
DB_NAME = 'audiu'
DB_HOST = 'localhost'
DB_PORT = 27017
PROD = True

## MAIN ##
# main entry point
def main():
    bk = Backend('static', 'templates', HOST, PORT, PORT + 1,
                 DATASET, DB_HOST, DB_PORT, DB_NAME)
    rc = Recommendations(DATASET)
    bk.run_forever(PROD)

# thread entry point
if __name__ == "__main__":
    main()
