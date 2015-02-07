from django.http import HttpResponse
from yelp_searcher import YelpSearcher


# Create your views here.
def place_finder(request, lat, long):
    json = YelpSearcher.get('546 West 113th Street, New York, NY')
    print("json value is: " + json)
#    print("lat is " + lat)
#    print("long is " + long)
    return HttpResponse(json, content_type="application/json")
