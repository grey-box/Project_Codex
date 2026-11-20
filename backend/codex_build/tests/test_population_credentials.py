"""Credential requirements only. No database or provider requests are made."""
import unittest

from neo4j_sources.credentials import validate_population_credentials


class PopulationCredentialsTests(unittest.TestCase):
    def test_credential_free_sources_do_not_require_other_provider_keys(self):
        for sources in ([], ["rxnorm"], ["snomed"], ["rxnorm", "snomed"]):
            for empty_val in ("", None):
                with self.subTest(sources=sources, empty_val=empty_val):
                    validate_population_credentials(sources, empty_val, empty_val, empty_val)

    def test_drugbank_rejects_empty_whitespace_or_null_key(self):
        for key in (None, "", " ", "\t\n"):
            with self.subTest(key=repr(key)):
                with self.assertRaisesRegex(ValueError, "DrugBank API key"):
                    validate_population_credentials(["drugbank"], key, None, None)

    def test_icd11_requires_both_credentials(self):
        invalid_pairs = (
            (None, None),
            ("client", None),
            (None, "secret"),
            ("", ""),
            ("client", ""),
            ("", "secret"),
            (" ", "secret"),
            ("client", "\t"),
        )
        for client_id, secret in invalid_pairs:
            with self.subTest(client_id=client_id, secret=bool(secret)):
                with self.assertRaisesRegex(ValueError, "ICD-11 client ID and client secret"):
                    validate_population_credentials(["icd11"], None, client_id, secret)

    def test_only_selected_sources_are_validated(self):
        self.assertIsNone(validate_population_credentials(["drugbank"], "fixture-key", None, None))
        self.assertIsNone(validate_population_credentials(["icd11"], None, "fixture-client", "fixture-secret"))

    def test_mixed_selection_requires_every_selected_provider(self):
        with self.assertRaisesRegex(ValueError, "ICD-11"):
            validate_population_credentials(["drugbank", "icd11", "rxnorm"], "fixture-key", "client", None)
        validate_population_credentials(["drugbank", "icd11", "rxnorm"], "fixture-key", "fixture-client", "fixture-secret")

    def test_validation_errors_do_not_echo_supplied_credentials(self):
        supplied_key = "synthetic-private-key"
        with self.assertRaises(ValueError) as raised:
            validate_population_credentials(["drugbank", "icd11"], supplied_key, None, None)
        self.assertNotIn(supplied_key, str(raised.exception))


if __name__ == "__main__":
    unittest.main()