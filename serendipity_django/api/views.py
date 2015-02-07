from django.http import HttpResponse
from yelp_searcher import YelpSearcher
from geopy.geocoders import Nominatim
from google_searcher import GoogleSearcher


# Create your views here.
def place_finder(request, lat, lon):
#   40.805351, -73.964458
    json = YelpSearcher.get(coords_to_address(lat, lon))
#    json = GoogleSearcher.get('1000 5th Avenue, New York, NY 10028')
#    json = YelpSearcher.get(coords_to_address(lat, lon))
    return HttpResponse(json, content_type="application/json")

def simulate(request, number):
	if number == 1:
		#simulate from time square
		json = YelpSearcher.get('234 W 42nd Street, New York, NY 10036')
		return HttpResponse(json, content_type="application/json")
	elif number == 2:
		#simulate from LA 
		json = GoogleSearcher.get('5950 Wilshire Blvd, Los Angeles, CA 90036')
		return HttpResponse(json, content_type="application/json")

def coords_to_address(lat, lon):
	"""
	
	This function converst latitude and longitude into an address 

	"""
	geolocator = Nominatim()
	coords = str(lat) + ',' + str(lon)
	location = geolocator.reverse(coords)
	print(location.address)
	return location.address
