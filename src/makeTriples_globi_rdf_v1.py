'''
    File name: makeTriples_interactions_rdf_v1.py
    Author: Disha Tandon
    Date created: 12/11/2024
    Python Version: 3
'''


import pandas as pd
import rdflib
from rdflib import URIRef, Literal, Namespace, RDF, RDFS, XSD, DCTERMS, Graph, BNode
import gzip
import argparse
import configparser
import sys
import re
import os

sys.path.append('./functions')  # Add the 'src' directory to the sys.path
import data_processing as dp
import matchNamesBiologicalGender as mbg

rdflib.plugin.register('turtle_custom', rdflib.plugin.Serializer, 'turtle_custom.serializer', 'TurtleSerializerCustom')

# First set : Namespace declarations universal
emi = Namespace("https://purl.org/emi#")
emiBox = Namespace("https://purl.org/emi/abox#")
emiGender = Namespace("https://purl.org/emi/biological-sex#")
sosa = Namespace("http://www.w3.org/ns/sosa/")
dcterms = Namespace("http://purl.org/dc/terms/")
wd = Namespace("http://www.wikidata.org/entity/")
prov = Namespace("http://www.w3.org/ns/prov#")
wgs84 = Namespace("http://www.w3.org/2003/01/geo/wgs84_pos#")
qudt = Namespace("http://qudt.org/schema/qudt/")
nTemp = Namespace("http://example.com/base-ns#")

# Second set : Namespaces for body part (anatomical entity) and life stage (developmental) names
aeo = Namespace("http://purl.obolibrary.org/obo/AEO_")
chebi = Namespace("http://purl.obolibrary.org/obo/CHEBI_")
clyh = Namespace("http://purl.obolibrary.org/obo/CLYH_")
envo = Namespace("http://purl.obolibrary.org/obo/ENVO_")
fao = Namespace("http://purl.obolibrary.org/obo/FAO_")
fbdv = Namespace("http://purl.obolibrary.org/obo/FBdv_")
hao = Namespace("http://purl.obolibrary.org/obo/HAO_")
ncit = Namespace("http://purl.obolibrary.org/obo/NCIT_")
omit = Namespace("http://purl.obolibrary.org/obo/OMIT_")
pato = Namespace("http://purl.obolibrary.org/obo/PATO_")
po = Namespace("http://purl.obolibrary.org/obo/PO_")
poro = Namespace("http://purl.obolibrary.org/obo/PORO_")
ro = Namespace("http://purl.obolibrary.org/obo/RO_")
uberon = Namespace("http://purl.obolibrary.org/obo/UBERON_")


# Mapping prefixes to namespaces only for the second set
prefix_to_namespace = {
    "AEO:" : aeo,
    "CHEBI:" : chebi,
    "CLYH:" : clyh,
    "ENVO:" : envo,
    "FAO:" : fao,
    "FBdv:" : fbdv,
    "HAO:" : hao,
    "NCIT:" : ncit,
    "OMIT:" : omit,
    "PATO:" : pato,
    "PORO:" : poro,
    "RO:" : ro,
    "UBERON:" : uberon,
    "PO:" : po,
    "QUDT:" : qudt
}

    

