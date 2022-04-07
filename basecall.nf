#!/usr/bin/env nextflow

// import utility functions
GroovyShell shell = new GroovyShell()
def utils = shell.parse(new File("utils.groovy"))

// --------- workflow parameters --------- 


// watch for incoming files
params.set_watcher = false

// defines directories for input data and to output basecalled data
params.inputDir = "$projectDir/test_dataset/input"
params.outputDir ="$projectDir/test_dataset/output"
inputDir = file(params.inputDir, checkIfExists: true, type: "dir")
outputDir = file(params.outputDir)

// parameters file
params.parameterFile = "$projectDir/test_dataset/params_1.tsv"

// get a csv file with number of reads per barcode and time
// that gets updated live while basecalling is in process
params.liveStats = true

// whether to use gpu
params.gpu = false

// path of guppy binaries (cpu or gpu)
params.guppyCpu = "$projectDir/guppy_bin/guppy_basecaller_cpu"
params.guppyGpu = "$projectDir/guppy_bin/guppy_basecaller_gpu"
guppy_bin = params.gpu ? params.guppyGpu : params.guppyCpu

// --------- parse parameters from file --------- 

parFile = file(params.parameterFile, checkIfExists: true)
parDict = utils.createParamDictionary(parFile)
parDict = utils.formatParamDict(parDict)

// --------- produce log file ---------

log_filename = "${parDict.parDir}/${parDict.parPrefix}_${parDict.timeNow}.log"


// --------- workflow --------- 

// channel for already loaded fast5 files
fast5_loaded = Channel.fromPath("${params.inputDir}/*.fast5")

// watcher channel for incoming `.fast5` files.
// Terminates when `end-signal.fast5` file is created.
if ( params.set_watcher ) {
    fast5_watcher = Channel.watchPath("${params.inputDir}/*.fast5")
                            .until { it.name ==~ /end-signal.fast5/ }
}
else { fast5_watcher = Channel.empty() }


// combine the two fast5 channels
fast5_ch = fast5_loaded.concat(fast5_watcher)

// Process that for any input fast5 file uses guppy
// to perform basecalling and barcoding. The output
// channel collects a list of files in the form
// .../(barcodeXX|unclassified)/filename.fastq.gz
add_device = params.gpu ? '--device auto' : ''
process basecall {

    label params.gpu ? 'gpu_q30m' : 'q6h'

    input:
        path fast5_file from fast5_ch

    output:
        path "**/fastq_pass/*/*.fastq.gz" optional true into fastq_ch


    script:
        """
        $guppy_bin \
            -i . \
            -s . \
            --barcode_kits ${parDict.barcode_kits} \
            --flowcell ${parDict.flow_cell_type} \
            --kit ${parDict.ligation_kit} \
            --compress_fastq \
            --disable_pings \
            --nested_output_folder \
            --trim_barcodes \
            ${add_device}
        """

}

// Group results by barcode using the name of the parent
// folder in which files are stored (created by guppy)
fastq_barcode_ch = fastq_ch.flatten()
                    .tap { fastq_tap_ch }
                    .map { x -> [x.getParent().getName(), x] }
                    .groupTuple()

// This process takes as input a tuple composed of a barcode
// and a list of fastq.gz files corresponding to that barcode.
// It decompresses and concatenates these files, returning
// a unique compressed filename that is named `barcodeXX.fastq.gz`,
// where `XX` is the barcode number
process concatenate_and_compress {

    label 'q6h'

    publishDir outputDir, mode: 'move'

    input:
        tuple val(barcode), file('reads_*.fastq.gz') from fastq_barcode_ch

    output:
        file "${barcode}.fastq.gz"

    script:
    """
    # decompress with gzip, concatenate and compress with gz
    gzip -dc reads_*.fastq.gz | gzip -c > ${barcode}.fastq.gz
    """
}

// if liveStats is set to true, create a file to contain the stats
bcstats_filename = "${parDict.parPrefix}_basecalling_stats.csv"
if (params.liveStats) {
    // create csv stats file and write header
    bc_stats_file = file("${parDict.parDir}/$bcstats_filename")
    bc_stats_file.text = 'len,barcode,time\n'
}

// Create the input channel for the stat as a mix of a channel with a single file
// and the feedback channel
bc_stats_init = Channel.fromPath("${parDict.parDir}/$bcstats_filename")
feedback_ch = Channel.create()
bc_stats_in = bc_stats_init.mix( feedback_ch )

// creates a csv file with read length, barcode and timestamp
// content of the file get appended to the file "bc_stats.csv"
// The feedback loop avoids that multiple threads try to append
// text on the same file.
process basecalling_live_report {

    label 'q30m'

    publishDir parDict.parDir, mode: 'copy'

    input:
        file('reads_*.fastq.gz') from fastq_tap_ch.collate(50)
        file(bcstats_filename) from bc_stats_in

    output:
        file(bcstats_filename) into feedback_ch

    when:
        params.liveStats

    script:
        """
        gzip -dc reads_*.fastq.gz > reads.fastq
        python3 $projectDir/scripts/basecall_stats.py reads.fastq
        tail -n +2 basecalling_stats.csv >> $bcstats_filename
        rm reads.fastq
        """
}