# URACE Token Deployment on Polygon PoS

[← Economics](../index.md)

One URACE ERC-20 contract is deployed once by the network maintainer. Peers receive and send tokens via standard ERC-20 transfers — no on-chain registration required.

---

## Prerequisites

- Python 3.11+, `urace` installed
- ~0.1 MATIC in your URACE wallet (covers deployment gas + test transfers)
- A Polygon PoS JSON-RPC endpoint (free tier: `https://polygon-rpc.com`, or Alchemy/Infura)

---

## Step 1: Get your wallet address

```sh
urace crypto wallet init       # only if wallet doesn't exist yet
urace crypto wallet show
```

Copy the `address` field. This is your Polygon PoS address.

---

## Step 2: Fund with MATIC

Send 0.1 MATIC to your wallet address from any exchange (Coinbase, Binance, Kraken).  
Polygon PoS network, not Ethereum mainnet.

Verify balance:
```sh
# Check via any Polygon explorer, e.g.:
# https://polygonscan.com/address/<your-address>
```

---

## Step 3: Configure RPC endpoint

```sh
urace exchange settings set --rpc-provider-url https://polygon-rpc.com --chain-id 137
```

Or use a private endpoint:
```sh
urace exchange settings set --rpc-provider-url https://polygon-mainnet.g.alchemy.com/v2/<KEY> --chain-id 137
```

---

## Step 4: Deploy the ERC-20 contract

The URACE ERC-20 is a standard OpenZeppelin contract with fixed supply. Deploy using Remix or Hardhat:

**Using Remix (browser, no install):**
1. Open `https://remix.ethereum.org`
2. Create `Urace.sol`:

```solidity
// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract URACEToken is ERC20, Ownable {
    uint8 private _decimals = 8;

    constructor(uint256 initialSupply) ERC20("URACE", "URACE") Ownable(msg.sender) {
        _mint(msg.sender, initialSupply * 10 ** decimals());
    }

    function decimals() public view override returns (uint8) {
        return _decimals;
    }

    // Owner can mint additional supply as network grows
    function mint(address to, uint256 amount) external onlyOwner {
        _mint(to, amount);
    }
}
```

3. Compile with Solidity 0.8.20
4. Connect MetaMask to Polygon PoS (chain ID 137)
5. Deploy with `initialSupply = 1000000` (1M URACE tokens)
6. Copy the deployed contract address

---

## Step 5: Register contract address

```sh
urace exchange settings set --erc20-contract 0x<deployed-contract-address>
```

Update `exchange/token_contract.json` with the deployed address and tx hash.

---

## Step 6: Verify settlement config

```sh
urace exchange settle status
```

Expected output:
```json
{
  "rpc_configured": true,
  "chain_id": 137,
  "erc20_contract": "0x...",
  "token_settlement_enabled": false,
  "status": "ok"
}
```

Enable token settlement:
```sh
urace exchange settings set --enabled true
```

---

## Economics notes

- Each peer pays their own MATIC gas (~$0.001/tx) — no subsidization from deployer
- `urace_credit_usd_rate` (default: 1000 URACE = $1) is a **display-only** accounting rate — it does not set the market price of URACE tokens
- Market price is determined by supply/demand on DEXes (QuickSwap, Uniswap v3 on Polygon) once liquidity is added
- Deployer is `owner` — can mint additional supply via `mint()` as the network scales

---

## Bootstrap + relay node setup

After deploying the contract, announce your node as a bootstrap peer:

```sh
# Check your reachability first
urace exchange network reachability --json

# If can_bootstrap=true, register in bootstrap_peers.json
# Open a PR to add your HTTPS endpoint:
# exchange/bootstrap_peers.json  →  ["https://your-node.example.com:7301"]
```

For relay nodes (cone NAT with UPnP):
```sh
# Enable UPnP and start relay
urace exchange settings set --relay-only false
urace exchange network serve --port 7301
```
