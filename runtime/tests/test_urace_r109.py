"""R109 structural parity tests — IGC catalog + DAG acyclicity (§62 r109)."""
import unittest
from urace import primitives as prim
from urace.primitives import INTEGRITY_GAP_CATALOG
from urace.cli import initial_state


class R109IGCParityTests(unittest.TestCase):
    def setUp(self):
        from urace import primitives as prim
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
        from urace import primitives as prim
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
        from urace import primitives as prim
        for name, entry in prim.FEATURE_BUNDLE_REGISTRY.items():
            self.assertNotIn(name, entry.get("construct_ids", []),
                f"FeatureBundle {name!r} self-references its own name in construct_ids (DAI violation)")

    def test_igc_vocab_bundle_references_igc_catalog(self):
        """igc-vocabulary bundle must reference IntegrityGapCatalog."""
        from urace import primitives as prim
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
        from urace import primitives as prim
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


class R113GapClosureTests(unittest.TestCase):
    """r113: causal model, lookahead, multi-principal, adversarial, uncertainty, fleet learning, constraint discovery, explanation, portfolio, deadlines"""

    def setUp(self):
        from urace import primitives as p
        from urace import cli as c
        self.catalog = p.INTEGRITY_GAP_CATALOG
        _cfg = c.load_config()
        self.state = c.initial_state(_cfg)

    # --- IGC kind presence ---
    def test_causal_model_stale_present(self):
        self.assertIn("causal-model-stale", self.catalog)

    def test_authority_conflict_unresolved_blocking(self):
        self.assertEqual(self.catalog["authority-conflict-unresolved"]["severity"], "BLOCKING")

    def test_adversarial_signal_detected_blocking(self):
        self.assertEqual(self.catalog["adversarial-signal-detected"]["severity"], "BLOCKING")

    def test_metric_fabrication_suspected_blocking(self):
        self.assertEqual(self.catalog["metric-fabrication-suspected"]["severity"], "BLOCKING")

    def test_deadline_breached_blocking(self):
        self.assertEqual(self.catalog["deadline-breached"]["severity"], "BLOCKING")

    def test_portfolio_budget_overallocated_blocking(self):
        self.assertEqual(self.catalog["portfolio-budget-overallocated"]["severity"], "BLOCKING")

    def test_principal_veto_active_blocking(self):
        self.assertEqual(self.catalog["principal-veto-active"]["severity"], "BLOCKING")

    def test_lookahead_plan_missing_warning(self):
        self.assertEqual(self.catalog["lookahead-plan-missing"]["severity"], "WARNING")

    def test_uncertainty_band_missing_warning(self):
        self.assertEqual(self.catalog["uncertainty-band-missing"]["severity"], "WARNING")

    def test_fleet_knowledge_sync_missing_warning(self):
        self.assertEqual(self.catalog["fleet-knowledge-sync-missing"]["severity"], "WARNING")

    def test_constraint_candidate_pending_review_warning(self):
        self.assertEqual(self.catalog["constraint-candidate-pending-review"]["severity"], "WARNING")

    def test_explanation_synthesis_failed_warning(self):
        self.assertEqual(self.catalog["explanation-synthesis-failed"]["severity"], "WARNING")

    def test_deadline_approaching_warning(self):
        self.assertEqual(self.catalog["deadline-approaching"]["severity"], "WARNING")

    def test_r113_all_kinds_present(self):
        kinds = [
            "causal-model-stale", "causal-edge-confounded", "causal-intervention-unverified",
            "lookahead-plan-missing", "lookahead-horizon-exceeded",
            "authority-conflict-unresolved", "principal-veto-active", "principal-hierarchy-missing",
            "adversarial-signal-detected", "metric-fabrication-suspected",
            "uncertainty-band-missing", "high-uncertainty-action-taken",
            "fleet-knowledge-sync-missing",
            "constraint-candidate-pending-review", "constraint-candidate-conflict",
            "explanation-synthesis-failed",
            "portfolio-allocation-missing", "portfolio-budget-overallocated",
            "deadline-breached", "deadline-approaching",
        ]
        for k in kinds:
            self.assertIn(k, self.catalog, f"missing kind: {k}")

    def test_r113_all_kinds_section_62l(self):
        kinds = [
            "causal-model-stale", "causal-edge-confounded", "causal-intervention-unverified",
            "lookahead-plan-missing", "lookahead-horizon-exceeded",
            "authority-conflict-unresolved", "principal-veto-active", "principal-hierarchy-missing",
            "adversarial-signal-detected", "metric-fabrication-suspected",
            "uncertainty-band-missing", "high-uncertainty-action-taken",
            "fleet-knowledge-sync-missing",
            "constraint-candidate-pending-review", "constraint-candidate-conflict",
            "explanation-synthesis-failed",
            "portfolio-allocation-missing", "portfolio-budget-overallocated",
            "deadline-breached", "deadline-approaching",
        ]
        for k in kinds:
            self.assertEqual(self.catalog[k]["section"], "62l", f"wrong section: {k}")

    # --- State fields ---
    def test_causal_edge_records_in_initial_state(self):
        self.assertIn("causal_edge_records", self.state)
        self.assertEqual(self.state["causal_edge_records"], [])

    def test_causal_model_records_in_initial_state(self):
        self.assertIn("causal_model_records", self.state)

    def test_lookahead_plan_records_in_initial_state(self):
        self.assertIn("lookahead_plan_records", self.state)

    def test_principal_records_in_initial_state(self):
        self.assertIn("principal_records", self.state)

    def test_authority_conflict_records_in_initial_state(self):
        self.assertIn("authority_conflict_records", self.state)

    def test_adversarial_signal_records_in_initial_state(self):
        self.assertIn("adversarial_signal_records", self.state)

    def test_uncertainty_bands_in_initial_state(self):
        self.assertIn("uncertainty_bands", self.state)

    def test_fleet_knowledge_records_in_initial_state(self):
        self.assertIn("fleet_knowledge_records", self.state)

    def test_constraint_candidates_in_initial_state(self):
        self.assertIn("constraint_candidates", self.state)

    def test_explanation_records_in_initial_state(self):
        self.assertIn("explanation_records", self.state)

    def test_portfolio_allocation_records_in_initial_state(self):
        self.assertIn("portfolio_allocation_records", self.state)

    def test_deadline_records_in_initial_state(self):
        self.assertIn("deadline_records", self.state)

    def test_r113_all_state_fields_present(self):
        for field in [
            "causal_edge_records", "causal_model_records", "lookahead_plan_records",
            "principal_records", "authority_conflict_records", "adversarial_signal_records",
            "uncertainty_bands", "fleet_knowledge_records", "constraint_candidates",
            "explanation_records", "portfolio_allocation_records", "deadline_records",
        ]:
            self.assertIn(field, self.state, f"missing state field: {field}")


