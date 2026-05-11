# REP Baseline vs Edited Comparison

| Metric | Value |
|---|---:|
| task | REP |
| total_cases | 48 |
| baseline_valid_cases | 31 |
| edited_valid_cases | 37 |
| baseline_error_cases | 17 |
| edited_error_cases | 11 |
| edited_curated_covered_cases | 5 |
| edited_curated_turn_count | 32 |
| edited_curated_fact_count | 306 |
| baseline_avg_score | 0.8064516129032258 |
| edited_avg_score | 0.8378378378378378 |
| covered_edited_avg_score | 1.0 |
| edited_improved_cases | 11 |
| edited_regressed_cases | 1 |
| edited_reduced_write_edges_cases | 20 |
| edited_added_contradiction_edges_cases | 0 |
| edited_added_repair_edges_cases | 0 |

## Error Types

```json
{
  "baseline": {
    "Connection error": 16,
    "Invalid argument": 1
  },
  "edited": {
    "Invalid argument": 10,
    "Connection error": 1
  }
}
```
