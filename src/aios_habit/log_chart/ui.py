# -*- coding: utf-8 -*-
"""Giao dien the chon va bieu do tuong tac ngay trong khung chat (Chat-First Log Chart Builder).

Nhiem vu:
- Khong man hinh/bang moi, dung tu the san pham chat-first.
- The chon: cham chon cot kem vai tro (truc X / nhom / gia tri Y), chon hang (tat ca / khoang / loc dieu kien vi du chi dong NG).
- Thu vien bieu do: hien anh thu nho VE BANG CHINH DU LIEU cua file vua tha (khong phai hinh minh hoa chung).
- Goi y xep hang thong minh theo kieu cot da chon.
- Bieu do da chon ve ngay trong cau tra loi (PNG + Download).
- Vong lap cai thien: diem cham huu ich/chua huu ich kem ly do khi che.
- Ghi ro nguon du lieu da dung (ten file, so dong, dieu kien loc).
"""

from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st

from aios_habit.log_chart.feedback import (
    PRESET_CHART_DISLIKE_REASONS,
    RATING_CHUA_HUU_ICH,
    RATING_HUU_ICH,
    record_chart_feedback,
    record_chart_render_event,
)
from aios_habit.log_chart.parser import (
    ParsedLogTable,
    ROLE_CATEGORICAL,
    ROLE_DATETIME,
    ROLE_NUMERIC,
    ROLE_RESULT,
)
from aios_habit.log_chart.recommender import recommend_chart_types
from aios_habit.log_chart.renderer import render_chart_image, render_thumbnail_image
from aios_habit.log_chart.session_store import save_chart_session
from aios_habit.log_chart.spec import (
    ALL_CHART_TYPES,
    CHART_PARETO,
    CHART_SPC,
    CHART_TITLES_VI,
    CHART_TREND,
    ChartSpec,
)


