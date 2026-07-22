import streamlit as st
import pandas as pd
import requests
import re
from collections import Counter
from datetime import datetime

import matplotlib.pyplot as plt
import seaborn as sns

from wordcloud import WordCloud
from konlpy.tag import Okt
from transformers import pipeline


# =========================================================
# 기본 설정
# =========================================================

st.set_page_config(
    page_title="YouTube 댓글 분석기",
    page_icon="💬",
    layout="wide"
)

st.title("💬 YouTube 댓글 분석기")
st.write("유튜브 영상의 댓글을 수집하고 감정과 주요 키워드를 분석합니다.")


# =========================================================
# API 키 설정
# =========================================================

try:
    API_KEY = st.secrets["YOUTUBE_API_KEY"]
except Exception:
    st.error(
        "YouTube API 키를 찾을 수 없습니다. "
        "Streamlit Cloud의 Secrets에 YOUTUBE_API_KEY를 등록하세요."
    )
    st.stop()


# =========================================================
# 모델 불러오기
# =========================================================

@st.cache_resource
def load_sentiment_model():

    model = pipeline(
        "sentiment-analysis",
        model="cardiffnlp/twitter-xlm-roberta-base-sentiment"
    )

    return model


@st.cache_resource
def load_okt():

    return Okt()


# =========================================================
# 유튜브 영상 ID 추출
# =========================================================

def extract_video_id(url):

    patterns = [

        r"(?:v=)([A-Za-z0-9_-]{11})",

        r"(?:youtu\.be/)([A-Za-z0-9_-]{11})",

        r"(?:youtube\.com/shorts/)([A-Za-z0-9_-]{11})",

        r"(?:youtube\.com/embed/)([A-Za-z0-9_-]{11})"

    ]

    for pattern in patterns:

        match = re.search(pattern, url)

        if match:

            return match.group(1)

    return None


# =========================================================
# 영상 정보 가져오기
# =========================================================

def get_video_info(video_id):

    url = "https://www.googleapis.com/youtube/v3/videos"

    params = {

        "part": "snippet,statistics",

        "id": video_id,

        "key": API_KEY

    }

    response = requests.get(url, params=params)

    data = response.json()

    if "items" not in data or len(data["items"]) == 0:

        return None

    item = data["items"][0]

    snippet = item["snippet"]

    statistics = item.get("statistics", {})

    return {

        "title": snippet["title"],

        "channel": snippet["channelTitle"],

        "published_at": snippet["publishedAt"],

        "view_count": int(statistics.get("viewCount", 0)),

        "like_count": int(statistics.get("likeCount", 0)),

        "comment_count": int(statistics.get("commentCount", 0))

    }


# =========================================================
# 댓글 가져오기
# =========================================================

def get_comments(video_id, max_comments=500):

    comments = []

    url = "https://www.googleapis.com/youtube/v3/commentThreads"

    next_page_token = None

    while len(comments) < max_comments:

        params = {

            "part": "snippet",

            "videoId": video_id,

            "maxResults": 100,

            "pageToken": next_page_token,

            "textFormat": "plainText",

            "key": API_KEY

        }

        response = requests.get(url, params=params)

        data = response.json()

        if "error" in data:

            st.error(data["error"]["message"])

            break

        for item in data.get("items", []):

            comment = item["snippet"]["topLevelComment"]["snippet"]

            comments.append({

                "author": comment["authorDisplayName"],

                "text": comment["textDisplay"],

                "like_count": comment.get("likeCount", 0),

                "published_at": comment["publishedAt"],

                "updated_at": comment["updatedAt"]

            })

            if len(comments) >= max_comments:

                break

        next_page_token = data.get("nextPageToken")

        if not next_page_token:

            break

    return pd.DataFrame(comments)


# =========================================================
# 댓글 전처리
# =========================================================

def clean_text(text):

    text = str(text)

    # URL 제거
    text = re.sub(r"http\S+|www\S+", "", text)

    # 이모지와 특수문자 일부 제거
    text = re.sub(r"[^\w\s가-힣]", " ", text)

    # 여러 공백 제거
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# =========================================================
# 감정 분석
# =========================================================