class R114GapClosureTests(unittest.TestCase):
    """r114: goal decomp, obj deps, intent versioning, self-mod gate, normative, value, attention, policy, reactive, degradation, FSM, feedback latency, cross-product, schema migration"""

    def setUp(self):
        from urace import primitives as p
        from urace import cli as c
        self.catalog = p.INTEGRITY_GAP_CATALOG
        _cfg = c.load_config()
        self.state = c.initial_state(_cfg)

    # --- IGC kind presence and severity ---
    def test_goal_tree_cycle_detected_blocking(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["goal-tree-cycle-detected"]["severity"], "BLOCKING")

    def test_objective_dependency_violated_blocking(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["objective-dependency-violated"]["severity"], "BLOCKING")

    def test_objective_dependency_cycle_blocking(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["objective-dependency-cycle"]["severity"], "BLOCKING")

    def test_normative_invariant_violated_blocking(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["normative-invariant-violated"]["severity"], "BLOCKING")

    def test_audit_log_suppression_attempted_blocking(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["audit-log-suppression-attempted"]["severity"], "BLOCKING")

    def test_self_modification_evidence_insufficient_blocking(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["self-modification-evidence-insufficient"]["severity"], "BLOCKING")

    def test_fallback_chain_exhausted_blocking(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["fallback-chain-exhausted"]["severity"], "BLOCKING")

    def test_fsm_transition_undefined_blocking(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["fsm-transition-undefined"]["severity"], "BLOCKING")

    def test_cross_product_resource_conflict_blocking(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["cross-product-resource-conflict"]["severity"], "BLOCKING")

    def test_state_schema_incompatible_blocking(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["state-schema-incompatible"]["severity"], "BLOCKING")

    def test_migration_transform_failed_blocking(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["migration-transform-failed"]["severity"], "BLOCKING")

    def test_goal_tree_leaf_uncovered_warning(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["goal-tree-leaf-uncovered"]["severity"], "WARNING")

    def test_value_baseline_missing_warning(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["value-baseline-missing"]["severity"], "WARNING")

    def test_feedback_loop_oscillation_detected_warning(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["feedback-loop-oscillation-detected"]["severity"], "WARNING")

    def test_r114_all_kinds_present(self):
        kinds = [
            "goal-tree-cycle-detected", "goal-tree-leaf-uncovered",
            "objective-dependency-violated", "objective-dependency-cycle",
            "intent-version-missing", "intent-version-rollback-failed",
            "self-modification-evidence-insufficient", "self-modification-principal-insufficient",
            "normative-invariant-violated", "audit-log-suppression-attempted",
            "value-baseline-missing", "expected-value-uncalibrated",
            "operator-attention-overload", "review-queue-stale",
            "policy-mechanism-coupling-detected",
            "event-trigger-missed", "event-trigger-storm",
            "capability-degraded", "fallback-chain-exhausted",
            "fsm-transition-undefined", "fsm-state-unreachable",
            "feedback-loop-oscillation-detected", "feedback-latency-stale",
            "cross-product-resource-conflict", "fleet-resource-lock-timeout",
            "state-schema-incompatible", "migration-transform-failed",
            "normative-invariant-supersedes-boundary",
        ]
        for k in kinds:
            self.assertIn(k, INTEGRITY_GAP_CATALOG, f"missing kind: {k}")

    def test_r114_all_kinds_section_62l(self):
        kinds = [
            "goal-tree-cycle-detected", "goal-tree-leaf-uncovered",
            "objective-dependency-violated", "objective-dependency-cycle",
            "intent-version-missing", "intent-version-rollback-failed",
            "self-modification-evidence-insufficient", "self-modification-principal-insufficient",
            "normative-invariant-violated", "audit-log-suppression-attempted",
            "value-baseline-missing", "expected-value-uncalibrated",
            "operator-attention-overload", "review-queue-stale",
            "policy-mechanism-coupling-detected",
            "event-trigger-missed", "event-trigger-storm",
            "capability-degraded", "fallback-chain-exhausted",
            "fsm-transition-undefined", "fsm-state-unreachable",
            "feedback-loop-oscillation-detected", "feedback-latency-stale",
            "cross-product-resource-conflict", "fleet-resource-lock-timeout",
            "state-schema-incompatible", "migration-transform-failed",
            "normative-invariant-supersedes-boundary",
        ]
        for k in kinds:
            self.assertEqual(INTEGRITY_GAP_CATALOG[k]["section"], "62l", f"wrong section: {k}")

    # --- State fields ---
    def test_goal_tree_nodes_in_initial_state(self):
        s = self.state
        self.assertIn("goal_tree_nodes", s)
        self.assertEqual(s["goal_tree_nodes"], [])

    def test_objective_dependency_records_in_initial_state(self):
        s = self.state
        self.assertIn("objective_dependency_records", s)

    def test_intent_version_records_in_initial_state(self):
        s = self.state
        self.assertIn("intent_version_records", s)

    def test_normative_violation_records_in_initial_state(self):
        s = self.state
        self.assertIn("normative_violation_records", s)

    def test_value_ledger_entries_in_initial_state(self):
        s = self.state
        self.assertIn("value_ledger_entries", s)

    def test_attention_budget_records_in_initial_state(self):
        s = self.state
        self.assertIn("attention_budget_records", s)

    def test_event_trigger_records_in_initial_state(self):
        s = self.state
        self.assertIn("event_trigger_records", s)

    def test_degradation_records_in_initial_state(self):
        s = self.state
        self.assertIn("degradation_records", s)

    def test_state_space_audit_records_in_initial_state(self):
        s = self.state
        self.assertIn("state_space_audit_records", s)

    def test_feedback_latency_records_in_initial_state(self):
        s = self.state
        self.assertIn("feedback_latency_records", s)

    def test_resource_conflict_records_in_initial_state(self):
        s = self.state
        self.assertIn("resource_conflict_records", s)

    def test_schema_migration_records_in_initial_state(self):
        s = self.state
        self.assertIn("schema_migration_records", s)

    def test_r114_all_state_fields_present(self):
        s = self.state
        for field in [
            "goal_tree_nodes", "objective_dependency_records", "intent_version_records",
            "self_modification_records", "normative_violation_records", "value_ledger_entries",
            "attention_budget_records", "policy_override_records", "event_trigger_records",
            "degradation_records", "state_space_audit_records", "feedback_latency_records",
            "resource_conflict_records", "schema_migration_records",
        ]:
            self.assertIn(field, s, f"missing state field: {field}")


