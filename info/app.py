import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from collections import Counter
from kiwipiepy import Kiwi
import re
import os


# =========================
# 기본 설정
# =========================

st.set_page_config(
    page_title="웹페이지 정보 분석기",
    page_icon="📊",
    layout="wide"
)


st.title("📊 웹페이지 정보 분석기")

st.write(
    "웹페이지 링크를 입력하면 페이지의 내용을 분석하고 "
    "요약, 키워드, 통계, 시각화, 한글 워드클라우드를 제공합니다."
)


# =========================
# API 키 가져오기
# =========================

try:

    API_KEY = st.secrets["OPENAI_API_KEY"]

except:

    API_KEY = None


# =========================
# 웹페이지 내용 가져오기
# =========================

def get_webpage_text(url):

    headers = {

        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        )

    }

    response = requests.get(
        url,
        headers=headers,
        timeout=20
    )

    response.raise_for_status()


    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )


    # 분석에 필요하지 않은 태그 제거

    for tag in soup([
        "script",
        "style",
        "noscript",
        "header",
        "footer",
        "nav",
        "aside"
    ]):

        tag.decompose()


    text = soup.get_text(
        separator=" ",
        strip=True
    )


    # 여러 개의 공백을 하나로 정리

    text = re.sub(
        r"\s+",
        " ",
        text
    )


    return text


# =========================
# 텍스트 정제
# =========================

def clean_text(text):

    # URL 제거

    text = re.sub(
        r"http\S+",
        "",
        text
    )


    # 한글, 영어, 숫자, 공백만 남김

    text = re.sub(
        r"[^가-힣a-zA-Z0-9\s]",
        " ",
        text
    )


    # 여러 공백을 하나로 정리

    text = re.sub(
        r"\s+",
        " ",
        text
    )


    return text.strip()


# =========================
# 한글 키워드 추출
# =========================

def extract_korean_keywords(text):

    kiwi = Kiwi()


    tokens = kiwi.tokenize(
        text
    )


    nouns = []


    for token in tokens:

        # 일반명사(NNG), 고유명사(NNP) 추출

        if token.tag in [
            "NNG",
            "NNP"
        ]:

            word = token.form


            # 한 글자 단어는 제외

            if len(word) >= 2:

                nouns.append(
                    word
                )


    return nouns


# =========================
# 한글 워드클라우드 생성
# =========================

def create_wordcloud(words):

    word_counts = Counter(
        words
    )


    # app.py가 있는 폴더를 기준으로
    # fonts 폴더 안의 폰트 파일을 찾음

    font_path = os.path.join(
        os.path.dirname(__file__),
        "fonts",
        "NotoSansKR-ExtraBold.ttf"
    )


    wc = WordCloud(

        font_path=font_path,

        width=1000,

        height=600,

        background_color="white",

        max_words=100,

        collocations=False

    )


    wc.generate_from_frequencies(
        word_counts
    )


    return wc


# =========================
# OpenAI API를 이용한 요약
# =========================

def summarize_with_openai(text):

    if API_KEY is None:

        return (
            "API 키가 설정되지 않았습니다.\n\n"
            "Streamlit Cloud의 Secrets에 "
            "OPENAI_API_KEY를 등록해주세요."
        )


    api_url = (
        "https://api.openai.com/v1/chat/completions"
    )


    headers = {

        "Content-Type":
        "application/json",

        "Authorization":
        f"Bearer {API_KEY}"

    }


    # 너무 긴 텍스트는 일부만 사용

    text = text[:30000]


    data = {

        "model":
        "gpt-4o-mini",


        "messages": [

            {

                "role":
                "system",

                "content":
                (
                    "너는 웹페이지 분석 전문가다. "
                    "사용자가 제공한 웹페이지 내용을 "
                    "한국어로 분석하라."
                )

            },


            {

                "role":
                "user",

                "content":
                f"""
다음 웹페이지 내용을 분석해줘.

다음 항목을 포함해줘.

1. 핵심 내용 요약
2. 주요 주장
3. 핵심 키워드
4. 긍정적인 내용
5. 주의해서 볼 내용
6. 전체적인 결론

웹페이지 내용:

{text}
"""

            }

        ],


        "temperature":
        0.3

    }


    response = requests.post(

        api_url,

        headers=headers,

        json=data,

        timeout=60

    )


    result = response.json()


    if "choices" not in result:

        return (
            "API 응답 오류가 발생했습니다.\n\n"
            + str(result)
        )


    return (
        result["choices"][0]
        ["message"]
        ["content"]
    )


# =========================
# URL 입력
# =========================

url = st.text_input(

    "🔗 분석할 웹페이지 링크를 입력하세요",

    placeholder=
    "https://example.com"

)


analyze_button = st.button(

    "🔍 웹페이지 분석하기",

    use_container_width=True

)


# =========================
# 분석 실행
# =========================

