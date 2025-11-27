import argparse
import json
import MT5Manager
from MT5Service import MT5Service


def main():
    parser = argparse.ArgumentParser(description='RMS CLI - read-only MT5 operations')
    sub = parser.add_subparsers(dest='cmd')

    sub.add_parser('groups', help='List MT5 groups')

    sub_list = sub.add_parser('list', help='List MT5 accounts (index based)')

    sub_detail = sub.add_parser('detail', help='Show account details')
    sub_detail.add_argument('login', help='Account login')

    sub_pos = sub.add_parser('positions', help='Show open positions for account')
    sub_pos.add_argument('login', help='Account login')

    sub_scan = sub.add_parser('scan', help='Scan numeric login range')
    sub_scan.add_argument('--start', required=True, type=int, help='Start login (inclusive)')
    sub_scan.add_argument('--end', required=True, type=int, help='End login (inclusive)')
    sub_scan.add_argument('--workers', type=int, default=8, help='Worker threads')
    sub_scan.add_argument('--output', help='Optional output JSONL file')
    sub_diag = sub.add_parser('diag', help='Run MT5 connectivity diagnostics')
    sub_diag.add_argument('--sample-login', type=int, help='Optional sample login to check')

    args = parser.parse_args()
    svc = MT5Service()

    if args.cmd == 'groups':
        print(json.dumps(svc.get_group_list(), indent=2, default=str))
    elif args.cmd == 'list':
        accounts = svc.list_accounts_by_index()
        print(json.dumps({'count': len(accounts), 'sample': accounts[:10]}, indent=2, default=str))
    elif args.cmd == 'scan':
        res = svc.list_accounts_by_range(args.start, args.end, workers=args.workers, output_file=args.output)
        print(json.dumps({'found': len(res), 'sample': res[:10]}, indent=2, default=str))
    elif args.cmd == 'diag':
        # Connectivity diagnostics - don't crash on connection errors
        try:
            mgr = svc.connect()
            info = {}
            try:
                info['connected'] = bool(getattr(mgr, 'connected', False))
            except Exception:
                info['connected'] = True
            try:
                info['user_total'] = mgr.UserTotal()
            except Exception as e:
                info['user_total_error'] = str(e)
            try:
                info['group_total'] = mgr.GroupTotal()
            except Exception as e:
                info['group_total_error'] = str(e)
            try:
                info['last_error'] = MT5Manager.LastError()
            except Exception:
                info['last_error'] = None

            if args.sample_login:
                try:
                    info['sample_user'] = {}
                    u = mgr.UserGet(int(args.sample_login))
                    info['sample_user']['exists'] = bool(u)
                except Exception as e:
                    info['sample_user_error'] = str(e)

        except Exception as e:
            info = {'connect_error': str(e)}

        print(json.dumps(info, indent=2, default=str))
    elif args.cmd == 'detail':
        print(json.dumps(svc.get_account_details(args.login), indent=2, default=str))
    elif args.cmd == 'positions':
        print(json.dumps(svc.get_open_positions(args.login), indent=2, default=str))
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