def analyze_sentiment(df):

    model = load_sentiment_model()

    results = []

    for text in df["text"]:

        clean = clean_text(text)

        if len(clean) < 3:

            results.append({

                "sentiment": "중립",

                "score": 0.5

            })

            continue

        result = model(clean[:512])[0]

        label = result["label"]

        score = result["score"]

        # XLM-R 모델 라벨
        if label == "LABEL_2":

            sentiment = "긍정"

        elif label == "LABEL_0":

            sentiment = "부정"

        else:

            sentiment = "중립"

        results.append({

            "sentiment": sentiment,

            "score": score

        })

    df["sentiment"] = [r["sentiment"] for r in results]

    df["sentiment_score"] = [r["score"] for r in results]

    return df


# =========================================================
# 한글 명사 추출
# =========================================================

def extract_korean_nouns(texts):

    okt = load_okt()

    nouns = []

    for text in texts:

        text = clean_text(text)

        words = okt.nouns(text)

        for word in words:

            if len(word) >= 2:

                nouns.append(word)

    return nouns


# =========================================================
# 워드클라우드 생성
# =========================================================

def create_wordcloud(words):

    font_path = "fonts/NotoSansKR-Regular.ttf"

    word_count = Counter(words)

    wordcloud = WordCloud(

        font_path=font_path,

        width=1200,

        height=700,

        background_color="white",

        max_words=100,

        collocations=False

    ).generate_from_frequencies(word_count)

    return wordcloud


# =========================================================
# 사이드바
# =========================================================

st.sidebar.header("분석 설정")

max_comments = st.sidebar.slider(

    "수집할 댓글 수",

    min_value=100,

    max_value=2000,

    value=500,

    step=100

)


# =========================================================
# URL 입력
# =========================================================

youtube_url = st.text_input(

    "유튜브 영상 링크를 입력하세요",

    placeholder="https://www.youtube.com/watch?v=..."

)


analyze_button = st.button(

    "댓글 분석 시작",

    type="primary"

)


# =========================================================
# 분석 시작
# =========================================================

