#!/usr/bin/env python
from flask import Flask, make_response, request
from flask import jsonify
from flask_cors import CORS
from celery import Celery

flask_app = Flask(__name__)
flask_app.config.update(
    CELERY_BROKER_URL='redis://localhost:6379',
    CELERY_RESULT_BACKEND='redis://localhost:6379'
)

flask_app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
flask_app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

celery = Celery(flask_app.name, broker=flask_app.config['CELERY_BROKER_URL'])
celery.conf.update(flask_app.config)

@flask_app.route('/start_calibration', methods=['GET'])
def start_calibration():
    result = async_start_calibration.delay()
    return 'Starting Calibration...' 

@flask_app.route('/start_training/<int:profile_no>', methods=['GET'])
def start_training(profile_no):
    result = async_start_training.delay(profile_no)
    return 'Training...'

@flask_app.route('/testing', methods=['GET'])
def testing():
    return 'Hello World'

@celery.task()
def async_start_calibration():
    print('import serial')
    print('send "b\'C\'" via serial')
    print('wait until ACK received')
    print('read data after ack')
    print('store data as a string in variable data_s')
    print('Send ACK')
    data_s =  "1,1,1,1"
    import sqlite3 as sql
    connection = sql.connect("./.physio.db")
    cursor =  connection.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS profiles(profile_no INTEGER\
            PRIMARY KEY AUTOINCREMENT, profile_desc varchar(1500) NOT NULL);""")
    connection.commit()
    sql_statement = "INSERT INTO profiles(profile_desc) VALUES(\'{0}\');".format(data_s)
    cursor.execute(sql_statement)
    connection.commit()
    connection.close()
    return

@celery.task()
def async_start_training(profile_no):
    import sqlite3 as sql
    connection = sql.connect("./.physio.db")
    cursor =  connection.cursor()
    sql_statement =  "SELECT profile_desc FROM profiles WHERE profile_no IS {0};"\
                                .format(profile_no)
    cursor.execute(sql_statement)
    data_s = ""
    for row in cursor:
        for data in row:
            data_s = data
    print(data_s)
    connection.close()
    data_s_sz = str(len(data_s)).encode('ascii')
    print('Connect to device over serial')
    print('Send "b\'T\'" to indicate training mode')
    print('Wait for ACK')
    print('Send size of data_s as bytes - data_s_sz')
    print('Wait for ACK')
    print('Send data_s')
    print('Wait for ACK')
    return

if __name__ == '__main__':
    flask_app.run(debug = True)
