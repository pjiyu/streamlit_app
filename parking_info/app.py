import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium


# -------------------------
# 페이지 설정
# -------------------------
st.set_page_config(
    page_title="주차장 정보 검색 서비스",
    layout="wide"
)

st.title("🚗 서울 주차장 정보 검색 웹앱")
st.write("주차 위치, 요금, 예상 비용, 저렴한 주차장을 찾아주는 서비스입니다.")


# -------------------------
# CSV 업로드
# -------------------------
uploaded_file = st.file_uploader(
    "주차장 CSV 파일 업로드",
    type=["csv"]
)


if uploaded_file is not None:

    # cp949 인코딩 적용
    try:
        df = pd.read_csv(
            uploaded_file,
            encoding="cp949"
        )

    except:
        df = pd.read_csv(
            uploaded_file,
            encoding="utf-8"
        )


    st.success(
        f"데이터 불러오기 완료 : {len(df)}개 주차장"
    )


    # -------------------------
    # 데이터 전처리
    # -------------------------

    # 결측값 처리
    df["위도"] = pd.to_numeric(
        df["위도"],
        errors="coerce"
    )

    df["경도"] = pd.to_numeric(
        df["경도"],
        errors="coerce"
    )


    # 위치 없는 데이터 제거
    map_df = df.dropna(
        subset=["위도","경도"]
    )


    # 요금 숫자 변환
    price_cols = [
        "기본 주차 요금",
        "기본 주차 시간(분 단위)",
        "추가 단위 요금",
        "추가 단위 시간(분 단위)"
    ]

    for col in price_cols:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        ).fillna(0)



    # -------------------------
    # 검색 조건
    # -------------------------

    st.sidebar.header("검색 조건")


    # 자치구 추출
    df["자치구"] = df["주소"].str.split().str[0]


    gu_list = [
        "전체"
    ] + sorted(
        df["자치구"].dropna().unique()
    )


    selected_gu = st.sidebar.selectbox(
        "자치구 선택",
        gu_list
    )


    # 주차장 종류
    type_list = [
        "전체"
    ] + sorted(
        df["주차장 종류명"].dropna().unique()
    )


    selected_type = st.sidebar.selectbox(
        "주차장 종류",
        type_list
    )


    # 무료/유료
    pay_list = [
        "전체"
    ] + sorted(
        df["유무료구분명"].dropna().unique()
    )


    selected_pay = st.sidebar.selectbox(
        "무료/유료",
        pay_list
    )


    # 예상 주차시간
    parking_time = st.sidebar.number_input(
        "예상 주차시간(분)",
        min_value=10,
        value=60,
        step=10
    )


    # -------------------------
    # 필터링
    # -------------------------

    result = df.copy()


    if selected_gu != "전체":
        result = result[
            result["자치구"] == selected_gu
        ]


    if selected_type != "전체":
        result = result[
            result["주차장 종류명"] == selected_type
        ]


    if selected_pay != "전체":
        result = result[
            result["유무료구분명"] == selected_pay
        ]



    # -------------------------
    # 예상 요금 계산 함수
    # -------------------------

    def calculate_price(row, minutes):

        base_price = row["기본 주차 요금"]
        base_time = row["기본 주차 시간(분 단위)"]

        add_price = row["추가 단위 요금"]
        add_time = row["추가 단위 시간(분 단위)"]


        if minutes <= base_time:
            return base_price

        else:

            extra = minutes - base_time

            if add_time > 0:
                count = extra // add_time + 1
            else:
                count = 0

            return int(
                base_price +
                count * add_price
            )



    result["예상요금"] = result.apply(
        lambda x:
        calculate_price(
            x,
            parking_time
        ),
        axis=1
    )


    # -------------------------
    # 가장 저렴한 주차장
    # -------------------------

    st.subheader("💰 가장 저렴한 주차장")


    if len(result) > 0:

        cheap = result.sort_values(
            "예상요금"
        ).iloc[0]


        col1, col2, col3 = st.columns(3)


        with col1:
            st.metric(
                "주차장",
                cheap["주차장명"]
            )

        with col2:
            st.metric(
                "예상 요금",
                f"{int(cheap['예상요금'])}원"
            )

        with col3:
            st.metric(
                "위치",
                cheap["주소"]
            )


    else:
        st.warning(
            "조건에 맞는 주차장이 없습니다."
        )



    # -------------------------
    # 지도 표시
    # -------------------------

    st.subheader("🗺 주차장 위치")


    map_data = result.dropna(
        subset=["위도","경도"]
    )


    if len(map_data)>0:

        center = [
            map_data["위도"].mean(),
            map_data["경도"].mean()
        ]


        m = folium.Map(
            location=center,
            zoom_start=12
        )


        for _, row in map_data.iterrows():

            popup = f"""
            <b>{row['주차장명']}</b><br>
            주소 : {row['주소']}<br>
            종류 : {row['주차장 종류명']}<br>
            구분 : {row['유무료구분명']}<br>
            예상요금 : {int(row['예상요금'])}원
            """

            folium.Marker(
                [
                    row["위도"],
                    row["경도"]
                ],
                popup=popup
            ).add_to(m)


        st_folium(
            m,
            width=1000,
            height=600
        )

    else:
        st.warning(
            "지도 표시 가능한 좌표 데이터가 없습니다."
        )



    # -------------------------
    # 결과 테이블
    # -------------------------

    st.subheader("📋 검색 결과")


    show_cols = [
        "주차장명",
        "주소",
        "주차장 종류명",
        "유무료구분명",
        "기본 주차 요금",
        "예상요금"
    ]


    st.dataframe(
        result[show_cols]
        .sort_values("예상요금"),
        use_container_width=True
    )


else:

    st.info(
        "CSV 파일을 업로드해주세요."
    )
