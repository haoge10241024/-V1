import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import sys

# 添加当前目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from futures_position_analysis import FuturesPositionAnalyzer
except ImportError as e:
    st.error(f"导入错误：{str(e)}")
    st.error("请确保futures_position_analysis.py文件在正确的位置")
    st.stop()

# 设置页面配置
st.set_page_config(
    page_title="期货持仓分析系统",
    page_icon="📊",
    layout="wide"
)

# 初始化分析器
data_dir = "data"
if not os.path.exists(data_dir):
    os.makedirs(data_dir)
analyzer = FuturesPositionAnalyzer(data_dir)

# 创建标题
st.title("期货持仓分析系统")

# 创建日期选择器
trade_date = st.date_input(
    "选择交易日期",
    value=datetime.now(),
    format="YYYY-MM-DD"
)

# 转换日期格式
trade_date_str = trade_date.strftime("%Y%m%d")

# 创建分析按钮
if st.button("开始分析"):
    with st.spinner("正在分析数据..."):
        try:
            # 获取分析结果
            results = analyzer.fetch_and_analyze(trade_date_str)
            
            if not results:
                st.error("没有获取到分析结果")
                st.stop()
            
            # 为每个策略创建标签页
            tabs = st.tabs([strategy.name for strategy in analyzer.strategies])
            
            # 显示每个策略的结果
            for i, strategy in enumerate(analyzer.strategies):
                with tabs[i]:
                    # 分类整理数据
                    long_signals = []
                    short_signals = []
                    
                    for contract, data in results.items():
                        strategy_data = data['strategies'][strategy.name]
                        if strategy_data['signal'] == '看多':
                            long_signals.append({
                                'contract': contract,
                                'strength': strategy_data['strength'],
                                'reason': strategy_data['reason']
                            })
                        elif strategy_data['signal'] == '看空':
                            short_signals.append({
                                'contract': contract,
                                'strength': strategy_data['strength'],
                                'reason': strategy_data['reason']
                            })
                    
                    # 按强度排序
                    long_signals.sort(key=lambda x: x['strength'], reverse=True)
                    short_signals.sort(key=lambda x: x['strength'], reverse=True)
                    
                    # 创建两列布局
                    col1, col2 = st.columns(2)
                    
                    # 显示看多信号
                    with col1:
                        st.subheader("看多信号")
                        for signal in long_signals:
                            st.markdown(f"""
                            <div style='background-color: #e6ffe6; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                                <strong>{signal['contract']}</strong><br>
                                强度: {signal['strength']:.2f}<br>
                                {signal['reason']}
                            </div>
                            """, unsafe_allow_html=True)
                    
                    # 显示看空信号
                    with col2:
                        st.subheader("看空信号")
                        for signal in short_signals:
                            st.markdown(f"""
                            <div style='background-color: #ffe6e6; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                                <strong>{signal['contract']}</strong><br>
                                强度: {signal['strength']:.2f}<br>
                                {signal['reason']}
                            </div>
                            """, unsafe_allow_html=True)
                    
                    # 显示统计信息
                    st.markdown("---")
                    st.markdown(f"""
                    ### 统计信息
                    - 看多信号品种数量：{len(long_signals)}
                    - 看空信号品种数量：{len(short_signals)}
                    - 中性信号品种数量：{len(results) - len(long_signals) - len(short_signals)}
                    """)
                    
                    # 创建信号强度图表
                    if long_signals or short_signals:
                        fig = go.Figure()
                        
                        if long_signals:
                            fig.add_trace(go.Bar(
                                x=[s['contract'] for s in long_signals],
                                y=[s['strength'] for s in long_signals],
                                name='看多信号',
                                marker_color='green'
                            ))
                        
                        if short_signals:
                            fig.add_trace(go.Bar(
                                x=[s['contract'] for s in short_signals],
                                y=[-s['strength'] for s in short_signals],
                                name='看空信号',
                                marker_color='red'
                            ))
                        
                        fig.update_layout(
                            title='信号强度分布',
                            xaxis_title='合约',
                            yaxis_title='信号强度',
                            barmode='relative',
                            height=400
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"分析过程中出现错误：{str(e)}")

# 添加使用说明
with st.expander("使用说明"):
    st.markdown("""
    ### 使用步骤
    1. 选择要分析的交易日期
    2. 点击"开始分析"按钮
    3. 等待分析完成
    4. 查看不同策略的分析结果
    
    ### 注意事项
    - 首次运行需要下载数据，可能较慢
    - 确保网络连接正常
    - 数据文件会自动保存在data目录
    """) 
