import getpass
import os
import unittest
import warnings
from unittest.mock import patch
from fast_apam.credentials import sec_user_agent


class PrivateEntryTests(unittest.TestCase):
    def test_environment_does_not_prompt(self):
        with patch.dict(os.environ, {'APAM_SEC_USER_AGENT': 'Test contact@example.com'}), patch('getpass.getpass') as prompt:
            self.assertEqual(sec_user_agent(), 'Test contact@example.com')
            prompt.assert_not_called()

    def test_hidden_entry_is_not_saved_to_environment(self):
        with patch.dict(os.environ, {}, clear=True), patch('sys.stdin.isatty', return_value=True), patch('getpass.getpass', return_value='Test contact@example.com'):
            self.assertEqual(sec_user_agent(), 'Test contact@example.com')
            self.assertNotIn('APAM_SEC_USER_AGENT', os.environ)

    def test_unattended_missing_value_fails_without_prompt(self):
        with patch.dict(os.environ, {}, clear=True), patch('sys.stdin.isatty', return_value=False), patch('getpass.getpass') as prompt:
            with self.assertRaises(ValueError): sec_user_agent()
            prompt.assert_not_called()

    def test_visible_fallback_is_refused(self):
        def fallback(*args):
            warnings.warn('Cannot hide input', getpass.GetPassWarning)
            self.fail('Visible fallback must not run')
        with patch.dict(os.environ, {}, clear=True), patch('sys.stdin.isatty', return_value=True), patch('getpass.getpass', side_effect=fallback):
            with self.assertRaises(ValueError): sec_user_agent()

    def test_invalid_values_are_not_echoed_in_errors(self):
        for value in ['private\nidentifier', 'private\ridentifier', 'private\x00identifier']:
            with self.subTest(value=value), patch('fast_apam.credentials.os.environ', {'APAM_SEC_USER_AGENT': value}):
                with self.assertRaises(ValueError) as error: sec_user_agent()
                self.assertNotIn(value, str(error.exception))

    def test_cancel_and_empty_entry(self):
        for outcome in ['', EOFError(), KeyboardInterrupt()]:
            with self.subTest(outcome=type(outcome).__name__), patch.dict(os.environ, {}, clear=True), patch('sys.stdin.isatty', return_value=True), patch('getpass.getpass', **({'side_effect': outcome} if isinstance(outcome, BaseException) else {'return_value': outcome})):
                with self.assertRaises(ValueError): sec_user_agent()
