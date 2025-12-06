import pandas as pd
import streamlit as st
import time
from datetime import datetime
from net_lot import get_symbol_net_lot_pnl
import logging
import plotly.graph_objects as go
import plotly.io as pio
from streamlit_autorefresh import st_autorefresh

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

__all__ = ['display_trend_view']

# Use dark theme for charts
pio.templates.default = "plotly_dark"


def display_trend_view(data):
    """
    Display trend line chart for Net Lot over Time for selected symbols.
    Updates every 5 seconds via page reload.
    """
    st.subheader('📈 Net Lot Trend - Line Chart')
    st.write("This chart shows the trend of Net Lot over time for selected symbols. Data updates every 5 seconds.")

    # Auto-refresh every 15 seconds

    st_autorefresh(interval=15000, key="refresh_counter")
    if data.empty:
        st.info('No account data available.')
        return

    # Initialize history only first time
    if 'trend_history' not in st.session_state:
        st.session_state.trend_history = pd.DataFrame(columns=['timestamp', 'symbol', 'net_lot'])

    try:
        # Get latest net lot
        current_data = get_symbol_net_lot_pnl(data, st.session_state.get('positions_cache'))

        if current_data.empty:
            st.info('No net lot data found.')
            return

        current_time = datetime.now()

        # Add new rows to history
        new_rows = []
        for _, row in current_data.iterrows():
            new_rows.append({
                'timestamp': current_time,
                'symbol': row['symbol'],
                'net_lot': row['net_lot']
            })

        if new_rows:
            new_df = pd.DataFrame(new_rows)
            st.session_state.trend_history = pd.concat([st.session_state.trend_history, new_df], ignore_index=True)

        # Clean history keep last 100 per symbol
        trend_df = st.session_state.trend_history.copy()
        trend_df['timestamp'] = pd.to_datetime(trend_df['timestamp'])
        trend_df = trend_df.sort_values(['symbol', 'timestamp'])

        filtered_dfs = []
        for symbol in trend_df['symbol'].unique():
            filtered_dfs.append(trend_df[trend_df['symbol'] == symbol].tail(100))

        trend_df = pd.concat(filtered_dfs, ignore_index=True)
        st.session_state.trend_history = trend_df

        # Use all symbols
        available_symbols = sorted(current_data['symbol'].tolist())
        selected_symbols = available_symbols

        st.write("Displaying trends for all selected symbols.")

        # Filter for UI
        chart_data = trend_df[trend_df['symbol'].isin(selected_symbols)].copy()

        if chart_data.empty:
            st.info('No trend data available.')
            return

        # Metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Selected Symbols", len(selected_symbols))
        with col2:
            st.metric("Data Points", len(chart_data))
        with col3:
            st.metric("Last Update", current_time.strftime('%H:%M:%S'))

        # ------------------------------
        #   PLOTLY UI (NEW, IMPROVED)
        # ------------------------------
        for i in range(0, len(selected_symbols), 2):
            col1, col2 = st.columns(2)

            # First symbol
            with col1:
                symbol = selected_symbols[i]
                st.subheader(f'{symbol} Net Lot')

                symbol_data = chart_data[chart_data['symbol'] == symbol].set_index('timestamp')['net_lot']

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=symbol_data.index,
                    y=symbol_data.values,
                    mode="lines+markers",
                    line=dict(width=3),
                    marker=dict(size=6),
                    name=symbol,
                ))

                # X-axis formatting like screenshot
                fig.update_xaxes(
                    title="Time",
                    tickformat="%H:%M",      # show time
                    dtick=5 * 60 * 1000,              # 5 minutes
                    showgrid=True,
                    gridcolor="rgba(255,255,255,0.1)",
                    type="date"              # force datetime axis
                )

                fig.update_yaxes(
                    title="Net Lot",
                    showgrid=True,
                    gridcolor="rgba(255,255,255,0.1)",
                )

                # Layout match MT5 style
                fig.update_layout(
                    height=350,
                    margin=dict(l=20, r=20, t=40, b=20),
                    showlegend=False,
                )

                st.plotly_chart(fig, use_container_width=True)

            # Second symbol if exists
            if i + 1 < len(selected_symbols):
                with col2:
                    symbol = selected_symbols[i + 1]
                    st.subheader(f'{symbol} Net Lot')

                    symbol_data = chart_data[chart_data['symbol'] == symbol].set_index('timestamp')['net_lot']

                    fig = go.Figure()

                    fig.add_trace(go.Scatter(
                        x=symbol_data.index,
                        y=symbol_data.values,
                        mode="lines+markers",
                        line=dict(width=3),
                        marker=dict(size=6),
                        name=symbol,
                    ))

                    # X-axis formatting like screenshot
                    fig.update_xaxes(
                        title="Time",
                        tickformat="%H:%M",      # show time
                        dtick=5 * 60 * 1000,              # 5 minutes
                        showgrid=True,
                        gridcolor="rgba(255,255,255,0.1)",
                        type="date"              # force datetime axis
                    )

                    fig.update_yaxes(
                        title="Net Lot",
                        showgrid=True,
                        gridcolor="rgba(255,255,255,0.1)",
                    )

                    # Layout match MT5 style
                    fig.update_layout(
                        height=350,
                        margin=dict(l=20, r=20, t=40, b=20),
                        showlegend=False,
                    )

                    st.plotly_chart(fig, use_container_width=True)

        # Raw data
        with st.expander("📋 View Raw Trend Data"):
            st.dataframe(chart_data.sort_values(['symbol', 'timestamp'], ascending=[True, False]), use_container_width=True)

        st.info("📊 Chart updates automatically every 15 seconds. Refresh the page to update now.")

        if st.button('🔄 Refresh Now'):
            st.rerun()

    except Exception as e:
        logger.error(f"Error displaying trend view: {str(e)}")
        st.error(f'Failed to display trend chart: {e}')