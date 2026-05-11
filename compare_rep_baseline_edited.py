from bronze.experiment_compare import run_comparison


if __name__ == "__main__":
    payload = run_comparison(
        task="REP",
        cases_path="tests_peer_REP_cases.json",
        baseline_path="results_peer_REP.json",
        edited_path="results_peer_REP_edited.json",
        json_output="compare_peer_REP.json",
        csv_output="compare_peer_REP.csv",
        markdown_output="compare_peer_REP.md",
    )
    print(payload["summary"])
