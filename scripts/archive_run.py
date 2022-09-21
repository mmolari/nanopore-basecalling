# This python script is used to archive a sequencing run.
# It performs the following operations

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


class logger:
    """Simple logger class to save the print result to file"""

    def __init__(self, verbose=False):
        self.s = "#######################\n"
        self.s += f"Time: {datetime.now()}\n"
        self.verbose = verbose

    def print(self, *args):
        msg = "  ".join([str(a) for a in args])
        if self.verbose:
            print(msg)
        self.s += str(msg) + "\n"

    def save(self, fname):
        self.s += "---------------------\n\n"
        with open(fname, "a") as f:
            f.write(self.s)
        self.s = ""


def iso_today():
    """Return the current date in format YYYY-MM-DD."""
    return datetime.now().strftime("%Y-%m-%d")


def parse_args():
    parser = argparse.ArgumentParser(
        description="""
    Script used to archive the results of basecalling in the experiment folder.
    It subdivides the reads in folders based on the experiment id, creating symlinks
    to the original files. It also creates (or updates) a sample_info.csv file
    containing the information on the samples stored in each folder.
    """,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--reads_fld",
        help="the source folder, containing the reads for the sequencing run. These are in fastq.gz format.",
        required=True,
        type=str,
    )
    parser.add_argument(
        "--param_file",
        help="the parameters.tsv file containing information on every sample.",
        required=True,
        type=str,
    )
    parser.add_argument(
        "--archive_fld",
        help="the destination archive folder, containing one subfolder per experiment.",
        default="/scicore/home/nccr-antiresist/GROUP/unibas/neher/experiments",
        type=str,
    )
    parser.add_argument(
        "--overwrite",
        help="Do not raise an error if one or more barcodes are already present and overwrite them.",
        default=False,
        action="store_true",
    )
    parser.add_argument(
        "--only_barcodes",
        help="Only process the specified barcodes. Space-separated list of numbers (e.g. --only_barcodes 1 2 44 )",
        nargs="*",
        type=int,
    )

    return parser.parse_args()


def extract_paths(args):
    """Extract input paths and check that files and folders exist"""
    src_fld = Path(args.reads_fld)
    par_file = Path(args.param_file)
    arc_fld = Path(args.archive_fld)

    assert src_fld.is_dir(), f"Error: source folder {src_fld} is not a directory"
    assert par_file.is_file(), f"Error: parameter file {par_file} does not exist"
    assert arc_fld.is_dir(), f"Error: archive folder {arc_fld} is not a directory"

    return src_fld, par_file, arc_fld


def in_selected_barcodes(bc, selected_bc):
    """Check whether the barcode is in the set of selected barcodes"""
    if selected_bc is None:
        return True
    else:
        return bool(bc in selected_bc)


def load_par_file(par_file, src_fld, only_barcodes):
    """Load the parameter tsv files and performs sanity checks on its contents.
    It checks that the file contains all of the expected fields, and that the
    desired barcodes are present in the source folder."""

    # load parameter file
    par = pd.read_csv(par_file, sep="\t")

    # expected columns
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
        if in_selected_barcodes(int(b), only_barcodes):
            bc_file = src_fld / f"barcode{int(b):02d}.fastq.gz"
            if not bc_file.is_file():
                assert False, f"missing expected file: {bc_file}"

    # return parameter file
    return par


def find_experiment_subdir(archive_dir, research_group, experiment_id):
    """finds or creates the experiment sub-directory in which to archive the results"""

    # ending of the directory name
    tag = f"_{research_group}_{experiment_id}"

    # find or create experiment directory
    exp_dirs = [
        sd for sd in archive_dir.iterdir() if sd.is_dir and sd.name.endswith(tag)
    ]
    if len(exp_dirs) > 0:
        exp_fld = exp_dirs[0]
    else:
        exp_fld = archive_dir / f"{iso_today()}{tag}"
        exp_fld.mkdir()

    return exp_fld


