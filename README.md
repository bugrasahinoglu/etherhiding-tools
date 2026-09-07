# etherhiding-tools

Two small scripts for reading command-and-control addresses out of EtherHiding smart
contracts.

EtherHiding malware stores its C2 address in a public blockchain contract instead of
hardcoding a domain. The malware reads that value at runtime with an `eth_call`. So can
anyone else — the call is read-only, free, requires no wallet, and leaves no trace on
chain.

That asymmetry is the point. Every time the operator rotates infrastructure, they write a
signed, timestamped, permanent transaction that anyone can read. Defenders can watch the
contract instead of chasing the domains it hands out.

Written while investigating a macOS ClickFix campaign that resolves its C2 through a
Polygon contract. Full write-up: **[link to article]**

## Scripts

### `read_contract.py`

Reads the string currently stored in a contract and decodes it.

Answers: *what is the C2 right now?*

```bash
python3 read_contract.py
```

### `contract_history.py`

Walks every setter transaction against the contract, decodes the value written each time,
and prints a timeline with timestamps, block numbers and gas cost. Also writes a CSV.

Answers: *what has this operator used, how often do they rotate, and what does it cost
them?*

```bash
export ETHERSCAN_API_KEY=<your key>
python3 contract_history.py
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env    # then add your key
```

A free API key for `contract_history.py` comes from https://etherscan.io/apis. The same
key works across chains through Etherscan's V2 API. `read_contract.py` needs no key at
all — it talks directly to a public RPC endpoint.

The contract address and function selector are constants at the top of each script.
Change them to point at a different contract.

## Known limitation

`contract_history.py` reconstructs history from `setServerURL` calls, so it recovers every
*update* but not the value written by the constructor at deployment — that argument is
appended to the deploy bytecode rather than sent as a function call. To get it, read the
creation transaction's input data in a block explorer and look at the tail. Adding this to
the script is on the list.

## Safety

These scripts only print. They never execute anything they retrieve, and neither should
you — the values are attacker-controlled. Domains in the output are defanged.

Run them from a personal machine on a personal network. The requests are harmless, but you
probably do not want to be the person who generated the blockchain-RPC alert in your own
SOC.

## Provenance

These were written with AI assistance during the investigation described in the article.
I have worked through the logic and can explain what each script does and why; they are
published because the article claims its findings can be verified in five minutes, and
these are what I used to do that.

## License

MIT
