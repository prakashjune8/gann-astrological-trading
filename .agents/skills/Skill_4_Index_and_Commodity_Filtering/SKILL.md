---
name: Skill_4_Index_and_Commodity_Filtering
description: Route Gann timing triggers to NSE/BSE broad indices, NSE Nifty 50 options, MCX energy and MCX base-metal futures while hard-excluding all gold and silver instruments. Use when building instrument lists, feeds, or alerts.
---

# Skill 4 – Index & Commodity Filtering

## Allowed universe
* **NSE indices**: NIFTY 50, NIFTY NEXT 50, NIFTY 100, NIFTY 200, NIFTY 500, NIFTY BANK, NIFTY MIDCAP 100.
* **BSE indices**: SENSEX, BSE 100, BSE 200, BSE 500, BANKEX.
* **NSE options**: NIFTY 50 index options (strike step 50; weekly expiry Tuesday).
* **MCX energy**: CRUDEOIL, CRUDEOILM, NATURALGAS, NATGASMINI.
* **MCX base metals**: COPPER, ZINC, ZINCMINI, ALUMINIUM, ALUMINI, LEAD, LEADMINI, NICKEL.

## Hard exclusion (CRITICAL)
* Block any symbol matching `GOLD|SILVER|BULLION` (GOLD, GOLDM, GOLDGUINEA, GOLDPETAL, GOLDTEN,
  SILVER, SILVERM, SILVERMIC, …) at three layers: config load, trigger routing, and alert/export output.
* Do not map Sun→gold or Moon→silver rulerships; Sun/Moon remain *timing* bodies only.
* Unit-test that no output row ever contains an excluded symbol.

## Rulership relevance (traditional/modern astro-commodity associations, optional filter)
* Energy: Neptune (oil/gas), Pluto (underground resources), Mars (combustion), Jupiter.
* Base metals: Venus (copper), Saturn (lead), Mars (nickel/iron group), Uranus (aluminium), Jupiter (zinc/tin group).
* Indices/options: all bodies, ranked by Gann weight.
