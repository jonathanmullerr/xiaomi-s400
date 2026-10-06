import json
import os
import tempfile
import unittest
from pathlib import Path

from xiaomi_s400.errors import AuthenticationError, InputError
from xiaomi_s400.session import load_session, save_session


class SessionTests(unittest.TestCase):
    def test_import_formats_and_private_atomic_storage(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config' / 'session.json'
            for key in ('passToken', 'pass_token'):
                save_session(path, {'userId': 123, key: 'synthetic-token'})
                self.assertEqual(load_session(path), {'userId': '123', 'passToken': 'synthetic-token'})
                if os.name == 'posix':
                    self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                self.assertEqual(list(path.parent.iterdir()), [path])

    def test_missing_malformed_and_sanitized_session(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'session.json'
            with self.assertRaises(AuthenticationError):
                load_session(path)
            for text in ('synthetic-secret', '[]', '{}', '{"userId": "123", "passToken": {}}'):
                path.write_text(text)
                with self.assertRaises(AuthenticationError) as caught:
                    load_session(path)
                self.assertNotIn('synthetic-secret', str(caught.exception))
            with self.assertRaises(InputError):
                save_session(path, {'userId': '123', 'passToken': 'unsafe\r\ncookie'})
            path.write_text(json.dumps({'userId': '123', 'pass_token': 'synthetic'}))
            self.assertEqual(load_session(path)['passToken'], 'synthetic')
