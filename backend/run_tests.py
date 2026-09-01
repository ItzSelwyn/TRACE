"""Simple test runner for the TRACE backend."""
import subprocess
import sys

def run_tests():
    """Run the pytest test suite."""
    result = subprocess.run(
        ["python", "-m", "pytest", "tests/", "-q"],
        cwd="D:\\coding\\TRACE\\backend",
        capture_output=True,
        text=True
    )
    print(result.stdout)
    print(result.stderr)
    print(f"Return code: {result.returncode}")
    return result.returncode

if __name__ == "__main__":
    sys.exit(run_tests())