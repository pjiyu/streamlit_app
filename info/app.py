import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
from collections import Counter
import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from urllib.parse import urlparse

# -----------------------------
# 기본 설정
# -----------------------------
st.set_page_config(
    page_title="웹사이트 정보 분석기",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 웹사이트 정보 분석기")
st.write("웹페이지 링크를 입력하면 사이트의 텍스트 정보를 분석하고 시각화합니다.")

# -----------------------------
# API 키 불러오기
# -----------------------------
try:
    API_KEY = st.secrets["API_KEY"]
except:
    API_KEY = None

# -----------------------------
# URL 입력
# -----------------------------
url = st.text_input(
    "분석할 웹사이트 링크를 입력하세요.",
    placeholder="https://example.com"
)

analyze_button = st.button("🔍 분석 시작", use_container_width=True)


# -----------------------------
# 웹페이지 정보 가져오기
# -----------------------------
def get_webpage_text(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "Chrome/120.0 Safari/537.36"
        )
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=15
    )

    response.raise_for_status()

    # 한글 웹사이트 인코딩 문제 해결
    response.encoding = response.apparent_encoding

    soup = BeautifulSoup(response.text, "html.parser")

    # 필요 없는 태그 제거
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

    # 제목
    title = soup.title.string.strip() if soup.title else "제목 없음"

    # 설명
    description = ""

    meta_description = soup.find(
        "meta",
        attrs={"name": "description"}
    )

    if meta_description:
        description = meta_description.get("content", "")

    # 본문 텍스트
    text = soup.get_text(separator=" ", strip=True)

    # 여러 공백 정리
    text = re.sub(r"\s+", " ", text)

    return title, description, text


# -----------------------------
# 한글 단어 추출
# -----------------------------
def extract_korean_words(text):

    # 한글 2글자 이상 단어 추출
    words = re.findall(r"[가-힣]{2,}", text)

    # 분석에 필요 없는 단어
    stopwords = {
        "그리고",
        "하지만",
        "때문에",
        "있습니다",
        "합니다",
        "대한",
        "통해",
        "위해",
        "에서",
        "으로",
        "하는",
        "것으로",
        "있는",
        "이번",
        "관련",
        "이후",
        "대해",
        "또한",
        "따라서",
        "사이트",
        "페이지"
    }

    filtered_words = [
        word for word in words
        if word not in stopwords
    ]

    return filtered_words


# -----------------------------
# 간단한 감정 분석
# -----------------------------
def sentiment_analysis(text):

    positive_words = [
        "좋다", "좋은", "성공", "발전",
        "성장", "효과", "긍정", "기대",
        "개선", "만족", "추천", "편리",
        "안전", "유익"
    ]

    negative_words = [
        "문제", "위험", "실패", "감소",
        "부정", "피해", "논란", "우려",
        "비판", "어려움", "오류", "갈등",
        "불편", "위기"
    ]

    positive_count = sum(
        text.count(word)
        for word in positive_words
    )

    negative_count = sum(
        text.count(word)
        for word in negative_words
    )

    if positive_count > negative_count:
        result = "긍정적"
    elif negative_count > positive_count:
        result = "부정적"
    else:
        result = "중립적"

    return result, positive_count, negative_count


