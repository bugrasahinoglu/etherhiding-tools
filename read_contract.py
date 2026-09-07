#!/usr/bin/env python3
"""
Read a string stored in an EtherHiding smart contract.

Malware using the EtherHiding technique stores its current C2 address inside
a smart contract instead of hardcoding it. The malware reads that value at
runtime with an eth_call. So can you — the call is read-only, free, requires
no wallet, and leaves no trace on-chain.

This script performs the same read and prints the decoded string.
IT NEVER EXECUTES ANYTHING IT RECEIVES. It only prints.

Usage:
    pip install requests
    python3 read_contract_string.py

Run this from a personal machine on a personal network, not from a corporate
endpoint. The request itself is harmless, but you do not want to be the person
who generated the blockchain-RPC alert in your own SOC.
"""

import sys
import requests

# Public Polygon RPC endpoint. If one is rate-limited, try another.
RPC_ENDPOINTS = [
    "https://polygon-rpc.com",
    "https://polygon.drpc.org",
]

CONTRACT = "0xA3a603F8a454a9c905b4c579Bb72628F7C15C2A0"

# 4-byte function selector observed in the malicious command.
# This identifies which function on the contract is being called.
SELECTOR = "0x2686ecea"


def eth_call(endpoint, contract, selector, block="latest"):
    """Perform a read-only contract call and return the raw hex result."""
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_call",
        "params": [{"to": contract, "data": selector}, block],
        "id": 1,
    }
    response = requests.post(endpoint, json=payload, timeout=20)
    response.raise_for_status()
    body = response.json()

    if "error" in body:
        raise RuntimeError(f"RPC error: {body['error']}")
    return body.get("result", "")


def decode_abi_string(raw_hex):
    """
    Decode an ABI-encoded dynamic string.

    Layout, in 32-byte (64 hex char) words:
        word 0  -> offset to where the string data begins
        word 1  -> length of the string in bytes
        word 2+ -> the string bytes, right-padded to a 32-byte boundary
    """
    h = raw_hex[2:] if raw_hex.startswith("0x") else raw_hex
    if len(h) < 128:
        return None

    offset = int(h[0:64], 16) * 2          # byte offset -> hex char offset
    length = int(h[offset:offset + 64], 16)  # length in bytes
    start = offset + 64
    data = h[start:start + length * 2]

    return bytes.fromhex(data).decode("utf-8", errors="replace")


def main():
    raw = None
    for endpoint in RPC_ENDPOINTS:
        try:
            raw = eth_call(endpoint, CONTRACT, SELECTOR)
            print(f"[+] Queried via {endpoint}")
            break
        except Exception as exc:
            print(f"[-] {endpoint} failed: {exc}", file=sys.stderr)

    if not raw or raw == "0x":
        print("[-] Contract returned nothing. It may have been cleared, "
              "or the selector may target a different function.")
        return

    print(f"\n[ raw hex ]\n{raw}\n")

    decoded = decode_abi_string(raw)
    if decoded:
        # Defanged so this cannot be copy-pasted into a browser by accident.
        print(f"[ decoded ]\n{decoded.replace('.', '[.]')}\n")
    else:
        print("[-] Result is not an ABI-encoded string. It may be a raw value; "
              "inspect the hex above manually.")


if __name__ == "__main__":
    main()
