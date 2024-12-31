# FLICKERING STOPPED AND HISTORICAL TIMESTAMP CHANGE AND REALTIME COLUMN CHANGES IN SIZE
#https://claude.ai/chat/a126edc0-449e-4d4d-88e6-e6f0397339f8

# Libraries
import streamlit as st
import pandas as pd
from time import sleep, time
from collections import defaultdict, deque
import threading
import plotly.express as px
import logging
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from constants.timeRange import TimeRange
from utils.getTimeRangeSpecificData import get_time_specific_data
from utils.connectionUtils import connect_ssh_agent
from utils.dataParser import parse_real_time_data, parse_hist1h_data, parse_hist1m_data, parse_hist1s_data

# Retrieve Real-Time (rt) data  
def get_real_time_data_rt(channel, historic_data):
    if channel.recv_ready():
        data = channel.recv(4096).decode('ascii')
        table_data = parse_real_time_data(data, historic_data)
    
        for symbol in historic_data.keys():
            if symbol not in [item['Symbol'] for item in table_data]:
                last_known_price = historic_data[symbol][-1]
                table_data.append({
                    'Symbol': symbol,
                    'Price': last_known_price,
                    'Change': 0,
                    '% Change': 0,
                    'Trend': list(historic_data[symbol]),
                })

        return table_data

# Retrieve Historical data
def get_historical_data(userName, timeout=300):
    print('connecting to ssh agent %s', userName)
    channel = connect_ssh_agent(userName)
    print('connected to channel of ssh agent %s', userName)
    print('fetching data for ssh channel of %s', userName)
    buffer = ''
    start_time = time()
    while True:
        if channel.recv_ready():
            data = channel.recv(16384).decode('ascii')
            buffer += data
        elif time() - start_time > timeout:
            logging.warning(f"Timeout reached for fetching data from {userName}")
            break
        if channel.exit_status_ready():
                break
        sleep(0.1)
    print('fetching data for ssh channel of is completed', userName)
    print('closing channel for ssh agent ', userName)
    channel.close()
    print('closed channel for ssh agent ', userName)
    return buffer

# Simulate multiple heavy data fetching functions
def fetch_resource_1h():
    historical_data_1h = get_historical_data("hist1h")
    parsed_hist1h_data = parse_hist1h_data(historical_data_1h)
    return parsed_hist1h_data


def fetch_resource_1m():
    historical_data_1m = get_historical_data("hist1m")
    parsed_hist1m_data = parse_hist1m_data(historical_data_1m)
    return parsed_hist1m_data

def fetch_resource_1s():
    historical_data_1s = get_historical_data("hist1s")
    parsed_hist1s_data = parse_hist1s_data(historical_data_1s)
    return parsed_hist1s_data

# Background fetching function to run in parallel
def fetch_all_historical_resources():
    parsed_hist1s_data = [None]
    parsed_hist1m_data = [None]
    parsed_hist1h_data = [None]
    
    def cached_fetch_resource_1h():
        parsed_hist1h_data[0] = fetch_resource_1h()

    def cached_fetch_resource_1m():
        parsed_hist1m_data[0] = fetch_resource_1m()

    def cached_fetch_resource_1s():
        parsed_hist1s_data[0] = fetch_resource_1s()

    
    thread1 = threading.Thread(target=cached_fetch_resource_1h)
    thread2 = threading.Thread(target=cached_fetch_resource_1m)
    thread3 = threading.Thread(target=cached_fetch_resource_1s)

    # Start threads
    thread1.start()
    thread2.start()
    thread3.start()

    # Wait for all threads to finish
    thread1.join()
    thread2.join()
    thread3.join()

    return parsed_hist1s_data[0], parsed_hist1m_data[0], parsed_hist1h_data[0]

@st.cache_resource
def fetch_all_historical_resource_once():
    return fetch_all_historical_resources()