# -----------------------------
# 분석 실행
# -----------------------------
if analyze_button:

    if not url:
        st.warning("분석할 웹사이트 링크를 입력하세요.")

    else:

        try:

            # URL 형식 확인
            parsed_url = urlparse(url)

            if not parsed_url.scheme:
                st.error(
                    "URL 앞에 https:// 또는 http://를 입력하세요."
                )
                st.stop()

            with st.spinner("웹페이지 정보를 분석하는 중입니다..."):

                title, description, text = get_webpage_text(url)

                words = extract_korean_words(text)

                word_counts = Counter(words)

                sentiment, positive, negative = sentiment_analysis(text)

                # 통계 계산
                character_count = len(text)
                word_count = len(text.split())
                sentence_count = len(
                    re.findall(
                        r"[.!?。！？]",
                        text
                    )
                )

            st.success("분석이 완료되었습니다.")

            # -----------------------------
            # 기본 정보
            # -----------------------------
            st.subheader("📄 웹페이지 기본 정보")

            st.write(f"**제목:** {title}")

            if description:
                st.write(f"**설명:** {description}")

            st.write(f"**주소:** {url}")

            # -----------------------------
            # 핵심 통계
            # -----------------------------
            st.subheader("📊 텍스트 분석 결과")

            col1, col2, col3, col4 = st.columns(4)

            col1.metric(
                "글자 수",
                f"{character_count:,}"
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
                "감정 분석",
                sentiment
            )

            # -----------------------------
            # 감정 분석
            # -----------------------------
            st.subheader("😊 감정 분석")

            sentiment_df = pd.DataFrame({
                "감정": ["긍정 단어", "부정 단어"],
                "등장 횟수": [positive, negative]
            })

            st.bar_chart(
                sentiment_df.set_index("감정")
            )

            # -----------------------------
            # 자주 등장하는 단어
            # -----------------------------
            st.subheader("🔠 자주 등장하는 단어 TOP 20")

            top_words = word_counts.most_common(20)

            word_df = pd.DataFrame(
                top_words,
                columns=["단어", "등장 횟수"]
            )

            st.dataframe(
                word_df,
                use_container_width=True,
                hide_index=True
            )

            # -----------------------------
            # 단어 빈도 그래프
            # -----------------------------
            st.subheader("📈 단어 빈도 시각화")

            fig, ax = plt.subplots(
                figsize=(10, 6)
            )

            graph_df = word_df.sort_values(
                "등장 횟수"
            )

            ax.barh(
                graph_df["단어"],
                graph_df["등장 횟수"]
            )

            ax.set_title(
                "웹페이지 주요 단어 빈도"
            )

            ax.set_xlabel(
                "등장 횟수"
            )

            ax.set_ylabel(
                "단어"
            )

            plt.tight_layout()

            st.pyplot(fig)

            # -----------------------------
            # 한글 워드클라우드
            # -----------------------------
            st.subheader("☁️ 한글 워드클라우드")

            # Streamlit Cloud에 업로드한 폰트
            font_path = "fonts/NotoSansKR-Regular.ttf"

            try:

                wordcloud = WordCloud(
                    font_path=font_path,
                    width=1000,
                    height=600,
                    background_color="white",
                    max_words=100,
                    collocations=False
                ).generate_from_frequencies(
                    word_counts
                )

                fig_wc, ax_wc = plt.subplots(
                    figsize=(14, 8)
                )

                ax_wc.imshow(
                    wordcloud,
                    interpolation="bilinear"
                )

                ax_wc.axis("off")

                st.pyplot(fig_wc)

            except Exception as e:

                st.error(
                    "한글 폰트를 찾을 수 없습니다."
                )

                st.info(
                    "fonts/NotoSansKR-Regular.ttf "
                    "파일을 업로드하세요."
                )

            # -----------------------------
            # 원문 일부 표시
            # -----------------------------
            st.subheader("📝 추출된 웹페이지 텍스트")

            with st.expander("본문 내용 확인"):

                st.write(
                    text[:5000]
                )

            # -----------------------------
            # CSV 다운로드
            # -----------------------------
            csv_data = word_df.to_csv(
                index=False,
                encoding="utf-8-sig"
            )

            st.download_button(
                label="📥 단어 빈도 데이터 다운로드",
                data=csv_data,
                file_name="website_word_frequency.csv",
                mime="text/csv"
            )

        except requests.exceptions.RequestException:

            st.error(
                "웹페이지에 접속할 수 없습니다. "
                "주소를 확인하세요."
            )

        except Exception as e:

            st.error(
                f"분석 중 오류가 발생했습니다: {e}"
            )
