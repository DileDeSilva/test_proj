import mysql.connector  # allows code to communicate with mysql


class Database:
    def __init__(self, host="localhost", user="root", password="", database="mental health app"):
        self.host = host
        self.user = user
        self.password = password
        self.database = database

    def get_connection(self):
        return mysql.connector.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            database=self.database,
        )

    def get_questions(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT question_text FROM questions ORDER BY QID")
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]

    def get_professionals(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT PID, name, designation, specialization, district, contact_no FROM professionals"
        )
        rows = cursor.fetchall()
        conn.close()
        return rows


# Backward-compatible function names (so old imports still work)
_db = Database()


def get_connection():
    return _db.get_connection()


def importing_qns():
    return _db.get_questions()


def get_professionals():
    return _db.get_professionals()