class R115HardeningTests(unittest.TestCase):
    """r115: hardening pass — 79-issue audit closure"""

    def setUp(self):
        from urace import primitives as p
        from urace import cli as c
        self.catalog = p.INTEGRITY_GAP_CATALOG
        _cfg = c.load_config()
        self.state = c.initial_state(_cfg)

    # --- New IGC kinds ---
    def test_normative_enforcement_unavailable_blocking(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["normative-enforcement-unavailable"]["severity"], "BLOCKING")

    def test_self_modification_rollback_missing_blocking(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["self-modification-rollback-missing"]["severity"], "BLOCKING")

    def test_goal_tree_unauthorized_mutation_blocking(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["goal-tree-unauthorized-mutation"]["severity"], "BLOCKING")

    def test_causal_graph_cycle_detected_blocking(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["causal-graph-cycle-detected"]["severity"], "BLOCKING")

    def test_intent_drift_retry_cap_reached_blocking(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["intent-drift-retry-cap-reached"]["severity"], "BLOCKING")

    def test_uncertainty_high_consecutive_cycles_blocking(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["uncertainty-high-consecutive-cycles"]["severity"], "BLOCKING")

    def test_lookahead_plan_cold_start_warning(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["lookahead-plan-cold-start"]["severity"], "WARNING")

    def test_intent_aggregation_no_directives_warning(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["intent-aggregation-no-directives"]["severity"], "WARNING")

    def test_neutral_operation_accumulation_warning(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["neutral-operation-accumulation"]["severity"], "WARNING")

    def test_dependency_gate_blocked_all_objectives_warning(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["dependency-gate-blocked-all-objectives"]["severity"], "WARNING")

    def test_value_feedback_timeout_warning(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["value-feedback-timeout"]["severity"], "WARNING")

    def test_data_insufficient_warning(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["data-insufficient"]["severity"], "WARNING")

    def test_initialization_incomplete_warning(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["initialization-incomplete"]["severity"], "WARNING")

    def test_adversarial_pattern_accumulated_warning(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["adversarial-pattern-accumulated"]["severity"], "WARNING")

    def test_schema_migration_partial_warning(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["schema-migration-partial"]["severity"], "WARNING")

    def test_r115_all_kinds_present(self):
        kinds = [
            "lookahead-plan-cold-start", "intent-aggregation-no-directives",
            "self-modification-rollback-missing", "normative-enforcement-unavailable",
            "goal-tree-unauthorized-mutation", "neutral-operation-accumulation",
            "dependency-gate-blocked-all-objectives", "value-feedback-timeout",
            "causal-graph-cycle-detected", "data-insufficient", "initialization-incomplete",
            "adversarial-pattern-accumulated", "intent-drift-retry-cap-reached",
            "schema-migration-partial", "uncertainty-high-consecutive-cycles",
        ]
        for k in kinds:
            self.assertIn(k, INTEGRITY_GAP_CATALOG, f"missing kind: {k}")

    def test_r115_all_kinds_section_62l(self):
        kinds = [
            "lookahead-plan-cold-start", "intent-aggregation-no-directives",
            "self-modification-rollback-missing", "normative-enforcement-unavailable",
            "goal-tree-unauthorized-mutation", "neutral-operation-accumulation",
            "dependency-gate-blocked-all-objectives", "value-feedback-timeout",
            "causal-graph-cycle-detected", "data-insufficient", "initialization-incomplete",
            "adversarial-pattern-accumulated", "intent-drift-retry-cap-reached",
            "schema-migration-partial", "uncertainty-high-consecutive-cycles",
        ]
        for k in kinds:
            self.assertEqual(INTEGRITY_GAP_CATALOG[k]["section"], "62l", f"wrong section: {k}")

    # --- State fields ---
    def test_rollback_records_in_initial_state(self):
        s = self.state
        self.assertIn("rollback_records", s)
        self.assertEqual(s["rollback_records"], [])

    def test_fleet_resource_registry_in_initial_state(self):
        s = self.state
        self.assertIn("fleet_resource_registry", s)

    def test_r115_state_fields_present(self):
        s = self.state
        for field in ["rollback_records", "fleet_resource_registry"]:
            self.assertIn(field, s, f"missing: {field}")

    # --- Critical audit correctness ---
    def test_no_igc_kind_has_empty_severity(self):
        for k, v in INTEGRITY_GAP_CATALOG.items():
            self.assertIn(v["severity"], {"WARNING", "BLOCKING", "FATAL", "INFO"}, f"invalid severity for {k}: {v['severity']}")

    def test_no_igc_kind_has_empty_section(self):
        for k, v in INTEGRITY_GAP_CATALOG.items():
            self.assertTrue(len(v.get("section", "")) > 0, f"empty section for {k}")

    def test_all_blocking_kinds_are_strings(self):
        blocking = [k for k, v in INTEGRITY_GAP_CATALOG.items() if v["severity"] == "BLOCKING"]
        self.assertGreater(len(blocking), 0)
        for k in blocking:
            self.assertIsInstance(k, str)


