#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Write frozen public evaluation documents for chunk evaluation.

These files are invented generic procedures. They are not company local_only
sources. Spreadsheet sources are stored as JSON tables and materialized to
.xlsx at evaluation time because repository gitignore excludes Excel files.

CJK procedure sections are a single paragraph (no blank lines) so markdown
ingest yields one element longer than max_chars=900. Numbered Latin repeats
are only used on Vietnamese sources, where spaces already provide split points.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
TABLES = ROOT / "tables"


def _repeat_block(paragraph: str, times: int) -> str:
    return "\n\n".join(f"{paragraph} ({index + 1})" for index in range(times))


def _repeat_inline(paragraph: str, times: int) -> str:
    """One element after markdown paragraph split — must exceed max_chars=900."""
    return "".join(paragraph for _ in range(times))


def write_markdown(name: str, body: str) -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / name).write_text(body.strip() + "\n", encoding="utf-8")


def write_table(
    name: str,
    headers: list[str],
    rows: list[list[str]],
    *,
    sheet: str | None = None,
) -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {"headers": headers, "rows": rows}
    if sheet:
        payload["sheet"] = sheet
    (TABLES / name).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    write_markdown(
        "src-quality-process.md",
        """# Quy trinh kiem tra chat luong san pham

## Muc dich
Tai lieu nay mo ta quy trinh kiem tra chat luong san pham tren day chuyen lap rap.
Nguoi van hanh phai doc het cac buoc truoc khi bat dau ca lam viec.

## Buoc thuc hien
"""
        + _repeat_block(
            "Nhan lo hang, doi chieu ma san pham, do kich thuoc chinh, ghi ket qua vao phieu "
            "kiem tra chat luong, va chi chuyen tiep neu tat ca hang muc dat. Neu mot hang muc "
            "khong dat, tach lo, dan nhan, va thong bao giam sat ca.",
            8,
        )
        + """

## An toan
Khong duoc bo qua buoc do lai sau khi hieu chinh dung cu. Moi lan dung cu bi roi hoac va cham, phai hieu chinh lai truoc khi do.
""",
    )
    write_markdown(
        "src-cost-analysis-a.md",
        """# Phuong an lap dat A - phan tich chi phi

Bang chi phi van hanh phuong an A:

| Hang muc | Chi phi thang | Ghi chu |
| --- | --- | --- |
| Nhan cong | 12000000 | 2 ca |
| Dien | 4500000 | dinh muc cu |
| Bao tri | 1800000 | dinh ky |

"""
        + _repeat_block(
            "Tong chi phi van hanh phuong an A cao hon o muc nhan cong vi can hai ca lien tuc. "
            "Chi phi dien nam o muc trung binh. Bao tri re hon phuong an B vi dung thiet bi cu.",
            6,
        ),
    )
    write_markdown(
        "src-cost-analysis-b.md",
        """# Phuong an lap dat B - phan tich chi phi

Bang chi phi van hanh phuong an B:

| Hang muc | Chi phi thang | Ghi chu |
| --- | --- | --- |
| Nhan cong | 8000000 | 1 ca tu dong |
| Dien | 6200000 | dong co moi |
| Bao tri | 3100000 | hop dong ngoai |

"""
        + _repeat_block(
            "Tong chi phi van hanh phuong an B thap hon o nhan cong nhung chi phi dien va bao tri cao hon. "
            "Khi so sanh chi phi van hanh, can cong ca ba hang muc chu khong chi nhin nhan cong.",
            6,
        ),
    )
    write_markdown(
        "src-troubleshooting.md",
        """# Xu ly su co cam bien nhiet do

## Trieu chung
He thong bao loi cam bien nhiet do khi gia tri doc duoc ngoai khoang hoac mat tin hieu.

## Kiem tra
"""
        + _repeat_block(
            "Kiem tra dau noi, day tin hieu, nguon 24V, va doi chieu gia tri voi nhiet ke cam tay. "
            "Neu cam bien nhiet do van bao loi sau khi thay day, thay cam bien va hieu chinh lai nguong.",
            7,
        )
        + """

## Hanh dong
Sau khi thay, chay lo hang thu 30 phut. Neu het loi, ghi serial cam bien cu vao so su co.
""",
    )
    ja_long = (
        "製造ラインの品質管理手順では工程ごとに寸法と外観を確認し記録票へ記入してから次工程へ送る"
        "必要があるがこの文は句点を置かずに説明を続けるため分割位置の測定に使う"
    ) * 16
    write_markdown(
        "src-manufacturing-qa.md",
        f"""# 製造ラインの品質管理手順

## 目的
本手順は製造ラインの品質管理を標準化する。

## 長文
{ja_long}。

## 通常手順
"""
        + _repeat_inline(
            "作業者は品質管理チェックリストを確認し、寸法、外観、ラベルを順番に点検する。不適合があればロットを隔離する。",
            32,
        ),
    )
    write_markdown(
        "src-safety-rules.md",
        """# 安全規則

安全規則は保護具、非常停止、火気の取扱いを定める。

"""
        + _repeat_inline(
            "保護メガネと手袋を着用し、非常停止位置を確認してから装置を起動する。安全規則に反するショートカットは禁止する。",
            32,
        ),
    )
    write_markdown(
        "src-work-procedures.md",
        """# 作業手順書

作業手順書は段取り、加工、後始末の順で記載する。

"""
        + _repeat_inline(
            "段取り後に安全規則の要点を復唱し、初品を確認してから連続加工を開始する。終了後は切粉を除去し点検表へ署名する。",
            32,
        ),
    )
    ja_trouble = (
        "温度異常が発生した場合はセンサー配線と制御盤の表示を確認し記録してから交換可否を判断する"
        "この説明も途中で句点を打たずに続ける"
    ) * 16
    write_markdown(
        "src-troubleshooting-ja.md",
        f"""# 温度異常のトラブルシューティング

## 現象
温度異常の警報が出る。

## 長文
{ja_trouble}。

## 手順
"""
        + _repeat_inline(
            "温度異常のときはセンサーを交換する前にコネクタと24V電源を確認する。交換後は校正して30分監視する。",
            32,
        ),
    )
    zh_long = (
        "生产线质量检查的标准流程要求对每一批次进行外观尺寸标签核对并在不合格时隔离批次"
        "本句故意不使用句号以便测量中文切分位置"
    ) * 16
    write_markdown(
        "src-production-qa-zh.md",
        f"""# 生产线质量检查流程

## 目的
本文件说明生产线质量检查的标准流程。

## 长句
{zh_long}。

## 步骤
"""
        + _repeat_inline(
            "质量检查人员应核对外观、尺寸和标签，只有全部项目合格才能流入下工序。发现不合格必须隔离并通知班长。",
            32,
        ),
    )
    write_markdown(
        "src-cost-plan-a-zh.md",
        """# 安装方案A运行成本

| 项目 | 月费用 | 说明 |
| --- | --- | --- |
| 人工 | 12000 | 两班 |
| 电费 | 4500 | 旧设备 |
| 维护 | 1800 | 定期 |

"""
        + _repeat_inline(
            "方案A的运行成本主要来自人工。与方案B对比时必须同时计算电费和维护费用。",
            32,
        ),
    )
    write_markdown(
        "src-cost-plan-b-zh.md",
        """# 安装方案B运行成本

| 项目 | 月费用 | 说明 |
| --- | --- | --- |
| 人工 | 8000 | 自动班 |
| 电费 | 6200 | 新电机 |
| 维护 | 3100 | 外包 |

"""
        + _repeat_inline(
            "方案B人工较低，但电费和维护费用更高。对比两种安装方案的运行成本和维护费用时不可只看人工。",
            32,
        ),
    )
    zh_trouble = (
        "当系统温度传感器报错时应先检查接头电源和手持温度计对照值再决定是否更换"
        "本句同样避免中途句号"
    ) * 16
    write_markdown(
        "src-troubleshooting-zh.md",
        f"""# 温度传感器故障排查

## 现象
系统温度传感器报错。

## 长句
{zh_trouble}。

## 步骤
"""
        + _repeat_inline(
            "温度传感器报错后先检查线束和24V电源，更换后重新标定并试运行三十分钟。",
            32,
        ),
    )
    write_table(
        "src-material-standards.table.json",
        ["Mã", "Tên nguyên liệu", "Tiêu chuẩn nhập kho", "Đơn vị"],
        [
            ["NL-01", "Thép tấm", "Độ dày 1.2mm +/-0.05", "tấm"],
            ["NL-02", "Sơn lót", "Độ dày 20um", "thùng"],
            ["NL-03", "Bu lông M8", "Cấp 8.8", "hộp"],
            ["NL-04", "Gioăng", "Chịu nhiệt 120C", "bộ"],
        ],
        sheet="NL nhập kho",
    )
    write_table(
        "src-maintenance-schedule.table.json",
        ["設備", "周期", "作業", "担当"],
        [
            ["コンベヤ", "週次", "注油", "保全A"],
            ["プレス", "月次", "点検", "保全B"],
            ["センサ", "日次", "清掃", "製造"],
            ["制御盤", "四半期", "絶縁測定", "電気"],
        ],
    )
    write_table(
        "src-material-inspection-zh.table.json",
        ["编号", "原材料", "入库检验项目", "标准"],
        [
            ["YL-01", "钢板", "厚度", "1.2mm"],
            ["YL-02", "涂料", "粘度", "合格区间"],
            ["YL-03", "螺栓", "强度等级", "8.8"],
            ["YL-04", "密封件", "耐温", "120C"],
        ],
    )
    sources = [
        ("src-quality-process", "vi", "markdown", False, "docs/src-quality-process.md"),
        ("src-material-standards", "vi", "spreadsheet", True, "tables/src-material-standards.table.json"),
        ("src-cost-analysis-a", "vi", "markdown", True, "docs/src-cost-analysis-a.md"),
        ("src-cost-analysis-b", "vi", "markdown", True, "docs/src-cost-analysis-b.md"),
        ("src-troubleshooting", "vi", "markdown", False, "docs/src-troubleshooting.md"),
        ("src-manufacturing-qa", "ja", "markdown", False, "docs/src-manufacturing-qa.md"),
        ("src-maintenance-schedule", "ja", "spreadsheet", True, "tables/src-maintenance-schedule.table.json"),
        ("src-safety-rules", "ja", "markdown", False, "docs/src-safety-rules.md"),
        ("src-work-procedures", "ja", "markdown", False, "docs/src-work-procedures.md"),
        ("src-troubleshooting-ja", "ja", "markdown", False, "docs/src-troubleshooting-ja.md"),
        ("src-production-qa-zh", "zh-CN", "markdown", False, "docs/src-production-qa-zh.md"),
        ("src-material-inspection-zh", "zh-CN", "spreadsheet", True, "tables/src-material-inspection-zh.table.json"),
        ("src-cost-plan-a-zh", "zh-CN", "markdown", True, "docs/src-cost-plan-a-zh.md"),
        ("src-cost-plan-b-zh", "zh-CN", "markdown", True, "docs/src-cost-plan-b-zh.md"),
        ("src-troubleshooting-zh", "zh-CN", "markdown", False, "docs/src-troubleshooting-zh.md"),
    ]
    import hashlib

    manifest_sources = []
    for source_id, language, document_type, has_tables, relative in sources:
        file_path = ROOT / relative
        digest = "sha256:" + hashlib.sha256(file_path.read_bytes()).hexdigest()
        manifest_sources.append({
            "source_id": source_id,
            "language": language,
            "document_type": document_type,
            "has_tables": has_tables,
            "path": relative.replace("\\", "/"),
            "sha256": digest,
        })
    manifest = {
        "manifest_version": "1.0",
        "corpus_kind": "public_evaluation",
        "synthetic": False,
        "privacy_note": "Invented public evaluation documents. No local_only factory text.",
        "sources": manifest_sources,
    }
    (ROOT / "corpus_public_v3.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote markdown to {DOCS}")
    print(f"Wrote tables to {TABLES}")
    print(f"Wrote {ROOT / 'corpus_public_v3.json'}")


if __name__ == "__main__":
    main()
