// OmniPulse Interactive Dashboard — Reactive Omni Buildathon (2026)

const COPILOT_PRESETS = [
  { uniPrice: 2945, basePrice: 2880, vel: 2.4, sand: 0.25 },
  { uniPrice: 2875, basePrice: 2580, vel: 3.8, sand: 0.45 },
  { uniPrice: 2690, basePrice: 2890, vel: 5.8, sand: 0.92 }
];

function setTab(tab) {
  ["pipeline", "copilot", "contracts"].forEach(t => {
    document.getElementById("tab-btn-" + t).classList.toggle("active", t === tab);
    document.getElementById("view-" + t).classList.toggle("active", t === tab);
  });
}

function renderPipelineSvg() {
  const w = 1280, h = 220;
  const boxes = [
    { x: 24, y: 26, w: 360, h: 168, col: "#06b6d4", step: "STEP 1: ORIGIN CHAIN EVENT", title: "Unichain (1301) & Base (84532)", l1: "Uniswap Pool emits Swap() / Sync()", l2: "AI Oracle emits RiskTelemetryUpdated()", l3: "Captured by Reactive Validator Nodes" },
    { x: 460, y: 26, w: 360, h: 168, col: "#8b5cf6", step: "STEP 2: REACTIVE NETWORK RVM", title: "OmniPulseReactiveSentinel.react()", l1: "Executes inside isolated RVM (~840 ms)", l2: "Checks Stop-Loss, Spread & AI Score", l3: "Emits Callback(chain_id, vault, gas, data)" },
    { x: 896, y: 26, w: 360, h: 168, col: "#10b981", step: "STEP 3: DESTINATION CALLBACK", title: "OmniPulseCallbackVault.sol", l1: "Proxy injects & verifies rvm_id", l2: "Unwinds Collateral / Hedges Spread", l3: "Isolates Vault via Circuit-Breaker" }
  ];

  let svg = "";
  boxes.forEach((b, i) => {
    svg += `
      <g transform="translate(${b.x}, ${b.y})">
        <rect x="0" y="0" width="${b.w}" height="${b.h}" rx="14" fill="#0b1222" stroke="${b.col}" stroke-width="2.8"/>
        <text x="20" y="30" fill="${b.col}" font-size="11.5" font-family="monospace" font-weight="800">${b.step}</text>
        <text x="20" y="56" fill="#f8fafc" font-size="16" font-weight="800">${b.title}</text>
        <text x="20" y="88" fill="#cbd5e1" font-size="13">• ${b.l1}</text>
        <text x="20" y="114" fill="#cbd5e1" font-size="13">• ${b.l2}</text>
        <text x="20" y="140" fill="#34d399" font-size="12.5" font-family="monospace">✓ ${b.l3}</text>
      </g>
    `;
    if (i < 2) {
      const ax = b.x + b.w + 8;
      svg += `
        <line x1="${ax}" y1="110" x2="${ax + 56}" y2="110" stroke="#22d3ee" stroke-width="3" stroke-dasharray="5,4"/>
        <polygon points="${ax + 52},103 ${ax + 64},110 ${ax + 52},117" fill="#22d3ee"/>
      `;
    }
  });

  document.getElementById("pipeline-svg-container").innerHTML =
    `<svg viewBox="0 0 ${w} ${h}" width="100%" height="auto">${svg}</svg>`;

  document.getElementById("pipeline-live-trace").textContent =
`[LASNA RVM BLOCK #4912015] LogRecord received from Unichain Sepolia (Chain ID: 1301)
  ├─ topic_0 : 0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67 (Swap)
  ├─ RVM Eval: Cross-chain spread = 225 bps (>= 120 bps threshold)
  └─ Emitted : Callback(chain_id=84532, vault=0xBaseSepoliaOmniPulseVault, gas=450000, action=HEDGE)`;
}

function loadCopilotPreset(idx) {
  const p = COPILOT_PRESETS[idx];
  [0, 1, 2].forEach(i => document.getElementById("sim-p" + i).classList.toggle("active", i === idx));
  document.getElementById("rng-uni-price").value = p.uniPrice;
  document.getElementById("rng-base-price").value = p.basePrice;
  document.getElementById("rng-vel").value = p.vel;
  document.getElementById("rng-sand").value = p.sand;
  updateCopilot();
}

