from Tests.test_full_topic_routing_matrix import ROUTING_CASES
from scripts.real_output_sampling_audit import all_topic_samples, run_audit


samples = all_topic_samples()
rows = run_audit(real_rag=False, samples=samples)

assert len(samples) == len(ROUTING_CASES)
assert len(rows) == len(ROUTING_CASES)

failures = {row["id"]: row["failures"] for row in rows if row["failures"]}
assert not failures, failures

topics = {row["expected_topic"] for row in rows}
assert len(topics) == len(ROUTING_CASES)
assert all(row["chunk_count"] >= 10 for row in rows)
assert all(row["allow_web_search"] for row in rows)
assert all(row["checks"]["mandatory_rag_policy_present"] for row in rows)
assert all(row["checks"]["quality_gate_present"] for row in rows)

print(f"All-topic real-output compile audit passed for {len(rows)} topics.")
