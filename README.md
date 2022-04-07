# nanopore-basecalling
Nextflow pipeline to perform live basecalling of nanopore reads on cpu/gpu on a cluster using SLURM.

## Setup

1. Have the nextflow command available in your path. This can be easily installed using [conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html)
    ```bash
    conda create --name nextflow -c bioconda python=3.9 nextflow
    conda activate nextflow
    ```
2. Download guppy binaries for gpu/cpu. Symlinks to the binaries should be placed in `guppy_bin/guppy_basecaller_cpu` and `guppy_bin/guppy_basecaller_gpu`. Alternatively the location of the binaries can be specified with the flag `--guppy_bin_cpu` and `--guppy_bin_gpu`.

## Minimal Usage

```bash
nextflow run basecall.nf \
    -profile cluster \
    --inputDir test_dataset/input \
    --outputDir test_dataset/output \
    --parameterFile test_dataset/params.tsv \
    --setWatcher true \
    --gpu true \
```

### Input

The input folder is specified with the parameter `--inputDir`.

### Output

### Parameter file

Information extracted from the file:
- flowcell-id

### Upload Watcher

### Log-file

- guppy version
- copy of parameter table
- input/output folders
- nextflow run id
- repo commit

### live basecalling stats

A csv file contanining live statistics on the basecalling can be produced by adding the option `--live-stats basecalling_stats.csv`.