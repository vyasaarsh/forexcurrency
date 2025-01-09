from datetime import datetime, timedelta
from constants.timeRange import TimeRange

def get_time_specific_data(time_range, parsed1s_data, parsed1m_data, parsed1h_data):
    current_date = datetime.now()

    def merge_hourly_and_minute_data(hourly_data, minute_data, start_date, end_date):
        # Convert minute data to hourly format for consistency
        converted_minute_data = []
        for data in minute_data:
            try:
                # Parse time using the minute data format
                time = datetime.strptime(data['Time'].strip(), '%Y%m%d %H:%M:%S')
                # Only include data within our target range
                if start_date <= time <= end_date:
                    # Round to the nearest hour for consistency with hourly data
                    rounded_time = time.replace(minute=0, second=0)
                    converted_minute_data.append({
                        'Time': rounded_time.strftime('%d.%m.%Y %H:%M:%S'),
                        'Symbol': data['Symbol'],
                        'Last Price': data['Last Price']
                    })
            except (ValueError, KeyError):
                continue


        # Group minute data by hour and calculate average price
        minute_hourly_data = {}
        for data in converted_minute_data:
            key = (data['Time'], data['Symbol'])
            if key not in minute_hourly_data:
                minute_hourly_data[key] = []
            minute_hourly_data[key].append(data['Last Price'])

        minute_hourly_averaged = [
            {'Time': time, 'Symbol': symbol, 'Last Price': sum(prices) / len(prices)}
            for (time, symbol), prices in minute_hourly_data.items()
        ]


        # Create a set of existing timestamps in hourly data
        hourly_timestamps = {(data['Time'], data['Symbol']) for data in hourly_data}

        # Only add minute data where hourly data is missing
        merged_data = list(hourly_data)
        for data in minute_hourly_averaged:
            if (data['Time'], data['Symbol']) not in hourly_timestamps:
                merged_data.append(data)

        return sorted(merged_data, key=lambda x: datetime.strptime(x['Time'], '%d.%m.%Y %H:%M:%S'))
    
    def is_time_period_started(start_date):
        """Check if the time period has started yet"""
        return current_date >= start_date

    match time_range:

        case TimeRange.LAST_YEAR_HOURLY.value:
            start_date = datetime(current_date.year - 1, 1, 1)  # 1st Jan of last year
            end_date = datetime(current_date.year - 1, 12, 31, 23, 59, 59)  # 31st Dec of last year
            
            # Filter hourly data
            filtered_hourly = [
                data for data in parsed1h_data 
                if start_date <= datetime.strptime(data['Time'], '%d.%m.%Y %H:%M:%S') <= end_date
            ]
            
            # Merge with minute data for missing periods
            return merge_hourly_and_minute_data(filtered_hourly, parsed1m_data, start_date, end_date)
        
        case TimeRange.CURRENT_YEAR_HOURLY.value:
            start_date = datetime(current_date.year, 1, 1)  # 1st Jan of current year
            end_date = current_date.replace(hour=23, minute=59, second=59)  # Current time
            
            # Filter hourly data
            filtered_hourly = [
                data for data in parsed1h_data 
                if start_date <= datetime.strptime(data['Time'], '%d.%m.%Y %H:%M:%S') <= end_date
            ]
            
            # Merge with minute data for missing periods
            return merge_hourly_and_minute_data(filtered_hourly, parsed1m_data, start_date, end_date)

        case TimeRange.CURRENT_YEAR_Q1_HOURLY.value:
            start_date = datetime(current_date.year, 1, 1)  # Q1 start
            end_date = datetime(current_date.year, 3, 31, 23, 59, 59)  # Q1 end
            if not is_time_period_started(start_date):
                return []
            filtered_hourly = [
                data for data in parsed1h_data 
                if start_date <= datetime.strptime(data['Time'], '%d.%m.%Y %H:%M:%S') <= end_date
            ]
            return merge_hourly_and_minute_data(filtered_hourly, parsed1m_data, start_date, end_date)

        case TimeRange.CURRENT_YEAR_Q2_HOURLY.value:
            start_date = datetime(current_date.year, 4, 1)  # Q2 start
            end_date = datetime(current_date.year, 6, 30, 23, 59, 59)  # Q2 end
            
            if not is_time_period_started(start_date):
                return []  # Return empty list if Q2 hasn't started yet
                
            filtered_hourly = [
                data for data in parsed1h_data 
                if start_date <= datetime.strptime(data['Time'], '%d.%m.%Y %H:%M:%S') <= end_date
            ]
            return merge_hourly_and_minute_data(filtered_hourly, parsed1m_data, start_date, end_date)


        case TimeRange.CURRENT_YEAR_Q3_HOURLY.value:
            start_date = datetime(current_date.year, 7, 1)  # Q3 start
            end_date = datetime(current_date.year, 9, 30, 23, 59, 59)  # Q3 end
            
            if not is_time_period_started(start_date):
                return []  # Return empty list if Q3 hasn't started yet
                
            filtered_hourly = [
                data for data in parsed1h_data 
                if start_date <= datetime.strptime(data['Time'], '%d.%m.%Y %H:%M:%S') <= end_date
            ]
            return merge_hourly_and_minute_data(filtered_hourly, parsed1m_data, start_date, end_date)

        case TimeRange.CURRENT_YEAR_Q4_HOURLY.value:
            start_date = datetime(current_date.year, 10, 1)  # Q4 start
            end_date = current_date  # Current time
            
            if not is_time_period_started(start_date):
                return []  # Return empty list if Q4 hasn't started yet
                
            filtered_hourly = [
                data for data in parsed1h_data 
                if start_date <= datetime.strptime(data['Time'], '%d.%m.%Y %H:%M:%S') <= end_date
            ]
            return merge_hourly_and_minute_data(filtered_hourly, parsed1m_data, start_date, end_date)

        case TimeRange.LAST_6_MONTHS_HOURLY.value:
            start_date = current_date - timedelta(days=6*30)  # Approximation of 6 months
            end_date = current_date
            filtered_data = [data for data in parsed1h_data if start_date <= datetime.strptime(data['Time'], '%d.%m.%Y %H:%M:%S') <= end_date]
            return filtered_data
  
        # Minute aggregations

        case TimeRange.LAST_MONTH_MINUTE.value:
            first_day_current_month = current_date.replace(day=1)
            last_day_previous_month = first_day_current_month - timedelta(days=1)
            start_date = last_day_previous_month.replace(day=1)
            end_date = last_day_previous_month
            filtered_data = [
                data for data in parsed1m_data 
                if data.get('Time') and 
                start_date <= datetime.strptime(data['Time'].strip(), '%Y%m%d %H:%M:%S') <= end_date
            ]
            return filtered_data
            
        case TimeRange.LAST_WEEK_MINUTE.value:
            start_date = current_date - timedelta(days=7)  # 7 days ago
            end_date = current_date
            filtered_data = [data for data in parsed1m_data if start_date <= datetime.strptime(data['Time'], '%Y%m%d %H:%M:%S') <= end_date]
            return filtered_data

        # Second aggregations
        case TimeRange.YESTERDAY_SECOND.value:
            start_date = (current_date - timedelta(days=1)).replace(hour=0, minute=0, second=0)  # Yesterday 12 AM
            end_date = start_date.replace(hour=23, minute=59, second=59)  # Yesterday 11:59 PM
            filtered_data = [data for data in parsed1s_data if start_date <= datetime.strptime(data['Time'], '%Y%m%d %H:%M:%S') <= end_date]
            return filtered_data
 
        case TimeRange.TODAY_SECOND.value:
            start_date = current_date.replace(hour=0, minute=0, second=0)  # Today 12 AM
            end_date = current_date  # Current time today
            filtered_data = [data for data in parsed1s_data if start_date <= datetime.strptime(data['Time'], '%Y%m%d %H:%M:%S') <= end_date]
            return filtered_data

        case TimeRange.LAST_12HR_SECOND.value:
            start_date = current_date - timedelta(hours=12)  # 12 hours ago
            end_date = current_date  # Current time
            filtered_data = [data for data in parsed1s_data if start_date <= datetime.strptime(data['Time'], '%Y%m%d %H:%M:%S') <= end_date]
            return filtered_data

        case TimeRange.LAST_24HR_SECOND.value:
            start_date = current_date - timedelta(hours=24)  # 24 hours ago
            end_date = current_date  # Current time
            filtered_data = [data for data in parsed1s_data if start_date <= datetime.strptime(data['Time'], '%Y%m%d %H:%M:%S') <= end_date]
            return filtered_data

        case _:
            return []  # No data for the time range

__all__ = ['get_time_specific_data']
