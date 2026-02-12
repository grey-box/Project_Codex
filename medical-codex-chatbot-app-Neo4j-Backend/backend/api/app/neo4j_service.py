"""Thin wrapper around the Neo4j Python driver."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase, READ_ACCESS
from neo4j.exceptions import Neo4jError

from .config import Settings
from .datasets import DatasetConfig

log = logging.getLogger("api.neo4j")


class Neo4jService:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        self._database = settings.neo4j_database
        self._timeout = settings.request_timeout_s

    def close(self) -> None:
        self._driver.close()

    def ping(self) -> bool:
        try:
            result = self._read("RETURN 1 AS ok", {})
        except Neo4jError:
            return False
        return bool(result and result[0].get("ok") == 1)

    def _read(self, query: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            with self._driver.session(database=self._database, default_access_mode=READ_ACCESS) as session:
                result = session.run(query, params, timeout=self._timeout)
                return [record.data() for record in result]
        except Neo4jError as exc:
            log.exception("Neo4j read failed: %s", exc)
            raise

    def fetch_node(
        self,
        dataset: DatasetConfig,
        identifier: str,
        dataset_tag: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        cypher = f"""
        MATCH (n:{dataset.label} {{{dataset.id_property}: $identifier}})
        WHERE $datasetTag IS NULL OR n.ds = $datasetTag
        OPTIONAL MATCH (n)-[:HAS_CHILD]->(child:{dataset.label})
        WHERE $datasetTag IS NULL OR child.ds = $datasetTag
        WITH n, count(DISTINCT child) AS child_count
        OPTIONAL MATCH (parent:{dataset.label})-[:HAS_CHILD]->(n)
        WHERE $datasetTag IS NULL OR parent.ds = $datasetTag
        RETURN n AS node, child_count, count(DISTINCT parent) AS parent_count
        """
        records = self._read(
            cypher,
            {"identifier": identifier, "datasetTag": dataset_tag},
        )
        return records[0] if records else None

    def search_nodes(
        self,
        dataset: DatasetConfig,
        query: str,
        limit: int,
        offset: int,
        dataset_tag: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query = query.strip()
        if not query:
            return []

        contains_fields = [f for f in dataset.search_properties if f != dataset.id_property]
        contains_clause = " OR ".join(
            f"toLower(coalesce(n.{field}, '')) CONTAINS $queryLower" for field in contains_fields
        )
        clauses = [f"toString(n.{dataset.id_property}) = $query"]
        if contains_clause:
            clauses.append(contains_clause)
        where_clause = " OR ".join(f"({clause})" for clause in clauses)

        cypher = f"""
        MATCH (n:{dataset.label})
        WHERE ({where_clause})
          AND ($datasetTag IS NULL OR n.ds = $datasetTag)
        RETURN n AS node
        ORDER BY coalesce(n.{dataset.display_property}, n.{dataset.id_property}) ASC
        SKIP $offset
        LIMIT $limit
        """
        return self._read(
            cypher,
            {
                "query": query,
                "queryLower": query.lower(),
                "datasetTag": dataset_tag,
                "offset": offset,
                "limit": limit,
            },
        )

    def list_children(
        self,
        dataset: DatasetConfig,
        identifier: str,
        limit: int,
        offset: int,
        dataset_tag: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        cypher = f"""
        MATCH (parent:{dataset.label} {{{dataset.id_property}: $identifier}})
        WHERE $datasetTag IS NULL OR parent.ds = $datasetTag
        MATCH (parent)-[:HAS_CHILD]->(child:{dataset.label})
        WHERE $datasetTag IS NULL OR child.ds = $datasetTag
        RETURN child AS node
        ORDER BY coalesce(child.{dataset.display_property}, child.{dataset.id_property}) ASC
        SKIP $offset
        LIMIT $limit
        """
        return self._read(
            cypher,
            {
                "identifier": identifier,
                "datasetTag": dataset_tag,
                "offset": offset,
                "limit": limit,
            },
        )

    def list_parents(
        self,
        dataset: DatasetConfig,
        identifier: str,
        limit: int,
        offset: int,
        dataset_tag: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        cypher = f"""
        MATCH (child:{dataset.label} {{{dataset.id_property}: $identifier}})
        WHERE $datasetTag IS NULL OR child.ds = $datasetTag
        MATCH (parent:{dataset.label})-[:HAS_CHILD]->(child)
        WHERE $datasetTag IS NULL OR parent.ds = $datasetTag
        RETURN parent AS node
        ORDER BY coalesce(parent.{dataset.display_property}, parent.{dataset.id_property}) ASC
        SKIP $offset
        LIMIT $limit
        """
        return self._read(
            cypher,
            {
                "identifier": identifier,
                "datasetTag": dataset_tag,
                "offset": offset,
                "limit": limit,
            },
        )
