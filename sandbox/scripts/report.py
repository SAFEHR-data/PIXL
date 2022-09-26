"""
Given an MRN and accession number, defining the patient and associated
x-ray study obtain the associated radiology report.
"""
import argparse

from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from core import QueryableDatabase, SQLQuery, _env_var


@dataclass
class RadiologyReport:
    """Dataclass for xray report unique to a patient and study"""

    mrn: str                # | Required identifiers
    accession_number: str   # |

    report_text: Optional[str] = None


def parse_args() -> argparse.Namespace:
    """Parse command line arguments and return a namespace"""

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-m',
        '--mrn',
        type=str,
        required=True,
        help="Patient identifier. aka. MRN, PatientID"
    )
    parser.add_argument(
        '-a',
        '--accession_number',
        type=str,
        required=True,
        help="Xray report identifier. aka AccessionNumber "
    )
    return parser.parse_args()


def main():

    args = parse_args()

    data = RadiologyReport(
        mrn=args.mrn,
        accession_number=args.accession_number
    )

    db = QueryableDatabase()
    query = SQLQuery(
        filepath=Path('../sql/mrn_accession_to_report.sql'),
        context={"schema_name": _env_var("EMAP_UDS_SCHEMA_NAME"),
                 "mrn": data.mrn,
                 "accession_number": data.accession_number
                 }
    )

    try:
        data.report_text = db.execute_or_raise(query, "Failed to get report")[0]
    except Exception as e:
        print(f"ERROR: {e}")

    print(vars(data))

    return None


if __name__ == '__main__':
    main()
