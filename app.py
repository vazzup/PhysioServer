#!/usr/bin/env python
from flask import Flask, make_response, request
from flask import jsonify
from flask_cors import CORS
from tasks import make_celery

flask_app = Flask(__name__)
flask_app.config.update(
    CELERY_BROKER_URL='redis://localhost:6379',
    CELERY_RESULT_BACKEND='redis://localhost:6379'
)
celery = make_celery(flask_app)

@flask_app.route('/start_calibration', methods=['GET'])
def start_calibration():
    result = add_together.delay(4, 4)
    return 'Starting Calibration...' 

@flask_app.route('/testing', methods=['GET'])
def testing():
    return 'Hello World'

@celery.task()
def start_calibration():
    print('import serial')
    print('send "b\'C\'" via serial')
    print('wait until ACK received')
    print('read data after ack')
    print('store data as a string in variable data_s')
    data_s =  ""
    import sqlite3 as sql
    connection = sql.connect("./.physio.db")
    cursor.execute("""CREATE TABLE IF NOT EXISTS
    return

if __name__ == '__main__':
    flask_app.run(debug = True)