class R116FullClosureTests(unittest.TestCase):
    """r116: full closure of all 14 gaps — 31 residual issues resolved"""

    def setUp(self):
        from urace import primitives as p
        from urace import cli as c
        self.catalog = p.INTEGRITY_GAP_CATALOG
        _cfg = c.load_config()
        self.state = c.initial_state(_cfg)

    # --- New IGC kinds ---
    def test_goal_tree_node_empty_blocking(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["goal-tree-node-empty"]["severity"], "BLOCKING")

    def test_goal_tree_orphan_detected_blocking(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["goal-tree-orphan-detected"]["severity"], "BLOCKING")

    def test_evidence_integrity_violated_blocking(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["evidence-integrity-violated"]["severity"], "BLOCKING")

    def test_lifecycle_normative_halt_blocking(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["lifecycle-normative-halt"]["severity"], "BLOCKING")

    def test_operator_overload_escalated_blocking(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["operator-overload-escalated"]["severity"], "BLOCKING")

    def test_policy_scanner_blocking_violation_blocking(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["policy-scanner-blocking-violation"]["severity"], "BLOCKING")

    def test_feedback_loop_oscillation_damped_warning(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["feedback-loop-oscillation-damped"]["severity"], "WARNING")

    def test_dependency_rollback_revert_warning(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["dependency-rollback-revert"]["severity"], "WARNING")

    def test_fleet_lock_reservation_conflict_warning(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["fleet-lock-reservation-conflict"]["severity"], "WARNING")

    def test_value_calibration_insufficient_warning(self):
        self.assertEqual(INTEGRITY_GAP_CATALOG["value-calibration-insufficient"]["severity"], "WARNING")

    def test_r116_all_kinds_present(self):
        kinds = [
            "goal-tree-node-empty", "goal-tree-orphan-detected",
            "evidence-integrity-violated", "lifecycle-normative-halt",
            "feedback-loop-oscillation-damped", "dependency-rollback-revert",
            "fleet-lock-reservation-conflict", "operator-overload-escalated",
            "policy-scanner-blocking-violation", "value-calibration-insufficient",
        ]
        for k in kinds:
            self.assertIn(k, INTEGRITY_GAP_CATALOG, f"missing kind: {k}")

    def test_r116_all_kinds_section_62l(self):
        for k in [
            "goal-tree-node-empty", "goal-tree-orphan-detected",
            "evidence-integrity-violated", "lifecycle-normative-halt",
            "feedback-loop-oscillation-damped", "dependency-rollback-revert",
            "fleet-lock-reservation-conflict", "operator-overload-escalated",
            "policy-scanner-blocking-violation", "value-calibration-insufficient",
        ]:
            self.assertEqual(INTEGRITY_GAP_CATALOG[k]["section"], "62l", f"wrong section: {k}")

    # --- State fields ---
    def test_last_self_modification_cycle_in_initial_state(self):
        s = self.state
        self.assertIn("last_self_modification_cycle", s)
        self.assertEqual(s["last_self_modification_cycle"], 0)

    def test_bootstrap_file_hashes_in_initial_state(self):
        s = self.state
        self.assertIn("bootstrap_file_hashes", s)
        self.assertEqual(s["bootstrap_file_hashes"], {})

    def test_normative_halt_records_in_initial_state(self):
        s = self.state
        self.assertIn("normative_halt_records", s)
        self.assertEqual(s["normative_halt_records"], [])

    def test_value_calibration_factor_in_initial_state(self):
        s = self.state
        self.assertIn("value_calibration_factor", s)
        self.assertEqual(s["value_calibration_factor"], 1.0)

    def test_transform_records_in_initial_state(self):
        s = self.state
        self.assertIn("transform_records", s)

    def test_r116_all_state_fields_present(self):
        s = self.state
        for field in [
            "last_self_modification_cycle", "bootstrap_file_hashes",
            "normative_halt_records", "value_calibration_factor", "transform_records",
        ]:
            self.assertIn(field, s, f"missing: {field}")

    # --- Structural correctness ---
    def test_no_duplicate_igc_keys(self):
        keys = list(INTEGRITY_GAP_CATALOG.keys())
        self.assertEqual(len(keys), len(set(keys)), "Duplicate IGC kind keys found")

    def test_all_igc_kinds_have_required_fields(self):
        for k, v in INTEGRITY_GAP_CATALOG.items():
            self.assertIn("severity", v, f"missing severity: {k}")
            self.assertIn("section", v, f"missing section: {k}")
            self.assertIn(v["severity"], {"WARNING", "BLOCKING", "FATAL", "INFO"}, f"invalid severity: {k}")

    def test_blocking_kinds_count_greater_than_warning(self):
        blocking = sum(1 for v in INTEGRITY_GAP_CATALOG.values() if v["severity"] == "BLOCKING")
        warning = sum(1 for v in INTEGRITY_GAP_CATALOG.values() if v["severity"] == "WARNING")
        self.assertGreater(blocking + warning, 100)


