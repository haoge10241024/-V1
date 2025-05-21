import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from futures_position_analysis import FuturesPositionAnalyzer
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

# 设置页面配置
st.set_page_config(
    page_title="期货持仓分析",
    page_icon="📊",
    layout="wide"
)

# 缓存数据获取和分析结果
@st.cache_data(ttl=3600)  # 缓存1小时
def get_analysis_results(trade_date):
    analyzer = FuturesPositionAnalyzer("data")
    return analyzer.fetch_and_analyze(trade_date)

# 缓存图表生成
@st.cache_data(ttl=3600)
def generate_charts(results):
    charts = {}
    for contract_name, data in results.items():
        if 'raw_data' in data:
            df = data['raw_data']
            # 生成持仓分布图
            fig = make_subplots(rows=1, cols=2, subplot_titles=('多空持仓分布', '持仓变化分布'))
            
            # 多空持仓分布
            fig.add_trace(
                go.Bar(x=df['long_party_name'], y=df['long_open_interest'], name='多单持仓'),
                row=1, col=1
            )
            fig.add_trace(
                go.Bar(x=df['short_party_name'], y=df['short_open_interest'], name='空单持仓'),
                row=1, col=1
            )
            
            # 持仓变化分布
            fig.add_trace(
                go.Bar(x=df['long_party_name'], y=df['long_open_interest_chg'], name='多单变化'),
                row=1, col=2
            )
            fig.add_trace(
                go.Bar(x=df['short_party_name'], y=df['short_open_interest_chg'], name='空单变化'),
                row=1, col=2
            )
            
            fig.update_layout(height=600, showlegend=True)
            charts[contract_name] = fig
    return charts

def main():
    st.title("期货持仓分析系统")
    
    # 日期选择
    today = datetime.now()
    default_date = today - timedelta(days=1)
    trade_date = st.date_input(
        "选择交易日期",
        value=default_date,
        max_value=today
    )
    
    # 转换日期格式
    trade_date_str = trade_date.strftime("%Y%m%d")
    
    # 获取分析结果
    results = get_analysis_results(trade_date_str)
    
    if not results:
        st.error("获取数据失败，请检查日期是否有效")
        return
    
    # 生成图表
    charts = generate_charts(results)
    
    # 创建多空信号和共同信号的标签页
    tab1, tab2, tab3 = st.tabs(["多空信号", "共同信号", "策略总结"])
    
    with tab1:
        st.subheader("多空信号分析")
        for contract_name, data in results.items():
            if 'strategies' in data:
                st.write(f"### {contract_name}")
                for strategy_name, strategy_data in data['strategies'].items():
                    if strategy_data['signal'] in ['多', '空']:
                        st.write(f"**{strategy_name}**: {strategy_data['signal']} - {strategy_data['reason']}")
                        if contract_name in charts:
                            st.plotly_chart(charts[contract_name], use_container_width=True)
    
    with tab2:
        st.subheader("共同信号分析")
        for contract_name, data in results.items():
            if 'strategies' in data:
                signals = [s['signal'] for s in data['strategies'].values()]
                if len(set(signals)) == 1 and signals[0] in ['多', '空']:
                    st.write(f"### {contract_name}")
                    for strategy_name, strategy_data in data['strategies'].items():
                        st.write(f"**{strategy_name}**: {strategy_data['signal']} - {strategy_data['reason']}")
                    if contract_name in charts:
                        st.plotly_chart(charts[contract_name], use_container_width=True)
    
    with tab3:
        st.subheader("策略总结")
        summary_data = []
        for contract_name, data in results.items():
            if 'strategies' in data:
                for strategy_name, strategy_data in data['strategies'].items():
                    summary_data.append({
                        '合约': contract_name,
                        '策略': strategy_name,
                        '信号': strategy_data['signal'],
                        '原因': strategy_data['reason'],
                        '强度': strategy_data['strength']
                    })
        
        if summary_data:
            df_summary = pd.DataFrame(summary_data)
            st.dataframe(df_summary)
            
            # 下载按钮
            if st.button("下载分析结果"):
                # 保存为Excel
                excel_path = "analysis_results.xlsx"
                with pd.ExcelWriter(excel_path, engine='xlsxwriter') as writer:
                    df_summary.to_excel(writer, sheet_name='策略总结', index=False)
                    
                    # 添加详细数据
                    for contract_name, data in results.items():
                        if 'raw_data' in data:
                            data['raw_data'].to_excel(writer, sheet_name=contract_name[:31], index=False)
                
                # 提供下载链接
                with open(excel_path, 'rb') as f:
                    st.download_button(
                        label="点击下载Excel文件",
                        data=f,
                        file_name="analysis_results.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                # 保存为TXT
                txt_path = "analysis_results.txt"
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write("期货持仓分析结果\n")
                    f.write("=" * 50 + "\n\n")
                    
                    for contract_name, data in results.items():
                        f.write(f"合约：{contract_name}\n")
                        f.write("-" * 30 + "\n")
                        
                        if 'strategies' in data:
                            for strategy_name, strategy_data in data['strategies'].items():
                                f.write(f"策略：{strategy_name}\n")
                                f.write(f"信号：{strategy_data['signal']}\n")
                                f.write(f"原因：{strategy_data['reason']}\n")
                                f.write(f"强度：{strategy_data['strength']}\n\n")
                        
                        if 'raw_data' in data:
                            f.write("持仓数据：\n")
                            f.write(data['raw_data'].to_string())
                            f.write("\n\n")
                
                # 提供TXT下载链接
                with open(txt_path, 'rb') as f:
                    st.download_button(
                        label="点击下载TXT文件",
                        data=f,
                        file_name="analysis_results.txt",
                        mime="text/plain"
                    )

if __name__ == "__main__":
    main() 
