#!/usr/bin/env python3
"""
scaffold_pbir.py — Cross-platform PBIR report scaffolder.
Creates a valid, compliant PBIR report directory (.Report) and optional PBIP project
with customizable pages, 16:9 canvas dimensions, and visual container templates.

Usage:
    python3 scripts/scaffold_pbir.py SalesAnalytics
    python3 scripts/scaffold_pbir.py SalesAnalytics --pages "Executive Overview" "Regional Breakdown" --template executive --pbip
    python3 scripts/scaffold_pbir.py MyReport --model "../CustomModel.SemanticModel"
"""

import argparse
import json
import re
import sys
import uuid
from pathlib import Path

# Official Microsoft PBIR JSON schemas
# Schema versions below are the Desktop-canonical ones, verified against a
# Desktop-authored project. Emitting older versions makes Desktop rewrite the file on
# first save, which produces spurious diffs. See docs/LINUX_WORKFLOW_GAPS.md GAP-09.
SCHEMA_REPORT = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.3.0/schema.json"
SCHEMA_PAGES_META = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json"
SCHEMA_PAGE = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"
SCHEMA_VISUAL = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json"
SCHEMA_PBIP = "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json"
SCHEMA_PBIR = "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json"
SCHEMA_VERSION = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json"
SCHEMA_PLATFORM = "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json"

# Desktop ships a built-in theme under this name; it needs no BaseThemes/*.json on disk.
DEFAULT_THEME_NAME = "CY24SU10"


def sanitize_identifier(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "", text.replace(" ", "_"))
    return cleaned or "Section"


