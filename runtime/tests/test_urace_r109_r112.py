"""R109 structural parity tests — IGC catalog + DAG acyclicity (§62 r109)."""
import unittest
from urace import primitives as prim
from urace.primitives import INTEGRITY_GAP_CATALOG


class R109IGCParityTests(unittest.TestCase):
    def setUp(self):
        self.prim = prim

    def test_all_igc_entries_have_severity(self):
        for kind, entry in self.prim.INTEGRITY_GAP_CATALOG.items():
            self.assertIn("severity", entry, f"IGC kind missing severity: {kind}")

    def test_all_igc_entries_have_section(self):
        for kind, entry in self.prim.INTEGRITY_GAP_CATALOG.items():
            self.assertIn("section", entry, f"IGC kind missing section: {kind}")

    def test_all_igc_severities_valid(self):
        valid = {"BLOCKING", "WARNING", "INFO"}
        for kind, entry in self.prim.INTEGRITY_GAP_CATALOG.items():
            self.assertIn(entry.get("severity"), valid, f"IGC kind has invalid severity: {kind}")

    def test_validate_igc_kind_entries_clean(self):
        errors = self.prim.validate_igc_kind_entries()
        self.assertEqual(errors, [], f"IGC validation errors: {errors}")

    def test_retired_igc_kinds_no_overlap(self):
        active = set(self.prim.INTEGRITY_GAP_CATALOG.keys())
        overlap = active & self.prim.RETIRED_IGC_KINDS
        self.assertEqual(overlap, set(), f"Retired kinds still active: {overlap}")

    def test_feature_bundle_registry_has_spec_bundles(self):
        self.assertIsInstance(self.prim.FEATURE_BUNDLE_REGISTRY, dict)
        self.assertGreaterEqual(len(self.prim.FEATURE_BUNDLE_REGISTRY), 21,
            "FEATURE_BUNDLE_REGISTRY must have at least 21 spec-defined bundles")

    def test_feature_bundle_entries_have_required_fields(self):
        required = {"construct_ids", "description", "spec_version", "source"}
        for name, entry in self.prim.FEATURE_BUNDLE_REGISTRY.items():
            for field in required:
                self.assertIn(field, entry, f"Bundle {name!r} missing field {field!r}")

    def test_feature_bundle_sources_valid(self):
        valid_sources = {"spec", "operator"}
        for name, entry in self.prim.FEATURE_BUNDLE_REGISTRY.items():
            self.assertIn(entry.get("source"), valid_sources,
                f"Bundle {name!r} has invalid source: {entry.get('source')!r}")

    def test_feature_bundle_construct_ids_are_lists(self):
        for name, entry in self.prim.FEATURE_BUNDLE_REGISTRY.items():
            self.assertIsInstance(entry["construct_ids"], list,
                f"Bundle {name!r} construct_ids is not a list")
            self.assertGreater(len(entry["construct_ids"]), 0,
                f"Bundle {name!r} has empty construct_ids")


