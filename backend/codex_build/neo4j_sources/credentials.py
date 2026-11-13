"""Validate the credentials required by the selected source loaders."""


def validate_population_credentials(
    sources: list[str], drugbank_key: str, icd_id: str, icd_secret: str
) -> None:
    # These loaders otherwise return early without raising an ingestion error.
    if "drugbank" in sources and not drugbank_key.strip():
        raise ValueError("Enter a DrugBank API key before populating DrugBank.")
    if "icd11" in sources and (not icd_id.strip() or not icd_secret.strip()):
        raise ValueError("Enter both an ICD-11 client ID and client secret before populating ICD-11.")
