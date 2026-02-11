## User Stories

## Use Cases

### 1.View EV population and charger placement in Seattle 
- User: Access “Location” tab
- System: Display “Input Zipcode” 
- User: Enters Zipcode of interest
- System: 
    * [if valid seattle zipcode] Display the map of zipcode area with the corresponding EV population and EV charging stations that are already established
    * [If invalid Seattle zipcode] Display “Invalid Zipcode”
### 2.Evaluate quality of placement for current EV charging stations
- User: Access the “Evaluation” tab
- System: Display “Input Zipcode” and filters for different evaluation criteria (e.g. traffic, population, wages)
- User: Input Zipcode and filters 
- System: Display a page with the rating of a specific station, along with the factors used to calculate it - nearby traffic, nearby population, wages of nearby population (zipcode/city), criminal activity, existing EV infrastructure. 

### 3.Predict optimal future placement of EV charging station
- User: Click to display locations with the most optimal scores based on evaluation algorithm
- System: Add functions to display/hide geographic markers on a map of Seattle, after getting details (e.g. ZIP code, lat & lon) from an internalized machine learning program.  Show an overlay on map of current EV charging stations (for both quality evaluation and EV population tabs) to compare them.

