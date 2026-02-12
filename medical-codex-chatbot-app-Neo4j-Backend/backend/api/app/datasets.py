"""Dataset metadata and helper utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class DatasetConfig:
    key: str
    label: str
    id_property: str
    display_property: str
    search_properties: List[str]
    description: str
    code_property: str | None = None

    @property
    def properties_for_payload(self) -> List[str]:
        """Fields to pull out for API payloads."""
        props = {self.id_property, self.display_property}
        if self.code_property:
            props.add(self.code_property)
        return list(props)


DATASETS: Dict[str, DatasetConfig] = {
    "drugbank": DatasetConfig(
        key="drugbank",
        label="DRUG",
        id_property="id",
        display_property="title",
        search_properties=["title", "code", "id"],
        code_property="code",
        description="DrugBank Discovery API ingest (nodes labeled :DRUG with :HAS_CHILD relationships).",
    ),
    "rxnorm": DatasetConfig(
        key="rxnorm",
        label="RXN",
        id_property="rxcui",
        display_property="name",
        search_properties=["name", "tty", "rxcui"],
        code_property="tty",
        description="RxNorm Prescribable ingest (nodes labeled :RXN with :HAS_CHILD).",
    ),
    "icd11": DatasetConfig(
        key="icd11",
        label="ICD",
        id_property="id",
        display_property="title",
        search_properties=["title", "code", "id"],
        code_property="code",
        description="ICD-11 Chapter 21 ingest (nodes labeled :ICD with :HAS_CHILD).",
    ),
    "snomedct": DatasetConfig(
        key="snomedct",
        label="SNOMED",
        id_property="id",
        display_property="title",
        search_properties=["title", "code", "id"],
        code_property="code",
        description="SNOMED CT Clinical findings ingest (nodes labeled :SNOMED with :HAS_CHILD).",
    ),
}


def list_datasets() -> List[DatasetConfig]:
    return list(DATASETS.values())


def get_dataset_config(key: str) -> DatasetConfig:
    normalized = (key or "").lower()
    config = DATASETS.get(normalized)
    if not config:
        raise KeyError(f"Dataset '{key}' is not defined")
    return config
