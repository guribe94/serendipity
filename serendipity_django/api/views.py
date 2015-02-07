from django.http import HttpResponse
from yelp_searcher import YelpSearcher
from geopy.geocoders import Nominatim

# Create your views here.
def place_finder(request, lat, long):
#   40.805351, -73.964458
    json = YelpSearcher.get('546 West 113th Street, New York, NY')
#    json = YelpSearcher.get(str(location))
    return HttpResponse(json, content_type="application/json")

