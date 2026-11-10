# Reactive Omni Buildathon Submission Guide (`OmniPulse`)

**Hackathon URL:** `https://dorahacks.io/hackathon/reactive-omni-buildathon/detail`  
**Prize Pool:** `$5,500 USD` in `REACT` (DoraHacks BUIDL)

---

## 1. Exact Copy-Paste DoraHacks BUIDL Fields

- **BUIDL Name:**  
  `OmniPulse: Reactive Smart Contract + AI DeFi Circuit-Breaker & Cross-Chain Automation Engine`

- **One-Line Elevator Pitch:**  
  `Inversion-of-Control Reactive Smart Contract (RSC) + AI Risk Copilot on Lasna Testnet that monitors Unichain (1301) & Base (84532) DEX events and dispatches <1s autonomous stop-loss, hedge & circuit-breaker callbacks.`

- **GitHub Repository URL:**  
  `https://github.com/jeffrey-graham/reactive-omni-ai-sentinel`

- **Live Demo / DApp URL:**  
  `https://jeffrey-graham.github.io/reactive-omni-ai-sentinel/`

- **Tags:**  
  `Reactive Network`, `DeFi`, `AI`, `Cross-Chain`, `Solidity`, `Unichain`, `Base`, `Smart Contracts`

---

## 2. Detailed Project Description (Markdown Copy-Paste for DoraHacks BUIDL)

### Problem Statement
DeFi vaults and multi-chain liquidity providers operating across **Unichain Sepolia (`1301`)** and **Base Sepolia (`84532`)** currently rely on centralized off-chain keeper bots to execute stop-losses, rebalance cross-chain inventory, or trigger emergency circuit-breakers during flash-loan manipulation attacks. When volatility spikes, off-chain keepers suffer RPC congestion or downtime, resulting in cascading liquidations.

### Solution: 3-Step Reactive Smart Contract Architecture
**OmniPulse** eliminates centralized keepers using **Reactive Network (Lasna / Kopli Testnet)** Inversion-of-Control Smart Contracts (`OmniPulseReactiveSentinel.sol`) paired with destination vaults (`OmniPulseCallbackVault.sol`) and an **AI DeFi Risk Copilot**:

1. **Step 1 — Origin Chain Event Subscription (`service.subscribe`):**
   - `OmniPulseReactiveSentinel.sol` subscribes to Uniswap `Swap` (`0xc42079...`), Pool `Sync` (`0x1c411e...`), and `RiskTelemetryUpdated` (`0x8a9c5b...`) events across **Unichain Sepolia (`1301`)** and **Base Sepolia (`84532`)** via System Contract `0x0000000000000000000000000000000000fffFfF`.
2. **Step 2 — Sub-Second RVM `react(LogRecord calldata log)` Evaluation (`~840ms` CometBFT Finality):**
   - Inside the isolated Reactive Virtual Machine (`vmOnly`), `react()` decodes real-time pool prices and AI risk scores and emits `Callback(chain_id, targetVault, 450000, payload)` for three autonomous protection workflows:
     - `ACTION_STOP_LOSS_EXIT (1)`: Triggered when pool price breaches the stop-loss floor (`<= $2,650`).
     - `ACTION_CROSS_CHAIN_HEDGE (2)`: Triggered when cross-chain price spread between Unichain (`1301`) and Base (`84532`) exceeds `120 bps`.
     - `ACTION_CIRCUIT_BREAKER_PAUSE (3)`: Triggered when the AI Risk Copilot composite manipulation score reaches `>= 8,000 bps` (`80%+`), isolating vaults on both chains simultaneously.
3. **Step 3 — Authenticated Destination Callback Execution (`OmniPulseCallbackVault.sol`):**
   - Enforces `authorizedSenderOnly` and `rvmIdOnly(_rvmId)` (verifying the first `address` argument overwritten by Reactive Network with the deployer's RVM ID) and executes atomic collateral unwinds, delta-neutral hedging, or vault isolation.

---

## 3. Local File Paths for Upload

- **60-Second 1080p Demo Video:** `/home/jeff/.gemini/antigravity/scratch/freelancework/reactive-omni-hackathon/demo.mp4`
- **Screenshot 1 (3-Step Reactive Loop Pipeline):** `/home/jeff/.gemini/antigravity/scratch/freelancework/reactive-omni-hackathon/screenshots/reactive_loop_pipeline.png`
- **Screenshot 2 (AI Risk Copilot & Callback Simulator):** `/home/jeff/.gemini/antigravity/scratch/freelancework/reactive-omni-hackathon/screenshots/ai_risk_copilot.png`
- **Screenshot 3 (Solidity RSC & Vault Audit Trail):** `/home/jeff/.gemini/antigravity/scratch/freelancework/reactive-omni-hackathon/screenshots/callback_vault_audit.png`
