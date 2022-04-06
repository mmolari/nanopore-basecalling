# nanopore-basecalling
Nextflow pipeline to perform live basecalling of nanopore reads on cpu/gpu on a cluster using SLURM.

## Setup

1. Have the nextflow command available in your path. This can be easily installed using [conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html)
    ```bash
    conda create --name nextflow -c bioconda python=3.9 nextflow
    conda activate nextflow
    ```
2. Download guppy binaries for gpu/cpu. These should be placed in `guppy`. By default they are

## Minimal Usage

```bash
nextflow run basecall.nf \
    -profile cluster \
    --input-dir test_dataset/input \
    --output-dir test_dataset/output \
    --parameters-file test_dataset/params.tsv
```

### Input

The input folder is specified with the parameter `--input-dir`.

### Output

### Log-file

- guppy version
- input/output folders
- copy of parameter table

### Optional: live stats

A csv file contanining live statistics on the basecalling can be produced by adding the option `--live-stats basecalling_stats.csv`.