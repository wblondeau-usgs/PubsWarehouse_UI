__author__ = 'jameskreft'

import requests
import feedparser
from bs4 import BeautifulSoup
import re
from operator import itemgetter
from pubs_ui import app
import json
from urlparse import urljoin
from copy import deepcopy


#should requests verify the certificates for ssl connections
verify_cert = app.config['VERIFY_CERT']

def pubdetails(pubdata):
    """
    build the ordered list to make the 'Publications details' box

    :param pubdata: the data pulled from the pubs warehouse web service
    :return: pubdata with an additional "details" element
    """

    pubdata['details'] = []
    #details list element has len of 2 or 3.  If 2, the item is coming back as a simple Key:value object, but if three
    # there are either lists or dicts. the first item in the list is the param in pubdata, the 2nd or 3rd is the display
    # descriptor and the second if it exists is the secondary key needed to get the text.
    detailslist = [
        ['publicationType', 'text', 'Publication type:'],
        ['publicationSubtype', 'text', 'Publication Subtype:'],
        ['seriesName', 'Series name:'],
        ['seriesNumber', 'Series number:'],
        ['subseriesTitle', 'Subseries'],
        ['chapter', 'Chapter:'],
        ['subchapterNumber', 'Sub-chapter:'],
        ['issn', 'online', 'ISSN (online):'],
        ['issn', 'print', 'ISSN (print):'],
        ['isbn', 'ISBN:'],
        ['doi', 'DOI:'],
        ['edition', 'Edition:'],
        ['volume', 'Volume'],
        ['issue', 'Issue:'],
        ['publicationYear', 'Year Published:'],
        ['language', 'Language:'],
        ['publisher', 'Publisher:'],
        ['publisherLocation', 'Publisher location:'],
        ['costCenters', 'text', 'Contributing office(s):'],
        ['productDescription', 'Description:'],
        ['numberofPages', 'Number of pages:'],
        ['largerWorkType', 'text', 'Publication type:'],
        ['largerWorkSubtype', 'text', 'Publication Subtype:'],
        ['largerWorkTitle', 'text', 'Larger Work Title:'],
        ['startPage', 'Start page:'],
        ['endPage', 'End page:'],
        ['temporalStart', 'Time Range Start:'],
        ['temporalEnd', 'Time Range End:'],
        ['conferenceTitle', 'Conference Title:'],
        ['conferenceLocation', 'Conference Location:'],
        ['conferenceDate', 'Conference Date:'],
        ['country', 'Country:'],
        ['state', 'State:'],
        ['county', 'County:'],
        ['city', 'City:'],
        ['otherGeospatial', 'Other Geospatial:'],
        ['datum', 'Datum:'],
        ['projection', 'Projection:'],
        ['scale', 'Scale:'],
        ['onlineOnly', 'Online Only (Y/N):'],
        ['additionalOnlineFiles', 'Additional Online Files(Y/N):']

    ]
    for detail in detailslist:

        if len(detail) == 3:
            #if the detail exists and is a dict with a couple key:value pairs, get the right value
            if pubdata.get(detail[0]) is not None and isinstance(pubdata.get(detail[0]), dict):
                pubdata['details'].append({detail[2]: pubdata[detail[0]].get(detail[1])})
            #if the thing is a list of dicts and if there is something in the list, concatenate the values into a string
            elif pubdata.get(detail[0]) is not None and isinstance(pubdata.get(detail[0]), list) \
                    and len(pubdata.get(detail[0])) > 0:
                dd = []
                for det in pubdata.get(detail[0]):
                    dd.append(det.get(detail[1]))
                dd = ', '.join(dd)
                pubdata['details'].append({detail[2]: dd})
        elif len(detail) == 2 and pubdata.get(detail[0]) is not None and len(pubdata.get(detail[0])) > 0:
            pubdata['details'].append({detail[1]: pubdata.get(detail[0])})
    return pubdata


