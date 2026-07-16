import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="주차장 정보", layout="wide")

st.title("🚗 주차장 정보 검색")

uploaded = st.file_uploader(
    "CSV 업로드 (cp949)",
    type=["csv"]
)

if uploaded is not None:

    df = pd.read_csv(uploaded, encoding="cp949")

    st.success("데이터 업로드 완료")

    # ----------------------
    # 사이드바
    # ----------------------

    st.sidebar.header("검색 조건")

    gu = st.sidebar.selectbox(
        "자치구 선택",
        ["전체"] + sorted(df["자치구"].unique().tolist())
    )

    parking_type = st.sidebar.selectbox(
        "주차장 종류",
        ["전체"] + sorted(df["종류"].unique().tolist())
    )

    pay_type = st.sidebar.selectbox(
        "무료/유료",
        ["전체","무료","유료"]
    )

    parking_time = st.sidebar.number_input(
        "예상 주차시간(분)",
        min_value=0,
        value=60
    )

    result = df.copy()

    if gu != "전체":
        result = result[result["자치구"] == gu]

    if parking_type != "전체":
        result = result[result["종류"] == parking_type]

    if pay_type != "전체":
        result = result[result["무료여부"] == pay_type]

    # ----------------------
    # 요금 계산 함수
    # ----------------------

    def calc_fee(row, minute):

        if row["무료여부"] == "무료":
            return 0

        base_fee = row["기본요금"]
        base_time = row["기본시간"]

        add_fee = row["추가요금"]
        add_time = row["추가시간"]

        if minute <= base_time:
            return base_fee

        extra = minute - base_time

        count = (extra + add_time - 1) // add_time

        return int(base_fee + count * add_fee)

    result["예상요금"] = result.apply(
        lambda x: calc_fee(x, parking_time),
        axis=1
    )

    st.subheader("검색 결과")

    st.dataframe(
        result[
            [
                "주차장명",
                "자치구",
                "종류",
                "무료여부",
                "예상요금"
            ]
        ],
        use_container_width=True
    )

    # ----------------------
    # 가장 저렴한 주차장
    # ----------------------

    st.subheader("💰 가장 저렴한 주차장")

    cheapest = result.sort_values("예상요금").head(1)

    if len(cheapest):

        row = cheapest.iloc[0]

        st.success(
            f"""
            주차장 : {row['주차장명']}

            자치구 : {row['자치구']}

            예상요금 : {row['예상요금']}원
            """
        )

    # ----------------------
    # 지도
    # ----------------------

    st.subheader("🗺 주차장 위치")

    if len(result):

        center = [
            result["위도"].mean(),
            result["경도"].mean()
        ]

        m = folium.Map(
            location=center,
            zoom_start=12
        )

        for _, row in result.iterrows():

            color = "green"

            if row["무료여부"] == "유료":
                color = "red"

            popup = f"""
            <b>{row['주차장명']}</b><br>
            자치구 : {row['자치구']}<br>
            종류 : {row['종류']}<br>
            예상요금 : {row['예상요금']}원
            """

            folium.Marker(
                location=[row["위도"], row["경도"]],
                popup=popup,
                icon=folium.Icon(color=color)
            ).add_to(m)

        st_folium(
            m,
            width=1000,
            height=600
        )
