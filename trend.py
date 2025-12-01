import pandas as pd
import streamlit as st
import time
from datetime import datetime
from net_lot import get_symbol_net_lot_pnl
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

__all__ = ['display_trend_view']


def display_trend_view(data):
    """
    Display trend line chart for Net Lot over Time for selected symbols.
    Updates every 15 seconds via page reload.
    """
    st.subheader('📈 Net Lot Trend - Line Chart')
    st.write("This chart shows the trend of Net Lot over time for selected symbols. Data updates every 15 seconds.")

    if data.empty:
        st.info('No account data available.')
        return

    # Initialize session state for trend history if not exists
    if 'trend_history' not in st.session_state:
        st.session_state.trend_history = pd.DataFrame(columns=['timestamp', 'symbol', 'net_lot'])

    try:
        # Get current net lot data
        current_data = get_symbol_net_lot_pnl(data, st.session_state.get('positions_cache'))

        if current_data.empty:
            st.info('No net lot data found.')
            return

        # Add current data to history
        current_time = datetime.now()
        new_rows = []
        for _, row in current_data.iterrows():
            new_rows.append({
                'timestamp': current_time,
                'symbol': row['symbol'],
                'net_lot': row['net_lot']
            })

        # Append to history
        if new_rows:
            new_df = pd.DataFrame(new_rows)
            st.session_state.trend_history = pd.concat([st.session_state.trend_history, new_df], ignore_index=True)

        # Keep only last 100 data points per symbol to avoid memory issues
        # Group by symbol and keep most recent 100 points
        trend_df = st.session_state.trend_history.copy()
        trend_df['timestamp'] = pd.to_datetime(trend_df['timestamp'])
        trend_df = trend_df.sort_values(['symbol', 'timestamp'])

        # Keep last 100 points per symbol
        filtered_dfs = []
        for symbol in trend_df['symbol'].unique():
            symbol_df = trend_df[trend_df['symbol'] == symbol].tail(100)
            filtered_dfs.append(symbol_df)

        if filtered_dfs:
            trend_df = pd.concat(filtered_dfs, ignore_index=True)
            st.session_state.trend_history = trend_df

        # Get available symbols
        available_symbols = sorted(current_data['symbol'].tolist())

        # Symbol selector
        selected_symbols = st.multiselect(
            'Select symbols to display in trend chart',
            options=available_symbols,
            default=available_symbols[:5] if len(available_symbols) >= 5 else available_symbols,
            key='trend_symbols'
        )

        if not selected_symbols:
            st.info('Please select at least one symbol to display the trend chart.')
            return

        # Filter data for selected symbols
        chart_data = trend_df[trend_df['symbol'].isin(selected_symbols)].copy()

        if chart_data.empty:
            st.info('No trend data available for selected symbols.')
            return

        # Prepare data for line chart
        # Pivot to have timestamps as index, symbols as columns
        pivot_df = chart_data.pivot(index='timestamp', columns='symbol', values='net_lot').fillna(method='ffill')

        # Display metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Selected Symbols", len(selected_symbols))
        with col2:
            total_points = len(chart_data)
            st.metric("Data Points", total_points)
        with col3:
            last_update = current_time.strftime('%H:%M:%S')
            st.metric("Last Update", last_update)

        # Display line chart
        st.subheader('Net Lot Trend Over Time')
        st.line_chart(pivot_df)

        # Show raw data table (optional, collapsible)
        with st.expander("📋 View Raw Trend Data"):
            st.dataframe(chart_data.sort_values(['symbol', 'timestamp'], ascending=[True, False]), use_container_width=True)

        # Auto-refresh info
        st.info("📊 Chart updates automatically every 15 seconds. Refresh the page to update now.")

        # Add manual refresh button
        if st.button('🔄 Refresh Now'):
            st.rerun()

    except Exception as e:
        logger.error(f"Error displaying trend view: {str(e)}")
        st.error(f'Failed to display trend chart: {e}')
