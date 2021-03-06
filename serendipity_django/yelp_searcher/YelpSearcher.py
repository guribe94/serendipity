# -*- coding: utf-8 -*-
"""
Yelp API v2.0 wrapper for serendipity.

This program demonstrates uses the Yelp API version 2.0
by using the Search API to query for businesses by a search term and location,
and the Business API to query additional information about the top result
from the search query to return as JSON.

"""
import argparse
import json
import pprint
import sys
import urllib
import urllib2

import oauth2

API_HOST = 'api.yelp.com'
DEFAULT_TERM = ''#'dinner'
DEFAULT_LOCATION = ''
DEFAULT_LATITUDE = 40.805741
DEFAULT_LONGITUDE = -73.964996
DEFAULT_LL = [DEFAULT_LATITUDE, DEFAULT_LONGITUDE]

SEARCH_PATH = '/v2/search/'
BUSINESS_PATH = '/v2/business/'

    # OAuth credential placeholders that must be filled in by users.
CONSUMER_KEY = 'r_jbHVPhxl6YXmTI7XB3vg'
CONSUMER_SECRET = 'E6MatPc81kIc_y-icB7pFUjEfgg'
TOKEN = 'l0jXKeNMzYsLLxN7iulBIzhGtUa5ejCZ'
TOKEN_SECRET = 'jFlyShJGUllmnpvkssEe84dmC2g'

def request(host, path, url_params=None):
    """Prepares OAuth authentication and sends the request to the API.
    Args:
        host (str): The domain host of the API.
        path (str): The path of the API after the domain.
        url_params (dict): An optional set of query parameters in the request.
    Returns:
        dict: The JSON response from the request.
    Raises:
        urllib2.HTTPError: An error occurs from the HTTP request.
    """
    url_params = url_params or {}
    url = 'http://{0}{1}?'.format(host, urllib.quote(path.encode('utf8')))

    consumer = oauth2.Consumer(CONSUMER_KEY, CONSUMER_SECRET)
    oauth_request = oauth2.Request(method="GET", url=url, parameters=url_params)

    oauth_request.update(
        {
            'oauth_nonce': oauth2.generate_nonce(),
            'oauth_timestamp': oauth2.generate_timestamp(),
            'oauth_token': TOKEN,
            'oauth_consumer_key': CONSUMER_KEY
        }
    )
    token = oauth2.Token(TOKEN, TOKEN_SECRET)
    oauth_request.sign_request(oauth2.SignatureMethod_HMAC_SHA1(), consumer, token)
    signed_url = oauth_request.to_url()
    
    print u'Querying {0} ...'.format(url)

    conn = urllib2.urlopen(signed_url, None)
    try:
        response = json.loads(conn.read())
    finally:
        conn.close()

    return response

def search(term, location):
    """Query the Search API by a search term and location.
    Args:
        term (str): The search term passed to the API.
        location (str): The search location passed to the API.
    Returns:
        dict: The JSON response from the request.
    """
    
    SEARCH_LIMIT = 5
    RADIUS_LIMIT = 1610

    url_params = {
        'term': term.replace(' ', '+'),
        'location': location.replace(' ', '+'),
        #'cll': [40.805741, -73.964996],
        #'cll': {'latitude':40.805741, 'longitude':-73.964996},
        #'cll': [(40.805741, -73.964996)],
        #'ll': [DEFAULT_LATITUDE, DEFAULT_LONGITUDE],
        'limit': SEARCH_LIMIT,
        'radius_filter': RADIUS_LIMIT,
        'deals_filter': True
    }
    return request(API_HOST, SEARCH_PATH, url_params=url_params)

def get_business(business_id):
    """Query the Business API by a business ID.
    Args:
        business_id (str): The ID of the business to query.
    Returns:
        dict: The JSON response from the request.
    """
    business_path = BUSINESS_PATH + business_id

    return request(API_HOST, business_path)

def query_api(term, location):
    """Queries the API by the input values from the user.
    Args:
        term (str): The search term to query.
        location (str): The location of the business to query.
    """
    response = search(term, location)

    businesses = response.get('businesses')

    deleteList = []

    if len(businesses) != 0:
        print len(businesses)
        for x in range(0, len(businesses)):
        #print businesses[x]
            print x
            if businesses[x].get('rating') > 3 and businesses[x].get('review_count') > 5: #and businesses[x].get('is_closed') == False:
                print 'good job'
            else:
                deleteList.insert(0,x);

    for y in range(0, len(deleteList)):
        del businesses[y]

    print 'yeahhh'
    for z in range(0, len(businesses)):
        print 'Result ' + str(z + 1)
        print businesses[z]
    
    print 'json part'
    #print businesses
    json1 = json.dumps(businesses, ensure_ascii=False)
    #print json1
    return json1


def get(address):

    try:
        # return query_api(input_values.term, input_values.location)
        return query_api('', address)
    except urllib2.HTTPError as error:
        sys.exit('Encountered HTTP error {0}. Abort program.'.format(error.code))