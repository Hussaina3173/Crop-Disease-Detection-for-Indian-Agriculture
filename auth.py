import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from pathlib import Path


class AuthService:
    def __init__(self, database_path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE,
                mobile TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                created_at REAL NOT NULL
            )''')
            connection.execute('''CREATE TABLE IF NOT EXISTS reset_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                channel TEXT NOT NULL,
                token TEXT NOT NULL,
                created_at REAL NOT NULL
            )''')

    def _connect(self):
        return sqlite3.connect(self.database_path)

    @staticmethod
    def _hash(password, salt=None):
        salt = salt or os.urandom(16)
        digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 210000)
        return salt.hex() + ':' + digest.hex()

    @classmethod
    def _check(cls, password, stored):
        salt, expected = stored.split(':', 1)
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 210000).hex()
        return hmac.compare_digest(actual, expected)

    def register(self, name, email, mobile, password):
        if not name or not password or (not email and not mobile):
            raise ValueError('Name, password, and an email or mobile number are required.')
        if len(password) < 8:
            raise ValueError('Password must contain at least 8 characters.')
        try:
            with self._connect() as connection:
                cursor = connection.execute('INSERT INTO users (name,email,mobile,password_hash,created_at) VALUES (?,?,?,?,?)', (name, email or None, mobile or None, self._hash(password), time.time()))
                return {'id': cursor.lastrowid, 'name': name}
        except sqlite3.IntegrityError as error:
            raise ValueError('An account already exists with that email or mobile number.') from error

    def login(self, identifier, password):
        with self._connect() as connection:
            user = connection.execute('SELECT id,name,email,mobile,password_hash FROM users WHERE email=? OR mobile=?', (identifier, identifier)).fetchone()
        if not user or not self._check(password, user[4]):
            raise ValueError('Incorrect email/mobile number or password.')
        return {'id': user[0], 'name': user[1], 'email': user[2], 'mobile': user[3]}

    def request_reset(self, destination):
        with self._connect() as connection:
            user = connection.execute('SELECT id,email,mobile FROM users WHERE email=? OR mobile=?', (destination, destination)).fetchone()
            if not user:
                raise ValueError('No account was found for that email or mobile number.')
            channel = 'email' if '@' in destination else 'sms'
            token = f'{secrets.randbelow(1000000):06d}'
            connection.execute('INSERT INTO reset_requests (user_id,channel,token,created_at) VALUES (?,?,?,?)', (user[0], channel, token, time.time()))
        return {'channel': channel, 'destination': destination, 'token': token}

    def reset_password(self, destination, token, new_password):
        if len(new_password) < 8:
            raise ValueError('Password must contain at least 8 characters.')
        with self._connect() as connection:
            request = connection.execute('''SELECT reset_requests.id, reset_requests.user_id
                FROM reset_requests JOIN users ON users.id = reset_requests.user_id
                WHERE reset_requests.token=? AND (users.email=? OR users.mobile=?)
                AND reset_requests.created_at > ? ORDER BY reset_requests.id DESC LIMIT 1''', (token, destination, destination, time.time() - 900)).fetchone()
            if not request:
                raise ValueError('The reset code is invalid or expired.')
            connection.execute('UPDATE users SET password_hash=? WHERE id=?', (self._hash(new_password), request[1]))
            connection.execute('DELETE FROM reset_requests WHERE user_id=?', (request[1],))
