import json
import re
import pandas as pd
import os
import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def dynamic_save_to_csv(
    data,
    filename,
    company_name,
    input_company_name,
    membership_column,
    membership_value,
    timestamp,
    redirected_to_URL,
    fill_value="-*",
):
    """
    Save 'What They Do' data to a CSV file dynamically handling role-based columns.
    """
    # Load existing CSV or create a new DataFrame if the file does not exist
    if os.path.isfile(filename):
        df = pd.read_csv(filename)
    else:
        df = pd.DataFrame(
            columns=[
                "Input Company Name",
                "Company Name",
                membership_column,
                "Time Stamp",
                "Redirected to URL",
            ]
        )

    # Prepare new row of data
    new_data = {
        "Input Company Name": input_company_name,
        "Company Name": company_name,
        membership_column: membership_value,
        "Time Stamp": timestamp,
        "Redirected to URL": redirected_to_URL,
    }

    # Add roles dynamically
    for role_entry in data:
        role_name = (
            role_entry.get("Role", "Unknown Role")
            if isinstance(role_entry, dict)
            else str(role_entry)
        )
        count = (
            role_entry.get("Count", fill_value)
            if isinstance(role_entry, dict)
            else fill_value
        )
        new_data[role_name] = count

    # Create a new DataFrame from the new data
    new_row_df = pd.DataFrame([new_data])

    # Combine and save
    df = pd.concat([df, new_row_df], ignore_index=True)

    # Ensure string-compatible columns are cast properly
    for col in df.select_dtypes(include=["number"]).columns:
        df[col] = df[col].astype("object")

    # Fill missing values
    df.fillna(fill_value, inplace=True)
    df.to_csv(filename, index=False)


def process_what_they_do(file_path, output_file, membership_column):
    """
    Process a JSON file for 'What They Do' data and save it to a CSV dynamically.
    """
    if not os.path.isfile(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, "r") as json_file:
        data = json.load(json_file)

    for entry in data:
        company_name = entry.get("Company Name", "-*")
        membership_value = entry.get(membership_column, "-*")
        roles = entry.get("Roles", [])
        timestamp = entry.get("Time Stamp", datetime.datetime.now().isoformat())
        redirected_to_URL = entry.get("Redirected to URL", "-*")
        input_company_name = entry.get("input_company_name", "-*")
        dynamic_save_to_csv(
            data=roles,
            filename=output_file,
            company_name=company_name,
            input_company_name=input_company_name,
            membership_column=membership_column,
            membership_value=membership_value,
            timestamp=timestamp,
            redirected_to_URL=redirected_to_URL,
        )


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
            re.sub(r"[^\d]", "", about_data.get("No. of associated members", ""))
            or "-*"
        )
        company_size = re.sub(r"[^\d\-]", "", about_data.get("Company size", "-*"))
        company_size = f"'{company_size}" if company_size != "-*" else company_size
        linkedin_url = about_data.get("LinkedIn URL", "-*").split("?")[0]

        rows.append(
            {
                "Input Company Name": about_data.get("input_company_name", "-*"),
                "Company Name": about_data.get("Company Name", "-*"),
                "Associated Members": associated_members,
                "Website": about_data.get("Website", "-*"),
                "Industry": about_data.get("Industry", "-*"),
                "Company Size": company_size,
                "Headquarters": about_data.get("Headquarters", "-*"),
                "Founded": about_data.get("Founded", "-*"),
                "Specialties": about_data.get("Specialties", "-*"),
                "LinkedIn URL": linkedin_url,
                "Time Stamp": about_data.get(
                    "Time Stamp", datetime.datetime.now().isoformat()
                ),
                "Redirected to URL": about_data.get("Redirected to URL", "-*"),
            }
        )

    df = pd.DataFrame(rows)

    # Ensure string-compatible columns are cast properly
    for col in df.select_dtypes(include=["number"]).columns:
        df[col] = df[col].astype("object")

    df.fillna("-*", inplace=True)

    if os.path.isfile(output_file):
        existing_df = pd.read_csv(output_file)
        df = pd.concat([existing_df, df], ignore_index=True)

    df.to_csv(output_file, index=False)
    print(f"About data saved to {output_file}.")


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
        locations = entry.get("Locations", [])
        for loc in locations:
            if isinstance(loc, dict):
                row = {
                    "Input Company Name": entry.get("input_company_name", "-*"),
                    "Company Name": entry.get("Company Name", "-*"),
                    "Location": loc.get("Location", "-*"),
                    "Count": loc.get("Count", "-*"),
                    "Time Stamp": entry.get(
                        "Time Stamp", datetime.datetime.now().isoformat()
                    ),
                    "Redirected to URL": entry.get("Redirected to URL", "-*"),
                }
                if include_quantum:
                    row["Quantum Associated Members"] = entry.get(
                        "Quantum Associated Members", "-*"
                    )
                else:
                    row["Associated Members"] = entry.get("Associated Members", "-*")
                rows.append(row)
            else:
                # Handle unexpected format
                rows.append(
                    {
                        "Input Company Name": entry.get("input_company_name", "-*"),
                        "Company Name": entry.get("Company Name", "-*"),
                        "Location": str(loc),
                        "Count": "-*",
                        "Time Stamp": entry.get(
                            "Time Stamp", datetime.datetime.now().isoformat()
                        ),
                        "Redirected to URL": entry.get("Redirected to URL", "-*"),
                    }
                )

    df = pd.DataFrame(rows)

    # Ensure string-compatible columns are cast properly
    for col in df.select_dtypes(include=["number"]).columns:
        df[col] = df[col].astype("object")

    df.fillna("-*", inplace=True)

    if os.path.isfile(output_file):
        existing_df = pd.read_csv(output_file)
        df = pd.concat([existing_df, df], ignore_index=True)

    df.to_csv(output_file, index=False)
    print(f"Where They Live data saved to {output_file}.")


def main():
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

    # Process files
    # Process 'About' data
    process_about_data(about_data_file, output_file="about_data.csv")

    process_what_they_do(
        file_path=what_they_do_file_with_quantum,
        output_file="what_they_do_with_quantum.csv",
        membership_column="Quantum Associated Members",
    )
    process_what_they_do(
        file_path=what_they_do_file_without_quantum,
        output_file="what_they_do_without_quantum.csv",
        membership_column="Associated Members",
    )
    process_where_they_live(
        file_path=where_they_live_file_with_quantum,
        output_file="where_they_live_with_quantum.csv",
        include_quantum=True,
    )

    process_where_they_live(
        file_path=where_they_live_file_without_quantum,
        output_file="where_they_live_without_quantum.csv",
        include_quantum=False,
    )

    print("All data processing completed.")


if __name__ == "__main__":
    main()