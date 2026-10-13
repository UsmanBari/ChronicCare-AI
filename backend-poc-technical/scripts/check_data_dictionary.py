import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

SCHEMA_FILE = ROOT / "backend-poc-technical" / "data_sources" / "app_store.py"
DICTIONARY_FILE = ROOT / "docs" / "DATA_DICTIONARY.md"


def extract_create_tables(schema_text):
    tables = {}

    pattern = re.compile(
        r"CREATE TABLE IF NOT EXISTS\s+(\w+)\s*\((.*?)\)"
        r"\s*(?:ENGINE=.*?)?[\"']{3}",
        re.IGNORECASE | re.DOTALL,
    )

    for match in pattern.finditer(schema_text):
        table_name = match.group(1)
        body = match.group(2)

        tables.setdefault(table_name, set())

        for line in body.splitlines():
            line = line.strip().rstrip(",")

            if not line:
                continue

            upper = line.upper()

            if upper.startswith(
                (
                    "PRIMARY KEY",
                    "FOREIGN KEY",
                    "UNIQUE",
                    "CHECK",
                    "INDEX",
                    "CONSTRAINT",
                )
            ):
                continue

            column_match = re.match(r"[`'\"]?(\w+)[`'\"]?\s+", line)

            if column_match:
                tables[table_name].add(column_match.group(1))

    return tables


def extract_alter_columns(schema_text, tables):
    pattern = re.compile(
        r"ALTER TABLE\s+(\w+)\s+ADD COLUMN\s+(\w+)",
        re.IGNORECASE,
    )

    for table_name, column_name in pattern.findall(schema_text):
        tables.setdefault(table_name, set()).add(column_name)


def extract_dictionary_sections(dictionary_text):
    sections = {}

    table_pattern = re.compile(
        r"Table:\s*`([^`]+)`(.*?)(?=\n## |\Z)",
        re.IGNORECASE | re.DOTALL,
    )

    for match in table_pattern.finditer(dictionary_text):
        table_name = match.group(1)
        section = match.group(2)

        columns = set(
            re.findall(
                r"^\|\s*`([^`]+)`\s*\|",
                section,
                re.MULTILINE,
            )
        )

        sections[table_name] = columns

    return sections


def main():
    schema_text = SCHEMA_FILE.read_text(encoding="utf-8")
    dictionary_text = DICTIONARY_FILE.read_text(encoding="utf-8")

    schema_tables = extract_create_tables(schema_text)
    extract_alter_columns(schema_text, schema_tables)

    dictionary_tables = extract_dictionary_sections(dictionary_text)

    print("Data dictionary schema check")
    print("=" * 40)

    mismatch_found = False

    for table_name in sorted(schema_tables):
        schema_columns = schema_tables[table_name]

        if table_name not in dictionary_tables:
            mismatch_found = True
            print(f"\nMISSING TABLE: {table_name}")
            continue

        documented_columns = dictionary_tables[table_name]

        missing = sorted(schema_columns - documented_columns)
        extra = sorted(documented_columns - schema_columns)

        print(f"\nTable: {table_name}")

        if missing:
            mismatch_found = True
            print("  Missing from dictionary:")
            for column in missing:
                print(f"    - {column}")
        else:
            print("  Missing from dictionary: none")

        if extra:
            print("  Documented but not found by static schema scan:")
            for column in extra:
                print(f"    - {column}")
        else:
            print("  Extra documented columns: none")

    print("\n" + "=" * 40)

    if mismatch_found:
        print("Result: mismatches found")
    else:
        print("Result: no missing schema tables/columns found")


if __name__ == "__main__":
    main()