def render_log_chart_builder_card(
    spec: ChartSpec,
    table: ParsedLogTable,
    conversation_id: str = "",
    file_path: Optional[Path] = None,
    locale: str = "vi",
) -> None:
    """Render toan bo the chon cot/hang, thu vien bieu do kem thumbnail that va bieu do chinh trong chat."""
    card_key_base = f"wsc_chart_builder_{spec.spec_id}"

    # Container border cho the bieu do
    with st.container(border=True):
        st.markdown(
            f"#### 📊 Trình tạo biểu đồ thông minh từ dữ liệu: `{table.file_name}`"
        )
        st.caption(
            f"📁 Đã nhận diện: **{table.total_rows:,}** dòng · **{len(table.columns)}** cột · "
            f"Phân cách: `{table.delimiter}` · {table.provenance_note}"
        )

        # -------------------------------------------------------------
        # 1. GOI Y XEP HANG THONG MINH
        # -------------------------------------------------------------
        ranked = recommend_chart_types(table, spec.x_col, spec.y_col, spec.group_col)
        top_type, top_score, top_reason = ranked[0]

        st.info(f"💡 **Gợi ý hàng đầu**: **{CHART_TITLES_VI.get(top_type, top_type)}**\n\n*{top_reason}*")

        # -------------------------------------------------------------
        # 2. THE CHON COT KEM VAI TRO & HANG DU LIEU
        # -------------------------------------------------------------
        with st.expander("⚙️ **Tùy chỉnh chọn Cột & Hàng dữ liệu**", expanded=False):
            col_x, col_y, col_grp = st.columns(3)

            all_cols = table.get_column_names()
            num_cols = [c.name for c in table.get_columns_by_role(ROLE_NUMERIC)]
            cat_cols = [c.name for c in table.get_columns_by_role(ROLE_CATEGORICAL) + table.get_columns_by_role(ROLE_RESULT)]
            dt_cols = [c.name for c in table.get_columns_by_role(ROLE_DATETIME)]

            with col_x:
                x_default_idx = all_cols.index(spec.x_col) if spec.x_col in all_cols else 0
                chosen_x = st.selectbox(
                    "📌 Trục hoành X (Thời gian / Phân loại):",
                    options=all_cols,
                    index=x_default_idx,
                    key=f"{card_key_base}_sel_x",
                )
                last_x_key = f"{card_key_base}_prev_x"
                if last_x_key not in st.session_state:
                    st.session_state[last_x_key] = chosen_x
                elif chosen_x != st.session_state[last_x_key]:
                    st.session_state[last_x_key] = chosen_x
                    spec.x_col = chosen_x
                    if file_path:
                        save_chart_session(conversation_id, spec, file_path)
                    st.rerun()

            with col_y:
                y_options = ["(Tự động / Không chọn)"] + (num_cols if num_cols else all_cols)
                y_default_idx = y_options.index(spec.y_col) if spec.y_col in y_options else 0
                chosen_y = st.selectbox(
                    "📈 Giá trị đo Y (Số đo / Thông số):",
                    options=y_options,
                    index=y_default_idx,
                    key=f"{card_key_base}_sel_y",
                )
                last_y_key = f"{card_key_base}_prev_y"
                if last_y_key not in st.session_state:
                    st.session_state[last_y_key] = chosen_y
                elif chosen_y != st.session_state[last_y_key]:
                    st.session_state[last_y_key] = chosen_y
                    spec.y_col = chosen_y if chosen_y != "(Tự động / Không chọn)" else ""
                    if file_path:
                        save_chart_session(conversation_id, spec, file_path)
                    st.rerun()

            with col_grp:
                grp_options = ["(Không nhóm)"] + cat_cols
                grp_default_idx = (
                    grp_options.index(spec.group_col) if spec.group_col in grp_options else 0
                )
                chosen_grp = st.selectbox(
                    "🏷️ Phân nhóm (Line / Ca / Máy):",
                    options=grp_options,
                    index=grp_default_idx,
                    key=f"{card_key_base}_sel_grp",
                )
                new_grp = chosen_grp if chosen_grp != "(Không nhóm)" else None
                last_grp_key = f"{card_key_base}_prev_grp"
                if last_grp_key not in st.session_state:
                    st.session_state[last_grp_key] = new_grp
                elif new_grp != st.session_state[last_grp_key]:
                    st.session_state[last_grp_key] = new_grp
                    spec.group_col = new_grp
                    if file_path:
                        save_chart_session(conversation_id, spec, file_path)
                    st.rerun()

            # Chon hang du lieu
            st.markdown("---")
            st.markdown("**🔍 Lọc hàng dữ liệu:**")
            fcol_1, fcol_2, fcol_3 = st.columns(3)

            with fcol_1:
                filter_mode_options = ["Tất cả dòng", "Chỉ dòng NG (Lỗi)", "Lọc theo giá trị cụ thể"]
                cur_mode_idx = 0
                if spec.filter_op == "only_ng":
                    cur_mode_idx = 1
                elif spec.filter_col and spec.filter_val:
                    cur_mode_idx = 2

                chosen_fmode = st.radio(
                    "Chế độ lọc hàng:",
                    options=filter_mode_options,
                    index=cur_mode_idx,
                    key=f"{card_key_base}_radio_fmode",
                    horizontal=True,
                )
                last_fmode_key = f"{card_key_base}_prev_fmode"
                if last_fmode_key not in st.session_state:
                    st.session_state[last_fmode_key] = chosen_fmode
                elif chosen_fmode != st.session_state[last_fmode_key]:
                    st.session_state[last_fmode_key] = chosen_fmode
                    if chosen_fmode == "Tất cả dòng":
                        spec.filter_col = None
                        spec.filter_val = None
                        spec.filter_op = "all"
                        if file_path:
                            save_chart_session(conversation_id, spec, file_path)
                        st.rerun()
                    elif chosen_fmode == "Chỉ dòng NG (Lỗi)":
                        res_cols = table.get_columns_by_role(ROLE_RESULT)
                        spec.filter_col = res_cols[0].name if res_cols else (table.get_column_names()[0])
                        spec.filter_val = "NG"
                        spec.filter_op = "only_ng"
                        if file_path:
                            save_chart_session(conversation_id, spec, file_path)
                        st.rerun()

            with fcol_2:
                if chosen_fmode == "Lọc theo giá trị cụ thể":
                    f_col_picked = st.selectbox("Chọn cột lọc:", options=all_cols, key=f"{card_key_base}_fcol_pick")
                    f_val_input = st.text_input("Giá trị cần lọc:", value=spec.filter_val or "", key=f"{card_key_base}_fval_txt")
                    if st.button("Áp dụng lọc", key=f"{card_key_base}_btn_apply_filter"):
                        spec.filter_col = f_col_picked
                        spec.filter_val = f_val_input
                        spec.filter_op = "contains"
                        if file_path:
                            save_chart_session(conversation_id, spec, file_path)
                        st.rerun()

            with fcol_3:
                # Tuy chon SMA
                show_sma_cur = spec.options.get("show_sma", True)
                toggle_sma = st.checkbox("Hiển thị đường SMA(20)", value=show_sma_cur, key=f"{card_key_base}_chk_sma")
                last_sma_key = f"{card_key_base}_prev_sma"
                if last_sma_key not in st.session_state:
                    st.session_state[last_sma_key] = toggle_sma
                elif toggle_sma != st.session_state[last_sma_key]:
                    st.session_state[last_sma_key] = toggle_sma
                    spec.options["show_sma"] = toggle_sma
                    if file_path:
                        save_chart_session(conversation_id, spec, file_path)
                    st.rerun()

        # -------------------------------------------------------------
        # 3. THU VIEN BIEU DO KEM ANH THU NHO VE TU DU LIEU THAT
        # -------------------------------------------------------------
        st.markdown("##### 📚 Thư viện 10 kiểu biểu đồ sản xuất (Ảnh thu nhỏ từ dữ liệu thật):")
        thumb_cols = st.columns(5)
        thumb_cols_2 = st.columns(5)
        all_cols_ui = thumb_cols + thumb_cols_2

        for i, ct in enumerate(ALL_CHART_TYPES):
            ui_col = all_cols_ui[i]
            with ui_col:
                is_active = (ct == spec.chart_type)
                # Tinh thumbnail tu chinh du lieu that
                t_bytes = render_thumbnail_image(ct, spec, table)
                st.image(t_bytes, use_container_width=True)
                btn_label = f"✓ {CHART_TITLES_VI[ct].split('.')[1].strip()}" if is_active else CHART_TITLES_VI[ct].split('.')[1].strip()
                if st.button(btn_label, key=f"{card_key_base}_btn_type_{ct}", use_container_width=True, disabled=is_active):
                    spec.chart_type = ct
                    if file_path:
                        save_chart_session(conversation_id, spec, file_path)
                    st.rerun()

        # -------------------------------------------------------------
        # 4. VE BIEU DO CHINH
        # -------------------------------------------------------------
        st.markdown("---")
        t_start = time.time()
        try:
            main_png = render_chart_image(spec, table)
            render_duration = (time.time() - t_start) * 1000.0
            record_chart_render_event(
                chart_type=spec.chart_type,
                success=True,
                duration_ms=render_duration,
                file_name=table.file_name,
                rows_count=table.total_rows,
            )
            st.image(main_png, use_container_width=True)
            st.download_button(
                label=f"⬇️ Tải ảnh biểu đồ ({spec.chart_type.upper()}) về máy",
                data=main_png,
                file_name=f"bieu_do_{spec.chart_type}_{table.file_name}.png",
                mime="image/png",
                key=f"{card_key_base}_dl_png",
            )
        except Exception as e:
            record_chart_render_event(
                chart_type=spec.chart_type,
                success=False,
                error_msg=str(e),
                file_name=table.file_name,
                rows_count=table.total_rows,
            )
            st.error(f"⚠️ Không thể vẽ kiểu biểu đồ '{spec.chart_type}': {e}. Vui lòng chọn kiểu biểu đồ khác.")

        # -------------------------------------------------------------
        # 5. GOI Y THAO TAC TIEP THEO QUA LOI
        # -------------------------------------------------------------
        st.caption(
            "💬 **Hỏi tiếp bằng lời để điều chỉnh biểu đồ**: Thử gõ *'thêm đường SMA(20)'*, *'chỉ xem dòng NG'*, "
            "*'chuyển sang biểu đồ Pareto'*, hoặc *'xem tất cả dòng'*."
        )

        # -------------------------------------------------------------
        # 6. VONG LAP CAI THIEN: DANH GIA HUU ICH / CHUA HUU ICH
        # -------------------------------------------------------------
        st.markdown("---")
        fb_col_l, fb_col_r = st.columns([0.65, 0.35], vertical_alignment="center")
        with fb_col_l:
            st.markdown("**Đánh giá biểu đồ này:**")
        with fb_col_r:
            b_good, b_bad = st.columns(2)
            with b_good:
                if st.button("👍 Hữu ích", key=f"{card_key_base}_fb_good", use_container_width=True):
                    res = record_chart_feedback(
                        conversation_id=conversation_id,
                        chart_id=spec.spec_id,
                        chart_type=spec.chart_type,
                        rating=RATING_HUU_ICH,
                        file_name=table.file_name,
                    )
                    st.session_state[f"{card_key_base}_fb_status"] = "good"
                    st.rerun()
            with b_bad:
                with st.popover("👎 Chưa tốt", use_container_width=True):
                    st.markdown("**Góp ý để cải thiện:**")
                    picked_reason = st.radio(
                        "Lý do chưa hài lòng:",
                        options=PRESET_CHART_DISLIKE_REASONS,
                        key=f"{card_key_base}_rad_reason",
                    )
                    extra_note = st.text_input("Ghi chú thêm (tuỳ chọn):", key=f"{card_key_base}_txt_extra")
                    if st.button("Gửi góp ý", key=f"{card_key_base}_btn_submit_bad"):
                        full_reason = picked_reason if not extra_note else f"{picked_reason} | {extra_note}"
                        record_chart_feedback(
                            conversation_id=conversation_id,
                            chart_id=spec.spec_id,
                            chart_type=spec.chart_type,
                            rating=RATING_CHUA_HUU_ICH,
                            reason=full_reason,
                            file_name=table.file_name,
                        )
                        st.session_state[f"{card_key_base}_fb_status"] = "bad"
                        st.rerun()

        if st.session_state.get(f"{card_key_base}_fb_status") == "good":
            st.success("✅ Cảm ơn bạn đã phản hồi! Đánh giá đã được ghi nhận vào vòng lặp cải thiện liên tục.")
        elif st.session_state.get(f"{card_key_base}_fb_status") == "bad":
            st.info("ℹ️ Đã ghi nhận lý do chưa hài lòng để hoàn thiện thuật toán tạo biểu đồ.")
