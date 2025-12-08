import os
import json
import time
import threading
import concurrent.futures
from MT5Service import MT5Service
import pandas as pd
import streamlit as st

# Local cache files (used so Streamlit clients can read pre-fetched data)
CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')
ACCOUNTS_CACHE_FILE = os.path.join(CACHE_DIR, 'accounts_cache.json')

def _ensure_cache_dir():
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
    except Exception:
        pass

def save_accounts_cache(df):
    """Save accounts DataFrame to local cache file as JSON records."""
    try:
        _ensure_cache_dir()
        # use orient='records' so it's easy to load back with json_normalize
        df.to_json(ACCOUNTS_CACHE_FILE, orient='records', force_ascii=False)
    except Exception as e:
        print(f"Error saving accounts cache: {e}")

def load_accounts_cache():
    """Load accounts cache from local JSON file. Returns DataFrame or empty DataFrame."""
    try:
        if os.path.exists(ACCOUNTS_CACHE_FILE):
            return pd.read_json(ACCOUNTS_CACHE_FILE)
    except Exception as e:
        print(f"Error loading accounts cache: {e}")
    return pd.DataFrame()

# Background updater for accounts cache
accounts_updater_thread = None
accounts_updater_stop_event = None

def accounts_updater_runner(interval_seconds=300, use_groups=True, stop_event=None):
    """Runner loop that periodically refreshes the accounts cache by calling
    `load_from_mt5()` (clearing the cache to force fresh fetch). The function
    will run until `stop_event` is set.
    """
    print(f"Accounts updater runner started (interval={interval_seconds}s)")
    while not (stop_event and stop_event.is_set()):
        try:
            # Force a fresh fetch from MT5 and persist to cache file
            try:
                # Use the non-Streamlit helper to fetch and persist accounts so
                # background threads do not call Streamlit cache APIs.
                _fetch_accounts_from_mt5(use_groups)
            except Exception as e:
                print(f"Accounts updater: error fetching from MT5: {e}")
        except Exception as e:
            print(f"Accounts updater unexpected error: {e}")

        # Sleep but exit early if stop requested
        for _ in range(max(1, int(interval_seconds))):
            if stop_event and stop_event.is_set():
                break
            time.sleep(1)

    print("Accounts updater runner stopping")

def start_accounts_updater(interval_seconds=300, use_groups=True):
    """Start the background thread that periodically updates accounts cache.
    Safe to call multiple times; will not start duplicate threads.
    Returns the thread object.
    """
    global accounts_updater_thread, accounts_updater_stop_event
    if accounts_updater_thread and accounts_updater_thread.is_alive():
        return accounts_updater_thread

    accounts_updater_stop_event = threading.Event()
    accounts_updater_thread = threading.Thread(target=accounts_updater_runner, args=(interval_seconds, use_groups, accounts_updater_stop_event), daemon=True)
    accounts_updater_thread.start()
    return accounts_updater_thread

def stop_accounts_updater(timeout=5):
    """Signal the background updater to stop and join the thread."""
    global accounts_updater_thread, accounts_updater_stop_event
    try:
        if accounts_updater_stop_event:
            accounts_updater_stop_event.set()
        if accounts_updater_thread and accounts_updater_thread.is_alive():
            accounts_updater_thread.join(timeout)
    except Exception:
        pass

def get_initial_caches():
    """Get initial caches without loading from files"""
    positions_cache = {'data': None, 'timestamp': 0, 'scanning': True, 'progress': {'current': 0, 'total': 0}, 'full_scan_done': False, 'stored_tickets': []}
    accounts_cache = {'timestamp': 0, 'scanning': False}
    return positions_cache, accounts_cache

# Process-shared positions cache and scanner thread
positions_cache_global = None
positions_scanner_thread = None
positions_scanner_stop_event = None

def get_shared_positions_cache():
    """Return the process-shared positions cache dict."""
    global positions_cache_global
    return positions_cache_global

def start_positions_scanner():
    """Start a single background position scanner for the process.
    This is safe to call multiple times: it will not create duplicate threads.
    The scanner uses `positions_cache_global` as its cache.
    """
    global positions_scanner_thread, positions_scanner_stop_event, positions_cache_global
    if positions_scanner_thread and positions_scanner_thread.is_alive():
        return positions_scanner_thread

    # Ensure we have a cache dict
    if positions_cache_global is None:
        positions_cache_global = load_positions_cache()

    positions_scanner_stop_event = threading.Event()
    positions_scanner_thread = threading.Thread(target=background_position_scanner, args=(positions_cache_global,), daemon=True)
    positions_scanner_thread.start()
    return positions_scanner_thread

