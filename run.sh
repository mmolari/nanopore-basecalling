nextflow run basecall.nf \
    -profile cluster \
    --inputDir "$1/raw" \
    --outputDir "$1/basecalled" \
    --parameterFile "$1/params.tsv" \
    --setWatcher true \
    --gpu true \
    --liveStats true \
    -resume