def create_display_links(pubdata):
    """
    restructures links from the API so that they are easy to display in a jinja template
    :param pubdata:
    :return: pubdata with new displayLinks array
    """
    display_links = {
        'Abstract': [],
        'Additional Report Piece': [],
        'Appendix': [],
        'Application Site': [],
        'Authors Website': [],
        'Chapter': [],
        'Companion Files': [],
        'Cover': [],
        'Database': [],
        'Digital Object Identifier': [],
        'Document': [],
        'Errata': [],
        'Illustration': [],
        'Image': [],
        'Index Page': [],
        'Metadata': [],
        'Plate': [],
        'Project Site': [],
        'Raw Data': [],
        'Read Me': [],
        'Referenced Work': [],
        'Related Work': [],
        'Spatial Data': [],
        'Thumbnail': [],
        'Version History': []
    }
    links = pubdata.get("links")
    for linktype in display_links:
        rankcounter = 1
        for link in links:
            if link['type']['text'] == linktype:
                if link.get('rank') is None:
                    link['rank'] = rankcounter
                    rankcounter += 1
                display_links[linktype].append(link)
    display_links = manipulate_plate_links(display_links)
    pubdata["displayLinks"] = display_links
    return pubdata


def manipulate_plate_links(display_links):
    """
    This function rejiggers plate link displays for plate links that are named regularly but do not have display text or
    a proper order
    :param display_links:
    :return: display links with rejiggered plate link order
    """
    #only do something if there are links in the plate links section
    if len(display_links.get("Plate")) > 0:
        for link in display_links["Plate"]:
            url = link["url"]
            file_name = url.split("/")[-1].split(".")
            text = file_name[0]
            if link.get("text") is None:
                if len(file_name[0].title().split('-')) > 1:
                    try:
                        text = file_name[0].title().split('-')
                        text[1] = int(text[1])
                    except (ValueError, IndexError):
                        text = file_name[0].title().split('-')
                if len(file_name[0].split("_")) > 1:
                    try:
                        text = file_name[0].split("_")[-1]
                        text = re.split('(\d+)', text)[0:2]
                        text[1] = int(text[1])
                    except (ValueError, IndexError):
                        try:
                            text = file_name[0].split("_")[0]
                            text = re.split('(\d+)', text)[0:2]
                            text[1] = int(text[1])
                        except (ValueError, IndexError):
                            text = file_name[0].split("_")

                link["text"] = text
            if link.get('linkFileType') is None:
                link['linkFileType'] = {'text': file_name[1]}
        display_links["Plate"] = sorted(display_links["Plate"], key=itemgetter('text'))
        rankcounter = 1
        for link in display_links["Plate"]:
            link['rank'] = rankcounter
            rankcounter += 1
            link['text'][1] = str(link['text'][1])
            link['text'] = " ".join(link['text']).title()
    return display_links


def pull_feed(feed_url):
    """
    pull page data from a my.usgs.gov confluence wiki feed
    :param feed_url: the url of the feed, created in confluence feed builder
    :return: the html of the page itself, stripped of header and footer
    """
    feed = feedparser.parse(feed_url)

    # Process html to remove unwanted mark-up and fix links
    post = ''
    if len(feed['entries']) > 0:
        soup = BeautifulSoup(feed['entries'][0].summary)

        # Remove edited by paragraph
        soup.p.extract()

        # Remove final div in the feed
        feed_div = soup.find('div', class_='feed')
        children_divs = feed_div.findAll('div')
        children_divs[len(children_divs) - 1].extract()

        # Translate any in page links to use relative URL
        base = feed['entries'][0].summary_detail.base
        links = feed_div.select('a[href^="' + base + '"]')
        for link in links:
            link['href'] = link['href'].replace(base, '')
        post = unicode(soup)

    return post


def supersedes(supersedes_url, index_id):
    """
    pull supersede info for a pub from legacy "extras" endpoint
    :param supersedes_url:url for extras endpoint
    :param index_id: index_id of pub
    :return: dict of relevant supersede info
    """

    supersede_array = requests.get(supersedes_url,
                                   params={'prod_id': index_id}, verify=verify_cert).json()['modsCollection']['mods'][0]['relatedItem'][0]
    #TODO: deal with pubs with more than one relationship
    return {'type': supersede_array['@type'], 'index_id': supersede_array['identifier']['#text'],
            'title': supersede_array['titleInfo']['title']}


