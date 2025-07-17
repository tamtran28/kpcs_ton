import pandas as pd
import numpy as np

# --- 1. HÀM TÍNH TOÁN CỐT LÕI (ĐÃ SỬA LỖI KEYERROR KHI DỮ LIỆU RỖNG) ---
def calculate_summary_metrics(dataframe, groupby_cols, year_start_date, quarter_start_date, quarter_end_date):
    """
    Hàm tính toán các chỉ số với logic đã được sửa lại.
    """
    if not isinstance(groupby_cols, list):
        raise TypeError("groupby_cols phải là một danh sách (list)")

    def agg(data_filtered, cols):
        """
        Hàm tổng hợp phụ. Đã sửa lỗi để xử lý trường hợp dữ liệu rỗng
        bằng cách trả về một Series rỗng có chỉ mục được đặt tên chính xác.
        """
        if not cols:
            return len(data_filtered)
        if data_filtered.empty:
            empty_index = pd.MultiIndex.from_tuples([], names=cols)
            return pd.Series(dtype=int, index=empty_index)
        return data_filtered.groupby(cols).size()

    # --- A. TÍNH TOÁN CÁC CHỈ SỐ DÒNG CHẢY ---
    ton_dau_quy = agg(dataframe[
        (dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] < quarter_start_date) &
        ((dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'].isnull()) | (dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] >= quarter_start_date))
    ], groupby_cols)

    phat_sinh_quy = agg(dataframe[
        (dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] >= quarter_start_date) &
        (dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] <= quarter_end_date)
    ], groupby_cols)

    khac_phuc_quy = agg(dataframe[
        (dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] >= quarter_start_date) &
        (dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] <= quarter_end_date)
    ], groupby_cols)

    phat_sinh_nam = agg(dataframe[
        (dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] >= year_start_date) &
        (dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] <= quarter_end_date)
    ], groupby_cols)

    khac_phuc_nam = agg(dataframe[
        (dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] >= year_start_date) &
        (dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] <= quarter_end_date)
    ], groupby_cols)

    ton_dau_nam = agg(dataframe[
        (dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] < year_start_date) &
        ((dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'].isnull()) | (dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] >= year_start_date))
    ], groupby_cols)

    # --- B. TỔNG HỢP BẢNG VÀ TÍNH TOÁN CÁC CHỈ SỐ TRẠNG THÁI ---
    summary = pd.DataFrame({
        'Tồn đầu quý': ton_dau_quy, 'Phát sinh quý': phat_sinh_quy, 'Khắc phục quý': khac_phuc_quy,
        'Tồn đầu năm': ton_dau_nam, 'Phát sinh năm': phat_sinh_nam, 'Khắc phục năm': khac_phuc_nam,
    }).fillna(0).astype(int)

    summary['Tồn cuối quý'] = summary['Tồn đầu quý'] + summary['Phát sinh quý'] - summary['Khắc phục quý']
    summary['Kiến nghị chưa khắc phục'] = summary['Tồn cuối quý']

    df_actually_outstanding = dataframe[
        (dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] <= quarter_end_date) &
        ((dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'].isnull()) | (dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] > quarter_end_date))
    ]

    qua_han_khac_phuc = agg(df_actually_outstanding[df_actually_outstanding['Thời hạn hoàn thành (mm/dd/yyyy)'] < quarter_end_date], groupby_cols)
    qua_han_tren_1_nam = agg(df_actually_outstanding[df_actually_outstanding['Thời hạn hoàn thành (mm/dd/yyyy)'] < (quarter_end_date - pd.DateOffset(years=1))], groupby_cols)

    summary['Quá hạn khắc phục'] = qua_han_khac_phuc
    summary['Trong đó quá hạn trên 1 năm'] = qua_han_tren_1_nam
    summary = summary.fillna(0).astype(int)

    denominator = summary['Tồn đầu quý'] + summary['Phát sinh quý']
    summary['Tỷ lệ chưa KP đến cuối Quý'] = (summary['Tồn cuối quý'] / denominator).replace([np.inf, -np.inf], 0).fillna(0)

    final_cols_order = [
        'Tồn đầu năm', 'Phát sinh năm', 'Khắc phục năm',
        'Tồn đầu quý', 'Phát sinh quý', 'Khắc phục quý', 'Tồn cuối quý',
        'Kiến nghị chưa khắc phục', 'Quá hạn khắc phục', 'Trong đó quá hạn trên 1 năm',
        'Tỷ lệ chưa KP đến cuối Quý'
    ]
    summary = summary[[col for col in final_cols_order if col in summary.columns]]
    return summary

# --- 2. CÁC HÀM TẠO BÁO CÁO ---

def create_summary_table(dataframe, groupby_col, title, excel_writer, sheet_name, dates):
    """Hàm tạo báo cáo tổng hợp dạng phẳng."""
    print(f"--- Đang tạo: {title} ---")
    summary = calculate_summary_metrics(dataframe, [groupby_col], **dates)
    if not summary.empty:
        total_row = pd.DataFrame(summary.sum(numeric_only=True)).T
        total_row.index = ['TỔNG CỘNG']
        total_denom = total_row.at['TỔNG CỘNG', 'Tồn đầu quý'] + total_row.at['TỔNG CỘNG', 'Phát sinh quý']
        total_row['Tỷ lệ chưa KP đến cuối Quý'] = (total_row.at['TỔNG CỘNG', 'Tồn cuối quý'] / total_denom) if total_denom != 0 else 0
        summary = pd.concat([summary, total_row])
    summary.to_excel(excel_writer, sheet_name=sheet_name)
    print(f"✅ Đã lưu '{title}' vào sheet '{sheet_name}'")

def create_top_n_table(dataframe, n, child_col, title, excel_writer, sheet_name, dates):
    """Hàm tạo báo cáo Top N."""
    print(f"--- Đang tạo: {title} ---")
    summary = calculate_summary_metrics(dataframe, [child_col], **dates)
    top_n = summary.sort_values(by='Quá hạn khắc phục', ascending=False).head(n)
    top_n.to_excel(excel_writer, sheet_name=sheet_name)
    print(f"✅ Đã lưu '{title}' vào sheet '{sheet_name}'")

def create_hierarchical_table(dataframe, parent_col, child_col, title, excel_writer, sheet_name, dates):
    """Hàm tạo báo cáo phân cấp."""
    print(f"--- Đang tạo: {title} ---")
    summary = calculate_summary_metrics(dataframe, [child_col], **dates)
    if summary.empty:
        print(f"⚠️ Dữ liệu rỗng cho '{title}', bỏ qua.")
        return

    parent_mapping = dataframe[[child_col, parent_col]].drop_duplicates().set_index(child_col)
    summary_with_parent = summary.join(parent_mapping)
    parent_summary = calculate_summary_metrics(dataframe, [parent_col], **dates)

    final_report = []
    for parent_name in dataframe[parent_col].unique():
        if parent_name not in parent_summary.index: continue
        parent_row = parent_summary.loc[[parent_name]].reset_index().rename(columns={parent_col: 'Tên Đơn vị'})
        parent_row['Phân cấp'] = 'Cha'
        final_report.append(parent_row)

        children_df = summary_with_parent[summary_with_parent[parent_col] == parent_name].reset_index().rename(columns={child_col: 'Tên Đơn vị'})
        children_df['Phân cấp'] = 'Con'
        final_report.append(children_df)

    if final_report:
        full_report_df = pd.concat(final_report, ignore_index=True)
        cols = full_report_df.columns.tolist()
        cols.insert(0, cols.pop(cols.index('Phân cấp')))
        cols.insert(1, cols.pop(cols.index('Tên Đơn vị')))
        full_report_df = full_report_df[cols]
        full_report_df.to_excel(excel_writer, sheet_name=sheet_name, index=False)
        print(f"✅ Đã lưu '{title}' vào sheet '{sheet_name}'")

def create_detailed_overdue_table(dataframe, root_col, parent_col, child_col, title, excel_writer, sheet_name, dates):
    """
    Tạo bảng chi tiết phân tích các kiến nghị quá hạn theo nhiều khoảng thời gian.
    Đã sửa lỗi KeyError bằng cách dùng pd.crosstab chuẩn xác.
    """
    print(f"--- Đang tạo: {title} ---")
    q_end = dates['quarter_end_date']
    
    df_outstanding = dataframe[
        (dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] <= q_end) &
        ((dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'].isnull()) | (dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] > q_end))
    ].copy()

    if df_outstanding.empty:
        print(f"⚠️ Không có kiến nghị tồn đọng cho '{title}', bỏ qua.")
        return

    ton_cuoi_quy_child = calculate_summary_metrics(dataframe, [child_col], **dates)[['Tồn cuối quý']]
    ton_cuoi_quy_parent = calculate_summary_metrics(dataframe, [parent_col], **dates)[['Tồn cuối quý']]
    ton_cuoi_quy_root = calculate_summary_metrics(dataframe, [root_col], **dates)[['Tồn cuối quý']]

    df_overdue = df_outstanding[df_outstanding['Thời hạn hoàn thành (mm/dd/yyyy)'] < q_end].copy()
    if df_overdue.empty:
        print(f"ℹ️ Không có kiến nghị quá hạn cho '{title}'. Bảng chi tiết quá hạn sẽ trống.")
        child_overdue, parent_overdue, root_overdue = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    else:
        df_overdue['Số ngày quá hạn'] = (q_end - df_overdue['Thời hạn hoàn thành (mm/dd/yyyy)']).dt.days
        bins = [-np.inf, 90, 180, 270, 365, np.inf]
        labels = ['Dưới 3 tháng', 'Từ 3-6 tháng', 'Từ 6-9 tháng', 'Từ 9-12 tháng', 'Trên 1 năm']
        df_overdue['Nhóm quá hạn'] = pd.cut(df_overdue['Số ngày quá hạn'], bins=bins, labels=labels, right=False)

        def aggregate_overdue(group_col_name):
            return pd.crosstab(index=df_overdue[group_col_name], columns=df_overdue['Nhóm quá hạn'])

        child_overdue = aggregate_overdue(child_col)
        parent_overdue = aggregate_overdue(parent_col)
        root_overdue = aggregate_overdue(root_col)

    final_report = []
    for root_name in dataframe[root_col].unique():
        if not root_name or root_name not in ton_cuoi_quy_root.index: continue
        root_data = pd.concat([ton_cuoi_quy_root.loc[[root_name]], root_overdue.loc[[root_name]] if root_name in root_overdue.index else None], axis=1).fillna(0)
        root_data['Tên đơn vị'] = root_name
        root_data['Cấp'] = 1
        final_report.append(root_data)

        for parent_name in dataframe[dataframe[root_col] == root_name][parent_col].unique():
            if not parent_name or parent_name not in ton_cuoi_quy_parent.index: continue
            parent_data = pd.concat([ton_cuoi_quy_parent.loc[[parent_name]], parent_overdue.loc[[parent_name]] if parent_name in parent_overdue.index else None], axis=1).fillna(0)
            parent_data['Tên đơn vị'] = f"  {parent_name}"
            parent_data['Cấp'] = 2
            final_report.append(parent_data)

            children_in_parent = dataframe[dataframe[parent_col] == parent_name][child_col].unique()
            for child_name in children_in_parent:
                if not child_name or child_name not in ton_cuoi_quy_child.index: continue
                child_data = pd.concat([ton_cuoi_quy_child.loc[[child_name]], child_overdue.loc[[child_name]] if child_name in child_overdue.index else None], axis=1).fillna(0)
                child_data['Tên đơn vị'] = f"    {child_name}"
                child_data['Cấp'] = 3
                final_report.append(child_data)
    
    if not final_report:
        print(f"⚠️ Không tạo được báo cáo chi tiết cho '{title}'.")
        return
        
    full_report_df = pd.concat(final_report).reset_index(drop=True).fillna(0)
    final_cols = ['Cấp', 'Tên đơn vị', 'Tồn cuối quý', 'Dưới 3 tháng', 'Từ 3-6 tháng', 'Từ 6-9 tháng', 'Từ 9-12 tháng', 'Trên 1 năm']
    final_cols_exist = [col for col in final_cols if col in full_report_df.columns]
    full_report_df = full_report_df[final_cols_exist]
    numeric_cols = [col for col in final_cols_exist if col not in ['Tên đơn vị', 'Cấp']]
    if numeric_cols:
        full_report_df[numeric_cols] = full_report_df[numeric_cols].astype(int)

    full_report_df.to_excel(excel_writer, sheet_name=sheet_name, index=False)
    print(f"✅ Đã lưu '{title}' vào sheet '{sheet_name}'")


# --- 3. HÀM THỰC THI CHÍNH ---
def main(df, year, quarter):
    """Gói toàn bộ logic xử lý và xuất file vào một hàm chính."""

    # 1. Thiết lập thời gian và chuẩn hóa dữ liệu
    dates = {
        'year_start_date': pd.to_datetime(f'{year}-01-01'),
        'quarter_start_date': pd.to_datetime(f'{year}-{(quarter-1)*3 + 1}-01'),
        'quarter_end_date': pd.to_datetime(f'{year}-{(quarter-1)*3 + 1}-01') + pd.offsets.QuarterEnd(0)
    }
    date_cols = [
        'Ngày, tháng, năm ban hành (mm/dd/yyyy)',
        'NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)',
        'Thời hạn hoàn thành (mm/dd/yyyy)'
    ]
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors='coerce')

    # Đổi tên các cột dài để dễ làm việc
    df = df.rename(columns={
        'Đơn vị thực hiện KPCS (Nhập theo cột D của Sheet DTTHKPCS, mỗi dòng kiến nghị chỉ nhập 1 Đơn vị thực hiện KPCS)': 'DonViThucHien',
        'SUM (THEO Khối, KV, ĐVKD, Hội sở, Ban Dự Án QLTS)': 'DonViCha',
        'ĐVKD, AMC, Hội sở (Nhập ĐVKD hoặc Hội sở hoặc AMC)': 'NhomDonViGoc'
    })

    # Làm sạch các cột văn bản (SỬA LỖI ATTRIBUTEERROR)
    # Vòng lặp này đảm bảo .str chỉ được dùng trên từng cột (Series)
    text_cols_to_clean = ['DonViThucHien', 'DonViCha', 'NhomDonViGoc']
    for col_name in text_cols_to_clean:
        if col_name in df.columns:
            df[col_name] = df[col_name].astype(str).str.strip().replace('nan', '')

    # Phân tách dữ liệu
    df['Nhom_Don_Vi'] = np.where(df['NhomDonViGoc'] == 'Hội sở', 'Hội sở', 'ĐVKD, AMC')
    df_hoiso = df[df['Nhom_Don_Vi'] == 'Hội sở'].copy()
    df_dvdk_amc = df[df['Nhom_Don_Vi'] == 'ĐVKD, AMC'].copy()

    # Định nghĩa các biến cột
    ROOT_COL = 'NhomDonViGoc'
    PARENT_COL = 'DonViCha'
    CHILD_COL = 'DonViThucHien'

    # 3. Thực thi và xuất Excel
    output_filename = f"Tong_hop_Bao_cao_KPCS_Q{quarter}_{year}.xlsx"
    with pd.ExcelWriter(output_filename, engine='xlsxwriter') as writer:
        print(f"🚀 Bắt đầu tạo các báo cáo cho Quý {quarter}/{year}...")

        create_summary_table(df, 'Nhom_Don_Vi', "BC Tình hình KPCS toàn hàng", writer, "1_TH_ToanHang", dates)
        
        # Báo cáo cho Hội sở
        create_summary_table(df_hoiso, PARENT_COL, "BC Tình hình KPCS các ĐV Hội sở", writer, "2_TH_HoiSo", dates)
        create_top_n_table(df_hoiso, 5, CHILD_COL, "BC Top 5 ĐV Hội sở quá hạn", writer, "3_Top5_HoiSo", dates)
        create_hierarchical_table(df_hoiso, PARENT_COL, CHILD_COL, "Chi tiết KPCS từng Phòng Ban Hội sở", writer, "4_PhanCap_HoiSo", dates)

        # Báo cáo cho ĐVKD & AMC
        create_summary_table(df_dvdk_amc, PARENT_COL, "BC ĐVKD & AMC theo Khu vực", writer, "5_TH_DVDK_KhuVuc", dates)
        create_top_n_table(df_dvdk_amc, 10, CHILD_COL, "BC Top 10 ĐVKD quá hạn", writer, "6_Top10_DVDK", dates)
        create_hierarchical_table(df_dvdk_amc, PARENT_COL, CHILD_COL, "Chi tiết ĐVKD theo Khu vực", writer, "7_ChiTiet_DVDK", dates)

        # Báo cáo chi tiết quá hạn mới
        create_detailed_overdue_table(df_hoiso, ROOT_COL, PARENT_COL, CHILD_COL, "BC chi tiết quá hạn Hội sở", writer, "8_ChiTietQuaHan_HS", dates)
        
        print(f"\n🎉 Đã tạo xong file Excel: {output_filename}")


# --- 4. ĐIỂM BẮT ĐẦU CHẠY SCRIPT ---
if __name__ == '__main__':
    # --- BƯỚC 1: TẢI DỮ LIỆU ---
    # Để chạy thực tế, hãy bỏ bình luận (xóa dấu #) các dòng dưới
    # và thay "ten_file_cua_ban.xlsx" bằng tên file thực tế của bạn.
    try:
        # df = pd.read_excel("ten_file_cua_ban.xlsx")
        
        # --- DÙNG DỮ LIỆU GIẢ LẬP ĐỂ KIỂM THỬ ---
        # (Bạn có thể xóa phần này khi chạy với file thật)
        print("⚠️ ĐANG SỬ DỤNG DỮ LIỆU GIẢ LẬP ĐỂ KIỂM THỬ SCRIPT.")
        data = {
            'Ngày, tháng, năm ban hành (mm/dd/yyyy)': pd.to_datetime(['2024-01-15', '2024-06-20', '2024-08-01', '2023-11-10', '2024-02-05', '2024-04-10']),
            'NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)': pd.to_datetime([None, '2024-08-10', None, None, '2025-01-01', None]),
            'Thời hạn hoàn thành (mm/dd/yyyy)': pd.to_datetime(['2024-03-15', '2024-07-30', '2024-09-01', '2024-01-10', '2024-05-05', '2024-06-15']),
            'ĐVKD, AMC, Hội sở (Nhập ĐVKD hoặc Hội sở hoặc AMC)': ['Hội sở', 'Hội sở', 'ĐVKD', 'Hội sở', 'Hội sở', 'Hội sở'],
            'SUM (THEO Khối, KV, ĐVKD, Hội sở, Ban Dự Án QLTS)': ['Khối Vận hành', 'Khối CNTT', 'Khu vực HCM', 'Khối Vận hành', 'Khối CNTT', 'Khối CNTT'],
            'Đơn vị thực hiện KPCS (Nhập theo cột D của Sheet DTTHKPCS, mỗi dòng kiến nghị chỉ nhập 1 Đơn vị thực hiện KPCS)': ['Phòng A', 'Phòng B', 'Chi nhánh X', 'Phòng A', 'Phòng C', 'Phòng B']
        }
        df = pd.DataFrame(data)
        # --- KẾT THÚC DỮ LIỆU GIẢ LẬP ---

        # --- BƯỚC 2: THIẾT LẬP THAM SỐ ---
        # Đặt năm và quý muốn chạy báo cáo ở đây
        TARGET_YEAR = 2024
        TARGET_QUARTER = 3

        # --- BƯỚC 3: GỌI HÀM CHÍNH ---
        main(df, TARGET_YEAR, TARGET_QUARTER)
        
    except FileNotFoundError:
        print("\n❌ LỖI: Không tìm thấy file Excel. Hãy chắc chắn rằng:")
        print("1. Tên file trong code `pd.read_excel(\"ten_file_cua_ban.xlsx\")` là chính xác.")
        print("2. File Excel nằm cùng thư mục với script Python này.")
    except Exception as e:
        print(f"\n❌ ĐÃ CÓ LỖI XẢY RA: {e}")
