import zenodo_get
import pandas as pd
import re
import gzip
import argparse


#extract taxonomic ids according to categories file
def extr(catg, fx2):
    res2 = None  # Initialize the result variable
    for i in range(len(catg)):  # Loop over rows in `catg`
        #print(catg.iloc[i, :])  # Print the current category
        # Perform regex search on the first column of `fx2`
        pattern = rf"{catg.iloc[i, 0]}[A-Z0-9]+"
        matches = [re.findall(pattern, str(val)) for val in fx2.iloc[:, 0]]
        # Extract unique matches
        #cols = pd.unique([item for sublist in matches for item in sublist]) #gives future warning
        cols = list(set(item for sublist in matches for item in sublist))
        res1 = pd.DataFrame({catg.iloc[i, 0]: [match[0] if match else None for match in matches]})
        # Remove the category prefix from the matched strings
        res1[catg.iloc[i, 0]] = res1[catg.iloc[i, 0]].str.replace(catg.iloc[i, 0], "", regex=False)
        # Combine the result with previous results
        res2 = pd.concat([res2, res1], axis=1) if res2 is not None else res1
    return res2


#try catch to see if the number of rows are not equal
def tryCatch(x1,x2,errorX):
    try:
        if x1 != x2:
            raise ValueError("lengths don't match", errorX)
        print("All good for ", errorX)
    except ValueError as e:
        print("Exception occurred:", e)
        raise  # Re-raise the exception to stop execution


# extract and write new interactions file for triple generation
def generateIds(categories,intxnFile,outputFile,cs=100000):
    dfCatg = pd.read_csv(categories, sep = "\t")
    i = 1
    for chunk in pd.read_csv(intxnFile, compression="gzip", sep="\t", dtype=str,  quoting=3, chunksize=cs):


        print("Processing chunk ",i)
        #print("NOW dfglobi-shape", chunk.shape)
        chunk = chunk[(chunk['sourceTaxonId'] != "no:match") & (chunk['targetTaxonId'] != "no:match")] # Remove if both source and target taxon main Ids are no:match
        chunk = chunk[(chunk['sourceTaxonId'] != "no:match") & (chunk['sourceTaxonName'] != "no name")] # Remove if sourceTaxonId and sourceTaxonName are null
        chunk = chunk[(chunk['targetTaxonId'] != "no:match") & (chunk['targetTaxonName'] != "no name")] # Remove if both sourceTaxonId and sourceTaxonName are null
        #print("THEN dfglobi-shape", chunk.shape)
        dfGlobi = chunk.reset_index(drop=True)

        dfSource = extr(dfCatg,pd.DataFrame(dfGlobi['sourceTaxonIds']))
#        dfSource.columns = ["source_COL", "source_ENVO", "source_EOL", "source_FB", "source_FBC", "source_GBIF", "source_IF", "source_IRMNG", "source_ITIS", "source_NBN", "source_NCBI", "source_PBDB", "source_SLB", "source_SPECCODE", "source_TAXON", "source_W", "source_WD", "source_WORMS"]
        dfSource.columns = ["source_WD"]   
        tryCatch(len(dfGlobi),len(dfSource),"Source")
        #print("SOURCE")
        #print(dfSource)
    
        dfTarget = extr(dfCatg,pd.DataFrame(dfGlobi['targetTaxonIds']))
        #dfTarget.columns = ["target_COL", "target_ENVO", "target_EOL", "target_FB", "target_FBC", "target_GBIF", "target_IF", "target_IRMNG", "target_ITIS", "target_NBN", "target_NCBI", "target_PBDB", "target_SLB", "target_SPECCODE", "target_TAXON", "target_W", "target_WD", "target_WORMS"]
        dfTarget.columns = ["target_WD"]
        tryCatch(len(dfGlobi),len(dfTarget),"Target")
        #print("TARGET")
        #print(dfTarget)


        dfAll = pd.concat([dfSource, dfTarget], axis=1)
        colsNames = ["sourceTaxonId","sourceTaxonName","sourceLifeStageId","sourceLifeStageName","sourceBodyPartId",
        "sourceBodyPartName","sourcePhysiologicalStateId","sourcePhysiologicalStateName","sourceSexId", "sourceTaxonPhylumName", "sourceTaxonKingdomName",
        "sourceSexName","interactionTypeName","interactionTypeId","targetTaxonId",
        "targetTaxonName","targetLifeStageId","targetLifeStageName","targetBodyPartId","targetBodyPartName",
        "targetPhysiologicalStateId","targetPhysiologicalStateName","targetSexId","targetSexName", "targetTaxonPhylumName", "targetTaxonKingdomName",
        "decimalLatitude","decimalLongitude","localityId","localityName",
        "eventDate","referenceCitation","referenceDoi","referenceUrl",
        "sourceCitation","sourceNamespace","sourceArchiveURI","sourceDOI"]
        tryCatch(len(dfGlobi),len(dfAll),"All")
        #print("ALL")
        #print(dfAll)

        # Subset to keep only the selected columns
        dfGlobi = dfGlobi[colsNames]
    
        # Concatenate fN and fNFinal_res column-wise
        dfFinal = pd.concat([dfGlobi, dfAll], axis=1)
        #print("FINAL")
        #print(dfFinal)
        with gzip.open(outputFile, "at", encoding="utf-8") as out_file:  # Append mode
            if i == 1:
                out_file.write(dfFinal.to_csv(index=False, sep='\t'))
            else:
                out_file.write(dfFinal.to_csv(index=False, sep='\t', header=False))

        del dfGlobi, dfAll, dfSource, dfTarget
        i = i + 1


# Main execution
if __name__ == "__main__":
    
    #zenodo_get.zenodo_get(['-g', 'interactions.tsv.gz','https://doi.org/10.5281/zenodo.3950589']) #download GloBI interactions.tsv.gz if not downloaded already
    # Create the argument parser
    parser = argparse.ArgumentParser()

    # Add arguments
    parser.add_argument('inputFile', type=str, help="Enter the GloBI gzip file")
    parser.add_argument('catgFile', type=str, help="Enter the categories file")
    parser.add_argument('outputFile', type=str, help="Enter the output file name")

    # Parse the arguments
    args = parser.parse_args()
    intxnFile = args.inputFile
    categories = args.catgFile
    outputFile = args.outputFile
    chunksize = 1000000
    #chunksize = 5
    generateIds(categories,intxnFile,outputFile,chunksize)

