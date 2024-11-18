# Forex Currency App

The Forex Currency App is a comprehensive platform built using Streamlit to analyze and visualize forex market data in real-time and across historical timeframes. This app is designed for clients who need quick access to currency trends, price changes, and performance metrics.

## Features 

- **Real-Time Data Display**:  
  Displays continuously updating tables with currency trends, prices, percentage changes, and more.

- **Historical Data Visualization**:  
  Explore currency trends at different intervals:
  - **1-second intervals** (from the start of the previous day)
  - **1-minute intervals** (from the start of the previous month)
  - **1-hour intervals** (from the start of the previous year)

- **Customizable Time Ranges**:  
  Visualize historical data trends for different periods, such as 1 day, 1 week, 1 month, or 1 year.

- **Dynamic Charts**:  
  Trend charts for each data source to help users quickly analyze performance and changes over time.

## How It Works

1. **Real-Time Data**:  
   Fetches live forex data for various currency pairs and displays it in a table with key metrics and mini charts.

2. **Historical Data**:  
   Retrieves data for different intervals (1s, 1m, 1h) and presents it in separate tables and visualizations.

3. **Interactive Graphs**:  
   Enables users to interact with dropdowns to select time ranges and customize their analysis.

## Technologies Used

- **Streamlit**: For building the web application.
- **Python**: Backend scripting for data processing and visualization.
- **SSH Connections**: For fetching real-time and historical data from multiple data sources.
- **Plotly**: For creating dynamic, interactive charts.

## Getting Started

### Prerequisites
- Python 3.9 or later
- Streamlit installed (`pip install streamlit`)
- Required libraries: Plotly, pandas, paramiko

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/forex-currency-app.git
   cd forex-currency-app
