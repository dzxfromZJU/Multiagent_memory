from bronze.experiment_compare import run_comparison


if __name__ == "__main__":
    payload = run_comparison(
        task="REV",
        cases_path="tests_peer_REV_cases.json",
        baseline_path="results_peer_REV.json",
        edited_path="results_peer_REV_edited.json",
        json_output="compare_peer_REV.json",
        csv_output="compare_peer_REV.csv",
        markdown_output="compare_peer_REV.md",
    )
    print(payload["summary"])
