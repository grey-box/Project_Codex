"""Exercise Bevin's export queries against the disposable test Neo4j database."""
import pytest
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

from codex.neo4j_driver import driver
from api import app

@pytest.fixture(autouse=True)
def export_records():
    with driver.session() as session:
        assert session.run('CALL db.info() YIELD name RETURN name').single()['name'] == 'neo4j-test', 'Export integration tests require the isolated test database.'
        session.run('''
            UNWIND [{name:'Alpha ingredient', tty:'IN'}, {name:'Beta ingredient', tty:'IN'}, {name:'Alpha brand', tty:'BN'}, {name:'Beta brand', tty:'BN'}] AS row
            CREATE (:RXN {name:row.name, tty:row.tty, rxcui:row.name, ds:'Synthetic RxNorm fixture', conceptID:'fixture-id', export_test:true})
        ''').consume()
        session.run('''
            UNWIND [{title:'Alpha condition', code:'1A00'}, {title:'Beta condition', code:'1A01'}, {title:'Gamma condition', code:'1A02'}] AS row
            CREATE (:ICD {title:row.title, code:row.code, export_test:true})
        ''').consume()
    yield
    with driver.session() as session:
        session.run('MATCH (n) WHERE n.export_test = true DETACH DELETE n').consume()


def test_medication_export_schema_and_inclusive_alphabetical_range():
    response = TestClient(app).get('/api/medication-export', params={'start_name':' alpha ', 'end_name':'BETA INGREDIENT'})
    assert response.status_code == 200
    body = response.json()
    assert body['row_count'] == 2
    assert [row['name'] for row in body['csv']] == ['Alpha ingredient', 'Beta ingredient']
    assert set(body['csv'][0]) >= {'source', 'conceptID', 'ds', 'name', 'rxcui', 'tty'}
    assert all(row['source'] == 'RxNorm' and row['tty'] == 'IN' for row in body['csv'])


def test_medication_brand_range_uses_brand_type():
    response = TestClient(app).get('/api/medication-export', params={'name_type':'brand', 'start_name':'Beta brand', 'end_name':'Beta brand'})
    assert response.status_code == 200
    body = response.json()
    assert body['row_count'] == 1
    assert body['csv'][0]['name'] == 'Beta brand'
    assert body['csv'][0]['tty'] == 'BN'


def test_medication_brand_and_upper_bound():
    body = TestClient(app).get('/api/medication-export', params={'name_type':'brand', 'end_name':'Alpha brand'}).json()
    assert body['row_count'] == 1
    assert body['csv'][0]['name'] == 'Alpha brand'
    assert body['csv'][0]['tty'] == 'BN'


def test_clinical_export_inclusive_alphabetical_range():
    response = TestClient(app).get('/api/clinical-export', params={'start_name':' alpha ', 'end_name':'BETA CONDITION'})
    assert response.status_code == 200
    body = response.json()
    assert body['row_count'] == 2
    assert [row['title'] for row in body['csv']] == ['Alpha condition', 'Beta condition']
    assert all(row['source'] == 'ICD-11' for row in body['csv'])


def test_clinical_export_upper_bound_only():
    response = TestClient(app).get('/api/clinical-export', params={'end_name':'Alpha condition'})
    assert response.status_code == 200
    body = response.json()
    assert body['row_count'] == 1
    assert body['csv'][0]['code'] == '1A00'


def test_clinical_export_lower_bound_only():
    response = TestClient(app).get('/api/clinical-export', params={'start_name':'Gamma'})
    assert response.status_code == 200
    body = response.json()
    assert body['row_count'] == 1
    assert body['csv'][0]['code'] == '1A02'


def test_empty_range_returns_empty_rows_without_fabricated_data():
    assert TestClient(app).get('/api/medication-export', params={'start_name':'Z'}).json() == {'csv':[], 'row_count':0}
    assert TestClient(app).get('/api/clinical-export', params={'start_name':'Z'}).json() == {'csv':[], 'row_count':0}


@pytest.mark.parametrize('endpoint, params, expected', [
    ('/api/medication-export', {'start_name':'Z','end_name':'A'}, 400),
    ('/api/medication-export', {'name_type':'unknown'}, 422),
    ('/api/clinical-export', {'start_name':'Z','end_name':'A'}, 400),
])
def test_invalid_export_filters_are_rejected(endpoint, params, expected):
    assert TestClient(app).get(endpoint, params=params).status_code == expected