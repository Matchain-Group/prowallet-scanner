# wallet-dat-scanner (Enhanced Dashboard Edition)

**Open-source Bitcoin wallet.dat batch scanner** with an interactive dashboard.
Scan a folder of old Bitcoin `wallet.dat` backups and find out which ones
still hold a balance and which are empty — all with a user-friendly interface.

## Features

✅ **Interactive Dashboard** — Menu-driven interface (Options 1-5)  
✅ **Multiple Input Modes**:
  - Scan wallet.dat files from a directory
  - Extract and scan from ZIP archives
  - Paste private keys directly and check balances
  - View previous reports

✅ **Real On-Chain Lookups** — Uses Blockstream Esplora API for accurate balances  
✅ **Fast & Efficient** — Configurable API delay & retry logic  
✅ **Multiple Export Formats** — CSV and JSON reports  
✅ **Secure** — All processing is local; wallet files never uploaded  
✅ **Open Source** — MIT licensed

## ⚠️ Security First

- These files contain **private keys**. Run this on a machine you trust.
  Never upload actual `wallet.dat` files anywhere online.
- `.gitignore` in this repo already excludes `*.dat` and dump files, so you
  won't accidentally commit your wallets if you push to GitHub.
- Once you find a wallet with a balance, **sweep the funds to a brand-new,
  securely generated wallet** as soon as possible.
- **Temporary files are auto-deleted** unless settings are changed.

## Requirements

- **Bitcoin Core** (`bitcoind` + `bitcoin-cli`) installed and on your PATH.
  - Download: https://bitcoincore.org/en/download/
  - Version **22.x–25.x recommended**. Some newer Core builds (26+) drop
    support for old Berkeley-DB-format wallets.
- **Python 3.8+**

## Quick Start (Dashboard Mode)

### Setup

```bash
git clone <this-repo-url>
cd wallet-dat-scanner
pip install -r requirements.txt
```

### Launch the Dashboard

```bash
python wallet_dashboard.py
```

You'll see the interactive menu:

```
======================================================================
              BITCOIN WALLET SCANNER DASHBOARD
              Secure • Fast • Transparent • Open Source
======================================================================

What would you like to do?

[1] Scan wallet.dat files from directory
[2] Extract and scan wallet.dat from ZIP archive
[3] Paste private keys directly
[4] View previous reports
[5] Configure settings
[0] Exit

Enter your choice (0-5): 
```

## How to Use Each Option

### Option 1: Scan Directory

**Use this to scan multiple wallet.dat files in a folder.**

```
Enter path to wallets directory: /path/to/my/wallets
✓ Found 5 wallet.dat file(s)
  • wallet_01.dat
  • wallet_02.dat
  ...
Proceed with scan? (y/n): y
```

The tool will:
1. Start a local Bitcoin Core node (temporary, no sync needed)
2. Load each wallet.dat file
3. Extract all addresses
4. Query on-chain balances via Blockstream API
5. Display results
6. Save CSV + JSON reports to `./wallet_reports/`

**Time estimate:** ~1 minute per 50 addresses checked

---

### Option 2: Scan from ZIP

**Use this if your wallets are in a ZIP archive (e.g., from GitHub or cloud backup).**

```
Enter path to ZIP file: /path/to/my_wallets.zip
✓ Extracted 5 wallet.dat file(s)
```

The tool will:
1. Extract the ZIP to a temporary directory
2. Find all `.dat` files inside
3. Run the same scan as Option 1
4. Clean up temp files automatically

**Why use this:**
- Download a public wallet archive without manually extracting
- Keep directory paths organized
- Safer than manually handling wallet files

---

### Option 3: Paste Private Keys

**Use this if you have private keys (WIF format) you want to check balances for.**

```
Paste Bitcoin private keys (WIF format), one per line.
Press Ctrl+D (Unix/Mac) or Ctrl+Z then Enter (Windows) when done.

5KN7MzqK5wt2TP1fQCYyHBtDrXdJuXbUzm4A9rKAteeLi3Qi5zf
5J...
```

The tool will:
1. Validate each key as proper WIF format
2. Import each into a temporary Bitcoin Core wallet
3. Derive the corresponding address
4. Check on-chain balance
5. Display and save results

**Time estimate:** ~5-10 minutes per key (due to blockchain rescan)

---

### Option 4: View Previous Reports

**Review any CSV reports you generated in previous sessions.**

```
Found 3 report(s):

[1] scan_20260704_101523.csv
[2] scan_20260703_150210.csv
[3] manual_keys_20260703_095000.csv

Select report (1-3) or 0 to cancel:
```

The tool displays a formatted summary with:
- Total BTC found
- Number of funded wallets
- Table of all results

---

### Option 5: Settings

**Customize tool behavior:**

```
[1] API delay (current: 0.3s)
    → Seconds between Blockstream API calls
    → Lower = faster but risks rate limits
    → Higher = safer, more polite to API
    
[2] Keep dump files (current: False)
    → Toggle whether to save extracted key dumps
    → ⚠️ Dumps contain PRIVATE KEYS, keep secure
    
[3] Output directory (current: ./wallet_reports)
    → Where CSV/JSON reports are saved
```

---

## How It Works Under the Hood

### The Process

1. **Bitcoin Core Node** — Spins up a temporary, isolated `bitcoind` instance.
   No blockchain sync needed; only the wallet subsystem is used.
