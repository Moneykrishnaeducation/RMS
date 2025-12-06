# TODO for Modifying XAUUSD.py

## Task: Modify XAUUSD.py to prioritize open position volumes over closed ones for XAUUSD positions.

### Steps:
1. [x] Add 'IsOpen' flag to combined_data: False for deals (closed), True for positions (open).
2. [x] Modify static aggregation in update_table() to calculate closed_lot and open_lot separately, then set net_lot = open_lot if open_lot != 0 else closed_lot.
3. [x] Modify dynamic aggregation during scan to do the same, and remove usd_pnl summation, use account profit instead.
4. [x] Update data appends to use the new net_lot calculation.
5. [ ] Test the changes to ensure correct behavior.

### Status:
- [x] Step 1: Add IsOpen to deals and positions
- [x] Step 2: Update static aggregation
- [x] Step 3: Update dynamic aggregation
- [x] Step 4: Update data appends
- [ ] Step 5: Verify changes
