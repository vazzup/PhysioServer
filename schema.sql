CREATE TABLE IF NOT EXISTS Doctors(
	doctorid INTEGER PRIMARY KEY AUTOINCREMENT,
	name TEXT NOT NULL,
	email TEXT NOT NULL,
	password TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS Patients(
	patientid INTEGER PRIMARY KEY AUTOINCREMENT,
	name TEXT NOT NULL,
	age INTEGER NOT NULL,
	sex TEXT NOT NULL,
	description TEXT);

CREATE TABLE IF NOT EXISTS ExerciseProfiles(
	profileid INTEGER PRIMARY KEY AUTOINCREMENT,
	doctorid INTEGER NOT NULL,
	patientid INTEGER NOT NULL,
	description TEXT,
	profile TEXT,
	lastused TEXT,
	FOREIGN KEY (doctorid) REFERENCES Doctors(doctorid),
	FOREIGN KEY (patientid) REFERENCES Patients(patientid)
	);

CREATE TABLE IF NOT EXISTS DP(
	doctorid INTEGER NOT NULL,
	patientid INTEGER NOT NULL,
	FOREIGN KEY (doctorid) REFERENCES Doctors(doctorid),
	FOREIGN KEY (patientid) REFERENCES Patients(patientid)
	);

CREATE TABLE IF NOT EXISTS TrainingsLedger(
	trainingid INTEGER PRIMARY KEY AUTOINCREMENT,
	doctorid INTEGER NOT NULL,
	patientid INTEGER NOT NULL,
	profileid INTEGER NOT NULL,
	repetitions INTEGER NOT NULL,
	timestamp TEXT NOT NULL,
	FOREIGN KEY (profileid) REFERENCES ExerciseProfiles(profileid),
	FOREIGN KEY (doctorid) REFERENCES Doctors(doctorid),
	FOREIGN KEY (patientid) REFERENCES Patients(patientid)
	);
