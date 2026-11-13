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
            UNWIND [{name:'Alpha', brand:'ZetaBrand'}, {name:'Beta', brand:'BetaBrand'}, {name:'Gamma', brand:'GammaBrand'}] AS row
            CREATE (t:Term {canonical:row.name, type:'medication', export_test:true})
            CREATE (tr:Translation {text:row.name, export_test:true})
            CREATE (l:Language {code:'en', name:'English', export_test:true})
            CREATE (c:Country {iso2:'US', export_test:true})
            CREATE (b:Brand {name:row.brand, export_test:true})
            CREATE (tr)-[:OF_TERM]->(t), (tr)-[:IN_LANGUAGE]->(l), (tr)-[:USED_IN]->(c), (tr)-[:HAS_BRAND]->(b)
        ''').consume()
        session.run('''
            UNWIND [{name:'Alpha ingredient', tty:'IN'}, {name:'Beta ingredient', tty:'IN'}, {name:'Alpha brand', tty:'BN'}] AS row
            CREATE (:RXN {name:row.name, tty:row.tty, rxcui:row.name, ds:'Synthetic RxNorm fixture', conceptID:'fixture-id', export_test:true})
        ''').consume()
    yield
    with driver.session() as session:
        session.run('MATCH (n) WHERE n.export_test = true DETACH DELETE n').consume()


def test_initial_data_schema_and_inclusive_alphabetical_range():
    response = TestClient(app).get('/csv', params={'source':'demo', 'start_name':' alpha ', 'end_name':'BETA'})
    assert response.status_code == 200
    body = response.json()
    assert body['row_count'] == 2
    assert [row['generic_name'] for row in body['csv']] == ['Alpha', 'Beta']
    assert set(body['csv'][0]) == {'generic_name','brand_name','country','original_language','translated_language'}


def test_brand_range_uses_brand_name_instead_of_generic_name():
    body = TestClient(app).get('/csv', params={'source':'demo', 'name_type':'brand', 'start_name':'BetaBrand', 'end_name':'BetaBrand'}).json()
    assert body['row_count'] == 1
    assert body['csv'][0]['generic_name'] == 'Beta'


def test_rxnorm_preserves_original_five_properties_and_generic_type():
    response = TestClient(app).get('/csv', params={'source':'rxnorm', 'name_type':'generic'})
    assert response.status_code == 200
    rows = response.json()['csv']
    assert len(rows) == 2
    assert set(rows[0]) == {'conceptID','ds','name','rxcui','tty'}
    assert all(row['tty'] == 'IN' for row in rows)


def test_rxnorm_brand_and_upper_bound():
    body = TestClient(app).get('/csv', params={'source':'rxnorm', 'name_type':'brand', 'end_name':'Alpha brand'}).json()
    assert body['row_count'] == 1
    assert body['csv'][0]['name'] == 'Alpha brand'
    assert body['csv'][0]['tty'] == 'BN'


def test_empty_range_returns_empty_rows_without_fabricated_data():
    assert TestClient(app).get('/csv', params={'source':'rxnorm','start_name':'Z'}).json() == {'csv':[], 'row_count':0}


@pytest.mark.parametrize('params, expected', [
    ({'start_name':'Z','end_name':'A'},400),
    ({'source':'unknown'},422),
    ({'name_type':'unknown'},422),
])
def test_invalid_export_filters_are_rejected(params, expected):
    assert TestClient(app).get('/csv',params=params).status_code == expected
