"""Metadata and access checks with a mocked database, without loading demo packs."""
import unittest
import os
import sys
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

# Make OCR dependencies optional
for mod in ("paddleocr", "paddle", "cv2", "scipy"):
    sys.modules.setdefault(mod, MagicMock())

# Add parent directory to sys.path
parent_dir = str(Path(__file__).resolve().parent.parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

import api
from codex import neo4j_driver



class AdminBootstrapTests(unittest.TestCase):
    def test_no_account_is_created_without_explicit_bootstrap_credentials(self):
        for settings in ({}, {'DEFAULT_ADMIN_EMAIL': 'admin@example.test'},
                         {'DEFAULT_ADMIN_PASSWORD': 'synthetic-test-password'}):
            with self.subTest(settings=list(settings)), patch.dict(os.environ, settings, clear=True), \
                    patch.object(neo4j_driver, 'driver') as driver:
                neo4j_driver.init_default_admin()
                driver.session.assert_not_called()

    def test_explicit_bootstrap_creates_an_admin_with_configured_credentials(self):
        settings = {'DEFAULT_ADMIN_EMAIL': 'admin@example.test',
                    'DEFAULT_ADMIN_PASSWORD': 'synthetic-test-password'}
        with patch.dict(os.environ, settings, clear=True), \
                patch.object(neo4j_driver, 'driver'), \
                patch.object(neo4j_driver, 'init_user_constraints'), \
                patch.object(neo4j_driver, 'get_user_by_email', return_value=None), \
                patch.object(neo4j_driver, 'create_user') as create:
            neo4j_driver.init_default_admin()
            self.assertEqual(create.call_args.kwargs['email'], settings['DEFAULT_ADMIN_EMAIL'])
            self.assertEqual(create.call_args.kwargs['password'], settings['DEFAULT_ADMIN_PASSWORD'])
            self.assertEqual(create.call_args.kwargs['role'], 'administrator')

    def test_startup_does_not_overwrite_an_existing_account(self):
        settings = {'DEFAULT_ADMIN_EMAIL': 'admin@example.test',
                    'DEFAULT_ADMIN_PASSWORD': 'synthetic-test-password'}
        with patch.dict(os.environ, settings, clear=True), \
                patch.object(neo4j_driver, 'driver'), \
                patch.object(neo4j_driver, 'init_user_constraints'), \
                patch.object(neo4j_driver, 'get_user_by_email', return_value={'email': settings['DEFAULT_ADMIN_EMAIL']}), \
                patch.object(neo4j_driver, 'create_user') as create:
            neo4j_driver.init_default_admin()
            create.assert_not_called()


class LanguageCatalogTests(unittest.TestCase):
    def test_loaded_countries_are_sorted_and_do_not_depend_on_a_fixed_frontend_list(self):
        driver = MagicMock()
        session = driver.session.return_value.__enter__.return_value
        session.run.return_value = [
            {"lang": "ru", "countries": ["RU", "KZ"]},
            {"lang": "uk", "countries": ["UA", "PL"]},
        ]
        with patch.object(api, 'driver', driver):
            response = TestClient(api.app).get('/languages')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "languages": ["ru", "uk"],
            "countries": {
                "ru": [
                    {"code": "KZ", "label": "KZ"},
                    {"code": "RU", "label": "Russia"},
                ],
                "uk": [
                    {"code": "PL", "label": "Poland"},
                    {"code": "UA", "label": "Ukraine"},
                ],
            },
        })

    def test_empty_database_does_not_claim_languages_are_loaded(self):
        driver = MagicMock()
        driver.session.return_value.__enter__.return_value.run.return_value = []
        with patch.object(api, 'driver', driver):
            response = TestClient(api.app).get('/languages')
        self.assertEqual(response.json(), {"languages": [], "countries": {}})

    def test_country_metadata_change_keeps_protected_data_routes_protected(self):
        client = TestClient(api.app)
        self.assertEqual(client.post('/api/populate-sources', json={
            "selectedSources": [], "DBAPIKey": "", "ICDID": "", "ICDSecret": "",
        }).status_code, 401)
        self.assertEqual(client.post('/packs/load', files={
            'file': ('synthetic.json', b'{}', 'application/json'),
        }).status_code, 401)
