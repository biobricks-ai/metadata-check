# BIOBRICK Metadata Check Action

A GitHub Action that validates BIOBRICK.yaml metadata files, verifies asset file existence, and checks schema conformance for parquet and SQLite files.

## Features

- ✅ Validates BIOBRICK.yaml file structure and required fields
- ✅ Verifies all asset files exist at their specified paths
- ✅ Ensures all `.parquet` and `.hdt` files in the brick directory are documented
- ✅ Validates parquet file schemas against JSON schema definitions
- ✅ Validates SQLite database schemas
- ✅ Provides detailed validation reports with expected vs actual comparisons
- ✅ Color-coded output for easy error identification

## Usage

### Using from an Organization Repository

Once you push this action to your organization's GitHub (e.g., `https://github.com/your-org/metadata-check`), you can use it in any repository within your organization or publicly.

#### Basic Usage

Add this action to your GitHub workflow in `.github/workflows/validate.yml`:

```yaml
name: Validate BIOBRICK Metadata

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v3
      
      - name: Validate BIOBRICK metadata
        uses: your-org/metadata-check@v1  # Replace 'your-org' with your GitHub organization name
```

#### Referencing the Action

You can reference the action in several ways:

**By Tag (Recommended for Production):**
```yaml
uses: your-org/metadata-check@v1.0.0  # Specific version
uses: your-org/metadata-check@v1      # Major version (gets latest v1.x.x)
```

**By Branch:**
```yaml
uses: your-org/metadata-check@main    # Latest from main branch
```

**By Commit SHA (Most Secure):**
```yaml
uses: your-org/metadata-check@a1b2c3d  # Specific commit
```

### Custom Path

If your repository structure is different, you can specify a custom path:

```yaml
      - name: Validate BIOBRICK metadata
        uses: your-org/metadata-check@v1
        with:
          path: './custom/path'
```

### Complete Example

Here's a complete workflow file (`.github/workflows/metadata-check.yml`):

```yaml
name: BIOBRICK Metadata Validation

on:
  push:
    branches: [ main, master, develop ]
  pull_request:
    branches: [ main, master ]
  workflow_dispatch:  # Allow manual triggering

jobs:
  validate-metadata:
    name: Validate BIOBRICK.yaml
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Run metadata validation
        uses: your-org/metadata-check@v1
        with:
          path: '.'
      
      - name: Comment on PR (optional)
        if: failure() && github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '❌ BIOBRICK metadata validation failed. Please check the action logs for details.'
            })
```

### Publishing the Action

After pushing this repository to your organization, create a release to make it available:

```bash
# 1. Push to your organization
git remote add origin https://github.com/your-org/metadata-check.git
git push -u origin main

# 2. Create and push a tag
git tag -a v1.0.0 -m "Initial release"
git push origin v1.0.0

# 3. Create a major version tag (optional, for easier updates)
git tag -a v1 -m "Major version 1"
git push origin v1
```

Then create a GitHub Release from the tag via the GitHub UI for better visibility.

### Making the Action Public

If you want to use this action across different organizations or make it publicly available:

1. Go to the repository Settings
2. Ensure the repository is set to "Public" (if desired)
3. No additional configuration needed - public actions are automatically usable by anyone

For private repositories, the action can only be used within:
- The same repository
- Other repositories in the same organization (if organization settings allow)

## BIOBRICK.yaml Schema

The BIOBRICK.yaml file must conform to the following structure:

```yaml
brick: brick-name

version: v1.0.0  # optional

description: A description of this brick

assets:
  path/to/file.parquet:
    description: Description of this asset
    schema: |
      [
        {column_name: col1, logical: DOUBLE, physical: DOUBLE},
        {column_name: col2, logical: VARCHAR, physical: BYTE_ARRAY}
      ]
  
  path/to/database.sqlite:
    description: Description of this database
    schema: |
      CREATE TABLE `table_name` (
        `column1` REAL,
        `column2` TEXT
      );
```

### Required Fields

#### Top Level
- `brick` (string): Name of the brick
- `description` (string): Description of the brick
- `assets` (object): Dictionary of assets

#### Assets
Each asset entry must contain:
- **Key**: Relative path from `brick/` directory to the asset file
  - Example: If file is at `./brick/subdir/file.parquet`, the key should be `subdir/file.parquet`
- **Value**: Object with:
  - `description` (string): Description of the asset
  - `schema` (string): Schema definition (format depends on file type)

