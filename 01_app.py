import streamlit as st
import requests
import random

st.set_page_config(
    page_title="오늘의 날씨 음식 추천",
    page_icon="🍽️",
    layout="wide"
)

st.title("🌤️ 오늘의 날씨 음식 추천")
st.write("현재 날씨에 어울리는 음식을 추천해드립니다.")

# OpenWeather API Key
API_KEY = st.secrets["OPENWEATHER_API_KEY"]

city = st.text_input("도시 입력", "Seoul")


foods = {

    "Clear":[
        {
            "name":"비빔밥",
            "image":"https://images.unsplash.com/photo-1553163147-622ab57be1c7",
            "calories":"560 kcal",
            "nutrition":{
                "탄수화물":"70g",
                "단백질":"22g",
                "지방":"18g"
            }
        },
        {
            "name":"샐러드",
            "image":"https://images.unsplash.com/photo-1546069901-ba9599a7e63c",
            "calories":"320 kcal",
            "nutrition":{
                "탄수화물":"18g",
                "단백질":"15g",
                "지방":"14g"
            }
        }
    ],

    "Rain":[
        {
            "name":"김치전",
            "image":"https://images.unsplash.com/photo-1604908176997-125f25cc6f3d",
            "calories":"430 kcal",
            "nutrition":{
                "탄수화물":"45g",
                "단백질":"10g",
                "지방":"22g"
            }
        },
        {
            "name":"칼국수",
            "image":"https://images.unsplash.com/photo-1617093727343-374698b1b08d",
            "calories":"520 kcal",
            "nutrition":{
                "탄수화물":"68g",
                "단백질":"20g",
                "지방":"14g"
            }
        }
    ],

    "Snow":[
        {
            "name":"떡국",
            "image":"https://images.unsplash.com/photo-1606787366850-de6330128bfc",
            "calories":"480 kcal",
            "nutrition":{
                "탄수화물":"58g",
                "단백질":"19g",
                "지방":"12g"
            }
        }
    ],

    "Clouds":[
        {
            "name":"돈까스",
            "image":"https://images.unsplash.com/photo-1544025162-d76694265947",
            "calories":"780 kcal",
            "nutrition":{
                "탄수화물":"65g",
                "단백질":"34g",
                "지방":"42g"
            }
        }
    ]
}


def get_weather(city):

    url=f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"

    response=requests.get(url)

    if response.status_code!=200:
        return None

    data=response.json()

    return {
        "temp":data["main"]["temp"],
        "weather":data["weather"][0]["main"],
        "description":data["weather"][0]["description"]
    }


if st.button("추천받기 🍴"):

    weather=get_weather(city)

    if weather is None:
        st.error("날씨 정보를 가져올 수 없습니다.")
        st.stop()

    st.subheader("🌍 현재 날씨")

    c1,c2,c3=st.columns(3)

    c1.metric("도시",city)
    c2.metric("기온",f'{weather["temp"]:.1f}℃')
    c3.metric("날씨",weather["description"])

    condition=weather["weather"]

    if condition not in foods:
        condition="Clear"

    food=random.choice(foods[condition])

    st.divider()

    st.header("🍽️ 오늘의 추천 음식")

    col1,col2=st.columns([2,1])

    with col1:

        st.image(food["image"],use_container_width=True)

    with col2:

        st.subheader(food["name"])

        st.success(f'칼로리 : {food["calories"]}')

        st.write("### 영양성분")

        for k,v in food["nutrition"].items():
            st.write(f"**{k}** : {v}")

        st.info("맛있게 드세요 😄")
