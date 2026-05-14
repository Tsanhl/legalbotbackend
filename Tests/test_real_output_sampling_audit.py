from scripts.real_output_sampling_audit import SAMPLES, run_audit


rows = run_audit(real_rag=False)

assert len(rows) == 8
assert [row["words"] for row in rows] == [1500, 2000, 2500, 3000, 3500, 4000, 4500, 6000]

failures = {row["id"]: row["failures"] for row in rows if row["failures"]}
assert not failures, failures

assert any(row["long_split"]["is_long_essay"] for row in rows if row["words"] >= 2500)
assert all(row["chunk_count"] >= 10 for row in rows)

print("Real-output sampling compile audit passed.")