def getbrowsecontent(browseurl, browsereplace):
    """
    Gets the content of the legacy browse interface so that it can be used without extension.
    :param browseurl: url of legacy browse interface
    :return: html content of links, breadcrumb, and title
    """
    app.logger.info('The get_browse_content function is being called')
    content = requests.get(browseurl, verify=verify_cert)
    app.logger.info(str(content.status_code)+ "  " +str(content.url))
    soup = BeautifulSoup(content.text)
    for a in soup.findAll('a'):
        a['href'] = a['href'].replace("browse", browsereplace)
    browse_content = {'links':soup.find('div', {"id": "pubs-browse-links"}).contents}
    browse_content['breadcrumbs'] = soup.find('div', {"id": "pubs-browse-breadcrumbs"}).contents
    browse_content['header'] = soup.find('div', {"id": "pubs-browse-header"}).contents

    return browse_content


class SearchPublications(object):
    
    """
    Methods for executing various types
    of searches against the backend
    Pubs API.
    
    :param str search_url: URL without any search parameters appended
    """
    
    def __init__(self, search_url):
        self.search_url = search_url
        
    def get_pubs_search_results(self, params=None):
        """
        Searches Pubs API for a specified query parameter
        
        :param str search_url: URL without any search parameters appended
        :param dict params: dictionary of form {'key1': 'value1', 'key2': 'value2}
        :return: query results (or None) and response status code.
        :rtype: tuple
        """
        search_result_obj = requests.get(url=self.search_url, params=params, verify=verify_cert)
        try:
            search_result_json = search_result_obj.json()
            for record in search_result_json['records']:
                if record.get("authors") is not None:
                    contributor_lists(record)
            error_response = None
        except ValueError:
            search_result_json = None
            error_response = search_result_obj.text
        except TypeError:
            search_result_json = None
            error_response = search_result_obj.text
        resp_status_code = search_result_obj.status_code
        return search_result_json, resp_status_code


def contributor_lists(record):
    contributor_types = ['authors', 'editors']
    for contributor_type in contributor_types:
        if record.get(contributor_type) is not None:
            record[contributor_type+"List"] = make_contributor_list(record[contributor_type])
            record[contributor_type+"ListTyped"] = concatenate_contributor_names(record[contributor_type])
    return record


def make_contributor_list(contributors):
    """
    Makes a list of names for contributors regardless of type that is easy to join in jinja.  Useful when you need
    a list of names and don't have to do all of the semantic jiggery-poky that one needs for names otherwise.

    :param list contributors: a list of dicts of a contributor type (authors, editors, etc)
    :return list of concatenated author names in given family suffix or corporate name
    :rtype: list
    """
    #turn the list of dicts into smaller, sorted list of dicts
    typed_contributor_list = concatenate_contributor_names(contributors)
    #only grab the string portion of the tuple, put it into its own list.
    contributor_list = []
    for contributor in typed_contributor_list:
        contributor_list.append(contributor["text"])
    return contributor_list


def concatenate_contributor_names(contributors):
    """
    Turns a dict with a lot of split-out contributor information into a simpler format of ("kind", "name")

    :param list contributors: a list of dicts of a contributor type (authors, editors, etc)
    :return:
    """
    #Sort the contributors by the rank that comes out of the web service- ranks is something that will always be there
    #  (it is fundamental to the pubs data model, so we don't have to deal with it not being there
    sorted_contributors = sorted(contributors, key=itemgetter('rank'))
    #empty list to build the names
    contributor_list = []
    for contributor in sorted_contributors:
        #test for the boolean "corporation" flag for each contributor
        if contributor['corporation'] is False:
            #list to set up join
            contributor_name_list = []
            #add parts of name to the list if they exist and aren't empty strings
            if contributor.get("given") is not None and len(contributor.get("given")) > 0:
                contributor_name_list.append(contributor['given'])
            if contributor.get("family") is not None and len(contributor.get("family")) > 0:
                contributor_name_list.append(contributor['family'])
            if contributor.get("suffix") is not None and len(contributor.get("suffix")) > 0:
                contributor_name_list.append(contributor['suffix'])
            contributor_dict = {"type": 'person', "text": " ".join(contributor_name_list)}
        #corporate authors- the other side of the boolean
        elif contributor['corporation'] is True:
            contributor_dict = {"type": 'corporation', "text": contributor.get('organization')}
        contributor_list.append(contributor_dict)
    return contributor_list

