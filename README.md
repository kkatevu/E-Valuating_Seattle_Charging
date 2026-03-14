# E-Valuating Seattle Charging: Watt’s best? 

![Code Quality](https://github.com/kkatevu/E-Valuating_Seattle_Charging/workflows/Code%20Quality%20%26%20Security/badge.svg)
[![codecov](https://codecov.io/gh/kkatevu/E-Valuating_Seattle_Charging/branch/main/graph/badge.svg)](https://codecov.io/gh/kkatevu/E-Valuating_Seattle_Charging)
![Python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11-blue)
![License](https://img.shields.io/badge/license-MIT-green)


An interactive Streamlit application for exploring EV charging station placement in Seattle.

## Project Group Members:
1. Jason Cao
2. Aiden Tan
3. Roxanne Dimadi
4. Katelyn Vu

## Project Type

### Data Presentation/Tool

## Questions of interest
1. Which areas in Seattle could use EV charging stations?
2. How can we evaluate the effectiveness of the location of Seattle’s current EV charging stations?
3. Which locations in Seattle are in need of EV charging stations?
4. How do the locations of current charging stations compare with our recommended locations (based on our efficiency metric)?

## Project Goal & Output
We will produce an interactive dashboard that allows users to:
- Explore current and recommended EV charging station locations in Seattle
- Visualize demand based on traffic and demographic variables

Final deliverables include:
- A data-driven dashboard with user inputs & filters
- Maps, charts, and efficiency metric visualizations
- Interpretation & recommendations for potential charging station placements

## Data 
### Population Data
Seattle population estimates
- https://geo.wa.gov/datasets/wa-geoservices::demographics-by-zipcode/about

### EV Charging Station Locations 
Alternative Fuels Data Center (AFDC) — Seattle/WA EV charging stations
- https://afdc.energy.gov/stations#/find/nearest?location=Washington&fuel=ELEC&country=US

### Electrical Line Location Data
Displays the line locations of eelctrical lines, above and below ground
- https://catalog.data.gov/dataset/seattle-city-light-lines-81e85

### Washington Vehicle Registration Data
WA Vehicle Registration Transactions
- https://data.wa.gov/Transportation/Vehicle-Registration-Transactions-by-Department-of/brw6-jymh/about_data

### Traffic Data (Seattle)
Traffic Flow Counts
- https://data.seattle.gov/Transportation/Traffic-Counts-by-Study/xucb-vzhc/about_data

## Running our app
If a user would like to run the streamlit application on their local device, they must install the required packages. Instructions are in docs/environment_setip.md. There are example walkthhroughs on examples/walkthrough_example.md that will tell you more about the applications and its features.