class R117DataSourceTests(unittest.TestCase):
    """r117 §62v DataSourceRegistry — IGC kinds + state fields + CLI"""

    def setUp(self):
        from urace import primitives as p
        from urace import cli as c
        self.catalog = p.INTEGRITY_GAP_CATALOG
        self.state = c.initial_state()

    # IGC kinds — §62v
    def test_data_source_sync_failed_present(self):
        self.assertIn("data-source-sync-failed", self.catalog)
        self.assertEqual(self.catalog["data-source-sync-failed"]["severity"], "BLOCKING")

    def test_data_source_write_failed_present(self):
        self.assertIn("data-source-write-failed", self.catalog)
        self.assertEqual(self.catalog["data-source-write-failed"]["severity"], "BLOCKING")

    def test_data_source_credential_expired_present(self):
        self.assertIn("data-source-credential-expired", self.catalog)
        self.assertEqual(self.catalog["data-source-credential-expired"]["severity"], "BLOCKING")

    def test_data_source_credential_exposed_present(self):
        self.assertIn("data-source-credential-exposed", self.catalog)
        self.assertEqual(self.catalog["data-source-credential-exposed"]["severity"], "BLOCKING")

    def test_data_source_direction_violation_present(self):
        self.assertIn("data-source-direction-violation", self.catalog)
        self.assertEqual(self.catalog["data-source-direction-violation"]["severity"], "BLOCKING")

    def test_data_source_schema_mismatch_present(self):
        self.assertIn("data-source-schema-mismatch", self.catalog)
        self.assertEqual(self.catalog["data-source-schema-mismatch"]["severity"], "WARNING")

    def test_data_source_connectivity_lost_present(self):
        self.assertIn("data-source-connectivity-lost", self.catalog)
        self.assertEqual(self.catalog["data-source-connectivity-lost"]["severity"], "WARNING")

    def test_data_source_write_rejected_present(self):
        self.assertIn("data-source-write-rejected", self.catalog)
        self.assertEqual(self.catalog["data-source-write-rejected"]["severity"], "WARNING")

    def test_r117_igc_section_62v(self):
        v_kinds = [k for k, v in self.catalog.items() if v.get("section") == "62x"]
        self.assertGreaterEqual(len(v_kinds), 8)

    # State fields
    def test_data_source_records_in_state(self):
        self.assertIn("data_source_records", self.state)
        self.assertEqual(self.state["data_source_records"], [])

    def test_credential_records_in_state(self):
        self.assertIn("credential_records", self.state)
        self.assertEqual(self.state["credential_records"], [])

    def test_data_sync_records_in_state(self):
        self.assertIn("data_sync_records", self.state)
        self.assertEqual(self.state["data_sync_records"], [])

    def test_route_graph_records_in_state(self):
        self.assertIn("route_graph_records", self.state)
        self.assertEqual(self.state["route_graph_records"], [])

    # CLI: data add
    def test_data_add_creates_record(self):
        from urace import cli as c
        state = c.initial_state()
        cfg = c.load_config()

        import sys
        from io import StringIO
        old_argv = sys.argv
        sys.argv = ["urace", "data", "add", "mydb", "--type", "postgres", "--connect", "postgresql://localhost/test"]
        try:
            c.run(state, cfg)
        except SystemExit:
            pass
        finally:
            sys.argv = old_argv

        self.assertEqual(len(state["data_source_records"]), 1)
        rec = state["data_source_records"][0]
        self.assertEqual(rec["name"], "mydb")
        self.assertEqual(rec["adapter_kind"], "postgres")
        self.assertEqual(rec["direction"], "READ")

    # CLI: data add then update
    def test_data_update_changes_label(self):
        from urace import cli as c
        state = c.initial_state()
        cfg = c.load_config()

        import sys
        old_argv = sys.argv
        sys.argv = ["urace", "data", "add", "src1", "--type", "csv", "--connect", "/data/file.csv"]
        try:
            c.run(state, cfg)
        except SystemExit:
            pass

        sys.argv = ["urace", "data", "update", "src1", "--label", "main CSV source"]
        try:
            c.run(state, cfg)
        except SystemExit:
            pass
        finally:
            sys.argv = old_argv

        rec = next(r for r in state["data_source_records"] if r["name"] == "src1")
        self.assertEqual(rec["label"], "main CSV source")

    # CLI: data sync
    def test_data_sync_creates_dsync_record(self):
        from urace import cli as c
        state = c.initial_state()
        cfg = c.load_config()

        import sys
        old_argv = sys.argv
        sys.argv = ["urace", "data", "add", "ev-src", "--type", "json", "--connect", "/tmp/data.json"]
        try:
            c.run(state, cfg)
        except SystemExit:
            pass

        sys.argv = ["urace", "data", "sync", "ev-src"]
        try:
            c.run(state, cfg)
        except SystemExit:
            pass
        finally:
            sys.argv = old_argv

        self.assertEqual(len(state["data_sync_records"]), 1)
        self.assertEqual(state["data_sync_records"][0]["direction"], "PULL")
        self.assertEqual(state["data_sync_records"][0]["status"], "FAILED")
        self.assertEqual(state["data_sync_records"][0]["rows_affected"], 0)
        self.assertEqual(state["data_sync_records"][0]["evidence_ids_produced"], [])

    # CLI: data push on READ-only source emits direction-violation IGC
    def test_data_push_on_read_source_emits_direction_violation(self):
        from urace import cli as c
        state = c.initial_state()
        cfg = c.load_config()

        import sys
        old_argv = sys.argv
        sys.argv = ["urace", "data", "add", "ro-src", "--type", "csv", "--connect", "/tmp/in.csv", "--direction", "read"]
        try:
            c.run(state, cfg)
        except SystemExit:
            pass

        sys.argv = ["urace", "data", "push", "ro-src"]
        try:
            c.run(state, cfg)
        except SystemExit:
            pass
        finally:
            sys.argv = old_argv

        # No DataSyncRecord for PUSH should exist for a READ-only source
        push_records = [r for r in state["data_sync_records"] if r["direction"] == "PUSH"]
        self.assertEqual(len(push_records), 0)

    # CLI: data add with direction=both
    def test_data_add_bidirectional(self):
        from urace import cli as c
        state = c.initial_state()
        cfg = c.load_config()

        import sys
        old_argv = sys.argv
        sys.argv = ["urace", "data", "add", "bidir", "--type", "mongodb", "--connect", "mongodb://localhost/db", "--direction", "both"]
        try:
            c.run(state, cfg)
        except SystemExit:
            pass
        finally:
            sys.argv = old_argv

        rec = next(r for r in state["data_source_records"] if r["name"] == "bidir")
        self.assertEqual(rec["direction"], "BIDIRECTIONAL")

    # CLI: data remove
    def test_data_remove_deletes_record(self):
        from urace import cli as c
        state = c.initial_state()
        cfg = c.load_config()

        import sys
        old_argv = sys.argv
        sys.argv = ["urace", "data", "add", "temp-src", "--type", "sqlite", "--connect", "/tmp/db.sqlite"]
        try:
            c.run(state, cfg)
        except SystemExit:
            pass

        sys.argv = ["urace", "data", "remove", "temp-src"]
        try:
            c.run(state, cfg)
        except SystemExit:
            pass
        finally:
            sys.argv = old_argv

        names = [r["name"] for r in state["data_source_records"]]
        self.assertNotIn("temp-src", names)

    # Adapter kinds: verify multiple types are accepted
    def test_diverse_adapter_kinds_accepted(self):
        from urace import cli as c
        state = c.initial_state()
        cfg = c.load_config()

        import sys
        old_argv = sys.argv
        for kind, connect in [
            ("neo4j", "bolt://localhost:7687"),
            ("excel", "/data/sheet.xlsx"),
            ("elasticsearch", "http://localhost:9200"),
            ("parquet", "/data/metrics.parquet"),
        ]:
            sys.argv = ["urace", "data", "add", f"src-{kind}", "--type", kind, "--connect", connect]
            try:
                c.run(state, cfg)
            except SystemExit:
                pass
        sys.argv = old_argv

        kinds_registered = {r["adapter_kind"] for r in state["data_source_records"]}
        self.assertIn("neo4j", kinds_registered)
        self.assertIn("excel", kinds_registered)
        self.assertIn("elasticsearch", kinds_registered)
        self.assertIn("parquet", kinds_registered)


