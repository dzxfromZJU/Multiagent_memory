from bronze.experiment_compare import run_comparison


if __name__ == "__main__":
    payload = run_comparison(
        task="MIS",
        cases_path="tests_peer_MIS_cases.json",
        baseline_path="results_peer_MIS.json",
        edited_path="results_peer_MIS_edited.json",
        json_output="compare_peer_MIS.json",
        csv_output="compare_peer_MIS.csv",
        markdown_output="compare_peer_MIS.md",
    )
    print(payload["summary"])
