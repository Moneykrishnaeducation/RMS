import os
import MT5Manager
import time
import json
import threading
from datetime import datetime

__all__ = ['MT5Service']


def _read_env(dotenv_path=None):
    env = {}
    path = dotenv_path or os.path.join(os.path.dirname(__file__), '.env')
    if not os.path.exists(path):
        return env
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    return env


class MT5Service:
    """Standalone, lightweight wrapper around MT5Manager for read-only operations.

    This avoids depending on Django models and provides simple helpers used by the
    RMS for listing accounts, reading account details and positions, and fetching groups.
    """

    _shared_manager = None
    _shared_lock = threading.Lock()

    def __init__(self, host=None, port=None, login=None, password=None, pump_mode=1, timeout=120000):
        # load defaults from .env if not provided
        env = _read_env()
        host = host or env.get('MT5_HOST')
        port = port or env.get('MT5_PORT')
        login = login or env.get('MT5_MANAGER_USER')
        password = password or env.get('MT5_MANAGER_PASS')

        if host is None or port is None or login is None or password is None:
            raise ValueError('MT5 connection parameters missing (host, port, login, password).')

        self.address = f"{host}:{port}"
        try:
            self.login = int(login)
        except Exception:
            self.login = login
        self.password = password
        self.pump_mode = pump_mode
        self.timeout = timeout
        self.manager = None
        self._instance_dir = None
        self._lock = threading.Lock()

    def _init_manager(self):
        # create per-process instance directory for MT5 library
        pid = str(os.getpid())
        base = os.path.join(os.getcwd(), 'mt5_instances')
        os.makedirs(base, exist_ok=True)
        inst = os.path.join(base, pid)
        os.makedirs(inst, exist_ok=True)
        self._instance_dir = inst
        MT5Manager.InitializeManagerAPIPath(module_path=inst, work_path=inst)
        self.manager = MT5Manager.ManagerAPI()

    def connect(self, max_retries=3, retry_delay=5):
        """Connect to MT5 Manager. Raises Exception on failure after retries."""
        with MT5Service._shared_lock:
            if MT5Service._shared_manager and getattr(MT5Service._shared_manager, 'connected', False):
                return MT5Service._shared_manager
            self._init_manager()
            MT5Service._shared_manager = self.manager
            # Choose pump mode: prefer library constant if available, else use provided numeric
            pump = self.pump_mode
            try:
                # Try to use enum constant if present (safer than hardcoding numeric)
                pump_enum = getattr(MT5Manager.ManagerAPI, 'EnPumpModes', None)
                if pump_enum and hasattr(pump_enum, 'PUMP_MODE_FULL'):
                    pump = pump_enum.PUMP_MODE_FULL
            except Exception:
                # fallback to numeric pump_mode already set
                pump = self.pump_mode

            for attempt in range(max_retries + 1):
                try:
                    if MT5Service._shared_manager.Connect(self.address, int(self.login), str(self.password), pump, int(self.timeout)):
                        # mark connected
                        try:
                            MT5Service._shared_manager.connected = True
                        except Exception:
                            pass
                        return MT5Service._shared_manager
                    else:
                        last = MT5Manager.LastError()
                        # Check if it's a network error (code 7)
                        if hasattr(last, 'code') and last.code == 7:
                            if attempt < max_retries:
                                print(f"Network error connecting to MT5 Manager (attempt {attempt + 1}/{max_retries + 1}). Retrying in {retry_delay} seconds...")
                                time.sleep(retry_delay)
                                continue
                        # try one more time with numeric fallback 1 if not network error or last attempt
                        if pump != 1 and attempt == max_retries:
                            try:
                                if MT5Service._shared_manager.Connect(self.address, int(self.login), str(self.password), 1, int(self.timeout)):
                                    MT5Service._shared_manager.connected = True
                                    return MT5Service._shared_manager
                            except Exception:
                                pass
                        raise Exception(f"Failed to connect to MT5 Manager after {max_retries + 1} attempts: {last}")
                except Exception as e:
                    if attempt < max_retries:
                        print(f"Exception connecting to MT5 Manager (attempt {attempt + 1}/{max_retries + 1}): {e}. Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        raise e

    def close(self):
        try:
            if self.manager and getattr(self.manager, 'connected', False):
                # MT5 API doesn't provide explicit disconnect; try to mark disconnected
                self.manager.connected = False
        except Exception:
            pass

    def get_group_list(self):
        """Return list of group names from MT5."""
        mgr = self.connect()
        groups = []
        try:
            total = mgr.GroupTotal()
        except Exception:
            total = 0
        if not total:
            return groups
        for i in range(total):
            try:
                g = mgr.GroupNext(i)
                if not g:
                    continue
                name = None
                for attr in ('Group', 'Name', 'group', 'name', 'GroupName'):
                    if hasattr(g, attr):
                        name = getattr(g, attr)
                        break
                if name:
                    groups.append(name)
            except Exception:
                continue
        return groups

    def get_account_details(self, login_id):
        """Return detailed account dict or None."""
        mgr = self.connect()
        try:
            user = mgr.UserGet(int(login_id))
            account = mgr.UserAccountGet(int(login_id))
            if not user or not account:
                return None
            return {
                'login': getattr(user, 'Login', None),
                'name': f"{getattr(user, 'FirstName', '')} {getattr(user, 'LastName', '')}".strip(),
                'email': getattr(user, 'EMail', None),
                'balance': float(getattr(account, 'Balance', 0.0)),
                'equity': float(getattr(account, 'Equity', 0.0)),
                'margin': float(getattr(account, 'Margin', 0.0)),
                'margin_free': float(getattr(account, 'MarginFree', 0.0)),
                'margin_level': float(getattr(account, 'MarginLevel', 0.0)),
                'profit': float(getattr(account, 'Profit', 0.0)),
                'group': getattr(user, 'Group', None),
                'leverage': getattr(user, 'Leverage', None),
                'rights': getattr(user, 'Rights', None),
                'last_access': getattr(user, 'LastAccess', None),
                'registration': getattr(user, 'Registration', None),
            }
        except Exception:
            return None

    def get_open_positions(self, login_id):
        """Return list of open positions for the given login id."""
        mgr = self.connect()
        try:
            positions = mgr.PositionGet(int(login_id))
            if not positions:
                return []
            out = []
            for p in positions:
                out.append({
                    'date': getattr(p, 'TimeCreate', None),
                    'id': getattr(p, 'Position', None),
                    'symbol': getattr(p, 'Symbol', None),
                    'volume': round(getattr(p, 'Volume', 0) / 10000, 2),
                    'price': getattr(p, 'PriceOpen', None),
                    'profit': getattr(p, 'Profit', None),
                    'type': 'Buy' if getattr(p, 'Action', None) == 0 else 'Sell',
                })
            return out
        except Exception:
            return []

    def list_accounts_by_index(self):
        """Iterate accounts using UserTotal/UserGet (index based). Returns list of dicts."""
        mgr = self.connect()
        accounts = []
        try:
            total = mgr.UserTotal()
        except Exception:
            return accounts
        for i in range(total):
            try:
                user = mgr.UserGet(i)
                if not user:
                    continue
                acc = mgr.UserAccountGet(getattr(user, 'Login', None))
                account_data = {
                    'login': getattr(user, 'Login', None),
                    'name': getattr(user, 'Name', None) or f"{getattr(user, 'FirstName', '')} {getattr(user, 'LastName', '')}".strip(),
                    'email': getattr(user, 'EMail', None),
                    'group': getattr(user, 'Group', None),
                    'leverage': getattr(user, 'Leverage', None),
                    'balance': float(getattr(acc, 'Balance', 0.0)) if acc else 0.0,
                    'equity': float(getattr(acc, 'Equity', 0.0)) if acc else 0.0,
                    'profit': float(getattr(acc, 'Profit', 0.0)) if acc else 0.0,
                }
                accounts.append(account_data)
            except Exception:
                continue
        return accounts

    def list_accounts_by_range(self, start, end, workers=8, batch_size=100, output_file=None):
        """Scan numeric login IDs from start..end (inclusive) and return found accounts.

        This is a reliable fallback when index-based enumeration returns few results.
        """
        mgr = self.connect()
        from concurrent.futures import ThreadPoolExecutor, as_completed

        start = int(start)
        end = int(end)
        if end < start:
            start, end = end, start

        def check_login(login_id):
            try:
                user = mgr.UserGet(int(login_id))
                if not user:
                    return None
                acc = mgr.UserAccountGet(int(login_id))
                return {
                    'login': getattr(user, 'Login', None),
                    'name': getattr(user, 'Name', None) or f"{getattr(user, 'FirstName', '')} {getattr(user, 'LastName', '')}".strip(),
                    'email': getattr(user, 'EMail', None),
                    'group': getattr(user, 'Group', None),
                    'leverage': getattr(user, 'Leverage', None),
                    'balance': float(getattr(acc, 'Balance', 0.0)) if acc else 0.0,
                    'equity': float(getattr(acc, 'Equity', 0.0)) if acc else 0.0,
                }
            except Exception:
                return None

        accounts = []
        # optional streaming to file to avoid memory growth
        write_file = None
        if output_file:
            write_file = open(output_file, 'w', encoding='utf-8')

        try:
            with ThreadPoolExecutor(max_workers=int(workers)) as ex:
                futures = {ex.submit(check_login, lid): lid for lid in range(start, end + 1)}
                for fut in as_completed(futures):
                    res = fut.result()
                    if res:
                        accounts.append(res)
                        if write_file:
                            write_file.write(json.dumps(res, default=str) + '\n')
        finally:
            if write_file:
                write_file.close()

        return accounts

    def list_accounts_by_groups(self, output_file=None):
        """Enumerate users by group using UserGetByGroup. Returns list of account dicts.

        This method is useful when index-based enumeration doesn't return all users.
        """
        mgr = self.connect()
        accounts = []
        write_file = None
        if output_file:
            write_file = open(output_file, 'w', encoding='utf-8')

        try:
            try:
                total = mgr.GroupTotal()
            except Exception:
                total = 0
            for i in range(total):
                try:
                    g = mgr.GroupNext(i)
                    if not g:
                        continue
                    group_name = getattr(g, 'Group', None)
                    if not group_name:
                        continue
                    # UserGetByGroup may return iterable of user objects
                    try:
                        users = mgr.UserGetByGroup(group_name)
                    except Exception:
                        users = []
                    if not users:
                        continue
                    for u in users:
                        try:
                            login = getattr(u, 'Login', None)
                            acc = mgr.UserAccountGet(login)
                            account_data = {
                                'login': login,
                                'name': getattr(u, 'Name', None) or f"{getattr(u, 'FirstName', '')} {getattr(u, 'LastName', '')}".strip(),
                                'email': getattr(u, 'EMail', None),
                                'group': getattr(u, 'Group', None),
                                'leverage': getattr(u, 'Leverage', None),
                                'balance': float(getattr(acc, 'Balance', 0.0)) if acc else 0.0,
                                'equity': float(getattr(acc, 'Equity', 0.0)) if acc else 0.0,
                                'profit': float(getattr(acc, 'Profit', 0.0)) if acc else 0.0,
                            }
                            accounts.append(account_data)
                            if write_file:
                                write_file.write(json.dumps(account_data, default=str) + '\n')
                        except Exception:
                            continue
                except Exception:
                    continue
        finally:
            if write_file:
                write_file.close()

        return accounts

    def list_deals_by_login(self, login_id):
        """Return list of closed deals for the given login id."""
        mgr = self.connect()
        try:
            deals = mgr.DealGet(int(login_id))
            if not deals:
                return []
            out = []
            for d in deals:
                out.append({
                    'Deal': getattr(d, 'Deal', None),
                    'Login': getattr(d, 'Login', None),
                    'Symbol': getattr(d, 'Symbol', None),
                    'Profit': getattr(d, 'Profit', None),
                    'Volume': round(getattr(d, 'Volume', 0) / 10000, 2),
                    'Price': getattr(d, 'Price', None),
                    'Time': getattr(d, 'Time', None),
                    'Type': getattr(d, 'Action', None),
                    'Entry': getattr(d, 'Entry', None),
                })
            return out
        except Exception:
            return []

    def search_accounts_by_name_email(self, name=None, email=None):
        """Search accounts by name or email. Returns list of matching accounts."""
        accounts = self.list_accounts_by_groups()
        if not accounts:
            return []

        results = []
        for acc in accounts:
            acc_name = acc.get('name', '').lower()
            acc_email = acc.get('email', '').lower()
            if name and name.lower() in acc_name:
                results.append(acc)
            elif email and email.lower() in acc_email:
                results.append(acc)
        return results


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='MT5Service quick test')
    parser.add_argument('--action', choices=['groups', 'list', 'detail', 'positions'], default='groups')
    parser.add_argument('--login', help='login id for detail/positions')
    args = parser.parse_args()

    svc = MT5Service()
    if args.action == 'groups':
        print(json.dumps(svc.get_group_list(), indent=2, default=str))
    elif args.action == 'list':
        lst = svc.list_accounts_by_index()
        print(json.dumps({'count': len(lst)}, indent=2))
    elif args.action == 'detail':
        print(json.dumps(svc.get_account_details(args.login), indent=2, default=str))
    elif args.action == 'positions':
        print(json.dumps(svc.get_open_positions(args.login), indent=2, default=str))