def build_textbox_visual(name: str, title_text: str, x: int, y: int, width: int, height: int, z: int = 1000):
    return {
        "$schema": SCHEMA_VISUAL,
        "name": name,
        "position": {
            "x": x,
            "y": y,
            "z": z,
            "width": width,
            "height": height,
            "tabOrder": z
        },
        "visual": {
            "visualType": "textbox",
            "objects": {
                "general": [
                    {
                        "properties": {
                            "paragraphs": [
                                {
                                    "textRuns": [
                                        {
                                            "value": title_text,
                                            "textStyle": {
                                                "fontWeight": "bold",
                                                "fontSize": "18pt",
                                                "color": "#0f172a"
                                            }
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                ]
            }
        }
    }


def build_card_placeholder(name: str, x: int, y: int, width: int, height: int, z: int = 2000):
    return {
        "$schema": SCHEMA_VISUAL,
        "name": name,
        "position": {
            "x": x,
            "y": y,
            "z": z,
            "width": width,
            "height": height,
            "tabOrder": z
        },
        "visual": {
            "visualType": "cardVisual",
            "query": {
                "queryState": {}
            }
        }
    }


def build_chart_placeholder(name: str, visual_type: str, x: int, y: int, width: int, height: int, z: int = 3000):
    return {
        "$schema": SCHEMA_VISUAL,
        "name": name,
        "position": {
            "x": x,
            "y": y,
            "z": z,
            "width": width,
            "height": height,
            "tabOrder": z
        },
        "visual": {
            "visualType": visual_type,
            "query": {
                "queryState": {}
            }
        }
    }


def scaffold_pbir(
    base_name: str,
    output_dir: Path,
    pages_list: list,
    model_path: str = None,
    template: str = "executive",
    create_pbip: bool = True
):
    # base_name may arrive as a path ("out/MyReport"); the manifest's report.path must be
    # the bare folder name, relative to the .pbip, or Desktop cannot resolve it (GAP-11).
    stem = Path(base_name).name
    clean_base = stem[:-7] if stem.endswith(".Report") else (stem[:-5] if stem.endswith(".pbip") else stem)
    report_folder_name = f"{clean_base}.Report"
    report_root = output_dir / report_folder_name
    definition_dir = report_root / "definition"
    pages_dir = definition_dir / "pages"

    if model_path is None:
        model_path = f"../{clean_base}.SemanticModel"

    print(f"[INFO] Scaffolding PBIR Report: {report_root}")

    # 0. .platform — Desktop writes one per item folder. Fabric flags a missing
    #    .platform as PBIR_PLATFORM_MISSING, so scaffold it up front (GAP-10).
    report_root.mkdir(parents=True, exist_ok=True)
    platform = {
        "$schema": SCHEMA_PLATFORM,
        "metadata": {
            "type": "Report",
            "displayName": clean_base
        },
        "config": {
            "version": "2.0",
            "logicalId": str(uuid.uuid4())
        }
    }
    (report_root / ".platform").write_text(json.dumps(platform, indent=2), encoding="utf-8")

    # 1. Root definition.pbir
    pbir_manifest = {
        "$schema": SCHEMA_PBIR,
        "version": "4.0",
        "datasetReference": {
            "byPath": {
                "path": model_path
            }
        }
    }
    (report_root / "definition.pbir").write_text(json.dumps(pbir_manifest, indent=2), encoding="utf-8")

    # 2. definition/version.json & definition/report.json
    definition_dir.mkdir(parents=True, exist_ok=True)
    (definition_dir / "version.json").write_text(
        json.dumps({"$schema": SCHEMA_VERSION, "version": "2.0.0"}, indent=2), encoding="utf-8"
    )
    # Desktop-canonical report.json: themeCollection is an object with a `baseTheme`,
    # resourcePackages is a FLAT list, and `layoutOptimization` is absent. See GAP-09.
    report_json = {
        "$schema": SCHEMA_REPORT,
        "themeCollection": {
            "baseTheme": {
                "name": DEFAULT_THEME_NAME,
                "reportVersionAtImport": {
                    "visual": "2.12.0",
                    "report": "3.4.0",
                    "page": "2.3.1"
                },
                "type": "SharedResources"
            }
        },
        "resourcePackages": [
            {
                "name": "SharedResources",
                "type": "SharedResources",
                "items": [
                    {
                        "name": DEFAULT_THEME_NAME,
                        "path": f"BaseThemes/{DEFAULT_THEME_NAME}.json",
                        "type": "BaseTheme"
                    }
                ]
            }
        ],
        "settings": {
            "exportDataMode": "AllowSummarized",
            "defaultDrillFilterOtherVisuals": True,
            "allowChangeFilterTypes": True,
            "useEnhancedTooltips": True,
            "useDefaultAggregateDisplayName": True
        }
    }
    (definition_dir / "report.json").write_text(json.dumps(report_json, indent=2), encoding="utf-8")

    # 3. definition/pages/pages.json
    pages_dir.mkdir(parents=True, exist_ok=True)
    page_section_names = []
    
    for idx, page_title in enumerate(pages_list):
        sanitized = sanitize_identifier(page_title)
        section_name = f"ReportSection_{sanitized}_{idx+1}"
        page_section_names.append((section_name, page_title))

    pages_meta = {
        "$schema": SCHEMA_PAGES_META,
        "pageOrder": [name for name, _ in page_section_names],
        "activePageName": page_section_names[0][0]
    }
    (pages_dir / "pages.json").write_text(json.dumps(pages_meta, indent=2), encoding="utf-8")

    # 4. Create individual pages & visuals
    for p_idx, (section_name, page_display_name) in enumerate(page_section_names):
        p_dir = pages_dir / section_name
        v_dir = p_dir / "visuals"
        p_dir.mkdir(parents=True, exist_ok=True)
        v_dir.mkdir(parents=True, exist_ok=True)

        page_def = {
            "$schema": SCHEMA_PAGE,
            "name": section_name,
            "displayName": page_display_name,
            "displayOption": "FitToPage",
            "height": 720,
            "width": 1280
        }
        (p_dir / "page.json").write_text(json.dumps(page_def, indent=2), encoding="utf-8")

        # Visual layout scaffolding
        if template in ["executive", "standard"]:
            # Title Visual
            title_id = f"title_{section_name[:12]}_{p_idx}"
            t_data = build_textbox_visual(title_id, page_display_name, x=20, y=15, width=900, height=55, z=1000)
            (v_dir / title_id).mkdir(parents=True, exist_ok=True)
            (v_dir / title_id / "visual.json").write_text(json.dumps(t_data, indent=2), encoding="utf-8")

            # Slicer placeholder
            slicer_id = f"slicer_{section_name[:12]}_{p_idx}"
            s_data = build_chart_placeholder(slicer_id, "slicer", x=940, y=15, width=320, height=55, z=1500)
            (v_dir / slicer_id).mkdir(parents=True, exist_ok=True)
            (v_dir / slicer_id / "visual.json").write_text(json.dumps(s_data, indent=2), encoding="utf-8")

            if p_idx == 0 and template == "executive":
                # 4 KPI cards ribbon
                kpi_w = 300
                gap = 13
                start_x = 20
                for k in range(4):
                    card_id = f"kpi_card_{k+1}"
                    c_data = build_card_placeholder(card_id, x=start_x + k * (kpi_w + gap), y=85, width=kpi_w, height=95, z=2000 + k*100)
                    (v_dir / card_id).mkdir(parents=True, exist_ok=True)
                    (v_dir / card_id / "visual.json").write_text(json.dumps(c_data, indent=2), encoding="utf-8")

                # Line trend chart
                line_id = "trend_chart_main"
                l_data = build_chart_placeholder(line_id, "lineChart", x=20, y=195, width=820, height=505, z=3000)
                (v_dir / line_id).mkdir(parents=True, exist_ok=True)
                (v_dir / line_id / "visual.json").write_text(json.dumps(l_data, indent=2), encoding="utf-8")

                # Bar chart
                bar_id = "breakdown_bar_main"
                b_data = build_chart_placeholder(bar_id, "barChart", x=860, y=195, width=400, height=505, z=3100)
                (v_dir / bar_id).mkdir(parents=True, exist_ok=True)
                (v_dir / bar_id / "visual.json").write_text(json.dumps(b_data, indent=2), encoding="utf-8")
            else:
                # Detail page: Matrix / Table + 2 charts
                table_id = f"detail_table_{p_idx}"
                tb_data = build_chart_placeholder(table_id, "tableEx", x=20, y=85, width=1240, height=615, z=2000)
                (v_dir / table_id).mkdir(parents=True, exist_ok=True)
                (v_dir / table_id / "visual.json").write_text(json.dumps(tb_data, indent=2), encoding="utf-8")

    # 5. Optional .pbip project manifest
    if create_pbip:
        pbip_file = output_dir / f"{clean_base}.pbip"
        pbip_data = {
            "$schema": SCHEMA_PBIP,
            "version": "1.0",
            "artifacts": [
                {
                    "report": {
                        "path": report_folder_name
                    }
                }
            ],
            "settings": {
                "enableAutoRecovery": True
            }
        }
        pbip_file.write_text(json.dumps(pbip_data, indent=2), encoding="utf-8")
        print(f"[OK] Generated PBIP manifest: {pbip_file}")

    print(f"[OK] Successfully scaffolded PBIR report with {len(page_section_names)} page(s) at {report_root}")
    return report_root


def main():
    parser = argparse.ArgumentParser(description="Scaffold a valid Power BI PBIR report and PBIP project.")
    parser.add_argument("name", help="Report or project base name (e.g. SalesAnalytics).")
    parser.add_argument("--pages", "-p", nargs="+", default=["Executive Overview", "Detailed Breakdown"], help="Page display names.")
    parser.add_argument("--model", "-m", default=None, help="Relative path to target SemanticModel folder.")
    parser.add_argument("--template", "-t", choices=["executive", "detail", "blank"], default="executive", help="Layout template preset.")
    parser.add_argument("--output-dir", "-o", default=".", help="Target output directory (default: current directory).")
    parser.add_argument("--no-pbip", action="store_true", help="Do not create .pbip manifest file.")

    args = parser.parse_args()
    out_dir = Path(args.output_dir)

    scaffold_pbir(
        base_name=args.name,
        output_dir=out_dir,
        pages_list=args.pages,
        model_path=args.model,
        template=args.template,
        create_pbip=not args.no_pbip
    )


if __name__ == "__main__":
    main()
