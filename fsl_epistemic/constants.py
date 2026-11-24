"""KIF v0.22 immutable candidate contract vocabulary. Apache-2.0."""
CHECKS = ["O1","O2","O3","O4","O5","O6","problem_value","substantive_validity","scoped_originality","formal_validity","safety","authorization"]
MINIMUM = {"problem_generation":["problem_value","O3","O6"],"theory_creation":["substantive_validity","scoped_originality","O3","O6"],"proof_production":["substantive_validity","O1","O3","O6"],"interpretation":["O1","O2","O3","O6"],"transfer":["O1","O2","O3","O6"],"cross_domain_bridge":["O1","O3","O4","O6"],"contextual_application":["O1","O3","O5","O6"]}
BUDGET = ["cost_minor","wall_seconds","human_core_minutes","compute_units"]
STAGES = ["G","V","A","I","B","U"]
FLOW_COUNTS = ["raw_candidates","valid_candidates","deduplicated_valid","new_demand_units","opening_backlog","completed","cancelled","closing_backlog","qualified_capacity","terminal_outputs"]
POP_COUNTS = ["baseline_n","retained_n","exited_n","lost_n","entrant_n","role_transition_n","baseline_formal_employed","followup_formal_employed","baseline_active_minutes","followup_active_minutes","baseline_accepted_outputs","followup_accepted_outputs"]
POP_SUMS = ["baseline_sum","retained_baseline_sum","retained_followup_sum","exit_baseline_sum","lost_baseline_sum","entrant_sum"]
TIERS = set(["unobserved","provider_claim","provider_demo","repeatable_test","independent_repeated","longitudinal_independent","synthetic_fixture"])
COMPUTABLE = {"repeatable_test", "independent_repeated", "longitudinal_independent", "synthetic_fixture"}
STATES = set(["passed","failed","unknown","not_applicable"])
SCHEMA = "fsl/kif/0.22"
