# REV Baseline vs Edited Comparison

| Metric | Value |
|---|---:|
| task | REV |
| total_cases | 40 |
| baseline_valid_cases | 31 |
| edited_valid_cases | 27 |
| baseline_error_cases | 9 |
| edited_error_cases | 13 |
| edited_curated_covered_cases | 4 |
| edited_curated_turn_count | 22 |
| edited_curated_fact_count | 225 |
| baseline_avg_score | 2.0 |
| edited_avg_score | 2.0 |
| covered_edited_avg_score | 2.0 |
| edited_improved_cases | 1 |
| edited_regressed_cases | 1 |
| edited_reduced_write_edges_cases | 26 |
| edited_added_contradiction_edges_cases | 2 |
| edited_added_repair_edges_cases | 0 |

## Error Types

```json
{
  "baseline": {
    "Invalid argument": 9
  },
  "edited": {
    "Invalid argument": 10,
    "timeout": 1,
    "Connection error": 2
  }
}
```