def jsonify_geojson(record):
    """
    turns the stringified geojson into actual json
    :param record:
    :return record with geojson in geographicExtents:
    """
    geojson = record.get('geographicExtents')
    if geojson is not None:
        try:
            geojson = json.loads(geojson)
            record['geographicExtents'] = geojson
        except Exception as e:
            app.logger.info("Prod ID "+str(record['id'])+" geographicExtents json parse error: "+str(e))
            del record['geographicExtents']
    return record

def preceding_and_superseding(context_id, supersedes_service_url):
    """
    Obtains supersede info for the context publication from an external (legacy) 
    service, and converts that info into an unambiguous form. Note that, 
    although the service endpoint is parameterized, that's only a convenience
    for exercising and testing this operation. This function contains 
    hard-wired assumptions about 
        - how the context_id is included in the service call;
        - the structure and semantics of the legacy service's return value.

    This function will therefore need to be changed if the supersedes service 
    definition changes.

    :param context_id: prod_id of context publication
    :param supersedes_service_url: url for supersede information service
    :return: dict containing three items:
        'predecessors':related items that the context list-valued ub supersedes
        'context_id': the index (prod) ID of the context pub. Included as 
            confirmation only; identical to the 'context_id' param.
        'successors': related items that supersede the context pub
    """
    response = requests.get(supersedes_service_url,params={'prod_id': context_id})
    related = response.json()['modsCollection']['mods'][0]['relatedItem']

    # REMARKS ABOUT SERVICE RETURNED VALUE ASSUMPTIONS
    #
    # The service returns JSON, which is converted into Python structures.
    #
    # Note that, despite the structure of the response, the "mods" array will
    # have at most only one contained element.
    #
    # Concerning the sense of the terminology, the occurrence of 
    # '"@type": "succeeding"' or '"@type": "preceding"' refers to the 
    # relationship of the linked pub TO the context pub. 
    #
    # To put it another way, the "@type" relationship descriptor assumes 
    # that the linked pub is the SUBJECT, and the context pub is the OBJECT. 
    # This can be subtly confusing for those of us who have absorbed the RDF 
    # conventions about framing the predicate from the viewpoint of the subject.
    # 
    # Just think of the @type as saying "This linked pub is ___ the context pub."

    predecessors = []
    successors = []

    for item in related:
        item_summary_info = {'index_id': item['identifier']['#text'],
                'title': item['titleInfo']['title'], 'date': item['originInfo']['dateIssued']}

        if item['@type'] == 'preceding':
            predecessors.append(item_summary_info)
        elif item['@type'] == 'succeeding':
            successors.append(item_summary_info)

    return {'predecessors': predecessors, 'context_item': context_id, 'successors': successors}


def make_relationship_graph(context_pub_dict, related_pub_dict, related_pub_relation):
    """
    Creates an "@graph" item for inclusion in the "relationship" element. This
    function exists to isolate the creation of the @graph element from external
    code. It will need to be modified if the desired return format changes, or 
    if the assumed format of the parameters changes.
    
    The graph makes safe copies of its dict params.

    :param context_pub_dict: the graph's basic representation of the context publication
    :param related_pub_dict: the graph's basic representation of the related publication
    :param related_pub_relation: description of the related publication's relation to the
        context publication.
    :returns: a dictionary with one item: key="@graph", value=a list containing 
        safe copies of the context publication and related publication, both in 
        @graph member form.
    """
    # necessary to make a deep, rather than shallow, copy - we do
    # not want to make any changes to the parameter.
    return_context_pub_dict = deepcopy(context_pub_dict)
    return_related_pub_dict = deepcopy(related_pub_dict)

    related_pub_url = related_pub_dict['@id']

    # relationship type is stashed in context_pub_dict: the "subject", if we can
    # safely call it that. However, it points to the related item. (NOTE:
    # this should be revisited. It's a confusing way to represent
    # a predicate.)
    if related_pub_relation == 'successor':
        # context pub is replaced by related pub, so we describe the context pub as
        return_context_pub_dict['rdaw:replacedByWork'] = related_pub_url

    elif related_pub_relation == 'predecessor':
        # context pub replaces related pub, so we describe the context pub as
        return_context_pub_dict['rdaw:replacementOfWork'] = related_pub_url

    return {'@graph': [return_context_pub_dict, return_related_pub_dict]}


