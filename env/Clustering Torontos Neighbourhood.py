import pandas as pd
from bs4 import BeautifulSoup
import requests
import numpy as np
from sklearn.cluster import KMeans
import matplotlib.cm as cm
import matplotlib.colors as colors
from geopy.geocoders import Nominatim
import folium

##
# PART 1 - Getting the data from Wikipedia with BS4
##


link = "https://en.wikipedia.org/wiki/List_of_postal_codes_of_Canada:_M"

# get the html site of the Wikipedia page
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:71.0) Gecko/20100101 Firefox/71.0"}
page = requests.get(link, headers=headers)
soup = BeautifulSoup(page.content, 'html.parser')
print(soup.prettify())
# from the html site, we only need the data inside the table (select only data inside the "table" html tag)
tables = soup.findChildren('table')

# there are more table html tags on the page - choose the relevant for us
Adresses = tables[0]
rows = Adresses.find_all("td") # get a Result Set with all values from this table (inside the "td" html tag)

# for each Value in the result set get the Postal Code, Boroughs and Neighbourhood
Postal_Codes = []
Boroughs = []
Neighborhoods = []
for row in rows:
    if row.find("i") is None: # when "not assigned" exists it is inside the "i" html tag - so only get values who do not have this tag
        Postal_Code = row.find("b").text # html tag "b" where to find the postal code
        print(Postal_Code)
        Borough_Neighborhood = row.find("span").text # html tag "span" where to find the Borough and Neighborhood
        Split = Borough_Neighborhood.split("(") # split the string result inside () is the neighborhood, before the borough
        if len(Split) >= 2 :
            Borough = Split[0]
            Neighborhood = Split[1].split(")")[0]
            # append the 3 informations to a list
            Postal_Codes.append(Postal_Code)
            Boroughs.append(Borough)
            Neighborhoods.append(Neighborhood)

# create the DF
Canada_district_df = pd.DataFrame({"Postal Code":Postal_Codes, "Borough": Boroughs, "Neighborhood": Neighborhoods})
Canada_district_df['Neighborhood'] = Canada_district_df['Neighborhood'].str.replace(r" / ", " , " ) # replace / by , as seperator between neigbourhoods
Canada_district_df.shape # result= (102, 3)

##
# PART 2 - Get the location Data to the df
##


# geo date in the link
geo_data = pd.read_csv("http://cocl.us/Geospatial_data")
# merge the two dfs
Merged_df = Canada_district_df.merge(geo_data, on='Postal Code', how='left')


##
# Part 3 - Cluster the Neighborhoud of Toronto and explore it with folium
##


# get only Boroughs in Toronto:
Toronto_df = Merged_df.loc[Merged_df["Borough"].str.contains("Toronto")]

address = 'Toronto'
# get coordinates of Toronto
geolocator = Nominatim(user_agent="t_explorer")
location = geolocator.geocode(address)
latitude = location.latitude
longitude = location.longitude
print('The geograpical coordinate of Toronto are {}, {}.'.format(latitude, longitude))

# create map of Toronto using latitude and longitude values
map_toronto = folium.Map(location=[latitude, longitude], zoom_start=10)

# add markers to map
for lat, lng, borough, neighborhood in zip(Toronto_df['Latitude'], Toronto_df['Longitude'],
                                           Toronto_df['Borough'], Toronto_df['Neighborhood']):
    label = '{}, {}'.format(neighborhood, borough)
    label = folium.Popup(label, parse_html=True)
    folium.CircleMarker(
        [lat, lng],
        radius=5,
        popup=label,
        color='blue',
        fill=True,
        fill_color='#3186cc',
        fill_opacity=0.7,
        parse_html=False).add_to(map_toronto)

map_toronto


CLIENT_ID = "1BGD4X1AQLSRCHH55KS1HTXN55EE2JD0MED41FABHHSH5ZF3"
CLIENT_SECRET = "ERSHWESPPOVFLM4MV2NDEWEFGOQ5RV303PADVLO4IQA4WRR1"
VERSION = "20180605"
LIMIT = 100