# Function for adding ambiguous entities to the graph
def add_entity_to_graph(fileName,keyCol,valCol1,valCol2,entity,entityID,subject,predicate,rdftype,ns,graph):
    eNamesDict = dp.create_dict_from_csv(fileName, keyCol, valCol1)
    eURIDict = dp.create_dict_from_csv(fileName, keyCol, valCol2)
    if dp.is_none_na_or_empty(entityID):
        if any(entityID.startswith(prefix) for prefix in prefix_to_namespace): #handle prefixed identifiers like 'UBERON:'
            for prefix, namespace in prefix_to_namespace.items():
                if entityID.startswith(prefix):
                    entity_Id = entityID[len(prefix):]
                    entityURI = namespace[entity_Id]
                    graph.add((subject,predicate,entityURI))
                    graph.add((entityURI, RDF.type, rdftype))
                    graph.add((entityURI, RDFS.label, Literal(entity, datatype=XSD.string)))
                    break
        elif entityID.startswith("http"):
            graph.add((subject,predicate,URIRef(entityID)))
            graph.add((URIRef(entityID), RDF.type, rdftype))
            graph.add((URIRef(entityID), RDFS.label, Literal(entity, datatype=XSD.string)))
    elif entity in eNamesDict:
        modEntityURI = URIRef(eURIDict[entity])  # Use standardized URI
        modEntityName = eNamesDict[entity]  # Use standardized URI
        graph.add((subject,predicate,modEntityURI))
        graph.add((modEntityURI, RDF.type, rdftype))
        graph.add((modEntityURI, RDFS.label, Literal(modEntityName, datatype=XSD.string)))
    else:
        graph.add((subject,predicate,emiBox[f"{ns}-{dp.format_uri(entity)}"])) #fallback URI
        graph.add((emiBox[f"{ns}-{dp.format_uri(entity)}"], RDF.type, rdftype))
   

# Function to generate full set of triples
def generate_rdf_in_batches(input_csv_gz, join_csv, output_file, join_column, batch_size=1000, ch=1):
    """
    Generate RDF triples in compact Turtle format using batches of rows and rdflib for serialization.

    :param input_csv_gz: Path to the gzipped CSV input file.
    :param join_csv: Path to the secondary CSV file for joining.
    :param output_file: Path to the output Turtle file.
    :param join_column: Column name for joining the two CSVs.
    :param batch_size: The number of rows to process per batch.
    """
    # Load input data
    print("Sent the arguments. Process started")

    if(ch == 1):
        data2 = pd.read_csv(join_csv, compression="gzip", sep="\t", dtype=str)
        merged_data = dp.filter_file_runtime_taxonomy(input_csv_gz, data2, key_column=join_column)
    else:
        merged_data = pd.read_csv(input_csv_gz, compression="gzip", sep="\t", dtype=str, encoding="utf-8")
    print("merged file with following dimensions")
    print(merged_data.shape)

    #data1 = pd.read_csv(input_csv_gz, compression="gzip", sep="\t", dtype=str, encoding="utf-8", quoting=3)
    
    # Filter the interactions based on WdID in enpkg and taxonomy data
    #valid_taxons = data2['wd_taxon_id'].unique()
    #merged_data = data1[(data1['source_WD'].isin(valid_taxons)) | 
    #    (data1['target_WD'].isin(valid_taxons))
    #]
   #print(merged_data)
   #merged_data.to_csv('intxns_subset_20241212_with_enpkg_wdIds.tsv.gz', sep='\t', compression='gzip', index=False)


    
    # Open the output file for writing
    with gzip.open(output_file, "wt", encoding="utf-8") as out_file:
        # Write prefixes directly to the file
        out_file.write("@prefix emi: <https://purl.org/emi#> .\n")
        out_file.write("@prefix : <https://purl.org/emi/abox#> .\n")
        out_file.write("@prefix sosa: <http://www.w3.org/ns/sosa/> .\n")
        out_file.write("@prefix dcterms: <http://purl.org/dc/terms/> .\n")
        out_file.write("@prefix wd: <http://www.wikidata.org/entity/> .\n")
        out_file.write("@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n")
        out_file.write("@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n")
        out_file.write("@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n")
        out_file.write("@prefix prov: <http://www.w3.org/ns/prov#> .\n")
        out_file.write("@prefix wgs84: <http://www.w3.org/2003/01/geo/wgs84_pos#> .\n")
        out_file.write("@prefix qudt: <http://qudt.org/schema/qudt/> .\n\n")

    # Process in batches
    i=0
    for start_row in range(0, len(merged_data), batch_size):
        end_row = min(start_row + batch_size, len(merged_data))
        batch_data = merged_data[start_row:end_row]
        #print(batch_data.shape)
        #print(start_row)
