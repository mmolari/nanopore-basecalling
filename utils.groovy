
// Given the tsv file containing the run parameters, creates a dictionary whose keys are
// column names, and whose entries are columns
def createParamDictionary(parFile) {
    parDict = [:]
    parDict["parDir"] = parFile.getParent()
    parDict["parPrefix"] = parFile.getBaseName()

    firstLine = true
    parFile.eachLine { line ->
        if (firstLine) {
            columns = line.split("\t")
            firstLine = false
            for (c in columns) { parDict[c] = [] }
        }
        else {
            for (x in [columns, line.split("\t")].transpose()) {
                parDict[x[0]].add(x[1])
                }
        }
    }
    return parDict
}

// function to check that all items in a list are the same
def checkSame(list) {
    return !list.any { l -> l != list[0] }
}

// Performs sanity checks and formatting on the parameter dictionary
def formatParamDict(parDict) {
    newParDict = [:]
    newParDict["parDir"] = parDict["parDir"]
    newParDict["parPrefix"] = parDict["parPrefix"]

    // check that values are consistent
    keys = ["flow_cell_id", "flow_cell_type", "ligation_kit", "barcode_kits", "nanopore_data_root_dir"]
    for (k in keys) {
        if (!checkSame(parDict[k])) {
            throw new Exception("ERROR: not all values in column $k of file ${parDict.parPrefix}.tsv are the same")
        }
        else {newParDict[k] = parDict[k][0]}   
    }

    // make sure that barcode kits are separated by double quotation marks
    newParDict.barcode_kits = "\"" + newParDict.barcode_kits.replace("\"","") + "\""

    // list of valid barcodes
    newParDict["barcode_id"] = []
    for (x in parDict.barcode_id) {
        newParDict["barcode_id"].add(x as Integer)
    }


    // capture timestamp
    newParDict["timeNow"] = (new Date()).format("yyyy-MM-dd--HH-mm-ss")

    return newParDict
}
