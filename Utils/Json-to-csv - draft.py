import json
import re
import pandas as pd
import os
import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def process_about_data(about_data_file, output_file="about_data.csv"):
    """
    Process 'About' data and save to CSV.
    """
    if not os.path.isfile(about_data_file):
        print(f"File not found: {about_data_file}")
        return

    with open(about_data_file, "r") as json_file:
        data = json.load(json_file)

    rows = []
    for about_data in data:
        associated_members = (
            re.sub(r"[^\d]", "", about_data.get("No. of associated members", "")) or "-"
        )
        company_size = re.sub(r"[^\d\-]", "", about_data.get("Company size", "-"))
        company_size = f"'{company_size}" if company_size != "-" else company_size
        linkedin_url = about_data.get("LinkedIn URL", "-").split("?")[0]

        rows.append(
            {
                "Input Company Name": about_data.get("input_company_name", "-"),
                "Company Name": about_data.get("Company Name", "-"),
                "Associated Members": associated_members,
                "Website": about_data.get("Website", "-"),
                "Industry": about_data.get("Industry", "-"),
                "Company Size": company_size,
                "Headquarters": about_data.get("Headquarters", "-"),
                "Founded": about_data.get("Founded", "-"),
                "Specialties": about_data.get("Specialties", "-"),
                "LinkedIn URL": linkedin_url,
                "Time Stamp": about_data.get(
                    "Time Stamp", datetime.datetime.now().isoformat()
                ),
                "Redirected to URL": about_data.get("Redirected to URL", "-"),
            }
        )

    df = pd.DataFrame(rows)

    # Ensure string-compatible columns are cast properly
    for col in df.select_dtypes(include=["number"]).columns:
        df[col] = df[col].astype("object")

    df.fillna("-", inplace=True)

    if os.path.isfile(output_file):
        existing_df = pd.read_csv(output_file)
        df = pd.concat([existing_df, df], ignore_index=True)

    df.to_csv(output_file, index=False)
    print(f"About data saved to {output_file}.")


def process_what_they_do_long_format(file_path, output_file, is_quantum=False):
    """
    Process 'What They Do' data and save to CSV in LONG FORMAT.
    Each role gets its own row (Company Name, Role, Count, Timestamp).
    """
    if not os.path.isfile(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, "r") as json_file:
        data = json.load(json_file)

    rows = []
    for entry in data:
        company_name = entry.get("Company Name", "-")
        input_company_name = entry.get("input_company_name", "-")
        timestamp = entry.get("Time Stamp", datetime.datetime.now().isoformat())
        redirected_to_url = entry.get("Redirected to URL", "-")
        roles = entry.get("Roles", [])

        # Get membership count
        if is_quantum:
            membership_value = entry.get("Quantum Associated Members", "-")
        else:
            membership_value = entry.get("Associated Members", "-")

        # Create one row per role
        for role_entry in roles:
            if isinstance(role_entry, dict):
                role_name = role_entry.get("Role", "Unknown Role")
                count = role_entry.get("Count", "-")
            else:
                role_name = str(role_entry)
                count = "-"

            row = {
                "Input Company Name": input_company_name,
                "Company Name": company_name,
                "Role": role_name,
                "Count": count,
                "Time Stamp": timestamp,
                "Redirected to URL": redirected_to_url,
            }

            # Add membership column
            if is_quantum:
                row["Quantum Associated Members"] = membership_value
            else:
                row["Associated Members"] = membership_value

            rows.append(row)

    df = pd.DataFrame(rows)

    # Ensure string-compatible columns are cast properly
    for col in df.select_dtypes(include=["number"]).columns:
        df[col] = df[col].astype("object")

    df.fillna("-", inplace=True)

    if os.path.isfile(output_file):
        existing_df = pd.read_csv(output_file)
        df = pd.concat([existing_df, df], ignore_index=True)

    df.to_csv(output_file, index=False)
    print(f"What They Do data (long format) saved to {output_file}.")