class R109DAGAcyclicityTests(unittest.TestCase):
    """Tests for DAI: Construct Dependency Acyclicity Invariant (§62 r62)."""

    def _build_dep_graph(self):
        """Build construct_ids adjacency from FEATURE_BUNDLE_REGISTRY."""
        graph: dict[str, set[str]] = {}
        for name, entry in prim.FEATURE_BUNDLE_REGISTRY.items():
            ids = entry.get("construct_ids", [])
            graph[name] = set(ids)
        return graph

    def _detect_cycle(self, graph: dict) -> list:
        """Return cycle path if found, else empty list. DFS-based."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {n: WHITE for n in graph}
        path: list = []

        def dfs(node):
            color[node] = GRAY
            path.append(node)
            for neighbor in graph.get(node, set()):
                if neighbor not in color:
                    continue  # external construct ref, not a bundle
                if color[neighbor] == GRAY:
                    return path + [neighbor]  # cycle found
                if color[neighbor] == WHITE:
                    result = dfs(neighbor)
                    if result:
                        return result
            path.pop()
            color[node] = BLACK
            return []

        for node in list(graph.keys()):
            if color[node] == WHITE:
                result = dfs(node)
                if result:
                    return result
        return []

    def test_feature_bundle_registry_acyclic(self):
        """FeatureBundle construct_ids graph must be acyclic (DAI §62)."""
        graph = self._build_dep_graph()
        cycle = self._detect_cycle(graph)
        self.assertEqual(cycle, [], f"DAI violation — cycle detected in bundle graph: {cycle}")

    def test_feature_bundle_no_self_reference(self):
        """A FeatureBundle MUST NOT list its own name as a construct_id (DAI §62)."""
        for name, entry in prim.FEATURE_BUNDLE_REGISTRY.items():
            self.assertNotIn(name, entry.get("construct_ids", []),
                f"FeatureBundle {name!r} self-references its own name in construct_ids (DAI violation)")

    def test_igc_vocab_bundle_references_igc_catalog(self):
        """igc-vocabulary bundle must reference IntegrityGapCatalog."""
        self.assertIn("igc-vocabulary", prim.FEATURE_BUNDLE_REGISTRY)
        bundle = prim.FEATURE_BUNDLE_REGISTRY["igc-vocabulary"]
        self.assertIn("IntegrityGapCatalog", bundle["construct_ids"])


class R109SchemaExportTests(unittest.TestCase):
    def test_export_output_schemas_returns_dict(self):
        from urace import schema_export
        result = schema_export.export_output_schemas()
        self.assertIn("schemas", result)
        self.assertIn("total", result)
        self.assertIsInstance(result["schemas"], list)
        self.assertGreater(result["total"], 0)

    def test_export_feature_bundles_returns_dict(self):
        from urace import schema_export
        result = schema_export.export_feature_bundles()
        self.assertIn("bundles", result)
        self.assertIn("total", result)
        self.assertGreaterEqual(result["total"], 21)

    def test_export_all_has_both_registries(self):
        from urace import schema_export
        result = schema_export.export_all()
        self.assertIn("output_schemas", result)
        self.assertIn("feature_bundles", result)

    def test_schema_export_bundle_fields(self):
        from urace import schema_export
        result = schema_export.export_feature_bundles()
        for bundle in result["bundles"]:
            for field in ("name", "construct_ids", "description", "spec_version", "source"):
                self.assertIn(field, bundle, f"Bundle missing field: {field}")


class R110GapClosureTests(unittest.TestCase):
    """Tests for r110 gap A+B+C: IntentFormulaValidity + AuthorityCeiling + IntentAmbiguityAudit."""

    def setUp(self):
        self.prim = prim

    # Gap B: authority-ceiling-reached IGC kind
    def test_authority_ceiling_reached_in_igc(self):
        self.assertIn("authority-ceiling-reached", self.prim.INTEGRITY_GAP_CATALOG)
        entry = self.prim.INTEGRITY_GAP_CATALOG["authority-ceiling-reached"]
        self.assertEqual(entry["severity"], "BLOCKING")

    # Gap A: intent-formula-structural-drift IGC kind
    def test_intent_formula_structural_drift_in_igc(self):
        self.assertIn("intent-formula-structural-drift", self.prim.INTEGRITY_GAP_CATALOG)
        entry = self.prim.INTEGRITY_GAP_CATALOG["intent-formula-structural-drift"]
        self.assertEqual(entry["severity"], "BLOCKING")

    def test_intent_formula_validation_skipped_in_igc(self):
        self.assertIn("intent-formula-validation-skipped", self.prim.INTEGRITY_GAP_CATALOG)
        entry = self.prim.INTEGRITY_GAP_CATALOG["intent-formula-validation-skipped"]
        self.assertEqual(entry["severity"], "WARNING")

    # Gap C: IntentAmbiguityAudit IGC kinds
    def test_intent_ambiguity_audit_igc_kinds_present(self):
        required = [
            "intent-coverage-dimensions-missing",
            "intent-dimension-unbound",
            "intent-binding-metric-unregistered",
            "intent-metric-baseline-missing",
            "intent-binding-threshold-missing",
        ]
        for kind in required:
            self.assertIn(kind, self.prim.INTEGRITY_GAP_CATALOG,
                f"Missing IntentAmbiguityAudit IGC kind: {kind}")
            entry = self.prim.INTEGRITY_GAP_CATALOG[kind]
            self.assertEqual(entry["severity"], "BLOCKING",
                f"IGC kind {kind} should be BLOCKING")

    def test_intent_binding_orphaned_is_warning(self):
        self.assertIn("intent-binding-orphaned", self.prim.INTEGRITY_GAP_CATALOG)
        self.assertEqual(
            self.prim.INTEGRITY_GAP_CATALOG["intent-binding-orphaned"]["severity"], "WARNING"
        )

    # New State fields present in initial_state()
    def test_initial_state_has_intent_formula_validity_records(self):
        from urace import cli
        state = cli.initial_state()
        self.assertIn("intent_formula_validity_records", state)
        self.assertEqual(state["intent_formula_validity_records"], [])

    def test_initial_state_has_authority_ceiling_records(self):
        from urace import cli
        state = cli.initial_state()
        self.assertIn("authority_ceiling_records", state)
        self.assertEqual(state["authority_ceiling_records"], [])

    def test_initial_state_has_intent_ambiguity_audit_records(self):
        from urace import cli
        state = cli.initial_state()
        self.assertIn("intent_ambiguity_audit_records", state)
        self.assertEqual(state["intent_ambiguity_audit_records"], [])

    # IGC parity: all r110 new kinds pass validate_igc_kind_entries
    def test_r110_igc_kinds_pass_validation(self):
        errors = self.prim.validate_igc_kind_entries()
        self.assertEqual(errors, [], f"IGC validation errors after r110 additions: {errors}")

    # Confirm total IGC count grew
    def test_igc_catalog_has_r110_kinds(self):
        catalog = self.prim.INTEGRITY_GAP_CATALOG
        r110_kinds = [
            "intent-formula-structural-drift",
            "intent-formula-validation-skipped",
            "authority-ceiling-reached",
            "intent-coverage-dimensions-missing",
            "intent-dimension-unbound",
            "intent-binding-metric-unregistered",
            "intent-metric-baseline-missing",
            "intent-binding-threshold-missing",
            "intent-binding-orphaned",
        ]
        for kind in r110_kinds:
            self.assertIn(kind, catalog, f"r110 IGC kind missing: {kind}")


class R111GapClosureTests(unittest.TestCase):
    def setUp(self):
        from urace import primitives as p
        from urace import cli as c
        self.catalog = p.INTEGRITY_GAP_CATALOG
        self.state = c.initial_state()

    def test_coverage_dimension_unreachable_kind_present(self):
        self.assertIn("coverage-dimension-unreachable", self.catalog)
        self.assertEqual(self.catalog["coverage-dimension-unreachable"]["severity"], "BLOCKING")

    def test_strategy_diverging_kind_present(self):
        self.assertIn("strategy-diverging", self.catalog)
        self.assertEqual(self.catalog["strategy-diverging"]["severity"], "BLOCKING")

    def test_domain_weight_insufficient_observations_kind_present(self):
        self.assertIn("domain-weight-insufficient-observations", self.catalog)
        self.assertEqual(self.catalog["domain-weight-insufficient-observations"]["severity"], "WARNING")

    def test_evidence_request_expired_kind_present(self):
        self.assertIn("evidence-request-expired", self.catalog)
        self.assertEqual(self.catalog["evidence-request-expired"]["severity"], "WARNING")

    def test_r111_kinds_all_in_igc(self):
        r111_kinds = [
            "coverage-dimension-unreachable",
            "strategy-diverging",
            "domain-weight-insufficient-observations",
            "evidence-request-expired",
        ]
        for kind in r111_kinds:
            self.assertIn(kind, self.catalog, f"r111 IGC kind missing: {kind}")

    def test_goal_coverage_completeness_records_in_initial_state(self):
        self.assertIn("goal_coverage_completeness_records", self.state)
        self.assertEqual(self.state["goal_coverage_completeness_records"], [])

    def test_strategic_review_records_in_initial_state(self):
        self.assertIn("strategic_review_records", self.state)
        self.assertEqual(self.state["strategic_review_records"], [])

    def test_domain_weight_records_in_initial_state(self):
        self.assertIn("domain_weight_records", self.state)
        self.assertEqual(self.state["domain_weight_records"], [])

    def test_evidence_requests_in_initial_state(self):
        self.assertIn("evidence_requests", self.state)
        self.assertEqual(self.state["evidence_requests"], [])

    def test_r111_state_fields_count(self):
        r111_fields = [
            "goal_coverage_completeness_records",
            "strategic_review_records",
            "domain_weight_records",
            "evidence_requests",
        ]
        for field in r111_fields:
            self.assertIn(field, self.state, f"r111 state field missing: {field}")

    def test_coverage_dimension_unreachable_section(self):
        self.assertEqual(self.catalog["coverage-dimension-unreachable"]["section"], "62l")

    def test_strategy_diverging_section(self):
        self.assertEqual(self.catalog["strategy-diverging"]["section"], "62l")


class R112GapClosureTests(unittest.TestCase):
    """r112: StateTransitionValidation + IntentDrift + IntentAggregation + GapImpactEstimation"""

    def setUp(self):
        from urace import primitives as p
        from urace import cli as c
        self.catalog = p.INTEGRITY_GAP_CATALOG
        _cfg = c.load_config()
        self.state = c.initial_state(_cfg)

    def test_gap_regression_detected_present(self):
        self.assertIn("gap-regression-detected", self.catalog)

    def test_gap_regression_detected_blocking(self):
        self.assertEqual(self.catalog["gap-regression-detected"]["severity"], "BLOCKING")

    def test_state_transition_validation_missing_present(self):
        self.assertIn("state-transition-validation-missing", self.catalog)

    def test_state_transition_validation_missing_warning(self):
        self.assertEqual(self.catalog["state-transition-validation-missing"]["severity"], "WARNING")

    def test_intent_semantic_drift_present(self):
        self.assertIn("intent-semantic-drift", self.catalog)

    def test_intent_semantic_drift_blocking(self):
        self.assertEqual(self.catalog["intent-semantic-drift"]["severity"], "BLOCKING")

    def test_intent_drift_assessment_missing_present(self):
        self.assertIn("intent-drift-assessment-missing", self.catalog)

    def test_intent_aggregation_missing_blocking(self):
        self.assertEqual(self.catalog["intent-aggregation-missing"]["severity"], "BLOCKING")

    def test_gap_impact_estimate_missing_warning(self):
        self.assertEqual(self.catalog["gap-impact-estimate-missing"]["severity"], "WARNING")

    def test_r112_all_kinds_present(self):
        for kind in [
            "gap-regression-detected", "state-transition-validation-missing",
            "intent-semantic-drift", "intent-drift-assessment-missing",
            "intent-aggregation-missing", "gap-impact-estimate-missing",
        ]:
            self.assertIn(kind, self.catalog, f"missing: {kind}")

    def test_state_transition_validation_records_in_initial_state(self):
        self.assertIn("state_transition_validation_records", self.state)
        self.assertEqual(self.state["state_transition_validation_records"], [])

    def test_intent_drift_records_in_initial_state(self):
        self.assertIn("intent_drift_records", self.state)
        self.assertEqual(self.state["intent_drift_records"], [])

    def test_intent_aggregate_gap_records_in_initial_state(self):
        self.assertIn("intent_aggregate_gap_records", self.state)
        self.assertEqual(self.state["intent_aggregate_gap_records"], [])

    def test_gap_impact_estimates_in_initial_state(self):
        self.assertIn("gap_impact_estimates", self.state)
        self.assertEqual(self.state["gap_impact_estimates"], [])

    def test_r112_state_fields_all_present(self):
        for field in [
            "state_transition_validation_records", "intent_drift_records",
            "intent_aggregate_gap_records", "gap_impact_estimates",
        ]:
            self.assertIn(field, self.state, f"missing state field: {field}")

    def test_r112_section_all_62l(self):
        for kind in [
            "gap-regression-detected", "state-transition-validation-missing",
            "intent-semantic-drift", "intent-drift-assessment-missing",
            "intent-aggregation-missing", "gap-impact-estimate-missing",
        ]:
            self.assertEqual(self.catalog[kind]["section"], "62l", f"wrong section: {kind}")