def stop_positions_scanner(timeout=5):
    """Signal the background positions scanner to stop and join the thread."""
    global positions_scanner_thread, positions_scanner_stop_event
    try:
        if positions_scanner_stop_event:
            positions_scanner_stop_event.set()
        if positions_scanner_thread and positions_scanner_thread.is_alive():
            positions_scanner_thread.join(timeout)
    except Exception:
        pass

def load_scanning_status():
    """Return default scanning status"""
    return {'scanning': False}

def save_scanning_status(status):
    """No-op: removed JSON storage"""
    pass

def load_positions_cache():
    """Return default positions cache"""
    return {'data': None, 'timestamp': 0, 'scanning': False, 'progress': {'current': 0, 'total': 0}, 'full_scan_done': False, 'stored_tickets': []}

def save_positions_cache(cache):
    """No-op: removed JSON storage"""
    pass

@st.cache_data(ttl=60)
def load_from_mt5(use_groups=True):
    # Wrapper that uses Streamlit's cache. Internally delegates to
    # `_fetch_accounts_from_mt5` which performs the real work without
    # touching Streamlit cache APIs. This allows background threads to
    # call `_fetch_accounts_from_mt5` directly and avoid ScriptRunContext warnings.
    df = _fetch_accounts_from_mt5(use_groups)
    return df


def _fetch_accounts_from_mt5(use_groups=True):
    """Fetch accounts directly from MT5 (no Streamlit cache). Returns DataFrame
    and persists to the local JSON cache file. This is safe to call from
    background threads.
    """
    svc = MT5Service()   # persistent connection

    if use_groups:
        accounts = svc.list_accounts_by_groups()
    else:
        accounts = svc.list_accounts_by_range(start=1, end=100000)

    if not accounts:
        return pd.DataFrame()

    df = pd.json_normalize(accounts)
    # persist fetched accounts to local cache so clients can read without hitting MT5
    try:
        save_accounts_cache(df)
    except Exception as e:
        print(f"Error saving accounts cache from fetch helper: {e}")
    return df

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
                            # store the discovered logins so incremental scans don't need to re-fetch accounts
                            positions_cache['logins'] = list(logins)
                            positions_cache['accounts_timestamp'] = current_time
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
                    # Incremental scan: update existing positions using the stored login list
                    print(f"Performing incremental scan (positions-only for stored logins)...")
                    logins = positions_cache.get('logins') or []

                    # If we don't have stored logins (unlikely), fall back to a lightweight fetch
                    if not logins:
                        print("No stored logins found for incremental scan, attempting to fetch accounts once...")
                        try:
                            accounts = svc.list_accounts_by_groups()
                            if not accounts:
                                accounts = svc.list_accounts_by_range(start=1, end=100000)
                            if accounts:
                                accounts_df = pd.json_normalize(accounts)
                                if 'login' in accounts_df.columns:
                                    accounts_df['login'] = accounts_df['login'].astype(str)
                                    logins = accounts_df['login'].unique()
                                    positions_cache['logins'] = list(logins)
                                    positions_cache['accounts_timestamp'] = current_time
                        except Exception as e:
                            print(f"Incremental scan fallback: failed to fetch accounts: {e}")

                    if logins:
                        total_accounts = len(logins)
                        positions_cache['progress']['total'] = total_accounts
                        positions_cache['progress']['current'] = 0
                        positions_cache['progress']['current_login'] = ''

                        all_positions = []
                        with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, total_accounts)) as executor:
                            # For incremental scanning we can pass an empty accounts_df; scan_single_account will
                            # still attach account metadata when possible. We provide a small dataframe if available.
                            accounts_df = None
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
                        print("No logins available for incremental scan; stopping scanning until manual trigger.")
                        positions_cache['scanning'] = False
                        save_scanning_status({'scanning': False})

        except Exception as e:
            print(f"Error in background position scanner: {e}")
            positions_cache['scanning'] = False

        # Sleep for 1 second for better responsiveness
        time.sleep(1)
