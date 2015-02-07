from django.conf.urls import patterns, include, url
from .views import place_finder

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'serendipity.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^get/(?P<lat>-?\d+\.\d+)/(?P<long>-?\d+\.\d+)/$', place_finder, name='place_finder_lat_long'),
#    url(r'get/(?P<address>)/', place_finder, name='place_finder_address')
)
