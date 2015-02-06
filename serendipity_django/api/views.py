from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.
def place_finder(request, lat, long):
    json = r'{"Name":"India","Population":1000000,"States":["Madhya Pradesh","Maharastra","Rajasthan"]}'
    print("lat is " + lat)
    print("long is " + long)
    return HttpResponse(json, content_type="application/json")
