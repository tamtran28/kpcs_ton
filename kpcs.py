import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# --- CẤU HÌNH TRANG WEB ---
st.set_page_config(layout="wide", page_title="Hệ thống Báo cáo KPCS Tự động")
st.title("📊 Hệ thống Báo cáo Tự động")

# ==============================================================================
# PHẦN 1: CÁC HÀM LOGIC CỐT LÕI
# ==============================================================================

# --- CÁC HÀM CŨ CHO 2 NÚT BẤM ĐẦU TIÊN (Giữ nguyên) ---
def calculate_summary_metrics(dataframe, groupby_cols, year_start_date, quarter_start_date, quarter_end_date):
    # ... (Nội dung hàm này không đổi)
    if not isinstance(groupby_cols, list):
        raise TypeError("groupby_cols phải là một danh sách (list)")
    def agg(data_filtered, cols):
        if data_filtered.empty: return 0 if not cols else pd.Series(dtype=int)
        if not cols: return len(data_filtered)
        return data_filtered.groupby(cols).size()
    ton_dau_quy = agg(dataframe[(dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] < quarter_start_date) & ((dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'].isnull()) | (dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] >= quarter_start_date))], groupby_cols)
    phat_sinh_quy = agg(dataframe[(dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] >= quarter_start_date) & (dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] <= quarter_end_date)], groupby_cols)
    khac_phuc_quy = agg(dataframe[(dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] >= quarter_start_date) & (dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] <= quarter_end_date)], groupby_cols)
    phat_sinh_nam = agg(dataframe[(dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] >= year_start_date) & (dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] <= quarter_end_date)], groupby_cols)
    khac_phuc_nam = agg(dataframe[(dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] >= year_start_date) & (dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] <= quarter_end_date)], groupby_cols)
    ton_dau_nam = agg(dataframe[(dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] < year_start_date) & ((dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'].isnull()) | (dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] >= year_start_date))], groupby_cols)
    if not groupby_cols:
        summary = pd.DataFrame({'Tồn đầu quý': [ton_dau_quy], 'Phát sinh quý': [phat_sinh_quy], 'Khắc phục quý': [khac_phuc_quy], 'Tồn đầu năm': [ton_dau_nam], 'Phát sinh năm': [phat_sinh_nam], 'Khắc phục năm': [khac_phuc_nam]})
    else:
        summary = pd.DataFrame({'Tồn đầu quý': ton_dau_quy, 'Phát sinh quý': phat_sinh_quy, 'Khắc phục quý': khac_phuc_quy, 'Tồn đầu năm': ton_dau_nam, 'Phát sinh năm': phat_sinh_nam, 'Khắc phục năm': khac_phuc_nam}).fillna(0).astype(int)
    summary['Tồn cuối quý'] = summary['Tồn đầu quý'] + summary['Phát sinh quý'] - summary['Khắc phục quý']
    df_actually_outstanding = dataframe[(dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] <= quarter_end_date) & ((dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'].isnull()) | (dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] > quarter_end_date))]
    qua_han_khac_phuc = agg(df_actually_outstanding[df_actually_outstanding['Thời hạn hoàn thành (mm/dd/yyyy)'] < quarter_end_date], groupby_cols)
    qua_han_tren_1_nam = agg(df_actually_outstanding[df_actually_outstanding['Thời hạn hoàn thành (mm/dd/yyyy)'] < (quarter_end_date - pd.DateOffset(years=1))], groupby_cols)
    summary['Quá hạn khắc phục'] = qua_han_khac_phuc
    summary['Trong đó quá hạn trên 1 năm'] = qua_han_tren_1_nam
    summary = summary.fillna(0).astype(int)
    denominator = summary['Tồn đầu quý'] + summary['Phát sinh quý']
    summary['Tỷ lệ chưa KP đến cuối Quý'] = (summary['Tồn cuối quý'] / denominator).replace([np.inf, -np.inf], 0).fillna(0)
    final_cols_order = ['Tồn đầu năm', 'Phát sinh năm', 'Khắc phục năm', 'Tồn đầu quý', 'Phát sinh quý', 'Khắc phục quý', 'Tồn cuối quý', 'Quá hạn khắc phục', 'Trong đó quá hạn trên 1 năm', 'Tỷ lệ chưa KP đến cuối Quý']
    summary = summary.reindex(columns=final_cols_order, fill_value=0)
    return summary

# ... (Các hàm create_summary_table, create_top_n_table, create_hierarchical_table_7_reports giữ nguyên)
def create_summary_table(dataframe, groupby_col, dates):
    summary = calculate_summary_metrics(dataframe, [groupby_col], **dates)
    if not summary.empty:
        total_row = pd.DataFrame(summary.sum(numeric_only=True)).T
        total_row.index = ['TỔNG CỘNG']
        total_denom = total_row.at['TỔNG CỘNG', 'Tồn đầu quý'] + total_row.at['TỔNG CỘNG', 'Phát sinh quý']
        total_row['Tỷ lệ chưa KP đến cuối Quý'] = (total_row.at['TỔNG CỘNG', 'Tồn cuối quý'] / total_denom) if total_denom != 0 else 0
        summary = pd.concat([summary, total_row])
    return summary

def create_top_n_table(dataframe, n, dates):
    CHILD_COL = 'Đơn vị thực hiện KPCS trong quý'
    if CHILD_COL not in dataframe.columns:
        st.error(f"Lỗi: Không tìm thấy cột '{CHILD_COL}' để tạo báo cáo Top {n}.")
        return pd.DataFrame()
    full_summary = calculate_summary_metrics(dataframe, [CHILD_COL], **dates)
    top_n = full_summary.sort_values(by='Quá hạn khắc phục', ascending=False).head(n)
    total_row = pd.DataFrame(full_summary.sum(numeric_only=True)).T
    total_row.index = ['TỔNG CỘNG CỦA NHÓM']
    total_denom = total_row.at['TỔNG CỘNG CỦA NHÓM', 'Tồn đầu quý'] + total_row.at['TỔNG CỘNG CỦA NHÓM', 'Phát sinh quý']
    total_row['Tỷ lệ chưa KP đến cuối Quý'] = (total_row.at['TỔNG CỘNG CỦA NHÓM', 'Tồn cuối quý'] / total_denom) if total_denom != 0 else 0
    return pd.concat([top_n, total_row])

def create_hierarchical_table_7_reports(dataframe, parent_col, child_col, dates):
    summary_cols_template = ['Tồn đầu năm', 'Phát sinh năm', 'Khắc phục năm', 'Tồn đầu quý', 'Phát sinh quý', 'Khắc phục quý', 'Tồn cuối quý', 'Quá hạn khắc phục', 'Trong đó quá hạn trên 1 năm', 'Tỷ lệ chưa KP đến cuối Quý']
    cols_order = ['Tên Đơn vị'] + summary_cols_template
    if dataframe.empty or parent_col not in dataframe.columns or child_col not in dataframe.columns:
        return pd.DataFrame(columns=cols_order)
    summary = calculate_summary_metrics(dataframe, [child_col], **dates)
    parent_mapping = dataframe[[child_col, parent_col]].drop_duplicates().set_index(child_col)
    summary_with_parent = summary.join(parent_mapping)
    parent_summary = calculate_summary_metrics(dataframe, [parent_col], **dates)
    final_report_rows = []
    unique_parents = dataframe[parent_col].dropna().unique()
    for parent_name in unique_parents:
        if parent_name not in parent_summary.index: continue
        parent_row = parent_summary.loc[[parent_name]].reset_index().rename(columns={parent_col: 'Tên Đơn vị'})
        parent_row['Tên Đơn vị'] = f"**{parent_name}**"
        final_report_rows.append(parent_row)
        children_df = summary_with_parent[summary_with_parent[parent_col] == parent_name].reset_index().rename(columns={'index': 'Tên Đơn vị'})
        children_df['Tên Đơn vị'] = "  •  " + children_df['Tên Đơn vị'].astype(str)
        final_report_rows.append(children_df)
    if not final_report_rows: return pd.DataFrame(columns=cols_order)
    full_report_df = pd.concat(final_report_rows, ignore_index=True)
    grand_total_row = calculate_summary_metrics(dataframe, [], **dates)
    grand_total_row['Tên Đơn vị'] = '**TỔNG CỘNG TOÀN BỘ**'
    full_report_df = pd.concat([full_report_df, grand_total_row], ignore_index=True)
    return full_report_df.reindex(columns=cols_order)

# --- HÀM MỚI: Các hàm cho chức năng "BÁO CÁO TÌNH HÌNH QUÁ HẠN" ---

def calculate_overdue_metrics(dataframe, groupby_cols, quarter_end_date):
    """Hàm mới chuyên tính toán các chỉ số quá hạn theo mốc thời gian."""
    if dataframe.empty:
        return pd.DataFrame()
    
    def agg(data_filtered, cols):
        if data_filtered.empty: return 0 if not cols else pd.Series(dtype=int)
        if not cols: return len(data_filtered)
        return data_filtered.groupby(cols).size()

    # 1. Xác định các kiến nghị còn tồn đọng tại cuối quý
    df_outstanding = dataframe[
        (dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] <= quarter_end_date) &
        ((dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'].isnull()) | (dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] > quarter_end_date))
    ].copy()

    ton_cuoi_quy = agg(df_outstanding, groupby_cols)

    # 2. Từ các kiến nghị tồn đọng, lọc ra các kiến nghị quá hạn
    df_overdue = df_outstanding[df_outstanding['Thời hạn hoàn thành (mm/dd/yyyy)'] < quarter_end_date].copy()
    
    # Tính số ngày quá hạn
    df_overdue['Số ngày quá hạn'] = (quarter_end_date - df_overdue['Thời hạn hoàn thành (mm/dd/yyyy)']).dt.days

    # 3. Phân loại quá hạn theo các mốc thời gian
    bins = [-1, 89, 179, 269, 364, np.inf]
    labels = ['Dưới 3 tháng', 'Từ 3 đến dưới 6 tháng', 'Từ 6 đến dưới 9 tháng', 'Từ 9 đến 12 tháng', 'Trên 12 tháng']
    df_overdue['Nhóm quá hạn'] = pd.cut(df_overdue['Số ngày quá hạn'], bins=bins, labels=labels)

    # 4. Thống kê theo nhóm
    if not groupby_cols: # Tính tổng
        overdue_breakdown = df_overdue['Nhóm quá hạn'].value_counts().to_frame().T
        overdue_breakdown['Tổng quá hạn'] = overdue_breakdown.sum(axis=1)
        summary = pd.DataFrame([{'Tồn cuối quý': ton_cuoi_quy}]).join(overdue_breakdown)
    else: # Tính chi tiết
        summary = pd.DataFrame({'Tồn cuối quý': ton_cuoi_quy})
        overdue_breakdown = pd.crosstab(df_overdue[groupby_cols[0]], df_overdue['Nhóm quá hạn'])
        summary = summary.join(overdue_breakdown, how='left')
        summary['Tổng quá hạn'] = summary[labels].sum(axis=1)

    # Đảm bảo tất cả các cột luôn tồn tại
    for col in labels:
        if col not in summary.columns:
            summary[col] = 0
    
    return summary.fillna(0).astype(int)

def create_overdue_report(dataframe, parent_col, child_col, quarter_end_date):
    """Hàm mới để tạo báo cáo Tình hình quá hạn có phân cấp."""
    cols_order = ['Tên Đơn vị', 'Tồn cuối quý', 'Tổng quá hạn', 'Dưới 3 tháng', 'Từ 3 đến dưới 6 tháng', 'Từ 6 đến dưới 9 tháng', 'Từ 9 đến 12 tháng', 'Trên 12 tháng']
    if dataframe.empty or parent_col not in dataframe.columns or child_col not in dataframe.columns:
        return pd.DataFrame(columns=cols_order)

    summary = calculate_overdue_metrics(dataframe, [child_col], quarter_end_date).reset_index().rename(columns={'index': child_col})
    parent_mapping = dataframe[[child_col, parent_col]].drop_duplicates().set_index(child_col)
    summary_with_parent = summary.join(parent_mapping, on=child_col)
    parent_summary = calculate_overdue_metrics(dataframe, [parent_col], quarter_end_date)
    
    final_report_rows = []
    unique_parents = dataframe[parent_col].dropna().unique()

    for parent_name in unique_parents:
        if parent_name not in parent_summary.index: continue
        
        parent_row = parent_summary.loc[[parent_name]].reset_index().rename(columns={parent_col: 'Tên Đơn vị'})
        parent_row['Tên Đơn vị'] = f"**{parent_name}**"
        final_report_rows.append(parent_row)
        
        children_df = summary_with_parent[summary_with_parent[parent_col] == parent_name].rename(columns={child_col: 'Tên Đơn vị'})
        children_df['Tên Đơn vị'] = "  •  " + children_df['Tên Đơn vị'].astype(str)
        final_report_rows.append(children_df)
    
    if not final_report_rows: return pd.DataFrame(columns=cols_order)
    
    full_report_df = pd.concat(final_report_rows, ignore_index=True)
    grand_total_row = calculate_overdue_metrics(dataframe, [], quarter_end_date)
    grand_total_row['Tên Đơn vị'] = '**TỔNG CỘNG TOÀN BỘ**'
    full_report_df = pd.concat([full_report_df, grand_total_row], ignore_index=True)

    return full_report_df.reindex(columns=cols_order).fillna(0)


# ==============================================================================
# PHẦN 4: GIAO DIỆN VÀ LUỒNG THỰC THI CỦA STREAMLIT
# ==============================================================================

with st.sidebar:
    st.header("⚙️ Tùy chọn báo cáo")
    input_year = st.number_input("Chọn Năm báo cáo", min_value=2020, max_value=2030, value=2024)
    input_quarter = st.selectbox("Chọn Quý báo cáo", options=[1, 2, 3, 4], index=3)
    uploaded_file = st.file_uploader("📂 Tải lên file Excel dữ liệu thô", type=["xlsx", "xls"])

if uploaded_file is not None:
    st.success(f"✅ Đã tải lên thành công file: **{uploaded_file.name}**")
    
    @st.cache_data
    def load_data(file):
        df = pd.read_excel(file)
        date_cols = ['Ngày, tháng, năm ban hành (mm/dd/yyyy)', 'NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)', 'Thời hạn hoàn thành (mm/dd/yyyy)']
        for col in date_cols:
            if col in df.columns: df[col] = pd.to_datetime(df[col], errors='coerce')
        return df

    df_raw = load_data(uploaded_file)
    st.write("Xem trước 5 dòng dữ liệu đầu tiên:")
    st.dataframe(df_raw.head())

    # --- Chuẩn bị dữ liệu chung sau khi tải lên ---
    df = df_raw.copy()
    dates = {'year_start_date': pd.to_datetime(f'{input_year}-01-01'), 'quarter_start_date': pd.to_datetime(f'{input_year}-{(input_quarter-1)*3 + 1}-01'), 'quarter_end_date': pd.to_datetime(f'{input_year}-{(input_quarter-1)*3 + 1}-01') + pd.offsets.QuarterEnd(0)}
    for col in ['Đơn vị thực hiện KPCS trong quý', 'SUM (THEO Khối, KV, ĐVKD, Hội sở, Ban Dự Án QLTS)', 'ĐVKD, AMC, Hội sở (Nhập ĐVKD hoặc Hội sở hoặc AMC)', 'Đoàn KT/GSTX']:
        if col in df.columns: df[col] = df[col].astype(str).str.strip().replace('nan', '')
    df['Nhom_Don_Vi'] = np.where(df['ĐVKD, AMC, Hội sở (Nhập ĐVKD hoặc Hội sở hoặc AMC)'] == 'Hội sở', 'Hội sở', 'ĐVKD, AMC')
    df_hoiso = df[df['Nhom_Don_Vi'] == 'Hội sở'].copy()
    df_dvdk_amc = df[df['Nhom_Don_Vi'] == 'ĐVKD, AMC'].copy()
    PARENT_COL = 'SUM (THEO Khối, KV, ĐVKD, Hội sở, Ban Dự Án QLTS)'
    CHILD_COL = 'Đơn vị thực hiện KPCS trong quý'

    # SỬA ĐỔI: TẠO 3 CỘT CHO 3 NÚT BẤM
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🚀 Tạo 7 Báo cáo (Tổng hợp)"):
            # ... (Logic của nút này không đổi)
            with st.spinner("⏳ Đang xử lý và tạo 7 báo cáo..."):
                # ... (phần code tạo df1, df2... df7 không đổi)
                df1 = create_summary_table(df, 'Nhom_Don_Vi', dates)
                df2 = create_summary_table(df_hoiso, PARENT_COL, dates)
                summary_hoiso_by_parent = calculate_summary_metrics(df_hoiso, [PARENT_COL], **dates)
                df3_top5_parents = summary_hoiso_by_parent.sort_values(by='Quá hạn khắc phục', ascending=False).head(5)
                total_hoiso_row = pd.DataFrame(summary_hoiso_by_parent.sum(numeric_only=True)).T
                total_hoiso_row.index = ['TỔNG CỘNG HỘI SỞ']
                df3 = pd.concat([df3_top5_parents, total_hoiso_row])
                df4 = create_hierarchical_table_7_reports(df_hoiso, PARENT_COL, CHILD_COL, dates)
                df5 = create_summary_table(df_dvdk_amc, PARENT_COL, dates)
                df6 = create_top_n_table(df_dvdk_amc, 10, dates)
                df7 = create_hierarchical_table_7_reports(df_dvdk_amc, PARENT_COL, CHILD_COL, dates)
                output_stream = BytesIO()
                with pd.ExcelWriter(output_stream, engine='xlsxwriter') as writer:
                    # ... (Phần code ghi ra excel không đổi)
                    workbook = writer.book
                    border_format = workbook.add_format({'border': 1, 'valign': 'vcenter'})
                    def write_to_sheet(df_to_write, sheet_name, index=True):
                        df_to_write.to_excel(writer, sheet_name=sheet_name, index=index)
                        worksheet = writer.sheets[sheet_name]
                        num_rows, num_cols = df_to_write.shape
                        worksheet.conditional_format(0, 0, num_rows, num_cols + (1 if index else 0) - 1, {'type': 'no_blanks', 'format': border_format})
                        for idx, col in enumerate(df_to_write.columns):
                            series = df_to_write[col]
                            max_len = max((series.astype(str).map(len).max(), len(str(series.name)))) + 2
                            worksheet.set_column(idx + (1 if index else 0), idx + (1 if index else 0), max_len)
                        if index:
                            max_len_idx = max(df_to_write.index.astype(str).map(len).max(), len(str(df_to_write.index.name))) + 2
                            worksheet.set_column(0, 0, max_len_idx)
                    write_to_sheet(df1, "1_TH_ToanHang", index=True)
                    write_to_sheet(df2, "2_TH_HoiSo", index=True)
                    write_to_sheet(df3, "3_Top5_HoiSo", index=True)
                    write_to_sheet(df4, "4_PhanCap_HoiSo", index=False)
                    write_to_sheet(df5, "5_TH_DVDK_KhuVuc", index=True)
                    write_to_sheet(df6, "6_Top10_DVDK", index=True)
                    write_to_sheet(df7, "7_ChiTiet_DVDK", index=False)
                excel_data = output_stream.getvalue()
            st.success("🎉 Đã tạo xong file Excel Tổng hợp!")
            st.download_button(label="📥 Tải xuống File Excel Tổng hợp", data=excel_data, file_name=f"Tong_hop_Bao_cao_KPCS_Q{input_quarter}_{input_year}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # Nút bấm thứ 3 cho chức năng mới
    with col3:
        if st.button("📈 Tạo Báo cáo Tình hình Quá hạn"):
            with st.spinner("⏳ Đang xử lý và tạo báo cáo Quá hạn..."):
                # Tạo 2 báo cáo quá hạn cho Hội sở và ĐVKD
                df_overdue_hoiso = create_overdue_report(df_hoiso, PARENT_COL, CHILD_COL, dates['quarter_end_date'])
                df_overdue_dvdk_amc = create_overdue_report(df_dvdk_amc, PARENT_COL, CHILD_COL, dates['quarter_end_date'])

                output_stream_overdue = BytesIO()
                with pd.ExcelWriter(output_stream_overdue, engine='xlsxwriter') as writer:
                    # Ghi 2 sheet vào file Excel
                    df_overdue_hoiso.to_excel(writer, sheet_name="QuaHan_HoiSo", index=False)
                    df_overdue_dvdk_amc.to_excel(writer, sheet_name="QuaHan_DVDK_AMC", index=False)
                
                excel_data_overdue = output_stream_overdue.getvalue()

            st.success("🎉 Đã tạo xong file Excel Tình hình Quá hạn!")
            st.download_button(
                label="📥 Tải xuống File Excel Quá hạn",
                data=excel_data_overdue,
                file_name=f"Tinh_hinh_Qua_han_Q{input_quarter}_{input_year}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

else:
    st.info("💡 Vui lòng tải lên file Excel chứa dữ liệu thô để bắt đầu.")