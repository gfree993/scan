import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import yfinance as yf
import numpy as np

# 1. 페이지 설정
st.set_page_config(page_title="Anti-Gravity Dashboard", layout="wide")
st.markdown("<style>.main { background-color: #0e1117; } .stMetric { border: 1px solid #4e4e4e; padding: 10px; border-radius: 5px; }</style>", unsafe_allow_html=True)

# 2. 사이드바: 미션 컨트롤
st.sidebar.header("🚀 Mission Control")
init_cash = st.sidebar.number_input("초기 투자 자금 ($)", value=10000, step=1000)
ticker_1x = st.sidebar.selectbox("기본 자산 (1x)", ["QQQ", "SOXX", "SPY"], index=0)
ticker_3x = st.sidebar.selectbox("가속 자산 (3x)", ["TQQQ", "SOXL", "UPRO"], index=0)
drop_trigger = st.sidebar.slider("급락 감지 기준 (%)", 1.0, 15.0, 5.0) / 100
switch_pct = st.sidebar.slider("스위칭 비중 (%)", 10, 100, 100) / 100

# 3. 데이터 로딩 (에러 방지 무적 로직)
@st.cache_data
def get_clean_data(t1, t2):
    try:
        d1_raw = yf.download(t1, start="2023-01-01", progress=False)
        d2_raw = yf.download(t2, start="2023-01-01", progress=False)
        
        def extract_price(df):
            if isinstance(df.columns, pd.MultiIndex): # 멀티인덱스 대응
                if 'Adj Close' in df.columns.get_level_values(0): return df['Adj Close']
                return df['Close']
            if 'Adj Close' in df.columns: return df['Adj Close']
            return df['Close']

        d1 = extract_price(d1_raw).ffill()
        d2 = extract_price(d2_raw).ffill()
        
        df = pd.concat([d1, d2], axis=1)
        df.columns = [t1, t2]
        return df.dropna()
    except Exception as e:
        st.error(f"데이터 다운로드 중 오류: {e}")
        return pd.DataFrame()

data = get_clean_data(ticker_1x, ticker_3x)

if not data.empty:
    # 4. 백테스팅 로직
    df_bt = data.copy()
    cash_1x, cash_3x = init_cash, 0.0
    history, events = [], []

    history.append({'Date': df_bt.index[0], 'Total': init_cash, '1x_Val': init_cash, '3x_Val': 0.0})

    for i in range(1, len(df_bt)):
        ret_1x = df_bt[ticker_1x].iloc[i] / df_bt[ticker_1x].iloc[i-1]
        ret_3x = df_bt[ticker_3x].iloc[i] / df_bt[ticker_3x].iloc[i-1]
        
        cash_1x *= ret_1x
        cash_3x *= ret_3x
        
        daily_ret = (df_bt[ticker_1x].iloc[i] / df_bt[ticker_1x].iloc[i-1]) - 1
        if daily_ret < -drop_trigger and cash_1x > 1.0:
            move = cash_1x * switch_pct
            cash_1x -= move
            cash_3x += move
            events.append(df_bt.index[i])
            
        history.append({'Date': df_bt.index[i], 'Total': cash_1x + cash_3x, '1x_Val': cash_1x, '3x_Val': cash_3x})

    res = pd.DataFrame(history).set_index('Date')
    benchmark = (df_bt[ticker_1x] / df_bt[ticker_1x].iloc[0]) * init_cash

    # 5. 화면 출력
    st.title("🛡️ Anti-Gravity Tactical Switching")
    m1, m2, m3 = st.columns(3)
    final_val = res['Total'].iloc[-1]
    m1.metric("최종 자산 가치", f"${final_val:,.0f}", f"{(final_val/init_cash-1)*100:.1f}%")
    m2.metric("현재 자산 배분", f"1x: {res['1x_Val'].iloc[-1]/final_val*100:.0f}% | 3x: {res['3x_Val'].iloc[-1]/final_val*100:.0f}%")
    m3.metric("Boost 횟수", f"{len(events)}회")

    # 차트 설정
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=benchmark.index, y=benchmark, name="1x 보유", line=dict(color='gray', dash='dot')))
    fig.add_trace(go.Scatter(x=res.index, y=res['Total'], name="전략 수익", line=dict(color='#00f2ff', width=3)))

    for e in events:
        fig.add_annotation(x=e, y=res.loc[e, 'Total'], text="🚀BOOST", showarrow=True, arrowhead=1, bgcolor="#ff00ff")

    # [핵심 수정] update_layout에는 width를 넣지 않습니다.
    fig.update_layout(template="plotly_dark", height=600, paper_bgcolor='#0e1117', plot_bgcolor='#0e1117')
    
    # [핵심 수정] st.plotly_chart에서만 width='stretch'를 사용합니다.
    st.plotly_chart(fig, width='stretch')
else:
    st.warning("데이터를 불러오지 못했습니다. 잠시 후 다시 시도하거나 티커를 확인해 주세요.")