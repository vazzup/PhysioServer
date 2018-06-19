#!/usr/bin/env python
import sqlite3
from flask import Flask, make_response, request
from flask import jsonify, g
from flask_cors import CORS
from celery import Celery
import serial

'''try:
    ser = serial.Serial('/dev/ttyUSB1', 9600)
except Exception as e:
    ser = serial.Serial('/dev/ttyUSB0', 9600)
'''
DATABASE = './.physio.db'

flask_app = Flask(__name__)
CORS(flask_app)
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

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        def make_dicts(cursor, row):
            return dict((cursor.description[idx][0], value)
                        for idx, value in enumerate(row))
        db.row_factory = make_dicts
    return db

def query_db(query, args=(), one=False):
    cursor = get_db().execute(query, args)
    rowvalues = cursor.fetchall()
    cursor.close()
    return (rowvalues[0] if rowvalues else None) if one else rowvalues

@flask_app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with flask_app.app_context():
        db = get_db()
        with flask_app.open_resource('schema.sql', 'r') as f:
            db.cursor().executescript(f.read())
        db.commit()

init_db()

@flask_app.route('/start_calibration/<int:doctorid>/<int:patientid>/<description>', methods=['GET'])
def start_calibration(doctorid, patientid, description):
    result = async_start_calibration.delay(doctorid, patientid, description)
    return 'Starting Calibration...' 

@flask_app.route('/start_training/<int:doctorid>/<int:patientid>/<int:profileid>/<int:reps>', methods=['GET'])
def start_training(doctorid, patientid, profileid, reps):
    result = async_start_training.delay(doctorid, patientid, profileid, reps)
    return 'Training...'

@flask_app.route('/get_profiles/<int:patientid>', methods=['GET'])
def get_profiles(patientid):
    sql = "SELECT profileid, description from ExerciseProfiles WHERE patientid is ?;"
    profiles = query_db(sql, [patientid])
    return jsonify({"profiles": profiles})

@flask_app.route('/delete_profile/<int:profile_no>', methods=['GET'])
def delete_profile(profile_no):
    async_delete_profile.delay(profile_no)
    return 'Deleting...'

@flask_app.route('/loginverify', methods=['POST'])
def loginverify():
    try:
        email = "\"" + request.form['email'] + "\""
        password = "\"" + request.form['password'] + "\""
        print(email, password)
        sql = "SELECT * FROM Doctors WHERE email is " + email + " AND password is " + password + ";"
        print(sql)
        count = query_db(sql, one=True)
        if count is not None:
            return jsonify({"status": "OK", "doctorid": count["doctorid"], "doctorname": count["name"]})
        else:
            return jsonify({"status": "NOK"})
    except Exception as e:
        print(e)
        return jsonify({"status": "NOK"})

@flask_app.route('/getpatients/<int:doctorid>', methods=['GET'])
def getpatients(doctorid):
    sql = "SELECT Patients.patientid, Patients.name, Patients.age, Patients.sex, Patients.description from Patients INNER JOIN DP ON Patients.patientid = DP.patientid WHERE DP.doctorid = ? ;"
    result = query_db(sql, [doctorid])
    return jsonify({"result": result})

@flask_app.route('/doctorsignup', methods=['POST'])
def doctorsignup():
    email = request.form['email'] 
    password = request.form['password']
    name = request.form['name']
    sql = "INSERT INTO Doctors(name, email, password) VALUES( ? , ? , ? );"
    args = [name, email, password]
    get_db().execute(sql, args)
    get_db().commit()
    return 'Doctor Signed Up Successfully!'

@flask_app.route('/patientsignup', methods=['POST'])
def patientsignup():
    doctorid = request.form['doctorid']
    name = request.form['name']
    age = request.form['age']
    sex = request.form['sex']
    description = request.form['description']
    sql = "INSERT INTO Patients(name, age, sex, description) VALUES( ? , ? , ? , ? );"
    args = [name, age, sex, description]
    get_db().execute(sql, args)
    get_db().commit()
    sql = "SELECT count(*) FROM PATIENTS;"
    result = query_db(sql, one=True)
    patientid = result['count(*)']
    sql = "INSERT INTO DP VALUES( ? , ? );"
    args = [doctorid, patientid]
    get_db().execute(sql, args)
    get_db().commit()

@celery.task()
def async_start_calibration(patientid, doctorid, description):
    print('Starting to calibrate...')
    data_s =  "1,1,1,1"
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
    sql = "INSERT INTO ExerciseProfiles(doctorid, patientid, description, profile) VALUES(\
             ? , ? , ? , ? );"
    args = [doctorid, patientid, "\"" + description + "\"", "\"" + data_s + "\""]
    with flask_app.app_context():
        get_db().execute(sql, args)
        get_db().commit()
    print('Calibration and Data Insertion has been completed successfully...!')
    return

@celery.task()
def async_start_training(doctorid, patientid, profileid, reps):
    data_s = ""
    with flask_app.app_context():
        sql_statement =  "SELECT profile FROM ExerciseProfiles WHERE profileid IS ? ;"
        args = [profileid]
        result = query_db(sql_statement, args, one=True)
        data_s = result['profile']
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
    with flask_app.app_context():
        sql = "INSERT INTO TrainingsLedger(doctorid, patientid, profileid, repetitions, timestamp) VALUES( ? , ? , ? , ? , datetime('now'));"
        args = [doctorid, patientid, profileid, reps]
        get_db().execute(sql, args)
        get_db().commit()
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