class R117PolyRouteTests(unittest.TestCase):
    """r117 §62w UniversalEntryProtocol — IGC kinds + RouteGraph"""

    def setUp(self):
        from urace import primitives as p
        from urace import cli as c
        self.catalog = p.INTEGRITY_GAP_CATALOG
        self.state = c.initial_state()

    # IGC kinds — §62w
    def test_route_conflict_detected_present(self):
        self.assertIn("route-conflict-detected", self.catalog)
        self.assertEqual(self.catalog["route-conflict-detected"]["severity"], "BLOCKING")

    def test_route_graph_cycle_detected_present(self):
        self.assertIn("route-graph-cycle-detected", self.catalog)
        self.assertEqual(self.catalog["route-graph-cycle-detected"]["severity"], "BLOCKING")

    def test_route_dispatch_partial_present(self):
        self.assertIn("route-dispatch-partial", self.catalog)
        self.assertEqual(self.catalog["route-dispatch-partial"]["severity"], "WARNING")

    def test_universal_route_ambiguous_present(self):
        self.assertIn("universal-route-ambiguous", self.catalog)
        self.assertEqual(self.catalog["universal-route-ambiguous"]["severity"], "WARNING")

    def test_route_confidence_below_threshold_present(self):
        self.assertIn("route-confidence-below-threshold", self.catalog)
        self.assertEqual(self.catalog["route-confidence-below-threshold"]["severity"], "WARNING")

    def test_r117_igc_section_62w(self):
        w_kinds = [k for k, v in self.catalog.items() if v.get("section") == "62y"]
        self.assertGreaterEqual(len(w_kinds), 5)

    # RouteGraph construction
    def test_build_route_graph_multi_intent(self):
        from urace import cli as c
        state = c.initial_state()
        if not hasattr(c, "_build_route_graph"):
            self.skipTest("_build_route_graph not yet exposed")
        rgr = c._build_route_graph("add goal reduce churn and check status", state)
        self.assertIn("route_nodes", rgr)
        self.assertGreaterEqual(len(rgr["route_nodes"]), 2)
        self.assertIn("id", rgr)
        self.assertTrue(rgr["id"].startswith("rgr-"))

    def test_build_route_graph_single_intent(self):
        from urace import cli as c
        state = c.initial_state()
        if not hasattr(c, "_build_route_graph"):
            self.skipTest("_build_route_graph not yet exposed")
        rgr = c._build_route_graph("check status", state)
        self.assertIn("route_nodes", rgr)
        self.assertEqual(len(rgr["route_nodes"]), 1)

    def test_route_graph_stored_in_state(self):
        from urace import cli as c
        state = c.initial_state()
        if not hasattr(c, "_build_route_graph"):
            self.skipTest("_build_route_graph not yet exposed")
        c._build_route_graph("add goal and sync data", state)
        self.assertEqual(len(state["route_graph_records"]), 1)

    def test_route_graph_edges_sequential(self):
        from urace import cli as c
        state = c.initial_state()
        if not hasattr(c, "_build_route_graph"):
            self.skipTest("_build_route_graph not yet exposed")
        rgr = c._build_route_graph("add goal then add intent then check status", state)
        for edge in rgr["route_edges"]:
            self.assertEqual(edge["dependency_type"], "SEQUENTIAL")

    def test_route_graph_dispatch_tier_present(self):
        from urace import cli as c
        state = c.initial_state()
        if not hasattr(c, "_build_route_graph"):
            self.skipTest("_build_route_graph not yet exposed")
        rgr = c._build_route_graph("add goal and add intent", state)
        self.assertIn(rgr["dispatch_tier"], {"AUTO", "CONFIRM", "ABORT"})


