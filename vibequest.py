import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import pandas as pd
import io
import requests
import json
from prophet import Prophet
import uuid
import arabic_reshaper
from bidi.algorithm import get_display
import base64

# إعداد الصفحة
st.set_page_config(
    page_title="VibeQuest™ - Feel the Buzz",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS مبهر (كما في الكود السابق)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap');
    * {font-family: 'Orbitron', sans-serif;}
    .main {background: linear-gradient(135deg, #1F0F3D, #4A2A7A); color: #E0E7FF; padding: 40px; border-radius: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.8);}
    h1, h2, h3 {background: linear-gradient(90deg, #FF00CC, #00FFFF); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900; letter-spacing: -1px; text-shadow: 0 2px 15px rgba(255,0,204,0.6);}
    .stButton>button {background: linear-gradient(90deg, #FF00CC, #00FFFF); color: #FFFFFF; border-radius: 50px; font-weight: 700; padding: 15px 35px; font-size: 18px; transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275); border: none; box-shadow: 0 8px 20px rgba(255,0,204,0.5); text-transform: uppercase;}
    .stButton>button:hover {transform: translateY(-5px) scale(1.05); box-shadow: 0 12px 30px rgba(0,255,255,0.7);}
    .stTextInput>div>div>input {background: rgba(255,255,255,0.1); border: 2px solid #FF00CC; border-radius: 15px; color: #00FFFF; font-weight: bold; padding: 15px; font-size: 18px; box-shadow: 0 5px 15px rgba(255,0,204,0.3); transition: all 0.3s ease;}
    .stTextInput>div>div>input:focus {border-color: #00FFFF; box-shadow: 0 5px 20px rgba(0,255,255,0.5);}
    .stSelectbox>label, .stRadio>label {color: #00FFFF; font-size: 22px; font-weight: 700; text-shadow: 1px 1px 5px rgba(0,0,0,0.5);}
    .stSelectbox>div>div>button {background: rgba(255,255,255,0.1); border: 2px solid #FF00CC; border-radius: 15px; color: #E0E7FF; padding: 15px; font-size: 18px;}
    .stRadio>div {background: rgba(255,255,255,0.05); border-radius: 20px; padding: 20px; box-shadow: 0 5px 20px rgba(0,0,0,0.5);}
    .stMarkdown {color: #D1C4E9; font-size: 18px; line-height: 1.6;}
    .share-btn {background: linear-gradient(90deg, #FF6F61, #FFD700); color: #FFFFFF; border-radius: 50px; padding: 12px 25px; text-decoration: none; transition: all 0.3s ease; box-shadow: 0 5px 15px rgba(255,111,97,0.4); font-size: 16px;}
    .share-btn:hover {transform: translateY(-3px); box-shadow: 0 10px 25px rgba(255,215,0,0.6);}
    .animate-in {animation: fadeInUp 1s forwards; opacity: 0;}
    @keyframes fadeInUp {from {opacity: 0; transform: translateY(20px);} to {opacity: 1; transform: translateY(0);}}
    </style>
""", unsafe_allow_html=True)

# تعريف الحالة الافتراضية
if "language" not in st.session_state:
    st.session_state["language"] = "English"
if "payment_verified" not in st.session_state:
    st.session_state["payment_verified"] = False
if "payment_initiated" not in st.session_state:
    st.session_state["payment_initiated"] = False
if "vibe_data" not in st.session_state:
    st.session_state["vibe_data"] = None

# مفاتيح Twitter API v2 (تم إضافتها من طلبك)
TWITTER_API_KEY = "bYtN5UHusJ0T2MzRHPSrjxAZH"
TWITTER_API_SECRET = "YcFkKkwQOJvGsg9PSwpcvHDaFvRYJQC5FcNTtKfyd0H6shpPSG"

# بيانات PayPal Sandbox
PAYPAL_CLIENT_ID = "AQd5IZObL6YTejqYpN0LxADLMtqbeal1ahbgNNrDfFLcKzMl6goF9BihgMw2tYnb4suhUfprhI-Z8eoC"
PAYPAL_SECRET = "EPk46EBw3Xm2W-R0Uua8sLsoDLJytgSXqIzYLbbXCk_zSOkdzFx8jEbKbKxhjf07cnJId8gt6INzm6_V"
PAYPAL_API = "https://api-m.sandbox.paypal.com"

# دالة للحصول على Bearer Token باستخدام API Key و API Secret
def get_twitter_bearer_token():
    try:
        auth = base64.b64encode(f"{TWITTER_API_KEY}:{TWITTER_API_SECRET}".encode()).decode()
        url = "https://api.twitter.com/oauth2/token"
        headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"
        }
        data = {"grant_type": "client_credentials"}
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        return response.json()["access_token"]
    except Exception as e:
        st.error(f"Failed to get Twitter Bearer Token: {e}")
        return None

# دالة لجلب التغريدات من Twitter API v2
def fetch_twitter_vibes(vibe_topic, bearer_token):
    try:
        url = f"https://api.twitter.com/2/tweets/search/recent?query={vibe_topic}&max_results=50"
        headers = {"Authorization": f"Bearer {bearer_token}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        tweets = response.json().get("data", [])
        positive, negative, neutral = 0, 0, 0
        for tweet in tweets:
            text = tweet["text"].lower()
            if "great" in text or "love" in text or "awesome" in text:
                positive += 1
            elif "bad" in text or "hate" in text or "terrible" in text:
                negative += 1
            else:
                neutral += 1
        total = positive + negative + neutral
        if total == 0:
            return {"positive": {"strong": 60, "mild": 25}, "negative": {"strong": 8, "mild": 12}, "neutral": 15}
        return {
            "positive": {"strong": int(positive * 0.7), "mild": int(positive * 0.3)},
            "negative": {"strong": int(negative * 0.7), "mild": int(negative * 0.3)},
            "neutral": neutral
        }
    except Exception as e:
        st.error(f"Failed to fetch Twitter vibes: {e}")
        return {"positive": {"strong": 60, "mild": 25}, "negative": {"strong": 8, "mild": 12}, "neutral": 15}

# العنوان والترحيب
st.markdown("""
    <h1 style='font-size: 60px; text-align: center; animation: fadeInUp 1s forwards;'>VibeQuest™</h1>
    <p style='font-size: 24px; text-align: center; animation: fadeInUp 1s forwards; animation-delay: 0.2s;'>
        Feel the World’s Social Energy!<br>
        <em>By Anas Hani Zewail • Contact: +201024743503</em>
    </p>
""", unsafe_allow_html=True)

# واجهة المستخدم
st.markdown("<h2 style='text-align: center;'>Quest Your Vibe</h2>", unsafe_allow_html=True)
vibe_topic = st.text_input("Enter Your Vibe (e.g., Oscars 2025):", "Oscars 2025", help="Feel the buzz of anything!")
language = st.selectbox("Select Language:", ["English", "Arabic"])
st.session_state["language"] = language
plan = st.radio("Choose Your Quest:", ["Vibe Peek (Free)", "Vibe Scout ($4)", "Vibe Hero ($9)", "Vibe Legend ($18)", "Vibe Elite ($30/month)"])
st.markdown("""
    <p style='text-align: center;'>
        <strong>Vibe Peek (Free):</strong> Quick Vibe Check<br>
        <strong>Vibe Scout ($4):</strong> Vibe Meter + Basic Report<br>
        <strong>Vibe Hero ($9):</strong> Full Report + 7-Day Forecast<br>
        <strong>Vibe Legend ($18):</strong> Advanced Insights + Tips<br>
        <strong>Vibe Elite ($30/month):</strong> Daily Vibes + Alerts
    </p>
""", unsafe_allow_html=True)

# دوال PayPal
def get_paypal_access_token():
    try:
        url = f"{PAYPAL_API}/v1/oauth2/token"
        headers = {"Accept": "application/json", "Accept-Language": "en_US"}
        data = {"grant_type": "client_credentials"}
        response = requests.post(url, headers=headers, auth=(PAYPAL_CLIENT_ID, PAYPAL_SECRET), data=data)
        response.raise_for_status()
        return response.json()["access_token"]
    except Exception as e:
        st.error(f"Failed to connect to PayPal: {e}")
        return None

def create_payment(access_token, amount, description):
    try:
        url = f"{PAYPAL_API}/v1/payments/payment"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"}
        payment_data = {
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "transactions": [{"amount": {"total": amount, "currency": "USD"}, "description": description}],
            "redirect_urls": {
                "return_url": "https://smartpulse-nwrkb9xdsnebmnhczyt76s.streamlit.app/?success=true",
                "cancel_url": "https://smartpulse-nwrkb9xdsnebmnhczyt76s.streamlit.app/?cancel=true"
            }
        }
        response = requests.post(url, headers=headers, json=payment_data)
        response.raise_for_status()
        for link in response.json()["links"]:
            if link["rel"] == "approval_url":
                return link["href"]
        st.error("Failed to extract payment URL.")
        return None
    except Exception as e:
        st.error(f"Failed to create payment request: {e}")
        return None

# بيانات وهمية احتياطية
vibe_sentiment_default = {"positive": {"strong": 60, "mild": 25}, "negative": {"strong": 8, "mild": 12}, "neutral": 15}
total_vibes = 300
vibe_by_day = {
    "2025-02-27_positive": 50, "2025-02-27_negative": 10,
    "2025-02-28_positive": 55, "2025-02-28_negative": 8,
    "2025-03-01_positive": 48, "2025-03-01_negative": 12
}
vibe_regions = {"Worldwide": {"positive": 80, "negative": 25, "neutral": 20}}
vibe_keywords = [("drama", 70), ("stars", 50)]

# دوال التحليل
def generate_vibe_meter(vibe_topic, language, vibe_sentiment):
    try:
        labels = ["Strong Positive", "Mild Positive", "Strong Negative", "Mild Negative", "Neutral"] if language == "English" else ["إيجابي قوي", "إيجابي خفيف", "سلبي قوي", "سلبي خفيف", "محايد"]
        sizes = [vibe_sentiment["positive"]["strong"], vibe_sentiment["positive"]["mild"], vibe_sentiment["negative"]["strong"], vibe_sentiment["negative"]["mild"], vibe_sentiment["neutral"]]
        colors = ["#00FFFF", "#66CCCC", "#FF00CC", "#CC0099", "#E0E7FF"]
        plt.figure(figsize=(8, 6))
        wedges, texts, autotexts = plt.pie(sizes, labels=labels, colors=colors, autopct="%1.1f%%", startangle=90, shadow=True, textprops={'fontsize': 14, 'color': 'white'})
        for w in wedges:
            w.set_edgecolor('#FFD700')
            w.set_linewidth(2)
        plt.title(f"{vibe_topic} Vibe Meter", fontsize=18, color="white", pad=20)
        plt.gca().set_facecolor('#1F0F3D')
        plt.gcf().set_facecolor('#1F0F3D')
        
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=300, bbox_inches="tight")
        img_buffer.seek(0)
        plt.close()
        return img_buffer
    except Exception as e:
        st.error(f"Failed to generate vibe meter: {e}")
        return None

def generate_forecast(vibe_topic, language, vibe_by_day):
    try:
        days = sorted(set(k.split('_')[0] for k in vibe_by_day.keys()))
        total_vibe = [vibe_by_day.get(f"{day}_positive", 0) - vibe_by_day.get(f"{day}_negative", 0) for day in days]
        df = pd.DataFrame({'ds': days, 'y': total_vibe})
        df['ds'] = pd.to_datetime(df['ds'])
        model = Prophet(daily_seasonality=True)
        model.fit(df)
        future = model.make_future_dataframe(periods=7)
        forecast = model.predict(future)
        plt.figure(figsize=(10, 6))
        plt.plot(df['ds'], df['y'], label="Current Vibe" if language == "English" else "الطاقة الحالية", color="#00FFFF", linewidth=2.5)
        plt.plot(forecast['ds'], forecast['yhat'], label="Forecast" if language == "English" else "التوقعات", color="#FFD700", linewidth=2.5)
        plt.fill_between(forecast['ds'], forecast['yhat_lower'], forecast['yhat_upper'], color="#FFD700", alpha=0.3)
        plt.title(f"{vibe_topic} 7-Day Vibe Forecast", fontsize=18, color="white", pad=20)
        plt.gca().set_facecolor('#1F0F3D')
        plt.gcf().set_facecolor('#1F0F3D')
        plt.legend(fontsize=12, facecolor="#1F0F3D", edgecolor="white", labelcolor="white")
        plt.xticks(color="white", fontsize=10)
        plt.yticks(color="white", fontsize=10)
        
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=300, bbox_inches="tight")
        img_buffer.seek(0)
        plt.close()
        trend = "Rising" if forecast['yhat'].iloc[-1] > forecast['yhat'].iloc[-8] else "Fading"
        reco = f"Vibe: {trend}. Jump in if rising, pivot if fading."
        return img_buffer, reco
    except Exception as e:
        st.error(f"Failed to generate forecast: {e}")
        return None, None

def generate_report(vibe_topic, language, vibe_regions, vibe_keywords, vibe_sentiment, vibe_by_day, total_vibes, vibe_meter_buffer, forecast_chart_buffer=None, plan="Vibe Scout"):
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        style = styles["Normal"]
        style.fontSize = 12
        style.textColor = colors.black
        style.fontName = "Helvetica"

        report = f"VibeQuest Report: {vibe_topic}\n"
        report += "=" * 50 + "\n"
        report += f"Quest: {plan}\n"
        report += f"Total Vibes: {total_vibes}\n"
        if language == "Arabic":
            report = arabic_reshaper.reshape(report)
            report = get_display(report)

        content = [Paragraph(report, style)]
        content.append(Image(vibe_meter_buffer, width=400, height=300))
        
        if forecast_chart_buffer and plan in ["Vibe Hero ($9)", "Vibe Legend ($18)", "Vibe Elite ($30/month)"]:
            content.append(Image(forecast_chart_buffer, width=400, height=300))
            content.append(Spacer(1, 20))
        
        if plan in ["Vibe Legend ($18)", "Vibe Elite ($30/month)"]:
            content.append(Paragraph("Top Vibes: " + ", ".join([f"{k} ({v}%)" for k, v in vibe_keywords]), style))
            content.append(Paragraph("Vibe Tip: Focus on Worldwide buzz (80% Positive).", style))
        
        doc.build(content)
        buffer.seek(0)
        return buffer.getvalue()
    except Exception as e:
        st.error(f"Failed to generate report: {e}")
        return None

# تشغيل التطبيق
if st.button("Start Your VibeQuest!", key="vibe_quest"):
    with st.spinner("Questing Your Vibe..."):
        bearer_token = get_twitter_bearer_token()  # جلب Bearer Token باستخدام API Key و API Secret
        if bearer_token:
            vibe_sentiment = fetch_twitter_vibes(vibe_topic, bearer_token)
            vibe_meter_buffer = generate_vibe_meter(vibe_topic, language, vibe_sentiment)
            if vibe_meter_buffer:
                st.session_state["vibe_data"] = {"vibe_meter": vibe_meter_buffer.getvalue()}
                st.image(vibe_meter_buffer, caption="Vibe Meter")
                
                share_url = "https://smartpulse-nwrkb9xdsnebmnhczyt76s.streamlit.app/"
                telegram_group = "https://t.me/+K7W_PUVdbGk4MDRk"
                
                st.markdown("<h3 style='text-align: center;'>Share Your Vibe!</h3>", unsafe_allow_html=True)
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.markdown(f'<a href="https://api.whatsapp.com/send?text=Feel%20the%20vibe%20with%20VibeQuest:%20{share_url}" target="_blank" class="share-btn">WhatsApp</a>', unsafe_allow_html=True)
                with col2:
                    st.markdown(f'<a href="https://t.me/share/url?url={share_url}&text=VibeQuest%20is%20electrifying!" target="_blank" class="share-btn">Telegram</a>', unsafe_allow_html=True)
                with col3:
                    st.markdown(f'<a href="https://www.facebook.com/sharer/sharer.php?u={share_url}" target="_blank" class="share-btn">Messenger</a>', unsafe_allow_html=True)
                with col4:
                    st.markdown(f'<a href="https://discord.com/channels/@me?message=Join%20VibeQuest:%20{share_url}" target="_blank" class="share-btn">Discord</a>', unsafe_allow_html=True)
                
                st.markdown(f"<p style='text-align: center;'>Join our Telegram: <a href='{telegram_group}' target='_blank'>Click Here</a> - Share with 5 friends for a FREE report!</p>", unsafe_allow_html=True)
                
                if plan == "Vibe Peek (Free)":
                    st.info("Unlock deeper vibes with a paid quest!")
                else:
                    if not st.session_state["payment_verified"] and not st.session_state["payment_initiated"]:
                        access_token = get_paypal_access_token()
                        if access_token:
                            amount = {"Vibe Scout ($4)": "4.00", "Vibe Hero ($9)": "9.00", "Vibe Legend ($18)": "18.00", "Vibe Elite ($30/month)": "30.00"}[plan]
                            approval_url = create_payment(access_token, amount, f"VibeQuest {plan}")
                            if approval_url:
                                st.session_state["payment_url"] = approval_url
                                st.session_state["payment_initiated"] = True
                                unique_id = uuid.uuid4()
                                st.markdown(f"""
                                    <a href="{approval_url}" target="_blank" id="paypal_auto_link_{unique_id}" style="display:none;">PayPal</a>
                                    <script>
                                        setTimeout(function() {{
                                            document.getElementById("paypal_auto_link_{unique_id}").click();
                                        }}, 100);
                                    </script>
                                """, unsafe_allow_html=True)
                                st.info(f"Vibe payment opened for {plan}. Complete it to feel the buzz!")
                    elif st.session_state["payment_verified"]:
                        forecast_chart_buffer, reco = generate_forecast(vibe_topic, language, vibe_by_day) if plan in ["Vibe Hero ($9)", "Vibe Legend ($18)", "Vibe Elite ($30/month)"] else (None, None)
                        if forecast_chart_buffer:
                            st.session_state["vibe_data"]["forecast_chart"] = forecast_chart_buffer.getvalue()
                            st.image(forecast_chart_buffer, caption="7-Day Vibe Forecast")
                            st.write(reco)
                        
                        vibe_meter_buffer = io.BytesIO(st.session_state["vibe_data"]["vibe_meter"])
                        forecast_chart_buffer = io.BytesIO(st.session_state["vibe_data"]["forecast_chart"]) if "forecast_chart" in st.session_state["vibe_data"] else None
                        pdf_data = generate_report(vibe_topic, language, vibe_regions, vibe_keywords, vibe_sentiment, vibe_by_day, total_vibes, vibe_meter_buffer, forecast_chart_buffer, plan)
                        if pdf_data:
                            st.download_button(
                                label=f"Download Your {plan.split(' (')[0]} Vibe Report",
                                data=pdf_data,
                                file_name=f"{vibe_topic}_vibequest_report.pdf",
                                mime="application/pdf",
                                key="download_report"
                            )
                            st.success(f"{plan.split(' (')[0]} Vibe Unlocked! Share to amplify your quest!")