if analyze_button:


    if not url:

        st.warning(
            "웹페이지 링크를 입력해주세요."
        )

        st.stop()


    try:


        # -------------------------
        # 웹페이지 내용 가져오기
        # -------------------------

        with st.spinner(
            "웹페이지 내용을 가져오는 중..."
        ):


            raw_text = get_webpage_text(
                url
            )


        if len(raw_text) < 100:

            st.error(
                "분석할 수 있는 텍스트가 "
                "충분하지 않습니다."
            )

            st.stop()


        cleaned_text = clean_text(
            raw_text
        )


        # -------------------------
        # 기본 통계
        # -------------------------

        st.subheader(
            "📌 웹페이지 기본 정보"
        )


        col1, col2, col3, col4 = st.columns(
            4
        )


        char_count = len(
            cleaned_text
        )


        word_count = len(
            cleaned_text.split()
        )


        sentence_count = len(
            re.findall(
                r"[.!?。！？]",
                raw_text
            )
        )


        unique_word_count = len(
            set(
                cleaned_text.split()
            )
        )


        col1.metric(
            "글자 수",
            f"{char_count:,}"
        )


        col2.metric(
            "단어 수",
            f"{word_count:,}"
        )


        col3.metric(
            "문장 수",
            f"{sentence_count:,}"
        )


        col4.metric(
            "고유 단어 수",
            f"{unique_word_count:,}"
        )


        # -------------------------
        # AI 요약
        # -------------------------

        st.subheader(
            "🤖 AI 내용 분석"
        )


        with st.spinner(
            "AI가 웹페이지를 분석하는 중..."
        ):


            summary = summarize_with_openai(
                cleaned_text
            )


        st.markdown(
            summary
        )


        # -------------------------
        # 키워드 추출
        # -------------------------

        st.subheader(
            "🔑 핵심 키워드 분석"
        )


        with st.spinner(
            "주요 키워드를 추출하는 중..."
        ):


            nouns = extract_korean_keywords(
                cleaned_text
            )


        if len(nouns) == 0:

            st.warning(
                "추출된 키워드가 없습니다."
            )

            st.stop()


        word_counts = Counter(
            nouns
        )


        top_words = word_counts.most_common(
            20
        )


        keyword_df = pd.DataFrame(

            top_words,

            columns=[
                "키워드",
                "빈도"
            ]

        )


        st.dataframe(

            keyword_df,

            use_container_width=True,

            hide_index=True

        )


        # -------------------------
        # 키워드 막대그래프
        # -------------------------

        st.subheader(
            "📊 주요 키워드 빈도"
        )


        chart_df = (

            keyword_df
            .head(10)
            .sort_values("빈도")

        )


        fig, ax = plt.subplots(

            figsize=(10, 5)

        )


        ax.barh(

            chart_df["키워드"],

            chart_df["빈도"]

        )


        ax.set_xlabel(
            "등장 횟수"
        )


        ax.set_ylabel(
            "키워드"
        )


        ax.set_title(
            "웹페이지 주요 키워드"
        )


        st.pyplot(
            fig
        )


        plt.close(
            fig
        )


        # -------------------------
        # 한글 워드클라우드
        # -------------------------

        st.subheader(
            "☁️ 한글 워드클라우드"
        )


        wc = create_wordcloud(
            nouns
        )


        fig_wc, ax_wc = plt.subplots(

            figsize=(12, 7)

        )


        ax_wc.imshow(

            wc,

            interpolation=
            "bilinear"

        )


        ax_wc.axis(
            "off"
        )


        st.pyplot(
            fig_wc
        )


        plt.close(
            fig_wc
        )


        # -------------------------
        # 단어 빈도 분포
        # -------------------------

        st.subheader(
            "📈 단어 빈도 분포"
        )


        frequency_values = list(

            word_counts.values()

        )


        frequency_df = pd.DataFrame(

            frequency_values,

            columns=[
                "빈도"
            ]

        )


        st.bar_chart(

            frequency_df[
                "빈도"
            ].value_counts()

        )


        # -------------------------
        # 원문 보기
        # -------------------------

        with st.expander(

            "📄 추출된 웹페이지 원문 보기"

        ):


            st.write(

                cleaned_text

            )


        # -------------------------
        # 분석 결과 다운로드
        # -------------------------

        result_text = f"""

웹페이지 분석 결과


URL:

{url}


기본 정보

- 글자 수: {char_count}

- 단어 수: {word_count}

- 문장 수: {sentence_count}

- 고유 단어 수: {unique_word_count}


AI 분석 결과

{summary}


주요 키워드

{keyword_df.to_string(index=False)}

"""


        st.download_button(

            label=
            "📥 분석 결과 다운로드",

            data=
            result_text,

            file_name=
            "웹페이지_분석결과.txt",

            mime=
            "text/plain"

        )


    except Exception as e:


        st.error(

            "웹페이지를 분석하는 중 "
            "오류가 발생했습니다."

        )


        st.exception(
            e
        )
