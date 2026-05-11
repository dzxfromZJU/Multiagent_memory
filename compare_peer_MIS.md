# MIS Baseline vs Edited Comparison

| Metric | Value |
|---|---:|
| task | MIS |
| total_cases | 72 |
| baseline_valid_cases | 66 |
| edited_valid_cases | 30 |
| baseline_error_cases | 6 |
| edited_error_cases | 42 |
| edited_curated_covered_cases | 6 |
| edited_curated_turn_count | 13 |
| edited_curated_fact_count | 177 |
| baseline_avg_score | 0.16666666666666666 |
| edited_avg_score | 0.03333333333333333 |
| covered_edited_avg_score | -0.4 |
| edited_improved_cases | 4 |
| edited_regressed_cases | 15 |
| edited_reduced_write_edges_cases | 48 |
| edited_added_contradiction_edges_cases | 1 |
| edited_added_repair_edges_cases | 0 |

## Error Types

```json
{
  "baseline": {
    "Connection error": 5,
    "timeout": 1
  },
  "edited": {
    "Invalid argument": 2,
    "Connection error": 40
  }
}
```
