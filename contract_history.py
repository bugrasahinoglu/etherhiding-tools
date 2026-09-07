#!/usr/bin/env python3
"""
Reconstruct the full C2 rotation history of an EtherHiding contract.

Every time the operator updates the stored C2 address, that write is a
transaction on the chain. Transactions are permanent, so the complete list of
every C2 domain the operator has ever used can be recovered — including ones
that were never seen in any incident.

This script pulls the contract's transaction list, decodes the string argument
out of each setter call, and prints a timeline.

Setup:
    pip install requests
    Get a free API key at https://etherscan.io/apis
    export ETHERSCAN_API_KEY=<your key>

Output is defanged. Nothing is executed, only printed.
"""

import os
import sys
from datetime import datetime, timezone

import requests

CONTRACT = "0xA3a603F8a454a9c905b4c579Bb72628F7C15C2A0"
CHAIN_ID = 137  # Polygon
API = "https://api.etherscan.io/v2/api"


def fetch_transactions(contract, api_key):
    """Fetch all normal transactions sent to the contract, oldest first."""
    params = {
        "chainid": CHAIN_ID,
        "module": "account",
        "action": "txlist",
        "address": contract,
        "startblock": 0,
        "endblock": 99999999,
        "sort": "asc",
        "apikey": api_key,
    }
    response = requests.get(API, params=params, timeout=30)
    response.raise_for_status()
    body = response.json()

    if body.get("status") != "1":
        raise RuntimeError(f"API returned: {body.get('message')} / {body.get('result')}")
    return body["result"]


def decode_string_argument(input_data):
    """
    Pull an ABI-encoded string out of transaction input data.

    Layout after the 4-byte selector, in 32-byte (64 hex char) words:
        word 0  -> offset to the string data
        word 1  -> length in bytes
        word 2+ -> the string bytes
    """
    h = input_data[2:] if input_data.startswith("0x") else input_data

    selector = h[:8]
    args = h[8:]
    if len(args) < 128:
        return selector, None

    try:
        offset = int(args[0:64], 16) * 2
        length = int(args[offset:offset + 64], 16)
        raw = args[offset + 64:offset + 64 + length * 2]
        return selector, bytes.fromhex(raw).decode("utf-8", errors="replace")
    except (ValueError, IndexError):
        return selector, None


def main():
    api_key = os.getenv("ETHERSCAN_API_KEY")
    if not api_key:
        print("Set ETHERSCAN_API_KEY first. Free key: https://etherscan.io/apis",
              file=sys.stderr)
        sys.exit(1)

    transactions = fetch_transactions(CONTRACT, api_key)
    print(f"{len(transactions)} transactions found for {CONTRACT}\n")

    rows = []
    for tx in transactions:
        selector, value = decode_string_argument(tx.get("input", ""))
        if not value:
            continue

        timestamp = datetime.fromtimestamp(int(tx["timeStamp"]), tz=timezone.utc)
        rows.append({
            "date": timestamp.strftime("%Y-%m-%d %H:%M UTC"),
            "block": tx["blockNumber"],
            "from": tx["from"],
            "selector": selector,
            "value": value,
            "gas_pol": int(tx["gasUsed"]) * int(tx["gasPrice"]) / 1e18,
        })

    if not rows:
        print("No decodable string arguments found.")
        return

    print(f"{'DATE':<22} {'BLOCK':<11} {'C2 VALUE':<40} {'GAS (POL)':>10}")
    print("-" * 88)
    for row in rows:
        print(f"{row['date']:<22} {row['block']:<11} "
              f"{row['value'].replace('.', '[.]'):<40} {row['gas_pol']:>10.5f}")

    # Operator tempo — the part worth writing about.
    first = datetime.strptime(rows[0]["date"], "%Y-%m-%d %H:%M UTC")
    last = datetime.strptime(rows[-1]["date"], "%Y-%m-%d %H:%M UTC")
    days = max((last - first).days, 1)
    total_gas = sum(r["gas_pol"] for r in rows)
    wallets = {r["from"].lower() for r in rows}

    print(f"\n{len(rows)} rotations over {days} days "
          f"(one every {days / len(rows):.1f} days on average)")
    print(f"Total gas spent by the operator: {total_gas:.4f} POL")
    print(f"Distinct controlling wallets: {len(wallets)}")
    for wallet in wallets:
        print(f"  {wallet}")

    with open("c2_rotation_history.csv", "w", encoding="utf-8") as fh:
        fh.write("date,block,from,c2_value,gas_pol\n")
        for row in rows:
            fh.write(f"{row['date']},{row['block']},{row['from']},"
                     f"{row['value']},{row['gas_pol']:.6f}\n")
    print("\nWritten to c2_rotation_history.csv")


if __name__ == "__main__":
    main()
