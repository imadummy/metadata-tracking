# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from lxml import etree
import requests
from bs4 import BeautifulSoup
from copy import deepcopy
import os, os.path
import json

"""
Script for writing ISO 19139 metadata for Esri Open Data datasets. Work in progress...
"""

def get_list_of_datasets(root_data_json):
    return [i.identifier for i in root_data_json]

def request_data_json(url, prefix):
    print "remote request for data.json"
    try:
        j = requests.get(url).json()
    except requests.exceptions.HTTPError as e:
        sys.exit(e.message)
    else:
        return j["dataset"]

def get_data_json(prefix, url):
    return request_data_json(url, prefix)

def get_elements_for_open_data(tree):
    field_map = {}
    for field in FIELDS:
        field_map[field] = tree.findall(PATHS[field],NSMAP)
    return field_map

def parse_template_into_tree(template_name="scrape_open_data/opendata_iso_template_gmd_gone.xml"):
    return etree.parse(template_name)

def get_bbox(dataset):
    return dataset["spatial"].split(",")

def check_for_landing_page_json(dataset):
    if landing_page_json is not None:
        return True
    else:
        return False

def get_dataset_json(dataset_id):
    try:
        r = requests.get(dataset_id + ".json")
    except requests.exceptions.HTTPError as e:
        sys.exit(e.message)
    finally:
        if "json" in r.headers["content-type"]:
            json = r.json()
            return json["data"]
        return None

def get_landing_page_json(dataset):
    if not check_for_landing_page_json(dataset):
        try:
            r = requests.get(dataset["landingPage"]+".json")
        except requests.exceptions.HTTPError as e:
            sys.exit(e.message)
        finally:
            if "json" in r.headers["content-type"]:
                landing_page_json = r.json()
                return landing_page_json
            return None

def clear_landing_page_json():
    landing_page_json = None

def get_fields(dataset):
    #dataset_details = get_landing_page_json(dataset)
    #load local for now
    dataset_details = json.load(open("dataset_detail.json"))


def parse_webservice(dataset):
    url = dataset["webService"]
    return url

def parse_datatype(dataset):

    try:
        geometryType = get_landing_page_json(dataset)["data"]["geometry_type"]
        print "geometryType: ", geometryType
    except (KeyError,TypeError) as e:
        print "couldn't get geometry type for {title}".format(title=dataset["title"])
        return "undefined"

    if geometryType == "esriGeometryPoint" or geometryType == "esriGeometryMultipoint":
        return "point"

    elif geometryType == "esriGeometryPolyline":
        return "curve"

    elif geometryType == "esriGeometryPolygon" or geometryType == "esriGeometryEnvelope":
        return "surface"
    else:
        return "nonspatial"


def main(url, prefix, output_path):
    """
        url = Esri Open Data root url (like opendata.minneapolismn.gov)
        prefix = what to put in front of each file name that gets written out
        output_path = where output files should be written
    """

    if not os.path.exists(output_path):
        os.mkdir(output_path)

    data_json = get_data_json(prefix, url)

    for dataset in data_json:
        dataset_detail = get_dataset_json(dataset["identifier"])
        print "Now on:", dataset_detail["name"]
        tree = parse_template_into_tree()
        elements = get_elements_for_open_data(tree)

        if len(elements["title"]) > 0:
            elements["title"][0].text = dataset["title"]

        if len(elements["pubdate"]) > 0:
            elements["pubdate"][0].text = dataset["modified"]

        if len(elements["title"]) > 0:
            elements["origin"][0].text = elements["publish"][0].text = dataset["publisher"]["name"]

        # bounding coordinates
        bbox = get_bbox(dataset)
        elements["westbc"][0].text = bbox[0]
        elements["southbc"][0].text = bbox[1]
        elements["eastbc"][0].text = bbox[2]
        elements["northbc"][0].text = bbox[3]

        distribution_list = dataset["distribution"]
        for dist in distribution_list:
            if dist["title"] == "Shapefile":
                elements["onlink"][0].text = dist["downloadURL"]
                elements["formname"][0].text = "shapefile"


        # REST service link
        elements["onlink"][1].text = parse_webservice(dataset)

        elements["datatype"][0].set("codeListValue", parse_datatype(dataset))


        elements["id"][0].text = dataset["identifier"].split("/")[-1]
        elements["accconst"][0].text = dataset["accessLevel"]

        # description and license oftentimes have HTML contents,
        # so use Beautiful Soup to get the plain text



        if dataset["description"]:
            abstract_soup = BeautifulSoup(dataset["description"])
            linebreaks = abstract_soup.findAll("br")
            [br.replace_with("&#xD;&#xA;") for br in linebreaks]

            elements["abstract"][0].text = abstract_soup.text
            #elements["abstract"][0].text = dataset["description"]
        else:
            elements["abstract"][0].text = "No description provided"

        elements["useconst"][0].text = dataset["license"]



        keywords_list = dataset["keyword"]

        keywords_element = elements["themekey"][0].getparent().getparent()
        keyword_element = keywords_element.find("gmd:keyword",NSMAP)

        for index, keyword in enumerate(keywords_list):
            keywords_element.findall("gmd:keyword", NSMAP)[index].find("gco:CharacterString", NSMAP).text = keyword

            if index != len(keywords_list) - 1:
                keywords_element.append(deepcopy(keyword_element))


        new_xml_filename = "{prefix}_{title}_{id}".format(prefix=prefix,
                                                          title=dataset["title"].replace(" ", "_").replace("/","_").lower(),
                                                          id=dataset["identifier"].split("/")[-1])

        print os.path.join(output_path, new_xml_filename + ".xml")
        tree.write(os.path.join(output_path, new_xml_filename + ".xml"), pretty_print=True)