def apply_preceding_and_superseding(context_pubdata, supersedes_service_url, pubs_base_url):
    """
    Accepts publication data JSON for the desired context publication,
    extracts the context publication's index_id, calls precedes_supersedes_url
    for that index_id. If the current publication supersedes, and/or
    is superseded by, any other publications, inserts summary info about 
    those pubs into the passed context_pubdata. 
    This function delegates formulation of @graph items to 
    make_relationship_graph().

    context_pubdata: the Python decode of the JSON representation of the 
        context publication
    supersedes_service_url: the endpoint of the service from which info about
        related items should be obtained
    param pubs_base_url: the url needed to compose a publication URL given 
        a known prod_id
    """
    return_pubdata = deepcopy(context_pubdata)
    index_id = context_pubdata['indexId']
    pub_url = urljoin(pubs_base_url, index_id)

    # this LITERAL is probably OK for this particular use. However, it
    # needs to be exported to a configuration.
    pub_type = 'rdac:Work'
    
    # obtain predecessor and successor related items
    pre_super =  preceding_and_superseding(index_id, supersedes_service_url)

    if pre_super['predecessors'] or pre_super['successors']:

        # ensure 'relationships' is set up
        if 'relationships' not in return_pubdata:
            return_pubdata['relationships'] = {}
        if '@context' not in return_pubdata['relationships']:
            return_pubdata['relationships']['@context'] = {}

        # JSON - Python conversion: the JSON appears to have 
        # multiple named elements with the samed name ('@graph'). 
        # should use a list of dictionaries,
        # rather than a dictionary, to represent these named items
        # robustly in Python. This may turn out to be an issue,
        # since we need to name this list rather than letting it remain
        # anonymous.

        if not 'relationships' in return_pubdata:
            return_pubdata['relationships'] = []
        if not 'graphs' in return_pubdata['relationships']:
            return_pubdata['relationships']['graphs'] = []

        return_pubdata['relationships']['@context']['dc'] = 'http://purl.org/dc/elements/1.1/'
        return_pubdata['relationships']['@context']['xsd'] = 'http://www.w3.org/2001/XMLSchema#'
        return_pubdata['relationships']['@context']['rdac'] = 'http://rdaregistry.info/Elements/c/'
        return_pubdata['relationships']['@context']['rdaw'] = 'http://rdaregistry.info/Elements/w/'

        return_pubdata['relationships']['@context']['rdaw:replacedByWork'] = {'@type': '@id'}
        return_pubdata['relationships']['@context']['rdaw:replacementOfWork'] = {'@type': '@id'}

        # make parameter for context publication
        this_pub = {
                '@id': pub_url,
                '@type': pub_type,
                'dc:title': return_pubdata['title']
            }

        # add any linked data for superseding another publication
        for item in pre_super['predecessors']:
            related_pub = {
                '@id':  urljoin(pubs_base_url, item['index_id']),

                '@type': pub_type,
                'dc:title': item['title']
                }
            if item['date']:
                related_pub['dc:date'] = item['date']

            return_pubdata['relationships']['graphs'].append(
                    make_relationship_graph(this_pub, related_pub, 'predecessor'))

        # add any linked data for being superseded by another publication
        for item in pre_super['successors']:
            related_pub = {
                '@id': urljoin(pubs_base_url, item['index_id']),

                '@type': pub_type,
                'dc:title': item['title']
                }
            if item['date']:
                related_pub['dc:date'] = item['date']

            return_pubdata['relationships']['graphs'].append(
                    make_relationship_graph(this_pub, related_pub, 'successor'))

    return return_pubdata


def add_supersede_pubs(context_pubdata):
    """
    Obtains superseding/superseded pubs info for a "context" pub from an 
    external (legacy) endpoint. Inserts that info into a copy of the
     "context_pubdata" parameter.

    :param context_pubreturn: the decoded JSON describing the context pub
    :return: a copy of the "context_pubdata" parameter with all obtained
        supersede information inserted in the "@context" item.
    """

    supersedes_service_url = 'http://pubs.er.usgs.gov/service/citation/json/extras' 
    pubs_base_url = 'http://pubs.er.usgs.gov/publication/'


    return_pubdata = apply_preceding_and_superseding(context_pubdata, supersedes_service_url, pubs_base_url)

    return return_pubdata