if analyze_button:

    if not youtube_url:

        st.warning("유튜브 영상 링크를 입력하세요.")

        st.stop()


    video_id = extract_video_id(youtube_url)


    if not video_id:

        st.error("올바른 유튜브 영상 링크가 아닙니다.")

        st.stop()


    with st.spinner("영상 정보를 가져오는 중입니다..."):

        video_info = get_video_info(video_id)


    if video_info is None:

        st.error("영상 정보를 가져올 수 없습니다.")

        st.stop()


    with st.spinner("댓글을 수집하는 중입니다..."):

        df = get_comments(

            video_id,

            max_comments

        )


    if df.empty:

        st.warning(

            "댓글이 없거나 댓글을 가져올 수 없습니다."

        )

        st.stop()


    with st.spinner("댓글 감정을 분석하는 중입니다..."):

        df = analyze_sentiment(df)


    # =====================================================
    # 영상 정보
    # =====================================================

    st.header("📺 영상 정보")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(

        "조회수",

        f"{video_info['view_count']:,}"

    )

    col2.metric(

        "좋아요",

        f"{video_info['like_count']:,}"

    )

    col3.metric(

        "댓글 수",

        f"{video_info['comment_count']:,}"

    )

    col4.metric(

        "분석 댓글",

        f"{len(df):,}"

    )


    st.subheader(video_info["title"])

    st.write(

        f"채널: {video_info['channel']}"

    )


    # =====================================================
    # 감정 분석
    # =====================================================

    st.header("😊 댓글 감정 분석")


    sentiment_counts = (

        df["sentiment"]

        .value_counts()

        .reindex(

            ["긍정", "중립", "부정"],

            fill_value=0

        )

    )


    col1, col2 = st.columns(2)


    with col1:

        st.subheader("감정별 댓글 비율")

        st.bar_chart(sentiment_counts)


    with col2:

        st.subheader("감정 분포")

        fig, ax = plt.subplots()

        ax.pie(

            sentiment_counts.values,

            labels=sentiment_counts.index,

            autopct="%1.1f%%"

        )

        ax.set_title("댓글 감정 분포")

        st.pyplot(fig)


    # =====================================================
    # 감정 점수 분포
    # =====================================================

    st.header("📊 감정 점수 분포")


    fig, ax = plt.subplots()

    sns.histplot(

        data=df,

        x="sentiment_score",

        hue="sentiment",

        bins=20,

        kde=True,

        ax=ax

    )

    ax.set_title("댓글 감정 분석 점수 분포")

    ax.set_xlabel("감정 분석 신뢰도")

    ax.set_ylabel("댓글 수")


    st.pyplot(fig)


    # =====================================================
    # 댓글 길이 분석
    # =====================================================

    df["comment_length"] = df["text"].str.len()


    st.header("📝 댓글 길이 분석")


    col1, col2, col3 = st.columns(3)


    col1.metric(

        "평균 댓글 길이",

        f"{df['comment_length'].mean():.1f}자"

    )


    col2.metric(

        "가장 긴 댓글",

        f"{df['comment_length'].max():,}자"

    )


    col3.metric(

        "가장 짧은 댓글",

        f"{df['comment_length'].min():,}자"

    )


    fig, ax = plt.subplots()

    sns.histplot(

        df["comment_length"],

        bins=30,

        ax=ax

    )

    ax.set_title("댓글 길이 분포")

    ax.set_xlabel("댓글 길이")

    ax.set_ylabel("댓글 수")


    st.pyplot(fig)


    # =====================================================
    # 댓글 좋아요 분석
    # =====================================================

    st.header("👍 좋아요를 많이 받은 댓글")


    top_comments = (

        df

        .sort_values(

            "like_count",

            ascending=False

        )

        .head(10)

    )


    st.dataframe(

        top_comments[

            [

                "author",

                "text",

                "like_count",

                "sentiment"

            ]

        ],

        use_container_width=True

    )


    # =====================================================
    # 핵심 키워드
    # =====================================================

    st.header("🔑 자주 등장하는 핵심 키워드")


    with st.spinner("한글 명사를 추출하는 중입니다..."):

        nouns = extract_korean_nouns(df["text"])


    word_counts = Counter(nouns)


    top_words = (

        pd.DataFrame(

            word_counts.most_common(20),

            columns=["단어", "빈도"]

        )

    )


    col1, col2 = st.columns(2)


    with col1:

        st.dataframe(

            top_words,

            use_container_width=True

        )


    with col2:

        st.bar_chart(

            top_words.set_index("단어")

        )


    # =====================================================
    # 워드클라우드
    # =====================================================

    st.header("☁️ 한글 워드클라우드")


    wordcloud = create_wordcloud(nouns)


    fig, ax = plt.subplots(

        figsize=(15, 8)

    )


    ax.imshow(

        wordcloud,

        interpolation="bilinear"

    )


    ax.axis("off")


    st.pyplot(fig)


    # =====================================================
    # 날짜별 댓글 수
    # =====================================================

    st.header("📅 시간에 따른 댓글 작성 추이")


    df["published_at"] = pd.to_datetime(

        df["published_at"]

    )


    daily_comments = (

        df

        .set_index("published_at")

        .resample("D")

        .size()

    )


    st.line_chart(

        daily_comments

    )


    # =====================================================
    # 감정별 댓글 확인
    # =====================================================

    st.header("💬 댓글 원문 분석")


    selected_sentiment = st.selectbox(

        "확인할 감정",

        ["전체", "긍정", "중립", "부정"]

    )


    if selected_sentiment == "전체":

        filtered_df = df

    else:

        filtered_df = df[

            df["sentiment"]

            == selected_sentiment

        ]


    st.dataframe(

        filtered_df[

            [

                "author",

                "text",

                "like_count",

                "sentiment",

                "sentiment_score",

                "published_at"

            ]

        ],

        use_container_width=True

    )


    # =====================================================
    # CSV 다운로드
    # =====================================================

    csv = df.to_csv(

        index=False,

        encoding="utf-8-sig"

    )


    st.download_button(

        label="📥 분석 결과 CSV 다운로드",

        data=csv,

        file_name="youtube_comment_analysis.csv",

        mime="text/csv"

    )