#        # Initialize a new graph for this batch
        graph = Graph()
        graph.bind("", emiBox)  # ":" will now map to "https://purl.org/emi/abox#"
        graph.bind("emi", emi)  # Bind the 'emi' prefix explicitly
        graph.bind("sosa", sosa)  # Bind the 'emi' prefix explicitly
        graph.bind("dcterms", dcterms)  # Bind the 'emi' prefix explicitly
        graph.bind("wd", wd)  # Bind the 'emi' prefix explicitly
        graph.bind("prov", prov)  # Bind the 'emi' prefix explicitly
        graph.bind("wgs84", wgs84)  # Bind the 'emi' prefix explicitly
        graph.bind("qudt", qudt)  # Bind the 'emi' prefix explicitly
#        graph.namespace_manager.bind("_", nTemp)

        # Process each row in the batch
        for _, row in batch_data.iterrows():
            # Define URIs (ensure spaces are replaced with underscores)
            source_taxon_uri = emiBox[f"SAMPLE-{dp.format_uri(row['sourceTaxonId'])}-inRec{i}"] if dp.is_none_na_or_empty(row['sourceTaxonId']) else None
            target_taxon_uri = emiBox[f"SAMPLE-{dp.format_uri(row['targetTaxonId'])}-inRec{i}"] if dp.is_none_na_or_empty(row['targetTaxonId']) else None

            intxn_type_uri = emiBox[f"{row['interactionTypeName']}"] if dp.is_none_na_or_empty(row['interactionTypeName']) else None
            intxn_type_Id_uri = URIRef(f"{row['interactionTypeId']}") if dp.is_none_na_or_empty(row['interactionTypeId']) else None #maybe add RO as namespace
            intxnRec_uri = emiBox[f"inRec{i}"]


            #Declare intxn record as emi:Interaction, this will never be NA/Non/empty
            graph.add((intxnRec_uri, RDF.type, emi.Interaction))


            # Add triples to the graph for interaction Record
            if dp.is_none_na_or_empty(source_taxon_uri):
                graph.add((intxnRec_uri, emi.hasSource, source_taxon_uri))
            if dp.is_none_na_or_empty(target_taxon_uri):
                graph.add((intxnRec_uri, emi.hasTarget, target_taxon_uri))

            if dp.is_none_na_or_empty(intxn_type_uri) and dp.is_none_na_or_empty(intxn_type_Id_uri):
                graph.add((intxnRec_uri, emi.isClassifiedWith, intxn_type_Id_uri))
                graph.add((intxn_type_Id_uri, RDF.type, emi.InteractionType))
                graph.add((intxn_type_Id_uri, RDFS.label, Literal(row['interactionTypeName'], datatype=XSD.string)))
            if not dp.is_none_na_or_empty(intxn_type_Id_uri):
                graph.add((intxnRec_uri, emi.isClassifiedWith, intxn_type_uri))
                graph.add((intxn_type_uri, RDF.type, emi.InteractionType))