## Schema Formats

### Parquet Files (`.parquet`)

Parquet file schemas must be valid JSON arrays conforming to:

```json
[
  {
    "column_name": "column_name_here",
    "logical": "DOUBLE",
    "physical": "DOUBLE"
  },
  {
    "column_name": "another_column",
    "logical": "VARCHAR",
    "physical": "BYTE_ARRAY"
  }
]
```

**JSON Schema:**
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "column_name": { "type": "string" },
      "logical": { "type": "string" },
      "physical": { "type": "string" }
    },
    "required": ["column_name", "logical", "physical"],
    "additionalProperties": false
  }
}
```

**Common Logical Types:**
- `DOUBLE`, `FLOAT`
- `INT32`, `INT64`
- `VARCHAR`, `STRING`
- `BOOLEAN`
- `TIMESTAMP`
- `BYTE_ARRAY`

### SQLite Files (`.sqlite`)

SQLite schemas should be equivalent to the output of `sqlite3 database.sqlite '.schema'`:

```sql
CREATE TABLE `table_name` (
  `column1` REAL,
  `column2` INTEGER,
  `column3` TEXT,
  `column4` BLOB
);
```

Multiple tables can be included:

```sql
CREATE TABLE `table1` (
  `id` INTEGER PRIMARY KEY,
  `name` TEXT
);

CREATE TABLE `table2` (
  `id` INTEGER PRIMARY KEY,
  `value` REAL
);
```

## Validation Checks

The action performs the following validations:

### 1. File Existence
- ✓ BIOBRICK.yaml exists in repository root
- ✓ `brick/` directory exists

### 2. YAML Structure
- ✓ Valid YAML syntax
- ✓ Required top-level keys present (`brick`, `description`, `assets`)
- ✓ All values are correct types (strings, objects)
- ✓ Assets dictionary is not empty

### 3. Asset Structure
- ✓ Each asset has `description` and `schema` keys
- ✓ Both description and schema are non-empty strings

### 4. File Verification
- ✓ All assets listed in YAML exist as files in `brick/` directory
- ✓ All `.parquet` files in `brick/` are documented in YAML
- ✓ All `.hdt` files in `brick/` are documented in YAML
- ℹ️ Other file types in `brick/` are ignored

### 5. Schema Validation

#### Parquet Files
- ✓ Schema is valid JSON
- ✓ JSON conforms to parquet schema format
- ✓ Column names match actual parquet file
- ✓ Column types are compatible with actual parquet file
- ⚠️ Warnings for potential type mismatches

#### SQLite Files
- ✓ SQLite database is readable
- ✓ Schema matches actual database schema

## Example BIOBRICK.yaml

```yaml
brick: hello-brick

version: v1.0.0

description: Brick used for testing purposes

assets:
  mtcars.parquet:
    description: The `mtcars` asset contains 11 columns of automotive performance data
    schema: |
      [
        {column_name: mpg, logical: DOUBLE, physical: DOUBLE},
        {column_name: cyl, logical: DOUBLE, physical: DOUBLE},
        {column_name: disp, logical: DOUBLE, physical: DOUBLE},
        {column_name: hp, logical: DOUBLE, physical: DOUBLE},
        {column_name: drat, logical: DOUBLE, physical: DOUBLE},
        {column_name: wt, logical: DOUBLE, physical: DOUBLE},
        {column_name: qsec, logical: DOUBLE, physical: DOUBLE},
        {column_name: vs, logical: DOUBLE, physical: DOUBLE},
        {column_name: am, logical: DOUBLE, physical: DOUBLE},
        {column_name: gear, logical: DOUBLE, physical: DOUBLE},
        {column_name: carb, logical: DOUBLE, physical: DOUBLE}
      ]

  rtbls/iris.parquet:
    description: This asset contains a sample of the Iris flower dataset
    schema: |
      [
        {column_name: Sepal.Length, logical: DOUBLE, physical: DOUBLE},
        {column_name: Sepal.Width, logical: DOUBLE, physical: DOUBLE},
        {column_name: Petal.Length, logical: DOUBLE, physical: DOUBLE},
        {column_name: Petal.Width, logical: DOUBLE, physical: DOUBLE},
        {column_name: Species, logical: VARCHAR, physical: BYTE_ARRAY}
      ]

  iris.sqlite:
    description: SQLite database with iris dataset
    schema: |
      CREATE TABLE `iris` (
        `Sepal.Length` REAL,
        `Sepal.Width` REAL,
        `Petal.Length` REAL,
        `Petal.Width` REAL,
        `Species` TEXT
      );
