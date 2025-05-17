import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
from futures_position_analysis import FuturesPositionAnalyzer

# 设置页面配置
st.set_page_config(
    page_title="期货持仓分析",
    page_icon="📈",
    layout="wide"
)

# 初始化分析器
data_dir = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(data_dir, exist_ok=True)
analyzer = FuturesPositionAnalyzer(data_dir)

# 页面标题
st.title("期货持仓分析系统")

# 日期选择
col1, col2 = st.columns([2, 1])
with col1:
    # 默认选择今天
    default_date = datetime.now()
    trade_date = st.date_input(
        "选择交易日期",
        value=default_date,
        format="YYYYMMDD"
    )
    
    # 转换日期格式
    trade_date_str = trade_date.strftime("%Y%m%d")

with col2:
    st.write("")
    st.write("")
    analyze_button = st.button("开始分析", type="primary")

# 分析逻辑
if analyze_button:
    with st.spinner("正在分析数据，请稍候..."):
        # 获取数据并分析
        results = analyzer.fetch_and_analyze(trade_date_str)
        
        if not results:
            st.error("没有获取到任何分析结果")
        else:
            # 为每个策略创建标签页
            tabs = st.tabs([strategy.name for strategy in analyzer.strategies])
            
            for tab, strategy in zip(tabs, analyzer.strategies):
                with tab:
                    strategy_name = strategy.name
                    
                    # 收集该策略的所有信号
                    long_signals = []
                    short_signals = []
                    
                    for contract, data in results.items():
                        strategy_data = data['strategies'][strategy_name]
                        signal_data = {
                            'contract': contract,
                            'strength': strategy_data['strength'],
                            'reason': strategy_data['reason']
                        }
                        
                        if strategy_data['signal'] == '看多':
                            long_signals.append(signal_data)
                        elif strategy_data['signal'] == '看空':
                            short_signals.append(signal_data)
                    
                    # 按强度排序
                    long_signals.sort(key=lambda x: x['strength'], reverse=True)
                    short_signals.sort(key=lambda x: x['strength'], reverse=True)
                    
                    # 创建两列布局
                    col1, col2 = st.columns(2)
                    
                    # 看多信号
                    with col1:
                        st.subheader("看多信号")
                        if long_signals:
                            # 创建看多信号表格
                            long_df = pd.DataFrame(long_signals)
                            long_df['强度'] = long_df['strength'].round(2)
                            long_df = long_df[['contract', '强度', 'reason']]
                            long_df.columns = ['合约', '强度', '原因']
                            st.dataframe(long_df, use_container_width=True)
                            
                            # 创建看多信号强度图表
                            fig_long = go.Figure(data=[
                                go.Bar(
                                    x=[s['contract'] for s in long_signals[:10]],
                                    y=[s['strength'] for s in long_signals[:10]],
                                    marker_color='green'
                                )
                            ])
                            fig_long.update_layout(
                                title="看多信号强度排名（前10）",
                                xaxis_title="合约",
                                yaxis_title="信号强度",
                                height=400
                            )
                            st.plotly_chart(fig_long, use_container_width=True)
                        else:
                            st.info("暂无看多信号")
                    
                    # 看空信号
                    with col2:
                        st.subheader("看空信号")
                        if short_signals:
                            # 创建看空信号表格
                            short_df = pd.DataFrame(short_signals)
                            short_df['强度'] = short_df['strength'].round(2)
                            short_df = short_df[['contract', '强度', 'reason']]
                            short_df.columns = ['合约', '强度', '原因']
                            st.dataframe(short_df, use_container_width=True)
                            
                            # 创建看空信号强度图表
                            fig_short = go.Figure(data=[
                                go.Bar(
                                    x=[s['contract'] for s in short_signals[:10]],
                                    y=[s['strength'] for s in short_signals[:10]],
                                    marker_color='red'
                                )
                            ])
                            fig_short.update_layout(
                                title="看空信号强度排名（前10）",
                                xaxis_title="合约",
                                yaxis_title="信号强度",
                                height=400
                            )
                            st.plotly_chart(fig_short, use_container_width=True)
                        else:
                            st.info("暂无看空信号")
                    
                    # 添加统计信息
                    st.subheader("统计信息")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("看多信号数量", len(long_signals))
                    with col2:
                        st.metric("看空信号数量", len(short_signals))
                    with col3:
                        st.metric("中性信号数量", len(results) - len(long_signals) - len(short_signals))

# 添加页脚
st.markdown("---")
st.markdown("### 使用说明")
st.markdown("""
1. 选择要分析的交易日期
2. 点击"开始分析"按钮
3. 查看不同策略的分析结果
4. 可以通过标签页切换不同的分析策略
""") 