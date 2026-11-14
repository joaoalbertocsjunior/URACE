# Milestone phases and statuses

`python3 -m urace milestone --json` now includes a read-only phase/status view for every configured milestone. Plain output shows the active phase and operational status. No model call is needed.

Canonical statuses remain `PENDING`, `ACTIVE`, `ACHIEVED`, `SUPERSEDED`. Existing capability, quality-streak, complexity and value-density rules still control achievement and version-chain activation. The phase view cannot set achievement, approve decisions, change thresholds or award value.

| Derived phase | Meaning |
| --- | --- |
| PLANNING | Configured milestone is pending activation |
| IMPLEMENTATION | Active milestone still has unsatisfied capability gates |
| VALIDATION | Capability gates are satisfied; quality/constraint evaluation remains |
| COMPLETE | Canonical achievement and current configured gate evidence agree |
| REASSESSMENT | Historical achievement remains recorded, but current gate evidence is missing or no longer satisfies it |
| SUPERSEDED | Historical milestone has been superseded |

Operational feedback separately exposes `PENDING`, `ACTIVE`, `BLOCKED`, `AWAITING_APPROVAL`, `READY_FOR_GATE_EVALUATION`, `ACHIEVED`, `NEEDS_REASSESSMENT`, `SUPERSEDED` or `UNKNOWN`. It includes failing/unknown gates, detected bottlenecks, recommended next checks and explicitly linked decision references. Approval derives from the existing authority outcome, never a benefit score. Missing evidence is not a zero measurement or passing check. A zero required quality streak remains a zero requirement, matching the existing contract.

The informational outcome-observation axis is `UNMEASURED` unless a separate verified outcome system provides evidence. It is not silently added as a new milestone gate. Capability achievement alone does not prove full functional/comparative assessment, comprehension, market fit or observed user benefit. Historical achievement and product versions are preserved if current evidence regresses.
