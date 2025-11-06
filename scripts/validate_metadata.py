#!/usr/bin/env python3
"""
BIOBRICK Metadata Validator

Validates BIOBRICK.yaml metadata files against schema requirements,
verifies asset file existence, and validates schemas for parquet and SQLite files.
"""

import sys
import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

import yaml
import pyarrow.parquet as pq
from jsonschema import validate, ValidationError, SchemaError


class Colors:
    """ANSI color codes for terminal output"""

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class ValidationReport:
    """Collects and formats validation results"""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.successes = []
        self.has_critical_errors = False

    def add_error(
        self, message: str, expected: Optional[str] = None, actual: Optional[str] = None
    ):
        """Add a validation error"""
        self.has_critical_errors = True
        error_msg = f"{Colors.FAIL}✗ ERROR:{Colors.ENDC} {message}"
        if expected and actual:
            error_msg += f"\n  {Colors.BOLD}Expected:{Colors.ENDC} {expected}"
            error_msg += f"\n  {Colors.BOLD}Actual:{Colors.ENDC} {actual}"
        self.errors.append(error_msg)

    def add_warning(self, message: str):
        """Add a validation warning"""
        self.warnings.append(f"{Colors.WARNING}⚠ WARNING:{Colors.ENDC} {message}")

    def add_success(self, message: str):
        """Add a successful validation"""
        self.successes.append(f"{Colors.OKGREEN}✓{Colors.ENDC} {message}")

    def print_report(self):
        """Print the complete validation report"""
        print("\n" + "=" * 80)
        print(
            f"{Colors.BOLD}{Colors.HEADER}BIOBRICK METADATA VALIDATION REPORT{Colors.ENDC}"
        )
        print("=" * 80 + "\n")

        if self.successes:
            print(f"{Colors.BOLD}Successful Checks:{Colors.ENDC}")
            for success in self.successes:
                print(f"  {success}")
            print()

        if self.warnings:
            print(f"{Colors.BOLD}Warnings:{Colors.ENDC}")
            for warning in self.warnings:
                print(f"  {warning}")
            print()

        if self.errors:
            print(f"{Colors.BOLD}Errors:{Colors.ENDC}")
            for error in self.errors:
                print(f"  {error}")
            print()

        print("=" * 80)
        if self.has_critical_errors:
            print(f"{Colors.FAIL}{Colors.BOLD}VALIDATION FAILED{Colors.ENDC}")
            print(
                f"{Colors.FAIL}Please fix the errors above and try again.{Colors.ENDC}"
            )
        else:
            print(f"{Colors.OKGREEN}{Colors.BOLD}VALIDATION PASSED{Colors.ENDC}")
            print(
                f"{Colors.OKGREEN}All metadata checks completed successfully!{Colors.ENDC}"
            )
        print("=" * 80 + "\n")


