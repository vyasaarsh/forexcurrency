# Libraries
import streamlit as st
import pandas as pd 
from time import sleep, time
from collections import defaultdict, deque
import threading
import plotly.express as px
import logging
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
                table_data_rt = pd.DataFrame(filtered_data)
                table_data_rt['% Change'] = table_data_rt['% Change'].apply(lambda x: f"{x:.2f}%")
                sorted_table_rt = table_data_rt[['Symbol', 'Trend', 'Price', 'Change', '% Change']]\
                    .drop_duplicates(subset=['Symbol'])\
                    .sort_values(by='Symbol')
                
                st.data_editor(
                    sorted_table_rt,
                    column_config={
                        "Symbol": st.column_config.TextColumn("Symbol"),
                        "Trend": st.column_config.LineChartColumn("Trend", width="medium"),
                        "Price": st.column_config.NumberColumn("Price"),
                        "Change": st.column_config.NumberColumn("Change"),
                        "% Change": st.column_config.NumberColumn("% Change"),
                    },
                    hide_index=True,
                    use_container_width=True,
                    key=f"rt_data_editor_{int(time())}"
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
            ["Line", "Area"],
            key="chart_type"
        )

    with col3:
        selected_pairs = st.multiselect(
            "💱 Currency Pairs",
            list(CURRENCY_PAIRS.keys()),
            default=list(CURRENCY_PAIRS.keys())[:1],
            key="currency_pairs"
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
    
    selected_symbols = [CURRENCY_PAIRS[pair] for pair in selected_pairs]
    selected_time_range = next((time_range for time_range in TimeRange if time_range.value == option), None)

    time_range_data = []
    if parsed_hist1s_data is not None and parsed_hist1m_data is not None and parsed_hist1h_data is not None:
            time_range_data = get_time_specific_data(selected_time_range.value, parsed_hist1s_data, parsed_hist1m_data, parsed_hist1h_data)

    st.subheader(f"Historical Data for {selected_time_range.value}")
    
    if time_range_data:
            df_time_range = pd.DataFrame(time_range_data)
            df_time_range = df_time_range[df_time_range['Symbol'].isin(selected_symbols)]

        # Calculate metrics
            #metrics_cols = st.columns(4)
            #for idx, symbol in enumerate(df_time_range['Symbol'].unique()):
             #   symbol_data = df_time_range[df_time_range['Symbol'] == symbol]
              #  current_price = symbol_data['Last Price'].iloc[-1]
               # price_change = current_price - symbol_data['Last Price'].iloc[0]
               # price_change_pct = (price_change / symbol_data['Last Price'].iloc[0]) * 100
            
                #with metrics_cols[idx]:
                 #   st.markdown(f"""
                  #      <div class="metric-card">
                   #         <h3>{symbol}</h3>
                    #        <p style="font-size: 24px">{current_price:.4f}</p>
                     #       <p style="color: {'#00ff00' if price_change >= 0 else '#ff0000'}">
                      #          {price_change:+.4f} ({price_change_pct:+.2f}%)
                       #     </p>
                        #</div>
                   # """, unsafe_allow_html=True)
        
    # Ensure that the dataframe contains 'Timestamp' and 'Last Price' for plotting
        
    st.subheader(f"📈 {selected_time_range.value} Price Trends")

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
                    color='Symbol',
                    title=f"{selected_time_range.value} Price Trends",
                    template=template
                )
            #elif chart_type == "Candlestick":
             #   fig = make_subplots(rows=len(selected_symbols), 
              #                    cols=1,
               #                   subplot_titles=[f"{symbol} Price" for symbol in selected_symbols],
                #                  vertical_spacing=0.05)
                
                #for idx, symbol in enumerate(selected_symbols, start=1):
                 #   symbol_data = df_time_range[df_time_range['Symbol'] == symbol]
                  #  fig.add_trace(
                   #     go.Scatter(
                    #        x=symbol_data['Time'],
                     #       y=symbol_data['Last Price'],
                      #      name=symbol,
                       #     line=dict(width=2)
                       # ),
                       # row=idx, col=1
                    #)
                    
               # fig.update_layout(
                #    height=250 * len(selected_symbols),
                 #   template=template,
                  #  showlegend=True
                #)
            else:  # Area chart
                fig = px.area(
                    df_time_range,
                    x='Time',
                    y='Last Price',
                    color='Symbol',
                    title=f"{selected_time_range.value} Price Trends",
                    template=template
                )

            # Common chart updates
            fig.update_layout(
                xaxis_title='Time',
                yaxis_title='Price',
                hovermode='x unified',
                legend=dict(
                    yanchor="top",
                    y=0.99,
                    xanchor="left",
                    x=0.01,
                    bgcolor="rgba(0,0,0,0.5)"
                ),
                plot_bgcolor=bg_color,
                paper_bgcolor=bg_color,
                font=dict(color='white')
            )

            fig.update_xaxes(gridcolor=grid_color, zeroline=False)
            fig.update_yaxes(gridcolor=grid_color, zeroline=False)

            # Add range selector for time range
            fig.update_xaxes(
                rangeslider_visible=True,
                rangeselector=dict(
                    buttons=list([
                        dict(count=1, label="1d", step="day", stepmode="backward"),
                        dict(count=7, label="1w", step="day", stepmode="backward"),
                        dict(count=1, label="1m", step="month", stepmode="backward"),
                        dict(step="all")
                    ])
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
        <div class="creator-credit">AV ANALYTIQUES - <a href="https://www.avanalytiques.com" target="_blank" style="color: #666; text-decoration: none;">www.avanalytiques.com</a> | Data Sourced By OLSEN DATA - <a href="https://www.olsendata.com" target="_blank" style="color: #666; text-decoration: none;">www.olsendata.com</a></div>
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
