import os
import json
import time
import threading
import concurrent.futures
from MT5Service import MT5Service
import pandas as pd
import streamlit as st

SCANNING_STATUS_FILE = 'scanning_status.json'
POSITIONS_CACHE_FILE = 'positions_cache.json'

def load_scanning_status():
    """Load scanning status from file"""
    if os.path.exists(SCANNING_STATUS_FILE):
        try:
            with open(SCANNING_STATUS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {'scanning': False}
    return {'scanning': False}

def save_scanning_status(status):
    """Save scanning status to file"""
    try:
        with open(SCANNING_STATUS_FILE, 'w') as f:
            json.dump(status, f)
    except Exception as e:
        print(f"Error saving scanning status: {e}")

def load_positions_cache():
    """Load positions cache from file"""
    default_cache = {'data': None, 'timestamp': 0, 'scanning': False, 'progress': {'current': 0, 'total': 0}, 'full_scan_done': False, 'stored_tickets': []}
    if os.path.exists(POSITIONS_CACHE_FILE):
        try:
            with open(POSITIONS_CACHE_FILE, 'r') as f:
                data = json.load(f)
                # Convert timestamp back to float
                if 'timestamp' in data:
                    data['timestamp'] = float(data['timestamp'])
                # Merge with defaults to ensure new keys are present
                default_cache.update(data)
                return default_cache
        except Exception as e:
            print(f"Error loading positions cache: {e}")
    return default_cache

def save_positions_cache(cache):
    """Save positions cache to file"""
    try:
        with open(POSITIONS_CACHE_FILE, 'w') as f:
            json.dump(cache, f, default=str)  # Use default=str to handle datetime objects
    except Exception as e:
        print(f"Error saving positions cache: {e}")

@st.cache_data(ttl=60)
def load_from_mt5(use_groups=True):
    svc = MT5Service()   # persistent connection

    if use_groups:
        accounts = svc.list_accounts_by_groups()
    else:
        accounts = svc.list_accounts_by_range(start=1, end=100000)

    if not accounts:
        return pd.DataFrame()

    return pd.json_normalize(accounts)

def scan_single_account(login, svc, accounts_df):
    """Helper function to scan positions for a single account"""
    positions_data = []
    try:
        positions = svc.get_open_positions(login)
        if positions:
            for p in positions:
                position_data = {
                    'Login': login,
                    'ID': p.get('id'),
                    'Symbol': p.get('symbol'),
                    'Vol': p.get('volume'),
                    'Price': p.get('price'),
                    'P/L': p.get('profit'),
                    'Type': p.get('type'),
                    'Date': p.get('date')
                }
                # Add account details
                account_row = accounts_df[accounts_df['login'] == login]
                if not account_row.empty:
                    position_data['Name'] = account_row['name'].iloc[0] if 'name' in account_row.columns else ''
                    position_data['Email'] = account_row['email'].iloc[0] if 'email' in account_row.columns else ''
                    position_data['Group'] = account_row['group'].iloc[0] if 'group' in account_row.columns else ''
                positions_data.append(position_data)
    except Exception as e:
        print(f"Error scanning positions for login {login}: {e}")
    return positions_data

def background_position_scanner(positions_cache):
    """Background thread function to continuously scan open positions simultaneously"""

    print("Background position scanner thread started!")
    while True:
        try:
            current_time = time.time()
            # Check if we need to scan (only when manually triggered)
            if positions_cache['scanning']:
                positions_cache['scanning'] = True
                print(f"Starting background position scan at {time.strftime('%H:%M:%S')}")

                svc = MT5Service()

                if not positions_cache.get('full_scan_done', False):
                    # Full scan: scan all accounts
                    print("Performing full scan of all accounts...")
                    accounts = svc.list_accounts_by_groups()
                    if not accounts:
                        print("No accounts from groups, trying range scan...")
                        accounts = svc.list_accounts_by_range(start=1, end=100000)

                    if accounts:
                        print(f"Found {len(accounts)} accounts to scan")
                        accounts_df = pd.json_normalize(accounts)
                        if 'login' in accounts_df.columns:
                            accounts_df['login'] = accounts_df['login'].astype(str)

                            logins = accounts_df['login'].unique()
                            total_accounts = len(logins)
                            positions_cache['progress']['total'] = total_accounts
                            positions_cache['progress']['current'] = 0
                            positions_cache['progress']['current_login'] = ''

                            # Scan positions for all accounts simultaneously
                            all_positions = []
                            with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, total_accounts)) as executor:
                                futures = {executor.submit(scan_single_account, login, svc, accounts_df): login for login in logins}
                                for future in concurrent.futures.as_completed(futures):
                                    login = futures[future]
                                    try:
                                        positions_data = future.result()
                                        all_positions.extend(positions_data)
                                        positions_cache['progress']['current'] += 1
                                        positions_cache['progress']['current_login'] = login
                                        # Update cache incrementally for dynamic display
                                        positions_cache['data'] = all_positions
                                        if positions_cache['progress']['current'] % 100 == 0:
                                            print(f"Scanned {positions_cache['progress']['current']}/{total_accounts} accounts, found {len(all_positions)} positions so far")
                                    except Exception as e:
                                        print(f"Error processing future for login {login}: {e}")

                            # Store tickets for incremental updates
                            stored_tickets = [p['ID'] for p in all_positions if p.get('ID')]
                            positions_cache['stored_tickets'] = stored_tickets
                            positions_cache['full_scan_done'] = True

                            # Final update cache
                            positions_cache['data'] = all_positions
                            positions_cache['timestamp'] = current_time
                            save_positions_cache(positions_cache)  # Persist cache to file
                            print(f"Full scan completed: {len(all_positions)} positions found from {total_accounts} accounts. Stored {len(stored_tickets)} tickets for incremental updates.")

                            # Sleep for 5 seconds before rescanning if still active
                            time.sleep(5)
                else:
                    # Incremental scan: full scan to update existing and add new positions
                    print(f"Performing incremental scan (full scan for updates and new positions)...")
                    accounts = svc.list_accounts_by_groups()
                    if not accounts:
                        print("No accounts from groups, trying range scan...")
                        accounts = svc.list_accounts_by_range(start=1, end=100000)

                    if accounts:
                        accounts_df = pd.json_normalize(accounts)
                        if 'login' in accounts_df.columns:
                            accounts_df['login'] = accounts_df['login'].astype(str)

                            logins = accounts_df['login'].unique()
                            total_accounts = len(logins)
                            positions_cache['progress']['total'] = total_accounts
                            positions_cache['progress']['current'] = 0
                            positions_cache['progress']['current_login'] = ''

                            all_positions = []
                            with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, total_accounts)) as executor:
                                futures = {executor.submit(scan_single_account, login, svc, accounts_df): login for login in logins}
                                for future in concurrent.futures.as_completed(futures):
                                    login = futures[future]
                                    try:
                                        positions_data = future.result()
                                        all_positions.extend(positions_data)
                                        positions_cache['progress']['current'] += 1
                                        positions_cache['progress']['current_login'] = login
                                        # Update cache incrementally for dynamic display
                                        positions_cache['data'] = all_positions
                                        if positions_cache['progress']['current'] % 100 == 0:
                                            print(f"Scanned {positions_cache['progress']['current']}/{total_accounts} accounts, found {len(all_positions)} positions so far")
                                    except Exception as e:
                                        print(f"Error processing future for login {login}: {e}")

                            # Update stored tickets with all current position IDs
                            stored_tickets = [p['ID'] for p in all_positions if p.get('ID')]
                            positions_cache['stored_tickets'] = stored_tickets

                            # Final update cache
                            positions_cache['data'] = all_positions
                            positions_cache['timestamp'] = current_time
                            save_positions_cache(positions_cache)  # Persist cache to file
                            print(f"Incremental scan completed: {len(all_positions)} positions found from {total_accounts} accounts. Updated stored tickets with {len(stored_tickets)} IDs.")

                            # Sleep for 5 seconds before rescanning if still active
                            time.sleep(5)
                    else:
                        print("No accounts found to scan")
                        positions_cache['scanning'] = False
                        save_scanning_status({'scanning': False})

        except Exception as e:
            print(f"Error in background position scanner: {e}")
            positions_cache['scanning'] = False

        # Sleep for 1 second for better responsiveness
        time.sleep(1)