class MetadataValidator:
    """Main validator class for BIOBRICK metadata"""

    PARQUET_SCHEMA_JSON = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "column_name": {"type": "string"},
                "logical": {"type": "string"},
                "physical": {"type": "string"},
            },
            "required": ["column_name", "logical", "physical"],
            "additionalProperties": False,
        },
    }

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()
        self.biobrick_path = self.repo_path / "BIOBRICK.yaml"
        self.brick_dir = self.repo_path / "brick"
        self.report = ValidationReport()
        self.metadata = None

    def validate(self) -> bool:
        """Run all validations and return True if successful"""
        print(
            f"\n{Colors.BOLD}Validating BIOBRICK metadata at:{Colors.ENDC} {self.repo_path}\n"
        )

        # Step 1: Check BIOBRICK.yaml exists
        if not self._check_biobrick_exists():
            self.report.print_report()
            return False

        # Step 2: Load and parse YAML
        if not self._load_yaml():
            self.report.print_report()
            return False

        # Step 3: Validate top-level structure
        if not self._validate_top_level_structure():
            self.report.print_report()
            return False

        # Step 4: Validate brick directory exists
        if not self._check_brick_dir():
            self.report.print_report()
            return False

        # Step 5: Validate assets structure
        if not self._validate_assets_structure():
            self.report.print_report()
            return False

        # Step 6: Cross-reference assets with actual files
        self._validate_asset_files()

        # Step 7: Validate asset counts
        self._validate_asset_counts()

        # Step 8: Validate schemas
        self._validate_schemas()

        # Print final report
        self.report.print_report()

        return not self.report.has_critical_errors

    def _check_biobrick_exists(self) -> bool:
        """Check if BIOBRICK.yaml exists"""
        if not self.biobrick_path.exists():
            self.report.add_error(
                "BIOBRICK.yaml file not found in repository root",
                expected=f"File at {self.biobrick_path}",
                actual="File does not exist",
            )
            return False

        self.report.add_success("BIOBRICK.yaml file exists")
        return True

    def _load_yaml(self) -> bool:
        """Load and parse YAML file"""
        try:
            with open(self.biobrick_path, "r") as f:
                self.metadata = yaml.safe_load(f)

            if self.metadata is None:
                self.report.add_error(
                    "BIOBRICK.yaml is empty",
                    expected="Valid YAML content",
                    actual="Empty file",
                )
                return False

            if not isinstance(self.metadata, dict):
                self.report.add_error(
                    "BIOBRICK.yaml must contain a dictionary/mapping",
                    expected="YAML dictionary",
                    actual=f"Type: {type(self.metadata).__name__}",
                )
                return False

            self.report.add_success("BIOBRICK.yaml parsed successfully")
            return True

        except yaml.YAMLError as e:
            self.report.add_error(
                f"Failed to parse BIOBRICK.yaml: {str(e)}",
                expected="Valid YAML syntax",
                actual="YAML parsing error",
            )
            return False
        except Exception as e:
            self.report.add_error(f"Failed to read BIOBRICK.yaml: {str(e)}")
            return False

    def _validate_top_level_structure(self) -> bool:
        """Validate required top-level keys"""
        required_keys = ["brick", "description", "assets"]
        missing_keys = [key for key in required_keys if key not in self.metadata]

        if missing_keys:
            self.report.add_error(
                f"Missing required top-level keys: {', '.join(missing_keys)}",
                expected=f"Keys: {', '.join(required_keys)}",
                actual=f"Found keys: {', '.join(self.metadata.keys())}",
            )
            return False

        # Validate brick key
        if (
            not isinstance(self.metadata["brick"], str)
            or not self.metadata["brick"].strip()
        ):
            self.report.add_error(
                "The 'brick' key must be a non-empty string",
                expected="Non-empty string",
                actual=f"Type: {type(self.metadata['brick']).__name__}, Value: {self.metadata['brick']}",
            )
            return False

        # Validate description key
        if (
            not isinstance(self.metadata["description"], str)
            or not self.metadata["description"].strip()
        ):
            self.report.add_error(
                "The 'description' key must be a non-empty string",
                expected="Non-empty string",
                actual=f"Type: {type(self.metadata['description']).__name__}",
            )
            return False

        # Validate assets key
        if not isinstance(self.metadata["assets"], dict):
            self.report.add_error(
                "The 'assets' key must be a dictionary",
                expected="Dictionary/mapping",
                actual=f"Type: {type(self.metadata['assets']).__name__}",
            )
            return False

        if not self.metadata["assets"]:
            self.report.add_error(
                "The 'assets' dictionary cannot be empty",
                expected="At least one asset defined",
                actual="Empty dictionary",
            )
            return False

        self.report.add_success("All required top-level keys present and valid")
        self.report.add_success(f"Brick name: {self.metadata['brick']}")
        self.report.add_success(
            f"Found {len(self.metadata['assets'])} asset(s) defined"
        )

        return True

    def _check_brick_dir(self) -> bool:
        """Check if brick directory exists"""
        if not self.brick_dir.exists():
            self.report.add_error(
                "The 'brick' directory not found",
                expected=f"Directory at {self.brick_dir}",
                actual="Directory does not exist",
            )
            return False

        if not self.brick_dir.is_dir():
            self.report.add_error(
                "'brick' exists but is not a directory",
                expected="Directory",
                actual="File or other type",
            )
            return False

        self.report.add_success("Brick directory exists")
        return True

    def _validate_assets_structure(self) -> bool:
        """Validate structure of each asset entry"""
        all_valid = True

        for asset_path, asset_data in self.metadata["assets"].items():
            if not isinstance(asset_data, dict):
                self.report.add_error(
                    f"Asset '{asset_path}' must have a dictionary value",
                    expected="Dictionary with 'description' and 'schema' keys",
                    actual=f"Type: {type(asset_data).__name__}",
                )
                all_valid = False
                continue

            # Check for required keys
            if "description" not in asset_data:
                self.report.add_error(
                    f"Asset '{asset_path}' missing 'description' key",
                    expected="'description' key present",
                    actual="Key not found",
                )
                all_valid = False
            elif (
                not isinstance(asset_data["description"], str)
                or not asset_data["description"].strip()
            ):
                self.report.add_error(
                    f"Asset '{asset_path}' description must be a non-empty string",
                    expected="Non-empty string",
                    actual=f"Type: {type(asset_data['description']).__name__}",
                )
                all_valid = False

            if "schema" not in asset_data:
                self.report.add_error(
                    f"Asset '{asset_path}' missing 'schema' key",
                    expected="'schema' key present",
                    actual="Key not found",
                )
                all_valid = False
            elif (
                not isinstance(asset_data["schema"], str)
                or not asset_data["schema"].strip()
            ):
                self.report.add_error(
                    f"Asset '{asset_path}' schema must be a non-empty string",
                    expected="Non-empty string",
                    actual=f"Type: {type(asset_data['schema']).__name__}",
                )
                all_valid = False

        if all_valid:
            self.report.add_success(
                "All assets have required 'description' and 'schema' keys"
            )

        return all_valid

    def _validate_asset_files(self):
        """Verify that asset files exist at their specified paths"""
        for asset_path in self.metadata["assets"].keys():
            full_path = self.brick_dir / asset_path

            if not full_path.exists():
                self.report.add_error(
                    f"Asset file not found: {asset_path}",
                    expected=f"File at {full_path}",
                    actual="File does not exist",
                )
            elif not full_path.is_file():
                self.report.add_error(
                    f"Asset path is not a file: {asset_path}",
                    expected="Regular file",
                    actual="Directory or other type",
                )
            else:
                self.report.add_success(f"Asset file exists: {asset_path}")

    def _validate_asset_counts(self):
        """Validate that the number of .parquet and .hdt files matches assets in YAML"""
        # Count files in brick directory
        parquet_files = set()
        hdt_files = set()

        for file_path in self.brick_dir.rglob("*"):
            if file_path.is_file():
                rel_path = file_path.relative_to(self.brick_dir)
                if str(rel_path).endswith(".parquet"):
                    parquet_files.add(str(rel_path))
                elif str(rel_path).endswith(".hdt"):
                    hdt_files.add(str(rel_path))

        # Count assets in YAML
        yaml_parquet = set()
        yaml_hdt = set()

        for asset_path in self.metadata["assets"].keys():
            if asset_path.endswith(".parquet"):
                yaml_parquet.add(asset_path)
            elif asset_path.endswith(".hdt"):
                yaml_hdt.add(asset_path)

        # Compare parquet files
        if parquet_files != yaml_parquet:
            missing_in_yaml = parquet_files - yaml_parquet
            extra_in_yaml = yaml_parquet - parquet_files

            if missing_in_yaml:
                self.report.add_error(
                    "Found .parquet files in brick directory not listed in YAML",
                    expected=f"All parquet files listed in assets",
                    actual=f"Missing from YAML: {', '.join(sorted(missing_in_yaml))}",
                )

            if extra_in_yaml:
                self.report.add_error(
                    "Found .parquet files listed in YAML but not in brick directory",
                    expected=f"All YAML assets exist as files",
                    actual=f"Not found in brick dir: {', '.join(sorted(extra_in_yaml))}",
                )
        else:
            if parquet_files:
                self.report.add_success(
                    f"All {len(parquet_files)} .parquet file(s) accounted for"
                )

        # Compare hdt files
        if hdt_files != yaml_hdt:
            missing_in_yaml = hdt_files - yaml_hdt
            extra_in_yaml = yaml_hdt - hdt_files

            if missing_in_yaml:
                self.report.add_error(
                    "Found .hdt files in brick directory not listed in YAML",
                    expected=f"All hdt files listed in assets",
                    actual=f"Missing from YAML: {', '.join(sorted(missing_in_yaml))}",
                )

            if extra_in_yaml:
                self.report.add_error(
                    "Found .hdt files listed in YAML but not in brick directory",
                    expected=f"All YAML assets exist as files",
                    actual=f"Not found in brick dir: {', '.join(sorted(extra_in_yaml))}",
                )
        else:
            if hdt_files:
                self.report.add_success(
                    f"All {len(hdt_files)} .hdt file(s) accounted for"
                )

    def _validate_schemas(self):
        """Validate schemas for parquet and SQLite files"""
        for asset_path, asset_data in self.metadata["assets"].items():
            full_path = self.brick_dir / asset_path

            # Skip if file doesn't exist (already reported)
            if not full_path.exists():
                continue

            if asset_path.endswith(".parquet"):
                self._validate_parquet_schema(
                    asset_path, asset_data["schema"], full_path
                )
            elif asset_path.endswith(".sqlite"):
                self._validate_sqlite_schema(
                    asset_path, asset_data["schema"], full_path
                )

    def _validate_parquet_schema(
        self, asset_path: str, schema_str: str, file_path: Path
    ):
        """Validate parquet file schema"""
        # Parse schema as JSON
        try:
            schema_json = json.loads(schema_str)
        except json.JSONDecodeError as e:
            self.report.add_error(
                f"Asset '{asset_path}' schema is not valid JSON: {str(e)}",
                expected="Valid JSON array",
                actual=f"JSON parse error at position {e.pos}",
            )
            return

        # Validate against JSON schema
        try:
            validate(instance=schema_json, schema=self.PARQUET_SCHEMA_JSON)
        except ValidationError as e:
            self.report.add_error(
                f"Asset '{asset_path}' schema does not conform to parquet schema format",
                expected="Array of objects with column_name, logical, and physical",
                actual=f"Validation error: {e.message}",
            )
            return
        except SchemaError as e:
            self.report.add_error(
                f"Internal schema validation error for '{asset_path}': {str(e)}"
            )
            return

        # Read actual parquet file schema
        try:
            parquet_file = pq.read_table(file_path)
            actual_schema = parquet_file.schema

            # Build expected schema from JSON
            expected_columns = {
                col["column_name"]: (col["logical"], col["physical"])
                for col in schema_json
            }

            # Build actual schema mapping
            actual_columns = {}
            for i in range(len(actual_schema)):
                field = actual_schema.field(i)
                actual_columns[field.name] = str(field.type)

            # Compare column names
            expected_names = set(expected_columns.keys())
            actual_names = set(actual_columns.keys())

            if expected_names != actual_names:
                missing = expected_names - actual_names
                extra = actual_names - expected_names

                error_parts = []
                if missing:
                    error_parts.append(f"Missing columns: {', '.join(sorted(missing))}")
                if extra:
                    error_parts.append(f"Extra columns: {', '.join(sorted(extra))}")

                self.report.add_error(
                    f"Asset '{asset_path}' schema column mismatch",
                    expected=f"Columns: {', '.join(sorted(expected_names))}",
                    actual=f"Columns: {', '.join(sorted(actual_names))} | {' | '.join(error_parts)}",
                )
                return

            # For columns that match, give a warning if types seem different
            # (Note: type comparison between YAML and PyArrow can be complex)
            type_mismatches = []
            for col_name in expected_names:
                expected_logical = expected_columns[col_name][0]
                actual_type = actual_columns[col_name]

                # Simple type checking (this could be more sophisticated)
                if not self._types_compatible(expected_logical, actual_type):
                    type_mismatches.append(
                        f"{col_name}: expected {expected_logical}, got {actual_type}"
                    )

            if type_mismatches:
                self.report.add_warning(
                    f"Asset '{asset_path}' has potential type mismatches:\n    "
                    + "\n    ".join(type_mismatches)
                )
            else:
                self.report.add_success(
                    f"Asset '{asset_path}' schema matches parquet file "
                    f"({len(expected_columns)} columns)"
                )

        except Exception as e:
            self.report.add_error(
                f"Failed to read parquet file '{asset_path}': {str(e)}",
                expected="Readable parquet file",
                actual=f"Error: {type(e).__name__}",
            )

    def _validate_sqlite_schema(
        self, asset_path: str, schema_str: str, file_path: Path
    ):
        """Validate SQLite file schema"""
        try:
            # Connect to SQLite database
            conn = sqlite3.connect(file_path)
            cursor = conn.cursor()

            # Get actual schema
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()

            if not tables:
                self.report.add_error(
                    f"Asset '{asset_path}' SQLite database contains no tables",
                    expected="At least one table with schema",
                    actual="No tables found",
                )
                conn.close()
                return

            # Combine all CREATE TABLE statements
            actual_schema_parts = [table[0] for table in tables if table[0]]
            actual_schema = ";\n".join(actual_schema_parts) + ";"

            # Normalize schemas for comparison (remove extra whitespace)
            def normalize_schema(s):
                # Remove extra whitespace and normalize
                lines = [line.strip() for line in s.strip().split("\n")]
                return "\n".join(line for line in lines if line)

            expected_normalized = normalize_schema(schema_str)
            actual_normalized = normalize_schema(actual_schema)

            # Compare schemas
            if expected_normalized.replace(" ", "").replace(
                "\n", ""
            ) != actual_normalized.replace(" ", "").replace("\n", ""):
                self.report.add_error(
                    f"Asset '{asset_path}' schema does not match SQLite database schema",
                    expected=f"\n{expected_normalized}",
                    actual=f"\n{actual_normalized}",
                )
            else:
                self.report.add_success(
                    f"Asset '{asset_path}' schema matches SQLite database"
                )

            conn.close()

        except sqlite3.Error as e:
            self.report.add_error(
                f"Failed to read SQLite database '{asset_path}': {str(e)}",
                expected="Valid SQLite database file",
                actual=f"SQLite error: {type(e).__name__}",
            )
        except Exception as e:
            self.report.add_error(
                f"Failed to validate SQLite schema for '{asset_path}': {str(e)}",
                expected="Readable SQLite file",
                actual=f"Error: {type(e).__name__}",
            )

    def _types_compatible(self, expected_logical: str, actual_type: str) -> bool:
        """Check if expected and actual types are compatible"""
        # Normalize types for comparison
        expected_upper = expected_logical.upper()
        actual_upper = actual_type.upper()

        # Define compatible type mappings
        type_mappings = {
            "DOUBLE": ["DOUBLE", "FLOAT64", "FLOAT", "DECIMAL"],
            "FLOAT": ["FLOAT", "DOUBLE", "FLOAT32", "FLOAT64"],
            "INT": ["INT32", "INT64", "INT", "INTEGER", "LONG"],
            "INT32": ["INT32", "INT", "INTEGER"],
            "INT64": ["INT64", "LONG", "BIGINT"],
            "VARCHAR": ["STRING", "VARCHAR", "TEXT", "UTF8"],
            "STRING": ["STRING", "VARCHAR", "TEXT", "UTF8"],
            "BYTE_ARRAY": ["BINARY", "BYTE_ARRAY", "VARBINARY", "BYTES"],
            "BOOLEAN": ["BOOL", "BOOLEAN"],
            "TIMESTAMP": [
                "TIMESTAMP",
                "DATETIME",
                "TIMESTAMP_MILLIS",
                "TIMESTAMP_MICROS",
            ],
        }

        # Check if types match directly
        if expected_upper == actual_upper:
            return True

        # Check if they're in the same compatibility group
        for compatible_types in type_mappings.values():
            if expected_upper in compatible_types or any(
                ct in expected_upper for ct in compatible_types
            ):
                if actual_upper in compatible_types or any(
                    ct in actual_upper for ct in compatible_types
                ):
                    return True

        return False


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        repo_path = "/github/workspace"
    else:
        repo_path = sys.argv[1]

    validator = MetadataValidator(repo_path)
    success = validator.validate()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
