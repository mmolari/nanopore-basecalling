nextflow run basecall.nf -profile cluster \
--inputDir /scicore/home/nccr-antiresist/GROUP/unibas/neher/nanopore_runs/2022-01-17_FAK00761_7813b240/raw \
--outputDir /scicore/home/nccr-antiresist/GROUP/unibas/neher/nanopore_runs/2022-01-17_FAK00761_7813b240/basecalled \
--parameterFile /scicore/home/nccr-antiresist/GROUP/unibas/neher/nanopore_runs/2022-01-17_FAK00761_7813b240/params_1.tsv \
--setWatcher false \
--gpu true \
--filterBarcodes true
