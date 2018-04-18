#!/usr/bin/env python
from flask import Flask, make_response, request
from flask import jsonify
from flask_cors import CORS
from celery import Celery
import serial

ser = serial.Serial('/dev/ttyUSB1', 9600)

flask_app = Flask(__name__)
flask_app.config.update(
    CELERY_BROKER_URL='redis://localhost:6379',
    CELERY_RESULT_BACKEND='redis://localhost:6379'
)

START, CALIB, TRANSMIT, BEG_T, CON_T = b's\n', b'c\n', b't\n', b'r\n', b'j\n'

ACK = [str.encode('a' + str(i) + '\n') for i in range(9)]

flask_app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
flask_app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

celery = Celery(flask_app.name, broker=flask_app.config['CELERY_BROKER_URL'])
celery.conf.update(flask_app.config)

@flask_app.route('/start_calibration', methods=['GET'])
def start_calibration():
    result = async_start_calibration.delay()
    return 'Starting Calibration...' 

@flask_app.route('/start_training/<int:profile_no>/<int:reps>', methods=['GET'])
def start_training(profile_no, reps):
    result = async_start_training.delay(profile_no, reps)
    return 'Training...'

@flask_app.route('/get_profiles', methods=['GET'])
def get_profiles():
    import sqlite3 as sql
    connection = sql.connect('./.physio.db')
    cursor = connection.cursor()
    cursor.execute("""SELECT profile_no FROM profiles;""")
    profile_nos = []
    for row in cursor:
        for column in row:
            profile_nos.append(column)
    print(profile_nos)
    return jsonify({"profile_nos": profile_nos})

@flask_app.route('/delete_profile/<int:profile_no>', methods=['GET'])
def delete_profile(profile_no):
    async_delete_profile.delay(profile_no)
    return 'Deleting...'

@celery.task()
def async_start_calibration():
    print('Starting to calibrate...')
    data_s =  ""
    global ser
    global CALIB
    global ACK
    ser.write(CALIB)
    ack = b'nack'
    while ack != ACK[1]:
        ack = ser.readline()
    print('Calibration has started...')
    while ack != ACK[2]:
        ack = ser.readline()
    print('Calibration ended! Waiting for data...')
    global TRANSMIT
    ser.write(TRANSMIT)
    while ack != ACK[5]:
        ack = ser.readline()
    print('Receiving Data...')
    data_bytes = ser.readline()
    data_s = bytes.decode(data_bytes)
    while ack != ACK[6]:
        ack = ser.readline()
    print('Data Received! Inserting into Database...')
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
    print('Calibration and Data Insertion has been completed successfully...!')
    return

@celery.task()
def async_start_training(profile_no, reps):
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
    connection.close()
    print('Data Retrieved from Database...')
    data_bytes = data_s.encode('ascii')
    data_length = len(data_s)
    packet_length = 10
    total_v = data_s.count('v')
    full_packets = total_v // packet_length
    packet_count, byte_count = 0, 0
    print('Starting transmission of data...')
    ser.write(b'r\n')
    ack = ser.readline()
    while ack != b'a7\n':
        ack = ser.readline()
    print('Ready for transmission...')
    while packet_count < full_packets:
        v_count = 0
        while v_count < packet_length:
            ser.write(data_bytes[byte_count])
            v_count += (1 if data_bytes[byte_count] == b'v' else 0)
            byte_count += 1
        ser.write(b'\n')
        print('Packet ', packet_count, ' sent...')
        packet_count += 1
        ack = ser.readline()
        while ack != b'a8\n':
            ack = ser.readline()
        print('Packet ', packet_count, ' received...')
        if packet_count >= full_packets:
            print('Data Completely transmitted...')
            break
        print('Starting transmission of data...')
        ser.write(b'j\n')
        ack = ser.readline()
        while ack != b'a7\n':
            ack = ser.readline()
        print('Ready for transmission...')
    repstr=format(reps, '03d')
    print('Starting training for ', reps, ' rep\(s\)...')
    ser.write(str.encode('m' + repstr + '\n'))
    ack = ser.readline()
    while ack != b'a3\n':
        ack = ser.readline()
    print('Training Started...')
    ack = ser.readline()
    while ack != b'a4\n':
        ack = ser.readline()
    print('Training Successful!')
    return

@celery.task()
def async_delete_profile(profile_no):
    import sqlite3 as sql
    connection = sql.connect("./.physio.db")
    cursor =  connection.cursor()
    if profile_no is not 0:
        sql_statement =  "DELETE FROM profiles WHERE profile_no IS {0};"\
                                    .format(profile_no)
        cursor.execute(sql_statement)
    else:
        sql_statement = """DROP TABLE IF EXISTS profiles;"""
        cursor.execute(sql_statement)
        connection.commit()
        sql_statement = "CREATE TABLE IF NOT EXISTS profiles(profile_no INTEGER\
                PRIMARY KEY AUTOINCREMENT, profile_desc varchar(1500) NOT NULL);"
        cursor.execute(sql_statement)
    connection.commit()

if __name__ == '__main__':
    flask_app.run(debug=True, threaded=True, host='0.0.0.0', port=5000)