def check_destination_file(dest_file, overwrite, log):
    """Check if destination file is already present. If so optionally removes it."""
    if dest_file.is_file():
        if overwrite:
            log.print(f"WARNING: overwriting {dest_file} (file removed)")
            os.system(f"rm {dest_file.absolute()}")
        else:
            assert (
                False
            ), f"file {dest_file} is already present at destination. Specify --overwrite option?"


def check_destination_df(df, barcode, flowcell_id, overwrite, log):
    """Check that an entry for the corresponding barcode and flowcell_id is not already
    present in the sample df. If so raises an error, unless `overwrite` is specified."""
    if len(df) == 0:
        return df

    mask = (df["barcode_id"] == barcode) & (df["flow_cell_id"] == flowcell_id)
    if mask.sum() == 0:
        return df

    entry = f"barcode {barcode} - flowcell {flowcell_id}"
    log.print(
        f"WARNING, entry [{entry}] already present in sample info: (N={mask.sum()}). Removing."
    )
    log.print(df[mask].to_dict())

    if overwrite:
        return df[~mask]
    else:
        assert (
            False
        ), f"entry [{entry}] already present in sample dataframe. Specify --overwrite?"


if __name__ == "__main__":

    # logger
    log = logger(verbose=True)

    # extract arguments
    args = parse_args()

    log.print("executing archiving script with arguments:")
    for k, v in args.__dict__.items():
        log.print(f"{k:>18} : {v}")
    log.print("---")

    # extract input paths and check that files and folders exist
    src_fld, par_file, arc_fld = extract_paths(args)

    # load parameter files and perform integrity checks
    par = load_par_file(par_file, src_fld, args.only_barcodes)

    # for every row in the parameter file
    archived_barcodes_count = 0
    for idx, row in par.iterrows():

        # parse values for the entry
        barcode = int(row["barcode_id"])
        exp_id = row["experiment_id"]
        res_group = str(row["research_group"]).lower()
        sample_id = row["sample_id"]
        flowcell_id = row["flow_cell_id"]

        # skip unmentioned barcodes if --only_barcodes option is used
        if not in_selected_barcodes(barcode, args.only_barcodes):
            continue
        log.print(
            f" # archiving sample {sample_id} - barcode {barcode} - experiment {exp_id}"
        )

        # find existing experiment folder or create a new one
        exp_fld = find_experiment_subdir(arc_fld, res_group, exp_id)

        # subdirectory to store the samples
        samples_fld = exp_fld / "samples" / f"{sample_id}"
        if not samples_fld.is_dir():
            samples_fld.mkdir(parents=True)

        # names of source and destination files
        src_file = src_fld / f"barcode{int(barcode):02d}.fastq.gz"
        dest_file = (
            samples_fld / f"{sample_id}_{flowcell_id}_barcode{barcode:02d}.fastq.gz"
        )

        # load dataframe if already present, otherwise create it
        sample_info = exp_fld / "sample_info.csv"
        if not sample_info.is_file():
            experiment_df = pd.DataFrame()
        else:
            experiment_df = pd.read_csv(sample_info)

        # check that file does not already exist. Optionally remove it if overwrite is specified
        check_destination_file(dest_file, args.overwrite, log)

        # check that the entry is not already present in the dataframe.
        # optionally remove it if overwrite is specified
        df = check_destination_df(
            experiment_df, barcode, flowcell_id, args.overwrite, log
        )

        # create link and remove write permission on the source file
        os.system(f"ln -s {src_file.absolute()} {dest_file.absolute()}")
        os.system(f"chmod a-w {src_file.absolute()}")

        row_dict = row.to_dict()
        row_dict["original_fastq_file"] = str(src_file.absolute())
        row_dict["archive_date"] = f"{iso_today()}"
        add_df = pd.DataFrame(pd.Series(row_dict)).T
        new_df = pd.concat([df, add_df], ignore_index=True).sort_values("sample_id")

        # save dataframe
        new_df.to_csv(sample_info, index=False)

        archived_barcodes_count += 1

    # save log file
    log.print(f"---\ntot n. archived barcodes = {archived_barcodes_count}")
    assert archived_barcodes_count > 0, "no barcode archived."
    log_fname = arc_fld / "archive_log.txt"
    log.save(log_fname)