def process_where_they_live(file_path, output_file, include_quantum):
    """
    Process 'Where They Live' data and save to CSV.
    """
    if not os.path.isfile(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, "r") as json_file:
        data = json.load(json_file)

    rows = []
    for entry in data:
        input_company_name = entry.get("input_company_name", "-")
        company_name = entry.get("Company Name", "-")
        timestamp = entry.get("Time Stamp", datetime.datetime.now().isoformat())
        redirected_to_url = entry.get("Redirected to URL", "-")
        locations = entry.get("Locations", [])

        # Get membership count
        if include_quantum:
            membership_value = entry.get("Quantum Associated Members", "-")
        else:
            membership_value = entry.get("Associated Members", "-")

        for loc in locations:
            if isinstance(loc, dict):
                row = {
                    "Input Company Name": input_company_name,
                    "Company Name": company_name,
                    "Location": loc.get("Location", "-"),
                    "Count": loc.get("Count", "-"),
                    "Time Stamp": timestamp,
                    "Redirected to URL": redirected_to_url,
                }
                if include_quantum:
                    row["Quantum Associated Members"] = membership_value
                else:
                    row["Associated Members"] = membership_value
                rows.append(row)
            else:
                # Handle unexpected format
                row = {
                    "Input Company Name": input_company_name,
                    "Company Name": company_name,
                    "Location": str(loc),
                    "Count": "-",
                    "Time Stamp": timestamp,
                    "Redirected to URL": redirected_to_url,
                }
                if include_quantum:
                    row["Quantum Associated Members"] = membership_value
                else:
                    row["Associated Members"] = membership_value
                rows.append(row)

    df = pd.DataFrame(rows)

    # Ensure string-compatible columns are cast properly
    for col in df.select_dtypes(include=["number"]).columns:
        df[col] = df[col].astype("object")

    df.fillna("-", inplace=True)

    if os.path.isfile(output_file):
        existing_df = pd.read_csv(output_file)
        df = pd.concat([existing_df, df], ignore_index=True)

    df.to_csv(output_file, index=False)
    print(f"Where They Live data saved to {output_file}.")


def main():
    """
    Main function to process all LinkedIn workforce data.

    Expected Input JSONs in output/ directory:
    - about_data.json
    - what_they_do_data_with_quantum.json
    - what_they_do_data_without_quantum.json
    - where_they_live_with_quantum_data.json
    - where_they_live_without_quantum_data.json

    Generated Output CSVs:
    - about_data.csv
    - what_they_do_with_quantum.csv (LONG FORMAT)
    - what_they_do_without_quantum.csv (LONG FORMAT)
    - where_they_live_with_quantum.csv
    - where_they_live_without_quantum.csv
    """
    # Define file paths located in the shared output directory
    about_data_file = OUTPUT_DIR / "about_data.json"
    what_they_do_file_with_quantum = OUTPUT_DIR / "what_they_do_data_with_quantum.json"
    what_they_do_file_without_quantum = (
        OUTPUT_DIR / "what_they_do_data_without_quantum.json"
    )
    where_they_live_file_with_quantum = (
        OUTPUT_DIR / "where_they_live_with_quantum_data.json"
    )
    where_they_live_file_without_quantum = (
        OUTPUT_DIR / "where_they_live_without_quantum_data.json"
    )

    print("=" * 60)
    print("LinkedIn Quantum Workforce Data Processor")
    print("=" * 60)

    # Process 'About' data
    print("\n[1/5] Processing About data...")
    process_about_data(about_data_file, output_file="about_data.csv")

    # Process 'What They Do' data - QUANTUM (LONG FORMAT)
    print("\n[2/5] Processing What They Do (Quantum) - LONG FORMAT...")
    process_what_they_do_long_format(
        file_path=what_they_do_file_with_quantum,
        output_file="what_they_do_with_quantum.csv",
        is_quantum=True,
    )

    # Process 'What They Do' data - GENERAL (LONG FORMAT)
    print("\n[3/5] Processing What They Do (General) - LONG FORMAT...")
    process_what_they_do_long_format(
        file_path=what_they_do_file_without_quantum,
        output_file="what_they_do_without_quantum.csv",
        is_quantum=False,
    )

    # Process 'Where They Live' data - QUANTUM
    print("\n[4/5] Processing Where They Live (Quantum)...")
    process_where_they_live(
        file_path=where_they_live_file_with_quantum,
        output_file="where_they_live_with_quantum.csv",
        include_quantum=True,
    )

    # Process 'Where They Live' data - GENERAL
    print("\n[5/5] Processing Where They Live (General)...")
    process_where_they_live(
        file_path=where_they_live_file_without_quantum,
        output_file="where_they_live_without_quantum.csv",
        include_quantum=False,
    )

    print("\n" + "=" * 60)
    print("All data processing completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
