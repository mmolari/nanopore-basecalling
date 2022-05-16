# This python script is used to archive a sequencing run

# input folder
# - check that folders and files exist
# - load the parameter file

# destination folder:
# - check if experiment folder exists
# - if not, create folder name and folder

# preliminary checks:
# - check that files do not exist already in destination
# - check that all expected barcodes are present
# - check that the csv file with the info on all the files is present, otherwise create it.
# - check that files with the same sample name are not already present.

# move files:
# - link the barcode files, with the name assigned from the parameter file
# - update the info file with the information for all the files.
# - add the following information for each file: source folder full path.

import argparse
import pandas as pd
from pathlib import Path
from datetime import datetime
import os

# help functions


def iso_today():
    """Return the current date in format YYYY-MM-DD."""
    return datetime.now().strftime("%Y-%m-%d")


parser = argparse.ArgumentParser(
    description="""
Script used to archive the results of basecalling in the experiment folder.
It subdivides the reads in folders based on the experiment id, creating symlinks
to the original files. It also creates (or updates) a sample_info.csv file
containing the information on the samples stored in each folder.
"""
)

parser.add_argument(
    "--reads_fld",
    help="the source folder, containing the reads for the sequencing run. These are in fastq.gz format.",
    required=True,
)
parser.add_argument(
    "--param_file",
    help="the parameters.tsv file containing information on every sample.",
    required=True,
)
parser.add_argument(
    "--archive_fld",
    help="the destination archive folder, containing one subfolder per experiment.",
    required=True,
)
parser.add_argument(
    "--allow_missing_barcodes",
    help="Do not raise an error if one or more expected barcodes are missing.",
    type=bool,
    default=False,
)
parser.add_argument(
    "--skip_present_barcodes",
    help="Do not raise an error if one or more expected barcodes are already present in the destination folder.",
    type=bool,
    default=False,
)

# extract arguments
args = parser.parse_args()

# check that files and folders exist
src_fld = Path(args.reads_fld)
par_file = Path(args.param_file)
arc_fld = Path(args.archive_fld)

assert src_fld.is_dir(), f"Error: source folder {src_fld} is not a directory"
assert par_file.is_file(), f"Error: parameter file {par_file} does not exist"
assert arc_fld.is_dir(), f"Error: archive folder {arc_fld} is not a directory"

# load parameter file
par = pd.read_csv(par_file, sep="\t")

# check parameter file fields
par_fields = [
    "barcode_id",
    "experiment_id",
    "sample_id",
    "research_group",
    "requester",
    "species_taxid",
    "strain_id",
    "clinical_sample_id",
    "flow_cell_id",
    "flow_cell_type",
    "ligation_kit",
    "barcode_kits",
    "nanopore_data_root_dir",
]
assert set(par.columns) == set(
    par_fields
), "Error: discrepancy in expected fields for parameter file"

# check that expected barcode files are present
for b in par["barcode_id"]:
    bc_file = src_fld / f"barcode{int(b):02d}.fastq.gz"
    if not bc_file.is_file():
        if args.allow_missing_barcodes:
            print("WARNING: expected file {bc_file} missing.")
        else:
            assert False, f"missing expected file: {bc_file}"


for idx, row in par.iterrows():

    # parse values
    barcode = row["barcode_id"]
    exp_id = row["experiment_id"]
    res_group = row["research_group"]
    sample_id = row["sample_id"]

    # ending of the directory name
    tag = f"_{res_group}_{exp_id}"

    # find or create experiment directory
    exp_dirs = [sd for sd in arc_fld.iterdir() if sd.is_dir and sd.name.endswith(tag)]
    if len(exp_dirs) > 0:
        exp_fld = exp_dirs[0]
    else:
        exp_fld = arc_fld / f"{iso_today()}{tag}"
        exp_fld.mkdir()

    print(f"archiving barcode {barcode} in folder {exp_fld}")

    # subdirectory to store the samples
    samples_fld = exp_fld / "samples"
    if not samples_fld.is_dir():
        samples_fld.mkdir()

    # source and destination files
    src_file = src_fld / f"barcode{int(barcode):02d}.fastq.gz"
    dest_file = samples_fld / f"{sample_id}.fastq.gz"

    # check that file does not already exist. If so create a link
    if dest_file.is_file():
        if args.skip_present_barcodes:
            print(f"WARNING: skipping linking of already present file: {dest_file}")
        else:
            assert False, f"file {dest_file} is already present at destination"
    else:
        os.system(f"ln -s {src_file.absolute()} {dest_file.absolute()}")
        # remove write permission on the source file
        os.system(f"chmod a-w {src_file.absolute()}")

    # load dataframe if already present, otherwise create it
    sample_info = exp_fld / "sample_info.csv"
    if not sample_info.is_file():
        df = pd.DataFrame()
    else:
        df = pd.read_csv(sample_info)

    # check that the sample id is not already present.
    if df.size > 0:
        if sample_id in df["sample_id"]:
            if args.skip_present_barcodes:
                print(
                    f"WARNING: sample {sample_id} is already registered in {sample_info}"
                )
            else:
                assert (
                    False
                ), f"Error: sample {sample_id} is already registered in {sample_info}"

    # add the corresponding line, together with information on the source
    row_dict = row.to_dict()
    row_dict["original_fastq_file"] = str(src_file.absolute())
    add_df = pd.DataFrame(pd.Series(row_dict)).T
    new_df = pd.concat([df, add_df], ignore_index=True).sort_values("sample_id")

    # save dataframe
    new_df.to_csv(sample_info, index=False)
