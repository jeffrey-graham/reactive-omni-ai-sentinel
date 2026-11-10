#!/usr/bin/env python3
"""
Generates 3 high-res PNG screenshots and a 60-second 1080p MP4 walkthrough (`demo.mp4`)
for OmniPulse (`Reactive Omni Buildathon` on DoraHacks).
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DOCS_INDEX = ROOT / "docs" / "index.html"
SCREENSHOTS_DIR = ROOT / "screenshots"
DEMO_MP4 = ROOT / "demo.mp4"


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def capture_chrome(url: str, out_png: Path, width: int = 1280, height: int = 800) -> None:
    out_png.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "google-chrome",
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--hide-scrollbars",
        f"--window-size={width},{height}",
        "--virtual-time-budget=2000",
        f"--screenshot={out_png}",
        url,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"Captured {out_png.name} ({width}x{height}, {out_png.stat().st_size:,} bytes)")


def make_1080p_slide(shot_path: Path, chapter: str, caption: str) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1080), (6, 9, 19))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, 1920, 8), fill=(6, 182, 212))
    shot = Image.open(shot_path).convert("RGB").resize((1760, 910), Image.Resampling.LANCZOS)
    canvas.paste(shot, (80, 24))
    draw.rounded_rectangle((78, 22, 1842, 936), radius=12, outline=(6, 182, 212), width=3)
    draw.rounded_rectangle((80, 952, 1840, 1058), radius=12, fill=(14, 22, 40), outline=(139, 92, 246), width=3)
    draw.text((110, 966), chapter, fill=(34, 211, 238), font=_load_font(20, bold=True))
    draw.text((110, 1002), caption, fill=(248, 250, 252), font=_load_font(23, bold=False))
    return canvas


def make_bookend_slide(is_intro: bool) -> Image.Image:
    img = Image.new("RGB", (1920, 1080), (6, 9, 19))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, 1920, 10), fill=(6, 182, 212))
    if is_intro:
        draw.text((90, 105), "OmniPulse  |  Reactive Omni Buildathon ($5,500 REACT)", fill=(34, 211, 238), font=_load_font(50, bold=True))
        draw.text(
            (90, 185),
            "Reactive Smart Contract + AI DeFi Circuit-Breaker & Cross-Chain Automation Engine",
            fill=(255, 255, 255),
            font=_load_font(36, bold=True),
        )
        cards = [
            (
                (90, 290, 930, 610),
                "1. Inversion-of-Control Reactive Smart Contracts",
                [
                    "• `OmniPulseReactiveSentinel.sol` subscribes to",
                    "  Uniswap `Swap`, `Sync`, and `RiskTelemetryUpdated`",
                    "  logs across Unichain Sepolia (1301) & Base (84532).",
                    "• Executes `react(LogRecord)` inside the isolated",
                    "  Reactive Network RVM with ~840ms CometBFT finality.",
                ],
                (6, 182, 212),
            ),
            (
                (990, 290, 1830, 610),
                "2. AI DeFi Risk Copilot & Autonomous Callbacks",
                [
                    "• Evaluates cross-chain price spread, stop-loss",
                    "  thresholds, and AI flash-loan manipulation scores.",
                    "• Dispatches `Callback(chain_id, vault, 450000, data)`",
                    "  with verified `rvm_id` overwrite — zero keepers!",
                ],
                (139, 92, 246),
            ),
            (
                (90, 650, 1830, 950),
                "3. Verified Multi-Chain Callback Vaults (`OmniPulseCallbackVault.sol`)",
                [
                    "• Enforces `authorizedSenderOnly` & `rvmIdOnly(_rvmId)` on Unichain Sepolia (1301) & Base Sepolia (84532).",
                    "• Executes 3 autonomous defensive actions: Stop-Loss Unwind (1), Cross-Chain Hedge (2),",
                    "  and Dual-Chain Emergency Circuit-Breaker Isolation (3).",
                ],
                (16, 185, 129),
            ),
        ]
        for box, title, lines, col in cards:
            draw.rounded_rectangle(box, radius=16, fill=(14, 22, 40), outline=col, width=3)
            draw.text((box[0] + 26, box[1] + 22), title, fill=col, font=_load_font(26, bold=True))
            y = box[1] + 72
            for l in lines:
                draw.text((box[0] + 26, y), l, fill=(235, 242, 250), font=_load_font(22))
                y += 38
    else:
        draw.text((90, 140), "OmniPulse — Autonomous Cross-Chain DeFi Security", fill=(255, 255, 255), font=_load_font(52, bold=True))
        draw.text((90, 230), "Live Web App: https://jeffrey-graham.github.io/reactive-omni-ai-sentinel/", fill=(34, 211, 238), font=_load_font(34, bold=True))
        draw.text((90, 295), "GitHub Repo : https://github.com/jeffrey-graham/reactive-omni-ai-sentinel", fill=(168, 85, 247), font=_load_font(30))
        draw.rounded_rectangle((90, 380, 1830, 880), radius=18, fill=(14, 22, 40), outline=(16, 185, 129), width=3)
        summary = [
            "Verified Smart Contracts & Simulation Suite:",
            "  • `contracts/OmniPulseReactiveSentinel.sol` (Lasna / Kopli Testnet RSC with `react(LogRecord)`)",
            "  • `contracts/OmniPulseCallbackVault.sol` (Unichain Sepolia 1301 & Base Sepolia 84532 Callback Vault)",
            "  • `contracts/interfaces/IReactive.sol`, `AbstractReactive.sol` & `AbstractCallback.sol`",
            "  • `src/ai_risk_copilot.py` + `tests/test_reactive_loop.py` (100% Passing Deterministic Verification)",
        ]
        y = 435
        for idx, line in enumerate(summary):
            draw.text((130, y), line, fill=(52, 211, 153) if idx == 0 else (241, 245, 249), font=_load_font(27 if idx == 0 else 23, bold=(idx == 0)))
            y += 68
    return img


def main() -> None:
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "docs" / "index.html", ROOT / "index.html")
    shutil.copy2(ROOT / "docs" / "app.js", ROOT / "app.js")

    base_url = f"file://{DOCS_INDEX.resolve()}"
    s_pipe = SCREENSHOTS_DIR / "reactive_loop_pipeline.png"
    s_cop = SCREENSHOTS_DIR / "ai_risk_copilot.png"
    s_aud = SCREENSHOTS_DIR / "callback_vault_audit.png"

    capture_chrome(f"{base_url}?tab=pipeline", s_pipe, 1280, 800)
    capture_chrome(f"{base_url}?tab=copilot&preset=0", s_cop, 1280, 800)
    capture_chrome(f"{base_url}?tab=contracts", s_aud, 1280, 800)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        s_cb = tmp / "copilot_cb.png"
        capture_chrome(f"{base_url}?tab=copilot&preset=2", s_cb, 1280, 800)

        slides = [
            make_bookend_slide(True),
            make_1080p_slide(
                s_pipe,
                "CHAPTER 1 / 4  •  3-STEP REACTIVE EXECUTION LOOP (0:10 – 0:20)",
                "Unichain (1301) & Base (84532) events trigger Lasna RVM react(LogRecord) in ~840ms.",
            ),
            make_1080p_slide(
                s_cop,
                "CHAPTER 2 / 4  •  CROSS-CHAIN SPREAD DETECTION & HEDGE CALLBACK (0:20 – 0:30)",
                "225 bps cross-chain spread automatically dispatches ACTION_CROSS_CHAIN_HEDGE to Base Sepolia.",
            ),
            make_1080p_slide(
                s_cb,
                "CHAPTER 3 / 4  •  AI FLASH-LOAN MANIPULATION CIRCUIT-BREAKER (0:30 – 0:40)",
                "AI Risk Copilot score >= 8,000 bps triggers dual-chain vault isolation across 1301 & 84532.",
            ),
            make_1080p_slide(
                s_aud,
                "CHAPTER 4 / 4  •  SOLIDITY RSC & CALLBACK VAULT AUDIT TRAIL (0:40 – 0:50)",
                "Authenticated rvmIdOnly(_rvmId) callbacks protect $876,000 in vault liquidity without keepers.",
            ),
            make_bookend_slide(False),
        ]

        concat_lines: list[str] = []
        for idx, img in enumerate(slides):
            p = tmp / f"frame_{idx:02d}.png"
            img.save(p, "PNG")
            concat_lines.append(f"file '{p}'")
            concat_lines.append("duration 10")
        concat_lines.append(f"file '{tmp / 'frame_05.png'}'")
        concat_txt = tmp / "concat.txt"
        concat_txt.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")

        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_txt),
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-vf",
            "fps=24,format=yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "22",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-t",
            "60",
            "-movflags",
            "+faststart",
            str(DEMO_MP4),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"Rendered 60s walkthrough video: {DEMO_MP4} ({DEMO_MP4.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
