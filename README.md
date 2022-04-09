# nanopore-basecalling
Nextflow pipeline to perform basecalling of nanopore reads on cpu/gpu on a cluster using SLURM.
Basecalling can be executed online while reads are uploaded to the input folder, in the form of fast5 files.

## Setup

1. Have [nextflow](https://www.nextflow.io/) available in your path. This can be easily installed using [conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html)
    ```bash
    conda create --name nextflow -c bioconda python=3.9 nextflow
    conda activate nextflow
    ```
2. Download guppy binaries for gpu/cpu. Symlinks to the binaries should be placed in `guppy_bin/guppy_basecaller_cpu` and `guppy_bin/guppy_basecaller_gpu`. Alternatively the location of the binaries can be specified with the flag `--guppyCpu` and `--guppyGpu` options.

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
- `barcode_kits` : list of barcode kits separated by spaces, e.g. `EXP-NBD114 EXP-NBD104`. This is passed to guppy as the `--barcode_kits` option. It must be the same for all columns.

Guppy is run with the `--trim_barcodes` flag, so that barcodes are removed from the reads.

## Upload Watcher

If `--setWatcher true` is specified, then the workflow instantiates a watcher that continually checks for uploads in the input folder. If a new `fast5` file is uploaded then a new basecalling job is dispatched.

In order to terminated the workflow and produce `fastq` files with the read, it is sufficient to create an empty file named `end-signal.fast5`. This stops the watcher and and after all basecalling jobs have been completed triggers the creation of the `fastq` files containing the reads.

## live basecalling stats

Unless `--liveStats false` is specified, the workflow will produce a `csv` file named `{params}_basecalling_stats.csv`, where `{params}` is the prefix of the parameters tsv file. This is placed in the same folder as the parameter file. This file is updated live as the basecalling proceeds, with each row corresponding to a single read. The file contains three columns: `len`,`barcode`,`time`. These contain the read length, the corresponding assigned barcode and the time in which it was basecalled.
This file can be used to estimate the length of reads and the barcode distribution, while the basecalling workflow is in progress.

## Log-file

Every time the workflow is launched a log file named `{params}_{time}.log` is created, where `{params}` is the prefix of the parameters tsv file and `{time}` is a timestamp in the form `yyyy-MM-dd--HH-mm-ss`. This files contains the following information: 

- execution time and id of the nextflow run
- remote and current commit of the repository containing this basecalling workflow.
- version of the guppy basecaller used, and whether the gpu version was used.
- path of the parameter file and relevant parameters (list of barcodes, flowcell id, flowcell type, ligation kit, barcode kits)
- input and output directories

## Other options

If `--filterBarcodes true` is specified, then only the `barcodeXX.fastq.gz` files corresponding to barcodes present in the parameter file are produced. Other barcodes (usually corresponding to mis-classfications) are excluded.