# Complete Usage Guide — Wallet Scanner Dashboard

## Table of Contents

1. [Installation & Setup](#installation--setup)
2. [Launching the Dashboard](#launching-the-dashboard)
3. [Menu Options Explained](#menu-options-explained)
4. [How It Works](#how-it-works)
5. [Report Formats](#report-formats)
6. [Performance Tips](#performance-tips)
7. [Security Deep Dive](#security-deep-dive)
8. [Advanced Usage](#advanced-usage)

---

## Installation & Setup

### Prerequisites

Before you start, ensure you have:

1. **Bitcoin Core installed** (version 22.x–25.x recommended)
   - Download: https://bitcoincore.org/en/download/
   - Check: `bitcoind -version`

2. **Python 3.8 or higher**
   - Check: `python3 --version`

3. **This repository cloned or downloaded**

### Step-by-Step Installation

```bash
# 1. Clone the repository
git clone https://github.com/Matchain-Group/wallet-dat-scanner.git
cd wallet-dat-scanner

# 2. Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Verify setup
bitcoind -version
bitcoin-cli -version
python3 wallet_dashboard.py --help
```

**Expected output:**
```
usage: wallet_dashboard.py [-h] [--legacy]

Bitcoin wallet.dat scanner with interactive dashboard.

optional arguments:
  -h, --help  show this help message and exit
  --legacy    Use legacy command-line interface instead of dashboard
```

---

## Launching the Dashboard

### Basic Launch

```bash
python3 wallet_dashboard.py
```

### With Legacy Mode (Original CLI)

```bash
# Fall back to the original scan_wallets.py if needed
python3 scan_wallets.py /path/to/wallets --out report.csv
```

---

## Menu Options Explained

### Option [1] — Scan Directory

**What it does:**
- Asks for a folder path containing `.dat` files
- Lists all wallet files found
- Confirms before scanning
- Runs full on-chain balance check
- Displays results and saves reports

**When to use:**
- You have multiple wallet.dat files organized in one folder
- You want to batch-scan them all at once
- You're cleaning up old backups

**Example workflow:**

```
Enter your choice (0-5): 1

Option 1: Scan Directory
--------------------------------------------------

Enter path to wallets directory: /Users/me/old_wallets

✓ Found 3 wallet.dat file(s)
  • wallet_2015.dat
  • wallet_2017.dat
  • wallet_2019.dat

Proceed with scan? (y/n): y

Starting Bitcoin Core node...
[1/3] wallet_2015
  OK
  -> 0.00000000 BTC across 0 funded address(es): EMPTY

[2/3] wallet_2017
  [10/40] [20/40] [30/40]
  -> 0.05420000 BTC across 2 funded address(es): HAS BALANCE

[3/3] wallet_2019
  -> 0.00000000 BTC across 0 funded address(es): EMPTY

======================================================================
                          RESULTS SUMMARY
======================================================================

Total BTC found: 0.05420000
Wallets with balance: 1/3

Wallet               Addresses    Funded     Balance (BTC)   Status
------------------------------------------------------------------------
wallet_2017          40           2          0.05420000      HAS BALANCE
wallet_2015          25           0          0.00000000      EMPTY
wallet_2019          32           0          0.00000000      EMPTY

✓ CSV report: ./wallet_reports/scan_20260704_120530.csv
✓ JSON report: ./wallet_reports/scan_20260704_120530.json
```

**Time estimate:** 2–3 minutes per 50 addresses checked

---

### Option [2] — Scan ZIP Archive

**What it does:**
- Asks for a path to a `.zip` file
- Extracts it to a temporary directory
- Finds all `.dat` files inside
- Runs the same scan as Option [1]
- Cleans up temp files automatically

**When to use:**
- You downloaded wallets as a ZIP from GitHub or a cloud backup
- You want to avoid manually extracting and managing folders
- You want automatic cleanup after scanning

**Example workflow:**

```
Enter your choice (0-5): 2

Option 2: Scan ZIP Archive
--------------------------------------------------

Enter path to ZIP file: /Users/me/Downloads/old_wallets_backup.zip

✓ Extracted 5 wallet.dat file(s)
  • wallet_01.dat
  • wallet_02.dat
  • wallet_03.dat
  • wallet_04.dat
  • wallet_05.dat

Proceed with scan? (y/n): y

Starting Bitcoin Core node...
[1/5] wallet_01
  ...
```

**Why this is better than manual extraction:**
- No dangling temporary folders to clean up
- One-step process
- Safer workflow

---

### Option [3] — Paste Private Keys

**What it does:**
- Prompts you to paste private keys (one per line, WIF format)
- Validates each key as proper Bitcoin WIF format
- Creates a temporary wallet and imports each key
- Derives the corresponding address
- Checks on-chain balance
- Deletes the temporary wallet
- Displays results

**When to use:**
- You have loose private keys you want to check balances for
- You're recovering lost keys and want to verify they have funds
- You're consolidating funds from multiple old keys

**Example workflow:**

```
Enter your choice (0-5): 3

Option 3: Manual Private Key Input
--------------------------------------------------

Paste Bitcoin private keys (WIF format), one per line.
Press Ctrl+D (Unix/Mac) or Ctrl+Z then Enter (Windows) when done.

5KN7MzqK5wt2TP1fQCYyHBtDrXdJuXbUzm4A9rKAteeLi3Qi5zf
✓ Key added
5KJJaMr7oKe4E4rLPVvfv6r7eQ8VQU4FkLxMfKCTEVfYDQkqZmB
✓ Key added
^D

✓ Loaded 2 private key(s)

WARNING: This requires Bitcoin Core to derive addresses.
Proceeding will load keys into a temporary, isolated wallet.

Continue? (y/n): y

[1/2] Checking key...
Address: 1A1z7agoat5owMRQTRC4rFj7BcV97Pfem
Balance: 0.12345678 BTC [HAS BALANCE]

[2/2] Checking key...
Address: 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2
Balance: 0.00000000 BTC [EMPTY]

Result:
manual_key_1: 0.12345678 BTC
manual_key_2: 0.00000000 BTC

✓ CSV report: ./wallet_reports/manual_keys_20260704_102030.csv
```

**Time estimate:** 5–10 minutes per key (includes blockchain rescan)

**Valid WIF key formats:**
- Starts with `5` (uncompressed) → 51 characters
- Starts with `K` or `L` (compressed) → 51 characters
- Examples:
  - ✅ `5KN7MzqK5wt2TP1fQCYyHBtDrXdJuXbUzm4A9rKAteeLi3Qi5zf`
  - ✅ `KwdB92NP6cci41PN4exPC335secretword3to4secretkey5...`
  - ❌ `0123456789abcdef...` (raw hex)
  - ❌ `ypub...` (public key)

---

### Option [4] — View Previous Reports

**What it does:**
- Lists all CSV reports from previous scans
- Lets you select one to view
- Displays results in formatted table
- Shows summary statistics

**When to use:**
- You want to review a previous scan's results
- You need to double-check findings
- You're comparing multiple scans over time

**Example workflow:**

```
Enter your choice (0-5): 4

Option 4: Previous Reports
--------------------------------------------------

Found 4 report(s):

[1] scan_20260704_120530.csv
[2] scan_20260703_095015.csv
[3] manual_keys_20260703_160245.csv
[4] scan_20260702_141020.csv

Select report (1-4) or 0 to cancel: 1

======================================================================
                    REPORT: scan_20260704_120530.csv
======================================================================

Total BTC: 0.05420000
Funded wallets: 1/3

Wallet               Addresses    Balance (BTC)
-----------------------------------------------
wallet_2017          40           0.05420000
wallet_2015          25           0.00000000
wallet_2019          32           0.00000000

Press Enter to continue...
```

---

### Option [5] — Configure Settings

**What it does:**
- Opens a submenu to customize tool behavior
- Changes persist until you modify them again
- Affects all subsequent scans in the same session

**Available settings:**

#### [1] API Delay
```
API delay (current: 0.3s)
Enter API delay in seconds (default 0.3): 1.0
✓ Updated
```

**What it does:** Controls the pause between Blockstream API calls.
- **Lower (0.1–0.3s):** Faster scanning, but risks rate limits
- **Higher (1.0–2.0s):** Safer, more respectful to API
- **Use higher if:** You hit "429 Too Many Requests" errors

#### [2] Keep Dump Files
```
Keep dump files (current: False)
✓ Updated to True
```

**What it does:** Toggle whether to save extracted wallet dumps.
- **Default (False):** Deletes dumps after scanning (recommended for security)
- **Enable (True):** Keeps dumps for advanced analysis (⚠️ contains private keys!)

⚠️ **WARNING:** Dump files contain **raw private keys in plaintext**. Only enable if you know what you're doing.

#### [3] Output Directory
```
Output directory (current: ./wallet_reports)
Enter output directory: /Users/me/Desktop/my_reports
✓ Updated
```

**What it does:** Changes where reports are saved.
- Default: `./wallet_reports/` (created automatically)
- You can change to any path

---

## How It Works

### The Scanning Process (Step by Step)

1. **Start Bitcoin Core Node** (10–15 sec)
   - Launches `bitcoind` in a temporary directory
   - Configures it NOT to sync the blockchain (no hours of waiting!)
   - Only the wallet subsystem is needed

2. **Load Wallet** (5–10 sec per wallet)
   - Copies your `.dat` file into the node's wallet folder
   - Runs `bitcoin-cli loadwallet`
   - If encrypted, prompts for passphrase

3. **Dump Addresses** (1–3 sec per wallet)
   - Runs `bitcoin-cli dumpwallet` to extract all addresses
   - Saves to temporary file
   - Parses out Bitcoin addresses using regex

4. **Check On-Chain Balance** (varies)
   - For each address, queries the Blockstream API
   - API call: `GET https://blockstream.info/api/address/{address}`
   - Returns: funded amount + spent amount = balance
   - Respects rate limits with configurable delays

5. **Display Results** (instant)
   - Shows formatted summary table
   - Highlights wallets with balance in green
   - Saves CSV and JSON reports

6. **Cleanup** (5–10 sec)
   - Stops Bitcoin Core node
   - Deletes temporary wallet directory
   - Optionally deletes dump files

**Total time for 100 wallets with 40 addresses each:** ~30–45 minutes

---

## Report Formats

### CSV Report

**File:** `./wallet_reports/scan_20260704_120530.csv`

```csv
wallet,addresses_found,addresses_checked,funded_addresses,total_btc,status
wallet_2017,40,40,2,0.05420000,HAS BALANCE
wallet_2015,25,25,0,0.00000000,EMPTY
wallet_2019,32,32,0,0.00000000,EMPTY
```

**Columns:**
- `wallet` — Filename of the .dat file
- `addresses_found` — Total unique addresses extracted
- `addresses_checked` — How many were queried (failures excluded)
- `funded_addresses` — How many have BTC
- `total_btc` — Sum of all balances
- `status` — "HAS BALANCE" or "EMPTY"

**Import into Excel/Sheets:**
```bash
# On Mac/Linux
open wallet_reports/scan_*.csv

# On Windows
start wallet_reports\scan_*.csv

# Or copy-paste the contents into Excel
```

### JSON Report

**File:** `./wallet_reports/scan_20260704_120530.json`

```json
[
  {
    "wallet": "wallet_2017",
    "addresses_found": 40,
    "addresses_checked": 40,
    "funded_addresses": 2,
    "total_btc": 0.0542,
    "status": "HAS BALANCE"
  },
  {
    "wallet": "wallet_2015",
    "addresses_found": 25,
    "addresses_checked": 25,
    "funded_addresses": 0,
    "total_btc": 0.0,
    "status": "EMPTY"
  }
]
```

**Use cases:**
- Import into databases
- Process with Python/Node scripts
- Feed into data analysis tools

---

## Performance Tips

### Scanning Speed

| Task | Time |
|------|------|
| Start Bitcoin Core | 10–15 sec |
| Load a wallet | 5–10 sec |
| Check 50 addresses | 2–3 min |
| Scan 5 wallets (40 addresses each) | 8–12 min |
| Scan 100 wallets (40 addresses each) | 30–45 min |

### How to Speed Up Scans

**1. Lower API delay (risky)**
```
Settings → [1] API delay → 0.1
```
Faster but risks Blockstream rate limits (429 errors).

**2. Batch similar-sized wallets**
- Scan 10 small wallets first
- Scan large wallets separately
- Allows you to spot problems early

**3. Run overnight**
```bash
nohup python3 wallet_dashboard.py &
```
Let it run in the background while you sleep.

**4. Use ZIP mode if possible**
- Option [2] avoids disk I/O overhead
- Faster than manually organizing files

### Bandwidth

- Each address check = ~1 KB downloaded from Blockstream API
- 4,000 addresses = ~4 MB total
- **Network-efficient; no streaming needed**

---

## Security Deep Dive

### Private Keys Never Leave Your Machine

**Flow:**

```
wallet.dat (your file)
    ↓
Bitcoin Core (local, air-gapped process)
    ↓ extracts addresses (NOT keys)
    ↓
Blockstream API (public endpoint)
    └─ Receives: Bitcoin addresses (public info)
    └─ Sends: Balance data (public info)
    └─ Cannot: See keys, modify wallets, steal funds
```

**Key security properties:**
- ✅ Private keys stay in Bitcoin Core's memory (never written to disk by you)
- ✅ Addresses sent to API are **public** information
- ✅ API is **read-only** (no write access to blockchain)
- ✅ No authentication = no credential theft
- ✅ HTTPS encryption in transit

### Temporary Files

**What gets created:**
1. Bitcoin Core datadir (temporary)
   - Contains: Wallet files, logs, prune data
   - Deleted: After scan completes
   - Sensitive: No

2. Dump files (temporary)
   - Contains: Addresses + **private keys** (if you enable `--keep-dumps`)
   - Deleted: Automatically (unless you change settings)
   - Sensitive: ⚠️ YES — keep secure if enabled

**Auto-deletion:**
```python
# Default behavior (secure)
if not args.keep_dumps:
    shutil.rmtree(dump_dir, ignore_errors=True)
```

### Using on an Air-Gapped Machine

For maximum security:

```bash
# 1. Transfer wallet.dat files via USB
# 2. Disconnect internet
# 3. Run the scanner
# 4. Reconnect internet (if you want reports uploaded)
# 5. Delete wallet.dat files
```

**Note:** Option [3] (check private keys) requires internet for blockchain rescan API.

---

## Advanced Usage

### Scanning Many Wallets (100+)

```bash
# Create a directory structure
mkdir -p wallets/batch_1 wallets/batch_2 wallets/batch_3

# Copy wallets (200 per batch to avoid timeouts)
cp my_old_wallets/wallet_*.dat wallets/batch_1/

# Scan batch 1
python3 wallet_dashboard.py
# Select [1] → wallets/batch_1/

# Scan batch 2, etc.
```

### Scripting / Automation

Fall back to the legacy CLI for batch processing:

```bash
# Scan a directory and save report
python3 scan_wallets.py ./wallets --out report.csv --delay 0.5

# Keep dumps for manual inspection
python3 scan_wallets.py ./wallets --keep-dumps --out report.csv
```

### Using with Git/GitHub

```bash
# Initialize a new repo with this tool
git clone https://github.com/Matchain-Group/wallet-dat-scanner.git
cd wallet-dat-scanner

# The .gitignore already excludes:
cat .gitignore
# *.dat (wallet files)
# *_dump.txt (extracted keys)
# wallet_reports/ (your reports)

# Safe to commit to GitHub
git add .
git commit -m "wallet scanner setup"
git push origin main
```

### Importing Reports into Excel

**CSV import:**
1. Open Excel → File → Open
2. Select your `scan_*.csv`
3. Use Data → Sort to rank by `total_btc`
4. Filter by `status == "HAS BALANCE"`

**Chart creation:**
```excel
# Create a pie chart of empty vs funded wallets
=COUNTIF(F:F, "HAS BALANCE") / COUNT(F:F)
```

---

## Frequently Asked Questions

**Q: Why does it need Bitcoin Core?**  
A: Only Bitcoin Core can properly parse Berkeley-DB wallet.dat files. No pure-Python alternative exists that supports all wallet formats.

**Q: Can I use Bitcoin Core 27.0?**  
A: Maybe. Bitcoin 26+ dropped support for old Berkeley-DB wallets. If `loadwallet` fails, downgrade to 25.x or use pywallet.py.

**Q: What if my wallet is encrypted?**  
A: The tool prompts for a passphrase. You must know it (no way to decrypt without password).

**Q: Does the Blockstream API know my IP?**  
A: Yes, like any internet request. For maximum privacy, use a VPN. For extreme privacy, use a fully air-gapped machine.

**Q: Can I use a different blockchain API?**  
A: Modify the `API_BASE` variable in the code to point to a different Esplora instance.

**Q: How do I sweep funds from an old wallet?**  
A: Use `bitcoin-cli sweepaddress` or the Bitcoin Core GUI. Transfer to a new, securely generated wallet.

---

**Happy scanning! Questions? Issues? Pull requests welcome.** 🚀