#                if dp.is_none_na_or_empty(intxn_type_uri):
#                    graph.add((intxn_type_uri, dcterms.identifier,intxn_type_Id_uri))

            if dp.is_none_na_or_empty(row['localityName']):
                graph.add((intxnRec_uri, prov.atLocation, Literal(row['localityName'], datatype=XSD.string)))
            if dp.is_none_na_or_empty(row['referenceDoi']):
                graph.add((intxnRec_uri, dcterms.bibliographicCitation, Literal(row['referenceDoi'], datatype=XSD.string)))
            if dp.is_none_na_or_empty(row['sourceDOI']):
                graph.add((intxnRec_uri, dcterms.bibliographicCitation, Literal(row['sourceDOI'], datatype=XSD.string)))
            if dp.is_none_na_or_empty(row['decimalLatitude']):
                graph.add((intxnRec_uri, wgs84.lat, Literal(row['decimalLatitude'], datatype=XSD.string)))
            if dp.is_none_na_or_empty(row['decimalLongitude']):
                graph.add((intxnRec_uri, wgs84.long, Literal(row['decimalLongitude'], datatype=XSD.string)))
    #            graph.add((intxnRec_uri, URIRef("http://www.w3.org/2003/01/geo/wgs84_pos#long"), Literal(row['decimalLongitude'], datatype=XSD.string)))


            #Add triples for source and targets
            if dp.is_none_na_or_empty(row['sourceTaxonName']) and dp.is_none_na_or_empty(source_taxon_uri):
                sourceSample_uri = emiBox[f"ORGANISM-{dp.format_uri(row['sourceTaxonName'])}"]
                #if(row['sourceTaxonName'] == "\\N"):
                #    print(i)
                #    print(row)
                graph.add((source_taxon_uri, RDF.type, sosa.Sample))
                graph.add((source_taxon_uri, sosa.isSampleOf, sourceSample_uri))
            if dp.is_none_na_or_empty(row['source_WD']) and dp.is_none_na_or_empty(source_taxon_uri):
                graph.add((source_taxon_uri, emi.inTaxon, wd[f"{row['source_WD']}"]))

            if dp.is_none_na_or_empty(row['targetTaxonName']) and dp.is_none_na_or_empty(target_taxon_uri):
                targetSample_uri = emiBox[f"ORGANISM-{dp.format_uri(row['targetTaxonName'])}"]
                graph.add((target_taxon_uri, RDF.type, sosa.Sample))
                graph.add((target_taxon_uri, sosa.isSampleOf, targetSample_uri))
            if dp.is_none_na_or_empty(row['target_WD']) and dp.is_none_na_or_empty(target_taxon_uri):
                graph.add((target_taxon_uri, emi.inTaxon, wd[f"{row['target_WD']}"]))
        


            # Write body part, physiological state, and other taxon attributes (if available)
            
            # first read the file in which the mappings are stored, followed by triples generation
            # for body part names
            if (dp.is_none_na_or_empty(row['sourceBodyPartName']) or dp.is_none_na_or_empty(row['sourceBodyPartId'])) and dp.is_none_na_or_empty(source_taxon_uri):
                add_entity_to_graph("../ontology/data/globi/correctedBodyPartNamesGlobi.csv","InputTerm","BestMatch","URI",row['sourceBodyPartName'],row['sourceBodyPartId'],source_taxon_uri,emi.hasAnatomicalEntity,emi.AnatomicalEntity, "ANATOMICAL_ENTITY", graph)
            if (dp.is_none_na_or_empty(row['targetBodyPartName']) or dp.is_none_na_or_empty(row['targetBodyPartId'])) and dp.is_none_na_or_empty(target_taxon_uri):
                add_entity_to_graph("../ontology/data/globi/correctedBodyPartNamesGlobi.csv","InputTerm","BestMatch","URI",row['targetBodyPartName'],row['targetBodyPartId'],target_taxon_uri,emi.hasAnatomicalEntity,emi.AnatomicalEntity, "ANATOMICAL_ENTITY", graph)
            
            # for life stage names
            if (dp.is_none_na_or_empty(row['sourceLifeStageName']) or dp.is_none_na_or_empty(row['sourceLifeStageId'])) and dp.is_none_na_or_empty(source_taxon_uri):
                add_entity_to_graph("../ontology/data/globi/correctedLifeStageNamesGlobi.csv","InputTerm","BestMatch","URI",row['sourceLifeStageName'],row['sourceLifeStageId'],source_taxon_uri,emi.hasDevelopmentalStage, emi.DevelopmentalStage, "DEVELOPMENTAL_STAGE", graph)
            if (dp.is_none_na_or_empty(row['targetLifeStageName']) or dp.is_none_na_or_empty(row['targetLifeStageId'])) and dp.is_none_na_or_empty(target_taxon_uri):
                add_entity_to_graph("../ontology/data/globi/correctedLifeStageNamesGlobi.csv","InputTerm","BestMatch","URI",row['targetLifeStageName'],row['targetLifeStageId'],target_taxon_uri,emi.hasDevelopmentalStage, emi.DevelopmentalStage, "DEVELOPMENTAL_STAGE", graph)

            #for biological sex
            if dp.is_none_na_or_empty(row['sourceSexName']) and dp.is_none_na_or_empty(source_taxon_uri):
                genderDict = mbg.map_terms_to_values(row['sourceSexName'])
                for uri, qty in genderDict.items():
                    gData = BNode()
                    graph.add((source_taxon_uri, emi.hasSex, gData))
                    graph.add((gData, qudt.quantityKind, URIRef(uri)))  
                    graph.add((gData, qudt.numericValue, Literal(qty, datatype=XSD.integer)))
                    graph.add((URIRef(uri), RDF.type, emi.BiologicalSex))  

            if dp.is_none_na_or_empty(row['targetSexName']) and dp.is_none_na_or_empty(target_taxon_uri):
                genderDict = mbg.map_terms_to_values(row['targetSexName'])
                for uri, qty in genderDict.items():
                    gData = BNode()
                    graph.add((source_taxon_uri, emi.hasSex, gData))
                    graph.add((gData, qudt.quantityKind, URIRef(uri)))  
                    graph.add((gData, qudt.numericValue, Literal(qty, datatype=XSD.integer)))
                    graph.add((URIRef(uri), RDF.type, emi.BiologicalSex))  
            
            #for physiological stage on-hold still because not enough physiological stages defined
            #if dp.is_none_na_or_empty(row['sourcePhysiologicalStateName']) and dp.is_none_na_or_empty(source_taxon_uri):
            #    graph.add((source_taxon_uri, emi.hasPhysiologicalStage, Literal(row['sourcePhysiologicalStateName'], datatype=XSD.string)))
            #if dp.is_none_na_or_empty(row['targetPhysiologicalStateName']) and dp.is_none_na_or_empty(target_taxon_uri):
            #    graph.add((target_taxon_uri, emi.hasPhysiologicalStage, Literal(row['targetPhysiologicalStateName'], datatype=XSD.string)))
            
            i = i + 1
        dp.add_inverse_relationships(graph)
        
        # Serialize the graph for the batch and write to the file
        with gzip.open(output_file, "at", encoding="utf-8") as out_file:  # Append mode
            print("written triples for",)
            out_file.write(graph.serialize(format="turtle_custom"))
        # Clear the graph to free memory
        del graph


    print(f"RDF triples saved to {output_file}")

# Main execution
if __name__ == "__main__":
    configFile = "config.txt"
    if os.path.exists(configFile):       #if config file is available
        config = configparser.ConfigParser()
        config.read(configFile)
        csv_file1 = config.get('tsv files', 'globi_tsv')
        csv_file2 = config.get('accessory files', 'enpkg_wd')
        output_file = config.get('output files', 'globi_ttl')
    else:                               #else use command line arguments
        # Create the argument parser
        parser = argparse.ArgumentParser()

        # Add arguments
        parser.add_argument('inputFile', type=str, help="Enter the file name for which you want the triples")
        parser.add_argument('joinFile', type=str, help="Enter the file name which will be used for filtering or joining the input_file")
        parser.add_argument('outputFile', type=str, help="Enter the output file name")

        # Parse the arguments
        args = parser.parse_args()
        csv_file1 = args.inputFile
        csv_file2 = args.joinFile
        output_file = args.outputFile

    generate_rdf_in_batches(csv_file1, csv_file2, output_file, join_column="wd_taxon_id", batch_size=10000)
