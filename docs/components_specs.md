## Software Components

1. Filtering for ZIPCode logic 
- Input: zipcode 
- Name: valid_zip
- What it does: Verifies if the zipcode is a valid seattle zipcode
- Inputs: zipcode of length 5
- Outputs: Boolean, True if valid , False if not
- Assumptions: User accessed the initial tab

2. Display charging stations on map: 
- Input: user loads page
- Name: display_stations
- What it does: displays all charging stations in Seattle
- Inputs: latitude, longitude, zipcode 
- Outputs: interactive (scrollable, zoomable) map displaying points/icons for where charging stations are located
- Assumptions: user just landed on page, no filters have been applied
 
3. Display charging station details:
- Input: user clicks icon representing specific charging station
- Name: show_station_details
- What it does: pulls up a page that shows the rating for a charging station, and a summary of the features used to evaluate it
- Inputs: geographic details (zipcode, lat, lon), social statistics (local zipcode population, local zipcode EV population/population proportion, local zipcode wage, zipcode-level charging incident stat, zipcode-level violent crime stat, traffic)
- Outputs: page displaying summary of input statistics using visual icons, a close/return button to revert back to the general view of the map
- Assumptions: clicked location (pixels on screen) recognized as part of charging station 

4. Population display
- Input: user loads page
- Name:  display_population 
- What it does: displays EV population through heat-map and able to filter by zip-code
- Inputs: EV population from `registered` data set 
- Outputs: heat-map, hovering able to see details 
- Assumptions: user just landed on page, no filters have been applied


5. Location quality evaluation
- Input: database containing geographic details (zipcode, lat, lon), social statistics (local zipcode population, local zipcode EV population/population proportion, local zipcode wage, zipcode-level charging incident stat, zipcode-level violent crime stat, traffic)
- Name:  loc_eval()
- What it does: function to calculate score to rate the effectiveness of a location
- Inputs: zipcode, lat, lon, local zipcode population, local zipcode EV population/population proportion, local zipcode wage, zipcode-level charging incident stat, zipcode-level violent crime stat, local zipcode traffic density
- Outputs: calculate a score that evaluates the efficacy of a charger’s location 
Assumptions: all data is available, joinable on zipcode


6. Optimal Future EV Station Placement ML Model
- Input: Population density, Housing type distribution, Income levels/ wage data, Vehicle registration rates, Traffic volume, Existing charger density, Distance to highways, Grid capacity by feeder
- Name: Spatial Demand Boosted Regressor for EV Infrastructure Placement
- Implementation: XGBoost Regressor (** IF XGBoost does prediction well)
- What it does: Uses the inputs to create an ‘optimal’ location using the efficacy scoring created prior as our test variable
- Outputs: Heatmap w/ prediction efficacy score and statistic showcasing how well ML models performs
Assumptions: User is familiar with scoring