```

## Output Examples

### Success
```
================================================================================
BIOBRICK METADATA VALIDATION REPORT
================================================================================

Successful Checks:
  ✓ BIOBRICK.yaml file exists
  ✓ BIOBRICK.yaml parsed successfully
  ✓ All required top-level keys present and valid
  ✓ Brick name: hello-brick
  ✓ Found 3 asset(s) defined
  ✓ Brick directory exists
  ✓ All assets have required 'description' and 'schema' keys
  ✓ Asset file exists: mtcars.parquet
  ✓ Asset file exists: rtbls/iris.parquet
  ✓ Asset file exists: iris.sqlite
  ✓ All 2 .parquet file(s) accounted for
  ✓ Asset 'mtcars.parquet' schema matches parquet file (11 columns)
  ✓ Asset 'rtbls/iris.parquet' schema matches parquet file (5 columns)
  ✓ Asset 'iris.sqlite' schema matches SQLite database

================================================================================
VALIDATION PASSED
All metadata checks completed successfully!
================================================================================
```

### Failure with Details
```
================================================================================
BIOBRICK METADATA VALIDATION REPORT
================================================================================

Successful Checks:
  ✓ BIOBRICK.yaml file exists
  ✓ BIOBRICK.yaml parsed successfully

Errors:
  ✗ ERROR: Missing required top-level keys: description
  Expected: Keys: brick, description, assets
  Actual: Found keys: brick, assets

  ✗ ERROR: Asset file not found: missing_file.parquet
  Expected: File at /path/to/brick/missing_file.parquet
  Actual: File does not exist

  ✗ ERROR: Asset 'data.parquet' schema column mismatch
  Expected: Columns: col1, col2, col3
  Actual: Columns: col1, col2 | Missing columns: col3

================================================================================
VALIDATION FAILED
Please fix the errors above and try again.
================================================================================
```

## Troubleshooting

### Common Issues

**Error: BIOBRICK.yaml file not found**
- Ensure the file is named exactly `BIOBRICK.yaml` (case-sensitive)
- Ensure it's in the repository root

**Error: Asset file not found**
- Check the asset path is relative to the `brick/` directory
- If file is at `./brick/data/file.parquet`, use `data/file.parquet` as the key

**Error: Schema is not valid JSON**
- For parquet files, ensure the schema is a valid JSON array
- Use a JSON validator to check syntax
- Common issues: missing quotes, trailing commas

**Error: Schema column mismatch**
- Run `parquet-tools schema file.parquet` to see actual schema
- Ensure all columns are listed in the YAML
- Check column name spelling matches exactly

**Error: SQLite schema does not match**
- Run `sqlite3 file.sqlite '.schema'` to see actual schema
- Copy the exact output into the YAML schema field
- Ensure formatting matches (whitespace is normalized during comparison)

## Development

### Local Testing

You can test the validator locally using Docker:

```bash
# Build the Docker image
docker build -t metadata-check .

# Run validation on a repository
docker run -v /path/to/repo:/github/workspace metadata-check /github/workspace
```

Or test directly with Python (requires dependencies):

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies (creates a virtual environment automatically)
uv sync

# Run validator
uv run validate_metadata.py /path/to/repository
```

### Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- Dependencies (managed via `pyproject.toml`):
  - PyYAML 6.0.1+
  - pyarrow 14.0.1+
  - jsonschema 4.20.0+

### Package Manager

This action uses [uv](https://github.com/astral-sh/uv) for dependency management with several advantages:

- **Faster installation**: uv is 10-100x faster than pip
- **Better reproducibility**: Lockfile (`uv.lock`) ensures exact versions across environments
- **Simplified workflow**: `uv sync` creates virtual environments automatically
- **Smaller image size**: Efficient caching and installation

### Project Structure

Dependencies are managed through:
- `pyproject.toml` - Defines project metadata and dependencies
- `uv.lock` - Lockfile ensuring reproducible builds (auto-generated by `uv lock`)

To update dependencies:
```bash
# Update a dependency
uv add package-name@version

# Regenerate lockfile
uv lock

# Install updated dependencies
uv sync
```

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

