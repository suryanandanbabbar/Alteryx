"""Semantic Validation Tests (Constraints C7, C10).

Executes generated Python workflows against input data and verifies
that output datasets match deterministic expectations (schema, rows, values).
"""

import sys
import os
import subprocess
import pandas as pd
import pytest
from pathlib import Path

from awa.analysis.workflow_analyzer import analyze_workflow


FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"


class TestSemanticExecution:
    """Execute generated workflow Python scripts and assert data correctness."""

    def test_simple_filter_execution(self, tmp_path):
        """Run simple_filter workflow end-to-end with real data and verify filtered output."""
        fixture = FIXTURES_DIR / "basic" / "simple_filter.yxmd"
        out_dir = tmp_path / "analysis"
        result = analyze_workflow(fixture, out_dir)

        # Create input file expected by the workflow
        # The workflow expects \\server\data\customers.xlsx or local file
        # We prepare test data
        input_data = pd.DataFrame({
            "customer_id": ["C1", "C2", "C3", "C4"],
            "name": ["Acme Corp", "Beta LLC", "Gamma Inc", "Delta Co"],
            "status": ["active", "inactive", "active", "active"],
            "revenue": [150.0, 500.0, 50.0, 300.0]
        })
        
        # Output directory for the script execution
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        input_file = data_dir / "customers.xlsx"
        output_file = data_dir / "active_customers.xlsx"
        input_data.to_excel(input_file, index=False)

        # In the generated script, patch the input/output paths to point to tmp_path
        script_path = out_dir / "workflow.py"
        script_code = script_path.read_text()
        
        input_raw = result.workflow.tools[1].configuration.parsed.get("file_path", "")
        output_raw = result.workflow.tools[3].configuration.parsed.get("file_path", "")
        
        patched_code = script_code.replace(
            repr(input_raw), repr(str(input_file))
        ).replace(
            repr(output_raw), repr(str(output_file))
        )
        patched_script = tmp_path / "run_workflow.py"
        patched_script.write_text(patched_code)

        # Execute the generated python script as a subprocess
        proc = subprocess.run(
            [sys.executable, str(patched_script)],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, f"Execution failed with stderr:\n{proc.stderr}"
        assert output_file.exists(), "Output file was not produced"

        # Verify output DataFrame
        result_df = pd.read_excel(output_file)
        assert len(result_df) == 2
        # C1 (active, 150) and C4 (active, 300) should be included
        assert set(result_df["customer_id"]) == {"C1", "C4"}
        assert all(result_df["status"] == "active")
        assert all(result_df["revenue"] > 100)

    def test_join_workflow_execution(self, tmp_path):
        """Run join_workflow end-to-end with real data and verify join, summarize, and sort results."""
        fixture = FIXTURES_DIR / "joins" / "join_workflow.yxmd"
        out_dir = tmp_path / "analysis_join"
        result = analyze_workflow(fixture, out_dir)

        # Prepare test data
        data_dir = tmp_path / "data_join"
        data_dir.mkdir(parents=True, exist_ok=True)
        customers_file = data_dir / "customers.xlsx"
        orders_file = data_dir / "orders.csv"
        output_file = data_dir / "customer_totals.xlsx"

        customers_df = pd.DataFrame({
            "customer_id": ["1", "2", "3"],
            "name": ["Alice", "Bob", "Charlie"]
        })
        orders_df = pd.DataFrame({
            "order_id": ["O101", "O102", "O103", "O104"],
            "customer_id": ["1", "1", "2", "99"],  # 99 has no customer match
            "amount": [100.0, 150.0, 50.0, 500.0]
        })

        customers_df.to_excel(customers_file, index=False)
        orders_df.to_csv(orders_file, index=False)

        # Patch paths in generated script
        script_path = out_dir / "workflow.py"
        script_code = script_path.read_text()

        input1_raw = result.workflow.tools[1].configuration.parsed.get("file_path", "")
        input2_raw = result.workflow.tools[2].configuration.parsed.get("file_path", "")
        output_raw = result.workflow.tools[6].configuration.parsed.get("file_path", "")

        patched_code = script_code.replace(
            repr(input1_raw), repr(str(customers_file))
        ).replace(
            repr(input2_raw), repr(str(orders_file))
        ).replace(
            repr(output_raw), repr(str(output_file))
        )
        patched_script = tmp_path / "run_join_workflow.py"
        patched_script.write_text(patched_code)

        # Execute
        proc = subprocess.run(
            [sys.executable, str(patched_script)],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, f"Execution failed with stderr:\n{proc.stderr}"
        assert output_file.exists(), "Output file was not produced"

        # Verify output DataFrame
        res_df = pd.read_excel(output_file)
        # Expected:
        # Customer 1 (Alice): 100 + 150 = 250
        # Customer 2 (Bob): 50
        # Customer 3 (Charlie): no orders, inner join drops
        # Sorted descending by total_amount: Alice (250) first, Bob (50) second
        assert len(res_df) == 2
        # customer_id might be parsed as int or str in Excel read
        assert str(res_df.iloc[0]["customer_id"]) == "1"
        assert res_df.iloc[0]["name"] == "Alice"
        assert res_df.iloc[0]["total_amount"] == 250.0

        assert str(res_df.iloc[1]["customer_id"]) == "2"
        assert res_df.iloc[1]["name"] == "Bob"
        assert res_df.iloc[1]["total_amount"] == 50.0
