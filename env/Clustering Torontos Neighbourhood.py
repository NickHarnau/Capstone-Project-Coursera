import pandas as pd
from bs4 import BeautifulSoup
import requests
import re


link = "https://en.wikipedia.org/wiki/List_of_postal_codes_of_Canada:_M"


headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:71.0) Gecko/20100101 Firefox/71.0"}
page = requests.get(link, headers=headers)
soup = BeautifulSoup(page.content, 'html.parser')
print(soup.prettify())
# get all tables from webpage
tables = soup.findChildren('table')

# table of interest
Adresses = tables[0]
rows = Adresses.find_all("td")

Postal_Codes = []
Boroughs = []
Neighborhoods = []
for row in rows:
    if row.find("i") is None:
        Postal_Code = row.find("b").text
        print(Postal_Code)
        Borough_Neighborhood = row.find("span").text
        Split = Borough_Neighborhood.split("(")
        if len(Split) >= 2 :
            Borough = Split[0]
            Neighborhood = Split[1].split(")")[0]
            next_neighbour = []
            """
            if "/" in Neighborhood:
                neighbours = Neighborhood.split("/")
                for neighbour in neighbours:
                    next_neighbour.append(neighbour)
            else:
                next_neighbour.append(Neighborhood)
                """
            Postal_Codes.append(Postal_Code)
            Boroughs.append(Borough)
            Neighborhoods.append(Neighborhood)

Canada_district_df = pd.DataFrame({"PostalCode":Postal_Codes, "Borough": Boroughs, "Neighborhood": Neighborhoods})
Canada_district_df['Neighborhood'] = Canada_district_df['Neighborhood'].str.replace(r" / ", " , " )