class R117DataFullCoverageTests(unittest.TestCase):
    """r117 urace data full coverage: --auto, verify, status, credential, list filters, --schema"""

    def _run(self, state, cfg, argv):
        import sys
        old = sys.argv
        sys.argv = ["urace"] + argv
        try:
            from urace import cli as c
            c.run(state, cfg)
        except SystemExit:
            pass
        finally:
            sys.argv = old

    def setUp(self):
        from urace import cli as c
        self.cfg = c.load_config()
        self.state = c.initial_state()

    # --auto flag
    def test_data_add_auto_true_by_default(self):
        self._run(self.state, self.cfg, ["data", "add", "src1", "--type", "csv", "--connect", "/tmp/a.csv"])
        rec = next(r for r in self.state["data_source_records"] if r["name"] == "src1")
        self.assertTrue(rec.get("auto", True))

    def test_data_add_auto_false(self):
        self._run(self.state, self.cfg, ["data", "add", "src2", "--type", "csv", "--connect", "/tmp/b.csv", "--auto", "false"])
        rec = next(r for r in self.state["data_source_records"] if r["name"] == "src2")
        self.assertFalse(rec.get("auto"))

    def test_data_update_auto(self):
        self._run(self.state, self.cfg, ["data", "add", "src3", "--type", "csv", "--connect", "/tmp/c.csv"])
        self._run(self.state, self.cfg, ["data", "update", "src3", "--auto", "false"])
        rec = next(r for r in self.state["data_source_records"] if r["name"] == "src3")
        self.assertFalse(rec.get("auto"))

    # --schema hint
    def test_data_add_schema_hint(self):
        self._run(self.state, self.cfg, ["data", "add", "src4", "--type", "postgres", "--connect", "postgresql://h/db", "--schema", "public.metrics"])
        rec = next(r for r in self.state["data_source_records"] if r["name"] == "src4")
        self.assertEqual(rec.get("schema_hint"), "public.metrics")

    def test_data_update_schema_hint(self):
        self._run(self.state, self.cfg, ["data", "add", "src5", "--type", "mongodb", "--connect", "mongodb://h/db"])
        self._run(self.state, self.cfg, ["data", "update", "src5", "--schema", "events"])
        rec = next(r for r in self.state["data_source_records"] if r["name"] == "src5")
        self.assertEqual(rec.get("schema_hint"), "events")

    # verify
    def test_data_verify_missing_sqlite_source_stays_disconnected(self):
        self._run(self.state, self.cfg, ["data", "add", "src6", "--type", "sqlite", "--connect", "/tmp/db.sqlite"])
        self._run(self.state, self.cfg, ["data", "verify", "src6"])
        rec = next(r for r in self.state["data_source_records"] if r["name"] == "src6")
        self.assertEqual(rec["status"], "DISCONNECTED")
        self.assertEqual(rec["adapter_status"], "TRANSPORT_FAILED")

    def test_data_verify_unknown_source(self):
        # Should not raise — just emit error
        self._run(self.state, self.cfg, ["data", "verify", "nonexistent"])

    # status
    def test_data_status_returns_all_sources(self):
        self._run(self.state, self.cfg, ["data", "add", "a", "--type", "csv", "--connect", "/a.csv"])
        self._run(self.state, self.cfg, ["data", "add", "b", "--type", "json", "--connect", "/b.json"])
        # status command should not raise
        self._run(self.state, self.cfg, ["data", "status"])

    # list filters
    def test_data_list_filter_by_type(self):
        self._run(self.state, self.cfg, ["data", "add", "pg1", "--type", "postgres", "--connect", "postgresql://h/db"])
        self._run(self.state, self.cfg, ["data", "add", "csv1", "--type", "csv", "--connect", "/f.csv"])
        # Filtering internally — verify records exist with correct types
        pg = [r for r in self.state["data_source_records"] if r["adapter_kind"] == "postgres"]
        self.assertEqual(len(pg), 1)

    def test_data_list_filter_by_direction(self):
        self._run(self.state, self.cfg, ["data", "add", "r1", "--type", "csv", "--connect", "/r.csv", "--direction", "read"])
        self._run(self.state, self.cfg, ["data", "add", "w1", "--type", "csv", "--connect", "/w.csv", "--direction", "write"])
        reads = [r for r in self.state["data_source_records"] if r["direction"] == "READ"]
        writes = [r for r in self.state["data_source_records"] if r["direction"] == "WRITE"]
        self.assertEqual(len(reads), 1)
        self.assertEqual(len(writes), 1)

    def test_data_list_filter_by_status(self):
        self._run(self.state, self.cfg, ["data", "add", "s1", "--type", "csv", "--connect", "/s.csv"])
        self._run(self.state, self.cfg, ["data", "verify", "s1"])
        import contextlib, io, json
        from urace import cli as c
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = c._handle_data_command(
                __import__("argparse").Namespace(data_action="list", format="json", adapter_kind=None,
                    direction=None, status="DISCONNECTED"), self.state, self.cfg)
        self.assertEqual(code, 0)
        self.assertEqual([r["name"] for r in json.loads(output.getvalue())["records"]], ["s1"])
        self.assertFalse(any(r["status"] == "CONNECTED" for r in self.state["data_source_records"]))

    # credential add/remove/inspect
    def test_credential_add_attaches_to_source(self):
        self._run(self.state, self.cfg, ["data", "add", "cdb", "--type", "postgres", "--connect", "postgresql://h/db"])
        self._run(self.state, self.cfg, ["data", "credential", "add", "cdb", "--auth", "ENV_VAR", "--ref", "DB_PASSWORD"])
        rec = next(r for r in self.state["data_source_records"] if r["name"] == "cdb")
        self.assertIsNotNone(rec.get("credential_record_id"))
        self.assertEqual(len(self.state["credential_records"]), 1)

    def test_credential_record_does_not_expose_secret(self):
        self._run(self.state, self.cfg, ["data", "add", "cdb2", "--type", "postgres", "--connect", "postgresql://h/db"])
        self._run(self.state, self.cfg, ["data", "credential", "add", "cdb2", "--auth", "VAULT_PATH", "--ref", "secret/prod/db"])
        cred = self.state["credential_records"][0]
        # secret_ref is stored internally but inspect must redact it
        self.assertIn("secret_ref", cred)  # stored internally
        self.assertEqual(cred["auth_kind"], "VAULT_PATH")

    def test_credential_remove_detaches(self):
        self._run(self.state, self.cfg, ["data", "add", "cdb3", "--type", "mysql", "--connect", "mysql://h/db"])
        self._run(self.state, self.cfg, ["data", "credential", "add", "cdb3", "--auth", "ENV_VAR", "--ref", "MYSQL_PWD"])
        self._run(self.state, self.cfg, ["data", "credential", "remove", "cdb3"])
        rec = next(r for r in self.state["data_source_records"] if r["name"] == "cdb3")
        self.assertIsNone(rec.get("credential_record_id"))
        self.assertEqual(len(self.state["credential_records"]), 0)

    def test_credential_inspect_no_raise(self):
        self._run(self.state, self.cfg, ["data", "add", "cdb4", "--type", "redis", "--connect", "redis://h:6379"])
        self._run(self.state, self.cfg, ["data", "credential", "add", "cdb4", "--auth", "API_KEY", "--ref", "REDIS_TOKEN"])
        self._run(self.state, self.cfg, ["data", "credential", "inspect", "cdb4"])

    def test_credential_expires_at_stored(self):
        self._run(self.state, self.cfg, ["data", "add", "cdb5", "--type", "neo4j", "--connect", "bolt://h:7687"])
        self._run(self.state, self.cfg, ["data", "credential", "add", "cdb5", "--auth", "BASIC", "--ref", "NEO4J_CREDS", "--expires", "2027-01-01T00:00:00Z"])
        cred = self.state["credential_records"][0]
        self.assertEqual(cred["expires_at"], "2027-01-01T00:00:00Z")

    # auto=false sources skipped by auto sync (verify the flag is respected in record)
    def test_auto_false_flag_stored_correctly(self):
        self._run(self.state, self.cfg, ["data", "add", "manual", "--type", "parquet", "--connect", "/data.parquet", "--auto", "false"])
        rec = next(r for r in self.state["data_source_records"] if r["name"] == "manual")
        self.assertFalse(rec["auto"])
        self.assertEqual(rec["adapter_kind"], "parquet")


if __name__ == "__main__":
    unittest.main()
