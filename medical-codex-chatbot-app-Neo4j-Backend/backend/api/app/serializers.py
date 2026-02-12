"""Helpers for shaping Neo4j nodes into API payloads."""

from __future__ import annotations

from typing import Any, Dict

from neo4j.graph import Node

from .datasets import DatasetConfig


def serialize_node(dataset_key: str, config: DatasetConfig, node: Node) -> Dict[str, Any]:
    props = dict(node)
    identifier = props.get(config.id_property)
    display = props.get(config.display_property)
    code = props.get(config.code_property) if config.code_property else None

    return {
        "dataset": dataset_key,
        "identifier": "" if identifier is None else str(identifier),
        "display": display,
        "code": code,
        "dataset_tag": props.get("ds"),
        "properties": props,
    }