NSMAP = {
   "srv":"http://www.isotc211.org/2005/srv",
   "gco":"http://www.isotc211.org/2005/gco",
   "xlink":"http://www.w3.org/1999/xlink",
   "gts":"http://www.isotc211.org/2005/gts",
   "xsi":"http://www.w3.org/2001/XMLSchema-instance",
   "gml":"http://www.opengis.net/gml",
   "gmd":"http://www.isotc211.org/2005/gmd"
}

FIELDS = [
    "title",
    "pubdate" ,
    "onlink"  ,
    "origin"  ,
    "publish" ,
    "westbc"  ,
    "eastbc"  ,
    "northbc" ,
    "southbc" ,
    "themekey",
    "placekey",
    "abstract",
    "accconst",
    "useconst",
    "formname",
    "id",
    "datatype"
]

PATHS = {
    "title"    : "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:title/gco:CharacterString",
    "onlink"   : "gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource/gmd:linkage/gmd:URL",
    "origin"   : "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:citedResponsibleParty/gmd:CI_ResponsibleParty/gmd:organisationName/gco:CharacterString",
    "publish"  : "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:citedResponsibleParty/gmd:CI_ResponsibleParty/gmd:organisationName/gco:CharacterString",
    "pubdate"  : "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:editionDate/gco:Date",
    "westbc"   : "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:westBoundLongitude/gco:Decimal",
    "eastbc"   : "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:eastBoundLongitude/gco:Decimal",
    "northbc"  : "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:northBoundLatitude/gco:Decimal",
    "southbc"  : "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:southBoundLatitude/gco:Decimal",
    "themekey" : "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords/gmd:type/gmd:MD_KeywordTypeCode[@codeListValue='theme']",
    "placekey" : "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords/gmd:type/gmd:MD_KeywordTypeCode[@codeListValue='place']",
    "abstract" : "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:abstract/gco:CharacterString",
    "accconst" : "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:otherConstraints/gco:CharacterString",
    "useconst" : "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceConstraints/gmd:MD_Constraints/gmd:useLimitation/gco:CharacterString",
    "formname" : "gmd:distributionInfo/gmd:MD_Distribution/gmd:distributionFormat/gmd:MD_Format/gmd:name/gco:CharacterString",
    "id"       : "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:identifier/gmd:MD_Identifier/gmd:code/gco:CharacterString",
    "datatype" : "gmd:spatialRepresentationInfo/gmd:MD_VectorSpatialRepresentation/gmd:geometricObjects/gmd:MD_GeometricObjects/gmd:geometricObjectType/gmd:MD_GeometricObjectTypeCode"
}

landing_page_json = None

if __name__ == "__main__":
    import sys
    main(sys.argv[1], sys.argv[2], sys.argv[3])