def display_real_time_data():
    st.markdown("### 🔄 Real-Time Price Updates")
    
    # Check if it's weekend
    current_day = pd.Timestamp.now().day_name()
    if current_day in ['Saturday', 'Sunday']:
        st.info("🕒 Market is closed on weekends. Real-time data updates will resume on Monday.", icon="ℹ️")
        st.markdown("""
            <div style='padding: 20px; background-color: #262730; border-radius: 10px; text-align: center;'>
                <h2>No Data to Display on {}</h2>
                <p>The forex market is closed during weekends. Regular trading and real-time updates resume on Monday.</p>
            </div>
        """.format(current_day), unsafe_allow_html=True)
        return
    
    # Add custom CSS for compact metric cards
    st.markdown("""
    <style>
    .compact-metric-card {
        background-color: #262730;
        padding: 10px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        margin-bottom: 10px;
    }
    .compact-metric-card h3 {
        text-align: center;
        color: #ffffff;
        font-size: 16px;
        margin-bottom: 5px;
    }
    .compact-metric-card p {
        text-align: center;
        margin: 2px 0;
        font-size: 14px;
    }
    .compact-metric-card .current-price {
        font-size: 16px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Predefined symbols to ensure only these are shown
    PREDEFINED_SYMBOLS = ['EURUSD', 'GBPUSD', 'USDCHF']
    
    # Initialize session state variables
    if 'rt_historic_data' not in st.session_state:
        st.session_state.rt_historic_data = defaultdict(deque)
    if 'highest_prices' not in st.session_state:
        st.session_state.highest_prices = {symbol: 0 for symbol in PREDEFINED_SYMBOLS}
    if 'lowest_prices' not in st.session_state:
        st.session_state.lowest_prices = {symbol: float('inf') for symbol in PREDEFINED_SYMBOLS}
    if 'rt_channel' not in st.session_state:
        st.session_state.rt_channel = connect_ssh_agent("rt")
    
    # Create static metric cards container
    st.markdown("### 📊 Price Statistics")
    metric_cols = st.columns(len(PREDEFINED_SYMBOLS))
    
    # Create metric card placeholders
    metric_cards = {}
    for idx, symbol in enumerate(PREDEFINED_SYMBOLS):
        with metric_cols[idx]:
            metric_cards[symbol] = st.empty()
    
    # Create data table placeholder
    data_placeholder = st.empty()
    
    # Initialize a dataframe in session state if it doesn't exist
    if 'rt_table_data' not in st.session_state:
        st.session_state.rt_table_data = pd.DataFrame(columns=['Symbol', 'Trend', 'Price', 'Change', '% Change'])

    while True:
        new_data_rt = get_real_time_data_rt(
            st.session_state.rt_channel, 
            st.session_state.rt_historic_data
        )
        
        if new_data_rt:
            # Filter and sort data for predefined symbols
            filtered_data = [
                item for item in new_data_rt 
                if item['Symbol'] in PREDEFINED_SYMBOLS
            ]
            
            # Create a new DataFrame from the filtered data
            new_df = pd.DataFrame(filtered_data)
            new_df['% Change'] = new_df['% Change'].apply(lambda x: f"{x:.2f}%")
            new_df = new_df[['Symbol', 'Trend', 'Price', 'Change', '% Change']].sort_values(by='Symbol').drop_duplicates(subset=['Symbol'])


            # Efficiently update the session state DataFrame
            st.session_state.rt_table_data = new_df

            for item in filtered_data:
                item['% Change'] = f"{item['% Change']:.2f}%" 

            # Update highest and lowest prices
            for item in filtered_data:
                symbol = item['Symbol']
                price = item['Price']
                st.session_state.highest_prices[symbol] = max(
                    st.session_state.highest_prices[symbol],
                    price
                )
                st.session_state.lowest_prices[symbol] = min(
                    st.session_state.lowest_prices[symbol],
                    price if price > 0 else float('inf')
                )
            
            # Update metric cards
            for item in filtered_data:
                symbol = item['Symbol']
                current_price = item['Price']
                highest_price = st.session_state.highest_prices[symbol]
                lowest_price = st.session_state.lowest_prices[symbol]
                
                with metric_cards[symbol]:
                    st.markdown(f"""
                        <div class="compact-metric-card">
                            <h3>{symbol}</h3>
                            <p class="current-price">Current: {current_price:.4f}</p>
                            <p style="color: #00ff00;">High: {highest_price:.4f}</p>
                            <p style="color: #ff4444;">Low: {lowest_price:.4f}</p>
                        </div>
                    """, unsafe_allow_html=True)
            
            # Update data table
            with data_placeholder.container():
                st.markdown("### 📈 Live Price Updates")
                st.dataframe(
                    st.session_state.rt_table_data,
                    column_config={
                        "Symbol": st.column_config.TextColumn("Symbol", width=30),
                        "Trend": st.column_config.LineChartColumn("Trend", width=600),
                        "Price": st.column_config.NumberColumn("Price", width=30),
                        "Change": st.column_config.NumberColumn("Change", width=30),
                        "% Change": st.column_config.TextColumn("% Change", width=30),
                    },
                    hide_index=True,
                    use_container_width=True
                )
            
        sleep(1)
def display_historical_data():
    st.markdown("### 🔍 Filters")
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

    CURRENCY_PAIRS = {
        'EUR/USD': 'EURUSD',
        'USD/CHF': 'USDCHF',
        'GBP/USD': 'GBPUSD'
    }

    with col1:
        option = st.selectbox(
            "📅 Time Range",
            [time_range.value for time_range in TimeRange.__members__.values()],
            key="time_range"
        )

    with col2:
        chart_type = st.selectbox(
            "📊 Chart Type",
            ["Line"],
            key="chart_type"
        )

    with col3:
        selected_pair = st.selectbox(
            "💱 Currency Pairs",
            list(CURRENCY_PAIRS.keys()),
            key="currency_pair"
        )

    with col4:
        chart_style = st.selectbox(
            "🎨 Chart Style",
            ["Default", "Trading View", "Minimal"],
            key="chart_style"
        )

    st.divider()

    # Get historical data
    parsed_hist1s_data, parsed_hist1m_data, parsed_hist1h_data = fetch_all_historical_resource_once()
    
    selected_symbol = CURRENCY_PAIRS[selected_pair]
    selected_time_range = next((time_range for time_range in TimeRange if time_range.value == option), None)

    time_range_data = []
    if parsed_hist1s_data is not None and parsed_hist1m_data is not None and parsed_hist1h_data is not None:
        time_range_data = get_time_specific_data(selected_time_range.value, parsed_hist1s_data, parsed_hist1m_data, parsed_hist1h_data)

    st.subheader(f"Historical Data for {selected_time_range.value}")

    if time_range_data:
        df_time_range = pd.DataFrame(time_range_data)
        df_time_range = df_time_range[df_time_range['Symbol'] == selected_symbol]

        st.subheader(f"📈 {selected_time_range.value}")

        if 'Time' in df_time_range.columns and 'Last Price' in df_time_range.columns:
            # Apply chart style
            if chart_style == "Trading View":
                template = "plotly_dark"
                bg_color = '#131722'
                grid_color = 'rgba(42, 46, 57, 0.2)'
            elif chart_style == "Minimal":
                template = "none"
                bg_color = 'rgba(0,0,0,0)'
                grid_color = 'rgba(128,128,128,0.1)'
            else:
                template = "plotly_dark"
                bg_color = 'rgba(0,0,0,0)'
                grid_color = 'rgba(128,128,128,0.1)'

            if chart_type == "Line":
                fig = px.line(
                    df_time_range,
                    x='Time',
                    y='Last Price',
                    title=f"{selected_time_range.value}",
                    template=template
                )
                
                # Remove duplicate traces
                fig.data = [fig.data[0]]
                
                n_ticks = 10  # Desired maximum number of ticks
                indices = np.linspace(0, len(df_time_range) - 1, n_ticks, dtype=int)
                x_axis_labels = df_time_range['Time'].iloc[indices]
                fig.update_layout(xaxis_tickvals=x_axis_labels.tolist())

                # Update line appearance
                fig.update_traces(
                    line=dict(width=1.5, color='#0066FF'),
                    showlegend=False
                )

            # Common chart updates
            fig.update_layout(
                xaxis_title='Time',
                yaxis_title='Price',
                hovermode='x unified',
                plot_bgcolor=bg_color,
                paper_bgcolor=bg_color,
                font=dict(color='white'),
                margin=dict(t=50, b=50, l=50, r=50),
                showlegend=False
            )

            # Update axes
            fig.update_xaxes(
                gridcolor=grid_color,
                zeroline=False,
                showline=True,
                linewidth=1,
                linecolor='rgba(255,255,255,0.2)',
                mirror=True
            )
            
            fig.update_yaxes(
                gridcolor=grid_color,
                zeroline=False,
                showline=True,
                linewidth=1,
                linecolor='rgba(255,255,255,0.2)',
                mirror=True
            )

            # Add range selector
            fig.update_xaxes(
                rangeslider=dict(visible=True, thickness=0.05),
                rangeselector=dict(
                    buttons=list([
                        dict(count=1, label="1d", step="day", stepmode="backward"),
                        dict(count=7, label="1w", step="day", stepmode="backward"),
                        dict(count=1, label="1m", step="month", stepmode="backward"),
                        dict(step="all")
                    ]),
                    bgcolor=bg_color,
                    activecolor='#1e88e5'
                )
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No data available for the selected time range.")

def main():
    st.set_page_config(layout="wide", page_title="Currency App", page_icon="📈")

    # Apply styling
    st.markdown("""
        <style>
        /* Reset margins and padding for the body */
        body {
            margin: 0;
            padding: 0;
        }     
        .stApp {
            background-color: #0e1117;
            color: #ffffff;
        }
        /* Remove default Streamlit padding */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            padding-left: 2rem;
            padding-right: 2rem;
        }
        .big-font {
            font-size: 24px !important;
            font-weight: bold !important;
        }
        .metric-card {
            background-color: #262730;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .creator-credit {
            position: fixed;
            top: 14px;
            left: 16px;
            z-index: 9999;  /* Increased z-index */
            font-size: 16px;
            color: #666;
            background-color: #11ffee00; /* Added semi-transparent background */
            padding: 4px 8px;  /* Added padding */
            border-radius: 4px;  /* Added rounded corners */
        }
        /* Modified padding to prevent overlap */
        .main .block-container {
            padding-top: 48px !important;  /* Increased top padding */
            padding-bottom: 48px !important;  /* Increased bottom padding */
            margin-top: 0px !important;  /* Reset margin */
        }
        /* Additional fix for Streamlit header */
        header {
            z-index: 99 !important;
        }
        </style>
        <div class="creator-credit">AV ANALYTIQUES - <a href="https://www.avanalytiques.com" target="_blank" style="color: #666; text-decoration: none;">www.avanalytiques.com</a> | Data Sourced from OLSEN DATA - <a href="https://www.olsendata.com" target="_blank" style="color: #666; text-decoration: none;">www.olsendata.com</a></div>
        """, unsafe_allow_html=True)
    
    # Add the hide Streamlit style here
    hide_streamlit_style = """ 
    <style>
    div[data-testid="stToolbar"] { visibility: hidden; height: 0%; position: fixed; } 
    div[data-testid="stDecoration"] { visibility: hidden; height: 0%; position: fixed; } 
    div[data-testid="stStatusWidget"] { visibility: hidden; height: 0%; position: fixed; } 
    #MainMenu { visibility: hidden; height: 0%; } 
    header { visibility: hidden; height: 0%; } 
    footer { visibility: hidden; height: 0%; } 
    </style> 
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)

    st.markdown('<p class="big-font">📊 Forex Currency App</p>', unsafe_allow_html=True)
    #st.divider()

    # Create tabs
    tab1, tab2 = st.tabs(["📈 Historical Data", "🔄 Real-Time Data"])

    # Handle each tab separately
    with tab1:
        display_historical_data()

    with tab2:
        if 'rt_update_thread' not in st.session_state:
            st.session_state.rt_update_thread = None
        
        display_real_time_data()

if __name__ == "__main__":
    main()