2. **Wallet Loading** — Copies each `.dat` file and loads it via `bitcoin-cli loadwallet`.
3. **Address Extraction** — Runs `dumpwallet` to extract all addresses.
   Prompts for passphrase if encrypted.
4. **On-Chain Lookup** — Queries Blockstream Esplora API for real, confirmed balances.
5. **Report Generation** — Writes CSV and JSON. Auto-deletes temp files for security.

### Why This Is Secure

- ✅ **Everything runs locally** — Bitcoin Core is on your machine
- ✅ **Private keys never leave your machine** — Only addresses are sent to API
- ✅ **Temporary wallets** — Created fresh each run, deleted after
- ✅ **API is read-only** — Only queries balance data, can't modify anything
- ✅ **No authentication needed** — Uses public Blockstream API (no account)

---

## Example Output

### Dashboard Results

```
======================================================================
                          RESULTS SUMMARY
======================================================================

Total BTC found: 0.45210000
Wallets with balance: 2/5

Wallet               Addresses    Funded     Balance (BTC)   Status
------------------------------------------------------------------------
wallet_07            40           3          0.45210000      HAS BALANCE
wallet_33            8            1          0.00120000      HAS BALANCE
wallet_01            12           0          0.00000000      EMPTY
wallet_02            15           0          0.00000000      EMPTY
wallet_04            22           0          0.00000000      EMPTY

✓ CSV report: ./wallet_reports/scan_20260704_120530.csv
✓ JSON report: ./wallet_reports/scan_20260704_120530.json
```

### CSV Report

```csv
wallet,addresses_found,addresses_checked,funded_addresses,total_btc,status
wallet_07,40,40,3,0.45210000,HAS BALANCE
wallet_33,8,8,1,0.00120000,HAS BALANCE
wallet_01,12,12,0,0.00000000,EMPTY
```

### JSON Report

```json
[
  {
    "wallet": "wallet_07",
    "addresses_found": 40,
    "addresses_checked": 40,
    "funded_addresses": 3,
    "total_btc": 0.4521,
    "status": "HAS BALANCE"
  },
  ...
]
```

---

## Performance & Speed

| Operation | Time | Notes |
|-----------|------|-------|
| Start Bitcoin Core | 10-15 sec | One-time per scan session |
| Load a wallet.dat | 5-10 sec | Depends on wallet size |
| Check 50 addresses | 2-3 min | At 0.3s API delay |
| Scan 100 wallets (40 addr each) | 30-45 min | ~4,000 addresses total |
| Check 1 private key | 5-10 min | Includes blockchain rescan |

**Pro tips for speed:**
1. Increase API delay gradually if you hit rate limits (instead of crashing)
2. Batch similar-sized wallets together
3. Run overnight for large scans

---

## Testing Before You Run on Real Wallets

To verify the tool works on your machine:

```bash
# Create a test wallet with Bitcoin Core
bitcoind -daemon
bitcoin-cli createwallet testwallet
bitcoin-cli -rpcwallet=testwallet getnewaddress
bitcoin-cli stop

# Copy its wallet.dat to a test folder
mkdir test_wallets
cp ~/.bitcoin/wallets/testwallet/wallet.dat test_wallets/

# Run the scanner
python wallet_dashboard.py
# Select [1] and point to ./test_wallets/
# It should report 0 BTC (since the test wallet is empty)
```

---

## Troubleshooting

### "bitcoind not found on PATH"
**Solution:** Install Bitcoin Core from https://bitcoincore.org/en/download/

Verify installation:
```bash
bitcoind -version
bitcoin-cli -version
```

### "Failed to load wallet" / "BerkeleyDB" error
**Problem:** Your wallet.dat is from a very old Bitcoin Core version (pre-0.8).

**Solution:**
1. Install Bitcoin Core 23.x or earlier
2. Or use [pywallet.py](https://github.com/jackjack-jj/pywallet) to extract
   addresses directly from the raw wallet file

### Slow API responses / "429 Too Many Requests"
**Problem:** Hitting Blockstream API rate limits.

**Solution:** Increase API delay in Settings (Option 5). Try 1.0-2.0 seconds.

### "Permission denied" on wallet files
**Solution:** Make files readable:
```bash
chmod 644 /path/to/wallet.dat
```

### "Invalid key format (expected WIF)" in Option 3
**Solution:** Private keys must be in WIF format, starting with `5` or `K`/`L`:
- Valid: `5KN7MzqK5wt2TP1...` (51 chars)
- Invalid: Raw hex strings (use conversion tool first)

---

## Advanced: Manual Setup from GitHub

If you're deploying to your own GitHub:

```bash
# Clone this repo
git clone https://github.com/Matchain-Group/wallet-dat-scanner.git
cd wallet-dat-scanner

# Install dependencies
pip install -r requirements.txt

# Launch
python wallet_dashboard.py
```

The `.gitignore` automatically excludes:
- `*.dat` (wallet files)
- Dump files (private key extracts)
- `wallet_reports/` (your generated reports)

So your actual wallets **will never be committed to GitHub** by accident.

---

## Contributing & Licensing

**This is open-source software.**

- Report bugs: Create an issue
- Submit improvements: Send a pull request
- Fork and customize: MIT licensed, do what you want

See `LICENSE` for full details.

---

**Built with ❤️ for Bitcoin security and transparency.**

Open source. Auditable. Local-first. No cloud. No tracking.
