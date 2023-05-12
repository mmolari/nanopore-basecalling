#!/usr/bin/env nextflow

// import utility functions
GroovyShell shell = new GroovyShell()
def utils = shell.parse(new File("utils.groovy"))

// --------- workflow parameters --------- 


// watch for incoming files
params.setWatcher = false

// defines directories for input data and to output basecalled data
params.inputDir = "$projectDir/test_dataset/raw"
params.outputDir ="$projectDir/test_dataset/basecalled"
inputDir = file(params.inputDir, checkIfExists: true, type: "dir")
outputDir = file(params.outputDir)

// parameters file
params.parameterFile = "$projectDir/test_dataset/params.tsv"

// get a csv file with number of reads per barcode and time
// that gets updated live while basecalling is in process
params.liveStats = true

// whether to use gpu
params.gpu = false

// path of guppy binaries (cpu or gpu)
params.guppyCpu = "$projectDir/guppy_bin/guppy_basecaller_cpu"
params.guppyGpu = "$projectDir/guppy_bin/guppy_basecaller_gpu"
guppy_bin = params.gpu ? params.guppyGpu : params.guppyCpu

// keep only selected barcodes
params.filterBarcodes = false

// --------- parse parameters from file --------- 

parFile = file(params.parameterFile, checkIfExists: true)
parDict = utils.createParamDictionary(parFile)
parDict = utils.formatParamDict(parDict)

// --------- produce log file ---------

log_filename = "${parDict.parPrefix}_${parDict.timeNow}.log"

log_text = """
Log-file for the basecalling executed by the nextflow basecall.nf script.
Execution time     : ${parDict.timeNow}
Nextflow run label : ${workflow.runName}

------- CODE -------
The code is stored in the repository : REPOREMOTE
The current commit is                : COMMITID

------- GUPPY -------
guppy version : GUPPYVER
gpu execution : ${params.gpu}

------- BASECALLING PARAMETERS -------
parameter file : ${parFile}
barcodes       : ${parDict.barcode_id}
flowcell id    : ${parDict.flow_cell_id}
flowcell type  : ${parDict.flow_cell_type}
kit            : ${parDict.ligation_kit}
guppy config   : ${parDict.guppy_config_file}
barcode kits   : ${parDict.barcode_kits}
nanopore data root dir : ${parDict.nanopore_data_root_dir}

------- INPUT / OUTPUT DIRECTORIES -------
input dir  : ${inputDir}
output dir : ${outputDir}
"""

// Process that generates the log file. If the gpu version of GUPPY is
// used then the process must be executed in the same environment in which
// GUPPY runs (gpu cluster), otherwise the command to retreive the version fails.
process generate_log_file {
    
    label params.gpu ? 'gpu_q30m' : 'q6h'

    publishDir "${parDict.parDir}", mode: 'copy'

    output:
        path "$log_filename"

    script:
        """
        echo "$log_text" > $log_filename
        REMOTE=\$(git remote -v | head -n 1)
        COMM=\$(git rev-parse HEAD)
        GUPPY=\$($guppy_bin -v | head -n 1)
        sed -i "s|REPOREMOTE|\$REMOTE|g" $log_filename
        sed -i "s|COMMITID|\$COMM|g" $log_filename
        sed -i "s|GUPPYVER|\$GUPPY|g" $log_filename
        """
}


// --------- workflow --------- 

// channel for already loaded fast5 files
fast5_loaded = Channel.fromPath("${params.inputDir}/*.fast5")

// watcher channel for incoming `.fast5` files.
// Terminates when `end-signal.fast5` file is created.
if ( params.setWatcher ) {
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
add_barcode_kits = parDict.barcode_kits == '""' ? '--detect_barcodes' : '--barcode_kits ' + parDict.barcode_kits
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
            -c ${parDict.guppy_config_file} \
            --compress_fastq \
            --disable_pings \
            --nested_output_folder \
            ${add_barcode_kits} \
            ${add_device}
        """

}

// Group results by barcode using the name of the parent
// folder in which files are stored (created by guppy)
// Optionally filter out barcodes that are not present in the 
// barcode list.
fastq_barcode_ch = fastq_ch.flatten()
                    .tap { fastq_tap_ch }
                    .map { x -> [x.getParent().getName(), x] }
                    .groupTuple()
                    .filter({ bc, files -> 
                    if (!params.filterBarcodes) {return true}; 
                    y = bc.replaceAll("[^0-9.]", "");
                    return (y.length() > 0) && (parDict.barcode_id.contains(y as Integer))
                    })

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
    chmod 444 ${barcode}.fastq.gz
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
bc_stats_in = params.liveStats ? bc_stats_init.mix( feedback_ch ) : Channel.empty()
bc_files_in = params.liveStats ? fastq_tap_ch.collate(50) : Channel.empty()

// creates a csv file with read length, barcode and timestamp
// content of the file get appended to the file with suffix
// "basecalling_stats.csv".
// The feedback loop avoids that multiple threads try to append
// text on the same file.
process basecalling_live_report {

    label 'q30m'

    publishDir parDict.parDir, mode: 'copy'

    input:
        file('reads_*.fastq.gz') from bc_files_in
        file("$bcstats_filename") from bc_stats_in

    output:
        file("$bcstats_filename") into feedback_ch

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