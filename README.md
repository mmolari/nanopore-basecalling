# nanopore-basecalling
Nextflow pipeline to perform basecalling of nanopore reads on cpu/gpu on a cluster using SLURM.
Basecalling can be executed online while reads are uploaded to the input folder, in the form of fast5 files.

## Setup

1. Have [nextflow](https://www.nextflow.io/) (version > 21.10) available in your path. This can be easily installed using [conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html)
    ```bash
    conda create --name nextflow -c bioconda python=3.9.12 nextflow=21.10
    conda activate nextflow
    ```
2. Download guppy binaries for gpu/cpu. Symlinks to the binaries should be placed in `guppy_bin/guppy_basecaller_cpu` and `guppy_bin/guppy_basecaller_gpu`. Alternatively the location of the binaries can be specified with the flag `--guppyCpu` and `--guppyGpu` options.

> **Nb:** the pipeline has been developed using guppy version `6.3.7+532d626`. Compatibility with other versions is not guaranteed.

## Minimal Usage

Given an input directory containing `fast5` files and a desired output directory, the workflow will perform the basecalling of these files, and save the resulting reads in the output directory in format `barcodeXX.fastq.gz`, where `XX` indicates the number of the barcode used.

```bash
nextflow run basecall.nf \
    -profile cluster \
    --inputDir test_dataset/input \
    --outputDir test_dataset/output \
    --parameterFile test_dataset/params.tsv \
    --setWatcher true \
    --gpu true \
```

- the `-profile cluster` option is used to trigger SLURM execution, as opposed to local execution.
- the `--inputDir` option is used to specify the input directory, in which `fast5` files are stored.
- `--outputDir` indicates the output directory, in which reads are stored in `barcodeXX.fastq.gz` format.
- `--parameterFile` is used to specify the parameter file, from which some options for the basecalling are parsed. See below for the format of this file.
- if `--setWatcher true` is specified then new basecalling jobs are dispatched live as new `fast5` files get uploaded in the input directory. See below for details.
- if the option `--gpu true` is specified then basecalling is performed on gpu. Otherwise the cpu version of guppy is used.

## Parameter file and guppy parameters

The parameter file, passed with the `--parameterFile` option, must be a `tsv` file in which each row corresponds to a different barcode. The file can be generated from the template `nanopore_sequencing_params_template.ods`. The relevant columns are:

- `barcode_id` : the barcode number.
- `flow_cell_type` : the flowcell type, e.g., `FLO-MIN106`. This corresponds to the `--flowcell` option for guppy. It must be the same for all columns.
- `ligation_kit` : the ligation kit used, e.g. `SQK-LSK109`. This is passed to guppy as the `--kit` option. It must be the same for all columns.
- `barcode_kits` : list of barcode kits separated by spaces, e.g. `EXP-NBD114 EXP-NBD104`. This is passed to guppy as the `--barcode_kits` option. It must be the same for all columns. If can also be left empty, in which case the `--barcode_kits` argument is not passed to guppy.

Guppy is run with the `--trim_barcodes` flag, so that barcodes are removed from the reads.

## Upload Watcher

If `--setWatcher true` is specified, then the workflow instantiates a watcher that continually checks for uploads in the input folder. If a new `fast5` file is uploaded then a new basecalling job is dispatched.

In order to terminated the workflow and produce `fastq` files with the read, it is sufficient to create an empty file named `end-signal.fast5`. This stops the watcher and and after all basecalling jobs have been completed triggers the creation of the `fastq` files containing the reads.

## live basecalling stats

Unless `--liveStats false` is specified, the workflow will produce a `csv` file named `{params}_basecalling_stats.csv`, where `{params}` is the prefix of the parameters tsv file. This is placed in the same folder as the parameter file. This file is updated live as the basecalling proceeds, with each row corresponding to a single read. The file contains three columns: `len`,`barcode`,`time`. These contain the read length, the corresponding assigned barcode and the time in which it was basecalled.
This file can be used to estimate the length of reads and the barcode distribution, while the basecalling workflow is in progress. The script `scripts/basecall_stats_plots.py` can be used to produce plots to visualize read count and length distribution stratified by barcode. See `scripts/basecall_stats_plots.py --help` for usage.

## Log-file

Every time the workflow is launched a log file named `{params}_{time}.log` is created, where `{params}` is the prefix of the parameters tsv file and `{time}` is a timestamp in the form `yyyy-MM-dd--HH-mm-ss`. This files contains the following information: 

- execution time and id of the nextflow run
- remote and current commit of the repository containing this basecalling workflow.
- version of the guppy basecaller used, and whether the gpu version was used.
- path of the parameter file and relevant parameters (list of barcodes, flowcell id, flowcell type, ligation kit, barcode kits)
- input and output directories

## Other options

If `--filterBarcodes true` is specified, then only the `barcodeXX.fastq.gz` files corresponding to barcodes present in the parameter file are produced. Other barcodes (usually corresponding to mis-classfications) are excluded.

## Archive the run

After basecalling is complete, the script `scripts/archive_run.py` can be used to archive the reads in an experiment folder.
It requires `pandas` to be installed. This can simply be installed with `conda install -c conda-forge pandas`.
The script has the following usage:

```
usage: archive_run.py [-h] --reads_fld READS_FLD --param_file PARAM_FILE [--archive_fld ARCHIVE_FLD] [--overwrite] [--only_barcodes [ONLY_BARCODES ...]]

Script used to archive the results of basecalling in the experiment folder.
It subdivides the reads in folders based on the experiment id, creating symlinks
to the original files. It also creates (or updates) a sample_info.csv file
containing the information on the samples stored in each folder.

optional arguments:
  -h, --help            show this help message and exit
  --reads_fld READS_FLD
                        the source folder, containing the reads for the sequencing run. These are in fastq.gz format.
  --param_file PARAM_FILE
                        the parameters.tsv file containing information on every sample.
  --archive_fld ARCHIVE_FLD
                        the destination archive folder, containing one subfolder per experiment.
                        (default: /scicore/home/nccr-antiresist/GROUP/unibas/neher/experiments)
  --overwrite           Do not raise an error if one or more barcodes are already present and overwrite them.
                        (default: False)
  --only_barcodes [ONLY_BARCODES ...]
                        Only process the specified barcodes. Space-separated list of numbers (e.g. --only_barcodes 1 2 44 )
                        (default: None)
```

The mandatory arguments are:
- `reads_fld` is the folder containing the reads for every barcode, saved as `barcodeXX.fastq.gz`.
- `param_file` is the `.tsv` file containing info on the link between each barcode and the corresponding experimental conditions.
- `archive_fld` is the `experiments` archive folder. The script will take care of creating sub-folders with the name of the experiments, where link to the reads are stored. These are named as `<date>_<research_group>_<experiment_id>`, where the last two parts are extracted from the parameter file, and the date is the date of first archiviation.
The optional arguments are:
- if `--overwrite` is specified then barcodes that are already present in the experiment folders are removed and substituted.
- if `--only_barcodes 3 5 7` is specified then only samples corresponding to barcodes 3,5,7 are archived.

Upon successful completion the script also updates an `archive_log.txt` file in the `--archive_fld` directory, with a list of archived barcodes.

The generated folder structure looks like this:

```
experiments/
├── <date>_<research-group>_<experiment-id>
│   ├── sample_info.csv (dataframe with list of samples archived, one per file)
│   └── samples (folder with one sample per subfolder)
│       ├── <sample-id-1>
│       │   └── <sample-id-1>_<flowcell-id-1>_barcode<barcode-1>.fastq.gz ->  symlink to corresponding file
│       ...
│       └── <sample-id-n>
│           └── <sample-id-n>_<flowcell-id-n>_barcode<barcode-n>.fastq.gz ->  symlink to corresponding file
└── archive_log.txt
```