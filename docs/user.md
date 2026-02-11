## User Stories

### Municipal city planner

Sam works for the City of Seattle’s Department of Transportation, working as a city planner who seeks to achieve the city’s goal of becoming a carbon neutral city by 2050 by increasing the electrification of its vehicles and optimizing its EV charging grid. To do this, Sam wants to identify the locations of existing EV charging stations and determine the areas that are most in-need of such stations based on the population, safety, and existing municipal infrastructure. To easily understand the data he’s working with, Sam would prefer to view a dashboard that displays his desired geographic details that includes sufficient background information on the objects being represented. As a planner, Sam may need a benchmark to evaluate the needs of EV stations, and that benchmark can provide some insight for him to plan EV station infrastructure in the future. From his bachelor’s degree, Sam has basic knowledge of how to read statistical charts or data visualization, and he may have interactive experience with applications before. He also possesses a keen knowledge of how city infrastructure should be built, and eagerly seeks an intuitive, interactive tool that will help him accomplish this task.  

### Private EV Charger Manufacturing Companies



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
- System: 
    * [if valid seattle zipcode] Populate data specific to the zipcode. Including the rating of a specific station, along with the factors used to calculate it - nearby traffic, nearby population, wages of nearby population (zipcode/city), criminal activity, existing EV infrastructure. 
    * [If invalid Seattle zipcode] Display “Invalid Zipcode”
- User: Click on a station 
- System: Display pop-up/page showing details about the measures used to evaluate it


### 3.Predict optimal future placement of EV charging station
- User: Click to display locations with the most optimal scores based on evaluation algorithm
- System: Display “Input Zipcode” and filters for different evaluation criteria (e.g. traffic, population, wages)
- User: Input Zipcode and filters 
- System: 
    * [if valid seattle zipcode] Show an overlay on map of current EV charging stations (for both quality evaluation and EV population tabs) to compare them.
    * [If invalid Seattle zipcode] Display “Invalid Zipcode”