# function to get nearby venues
def getNearbyVenues(names, latitudes, longitudes, radius=500):
    venues_list = []
    for name, lat, lng in zip(names, latitudes, longitudes):
        print(name)

        # create the API request URL
        url = 'https://api.foursquare.com/v2/venues/explore?&client_id={}&client_secret={}&v={}&ll={},{}&radius={}&limit={}'.format(
            CLIENT_ID,
            CLIENT_SECRET,
            VERSION,
            lat,
            lng,
            radius,
            LIMIT)

        # make the GET request
        results = requests.get(url).json()["response"]['groups'][0]['items']

        # return only relevant information for each nearby venue
        venues_list.append([(
            name,
            lat,
            lng,
            v['venue']['name'],
            v['venue']['location']['lat'],
            v['venue']['location']['lng'],
            v['venue']['categories'][0]['name']) for v in results])

    nearby_venues = pd.DataFrame([item for venue_list in venues_list for item in venue_list])
    nearby_venues.columns = ['Neighborhood',
                             'Neighborhood Latitude',
                             'Neighborhood Longitude',
                             'Venue',
                             'Venue Latitude',
                             'Venue Longitude',
                             'Venue Category']

    return (nearby_venues)

# get nearby venues for each neighborhood
toronto_venues = getNearbyVenues(names=Toronto_df['Neighborhood'],
                                   latitudes=Toronto_df['Latitude'],
                                   longitudes=Toronto_df['Longitude']
                                  )
print(toronto_venues.shape) # (1691, 7)

# one hot encoding
toronto_onehot = pd.get_dummies(toronto_venues[['Venue Category']], prefix="", prefix_sep="")

# add neighborhood column back to dataframe
toronto_onehot['Neighborhood'] = toronto_venues['Neighborhood']

# move neighborhood column to the first column
fixed_columns = [toronto_onehot.columns[-1]] + list(toronto_onehot.columns[:-1])
toronto_onehot = toronto_onehot[fixed_columns]

toronto_grouped = toronto_onehot.groupby('Neighborhood').mean().reset_index()

# function to retunr the most common venues
def return_most_common_venues(row, num_top_venues):
    row_categories = row.iloc[1:]
    row_categories_sorted = row_categories.sort_values(ascending=False)

    return row_categories_sorted.index.values[0:num_top_venues]

num_top_venues = 10

indicators = ['st', 'nd', 'rd']

# create columns according to number of top venues
columns = ['Neighborhood']
for ind in np.arange(num_top_venues):
    try:
        columns.append('{}{} Most Common Venue'.format(ind+1, indicators[ind]))
    except:
        columns.append('{}th Most Common Venue'.format(ind+1))

# create a new dataframe
neighborhoods_venues_sorted = pd.DataFrame(columns=columns)
neighborhoods_venues_sorted['Neighborhood'] = toronto_grouped['Neighborhood']

for ind in np.arange(toronto_grouped.shape[0]):
    neighborhoods_venues_sorted.iloc[ind, 1:] = return_most_common_venues(toronto_grouped.iloc[ind, :], num_top_venues)

# set number of clusters
kclusters = 5

toronto_grouped_clustering = toronto_grouped.drop('Neighborhood', 1)

# run k-means clustering
kmeans = KMeans(n_clusters=kclusters, random_state=0).fit(toronto_grouped_clustering)

# add clustering labels
neighborhoods_venues_sorted.insert(0, 'Cluster Labels', kmeans.labels_)

toronto_merged = Toronto_df

# merge toronto_grouped with toronto_data to add latitude/longitude for each neighborhood
toronto_merged = toronto_merged.join(neighborhoods_venues_sorted.set_index('Neighborhood'), on='Neighborhood')

# create map
map_clusters = folium.Map(location=[latitude, longitude], zoom_start=11)

# set color scheme for the clusters
x = np.arange(kclusters)
ys = [i + x + (i * x) ** 2 for i in range(kclusters)]
colors_array = cm.rainbow(np.linspace(0, 1, len(ys)))
rainbow = [colors.rgb2hex(i) for i in colors_array]

# add markers to the map
markers_colors = []
for lat, lon, poi, cluster in zip(toronto_merged['Latitude'], toronto_merged['Longitude'],
                                  toronto_merged['Neighborhood'], toronto_merged['Cluster Labels']):
    label = folium.Popup(str(poi) + ' Cluster ' + str(cluster), parse_html=True)
    folium.CircleMarker(
        [lat, lon],
        radius=5,
        popup=label,
        color=rainbow[cluster - 1],
        fill=True,
        fill_color=rainbow[cluster - 1],
        fill_opacity=0.7).add_to(map_clusters)

map_clusters