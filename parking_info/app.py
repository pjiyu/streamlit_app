import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="주차장 정보", layout="wide")

st.title("🚗 주차장 정보 검색")

uploaded = st.file_uploader(
    "CSV 업로드 (cp949 또는 UTF-8)",
    type=["csv"]
)


# -------------------------------
# CSV 읽기 (cp949 → utf-8 자동)
# -------------------------------
def load_csv(file):
    try:
        df = pd.read_csv(file, encoding="cp949")
    except:
        file.seek(0)
        df = pd.read_csv(file, encoding="utf-8-sig")

    df.columns = (
        df.columns
        .str.strip()
        .str.replace("\ufeff", "", regex=False)
    )

    return df


# -------------------------------
# 컬럼 자동 찾기
# -------------------------------
def find_column(df, candidates):

    for c in candidates:
        if c in df.columns:
            return c

    for col in df.columns:
        for c in candidates:
            if c in col:
                return col

    return None


if uploaded is not None:

    df = load_csv(uploaded)

    st.success("데이터 업로드 완료")

    # 컬럼 확인용 (필요 없으면 삭제 가능)
    with st.expander("CSV 컬럼 확인"):
        st.write(df.columns.tolist())

    name_col = find_column(df, ["주차장명", "주차장"])
    gu_col = find_column(df, ["자치구", "구명", "구", "소재지"])
    type_col = find_column(df, ["종류", "주차장종류", "주차장구분"])
    free_col = find_column(df, ["무료여부", "요금정보", "유무료"])
    lat_col = find_column(df, ["위도", "LAT"])
    lon_col = find_column(df, ["경도", "LON"])
    base_fee_col = find_column(df, ["기본요금"])
    base_time_col = find_column(df, ["기본시간"])
    add_fee_col = find_column(df, ["추가요금"])
    add_time_col = find_column(df, ["추가시간"])

    required = [
        name_col,
        gu_col,
        type_col,
        free_col,
        lat_col,
        lon_col,
        base_fee_col,
        base_time_col,
        add_fee_col,
        add_time_col
    ]

    if None in required:

        st.error("필요한 컬럼을 찾을 수 없습니다.")

        st.write("현재 CSV 컬럼")

        st.write(df.columns.tolist())

        st.stop()

    # 숫자형 변환
    for c in [base_fee_col, base_time_col, add_fee_col, add_time_col, lat_col, lon_col]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # -----------------------
    # Sidebar
    # -----------------------

    st.sidebar.header("검색")

    gu = st.sidebar.selectbox(
        "자치구",
        ["전체"] + sorted(df[gu_col].dropna().unique().tolist())
    )

    parking_type = st.sidebar.selectbox(
        "주차장 종류",
        ["전체"] + sorted(df[type_col].dropna().unique().tolist())
    )

    pay = st.sidebar.selectbox(
        "무료/유료",
        ["전체", "무료", "유료"]
    )

    parking_time = st.sidebar.number_input(
        "예상 주차시간(분)",
        0,
        1440,
        60
    )

    result = df.copy()

    if gu != "전체":
        result = result[result[gu_col] == gu]

    if parking_type != "전체":
        result = result[result[type_col] == parking_type]

    if pay != "전체":
        result = result[result[free_col].astype(str).str.contains(pay)]

    # -----------------------
    # 요금 계산
    # -----------------------

    def calc_fee(row):

        if "무료" in str(row[free_col]):
            return 0

        minute = parking_time

        base_fee = row[base_fee_col]
        base_time = row[base_time_col]
        add_fee = row[add_fee_col]
        add_time = row[add_time_col]

        if pd.isna(base_fee):
            return 0

        if minute <= base_time:
            return int(base_fee)

        extra = minute - base_time

        count = (extra + add_time - 1) // add_time

        return int(base_fee + count * add_fee)

    result["예상요금"] = result.apply(calc_fee, axis=1)

    # -----------------------
    # 결과
    # -----------------------

    st.subheader("검색 결과")

    st.dataframe(
        result[
            [
                name_col,
                gu_col,
                type_col,
                free_col,
                "예상요금"
            ]
        ],
        use_container_width=True
    )

    # -----------------------
    # 가장 저렴한 주차장
    # -----------------------

    if len(result):

        cheapest = result.sort_values("예상요금").iloc[0]

        st.success(
            f"""
가장 저렴한 주차장

주차장명 : {cheapest[name_col]}

예상요금 : {cheapest['예상요금']:,}원
"""
        )

    # -----------------------
    # 지도
    # -----------------------

    if len(result):

        m = folium.Map(
            location=[
                result[lat_col].mean(),
                result[lon_col].mean()
            ],
            zoom_start=12
        )

        for _, row in result.iterrows():

            color = "green"

            if "유료" in str(row[free_col]):
                color = "red"

            folium.Marker(
                [row[lat_col], row[lon_col]],
                popup=f"""
<b>{row[name_col]}</b><br>
자치구 : {row[gu_col]}<br>
종류 : {row[type_col]}<br>
예상요금 : {row['예상요금']:,}원
""",
                icon=folium.Icon(color=color)
            ).add_to(m)

        st.subheader("주차장 위치")

        st_folium(
            m,
            width=1000,
            height=600
        )