function updateCopilot() {
  const uniP = parseFloat(document.getElementById("rng-uni-price").value);
  const baseP = parseFloat(document.getElementById("rng-base-price").value);
  const vel = parseFloat(document.getElementById("rng-vel").value);
  const sand = parseFloat(document.getElementById("rng-sand").value);

  document.getElementById("lbl-uni-price").textContent = "$" + uniP.toLocaleString();
  document.getElementById("lbl-base-price").textContent = "$" + baseP.toLocaleString();
  document.getElementById("lbl-vel").textContent = vel.toFixed(1) + " σ";
  document.getElementById("lbl-sand").textContent = sand.toFixed(2);

  const high = Math.max(uniP, baseP), low = Math.min(uniP, baseP);
  const spreadBps = Math.round(((high - low) / low) * 10000);
  const dropPct = Math.max(0, (2880 - low) / 28.8);

  const z = -2.65 + 0.24 * dropPct + 0.58 * vel + 0.012 * spreadBps + 2.4 * sand + 0.08 * dropPct * vel;
  const prob = 1 / (1 + Math.exp(-Math.max(-25, Math.min(25, z))));
  const aiRiskBps = Math.round(prob * 10000);
  const velBps = Math.min(10000, Math.round(vel * 1650));
  const compositeBps = Math.round((aiRiskBps * 70 + velBps * 30) / 100);

  let actionName = "NO_ACTION_HEALTHY";
  let actionCode = 0;
  let destChain = 84532;
  let protectedUsd = 0;

  if (compositeBps >= 8000) {
    actionName = "ACTION_CIRCUIT_BREAKER_PAUSE (3)";
    actionCode = 3;
    destChain = 1301;
    protectedUsd = 876000;
  } else if (low <= 2650) {
    actionName = "ACTION_STOP_LOSS_EXIT (1)";
    actionCode = 1;
    destChain = uniP <= 2650 ? 1301 : 84532;
    protectedUsd = 285000;
  } else if (spreadBps >= 120) {
    actionName = "ACTION_CROSS_CHAIN_HEDGE (2)";
    actionCode = 2;
    destChain = uniP > baseP ? 84532 : 1301;
    protectedUsd = 116400;
  }

  document.getElementById("copilot-action-chip").textContent = actionName;
  document.getElementById("out-spread").textContent = spreadBps + " bps";
  document.getElementById("out-airisk").textContent = compositeBps.toLocaleString() + " bps";
  document.getElementById("out-protected").textContent = "$" + protectedUsd.toLocaleString();

  const rvmId = "0x7f4e9b20ca14de89123b4567c8901234567890ab";
  const payloadObj = {
    event: "Callback(uint256 indexed chain_id, address indexed _contract, uint64 indexed gas_limit, bytes payload)",
    chain_id: destChain,
    target_vault: destChain === 1301 ? "0xUnichainOmniPulseVault000000000000001301" : "0xBaseSepoliaOmniPulseVault000000000084532",
    gas_limit: 450000,
    signature: "executeReactiveAction(address,uint256,uint8,uint256,bytes32)",
    injected_rvm_id: rvmId,
    decoded_arguments: {
      originChainId: 1301,
      actionType: actionCode,
      actionLabel: actionName,
      severityBps: actionCode === 3 ? compositeBps : spreadBps,
      aiManipulationProbPct: +(prob * 100).toFixed(2)
    }
  };
  document.getElementById("copilot-callback-pre").textContent = JSON.stringify(payloadObj, null, 2);
}

window.addEventListener("DOMContentLoaded", () => {
  renderPipelineSvg();
  loadCopilotPreset(0);

  const params = new URLSearchParams(window.location.search);
  const tab = params.get("tab");
  if (tab && ["pipeline", "copilot", "contracts"].includes(tab)) {
    setTab(tab);
  }
  const preset = params.get("preset");
  if (preset !== null && COPILOT_PRESETS[parseInt(preset, 10)]) {
    loadCopilotPreset(parseInt(preset, 10));
  }
});
