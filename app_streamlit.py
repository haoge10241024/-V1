import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from futures_position_analysis import FuturesPositionAnalyzer
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import io

# 设置页面配置
st.set_page_config(
    page_title="期货持仓分析系统",
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
    
    # 创建分析按钮
    if st.button("开始分析"):
        with st.spinner("正在分析数据..."):
            # 获取分析结果
            results = get_analysis_results(trade_date_str)
            
            if not results:
                st.error("获取数据失败，请检查日期是否有效")
                return
            
            # 生成图表
            charts = generate_charts(results)
            
            # 为每个策略创建标签页，并添加策略总结标签页
            tabs = st.tabs(["多空力量变化策略", "蜘蛛网策略", "期限结构分析", "策略总结"])
            
            # 存储所有策略的信号数据
            all_strategy_signals = {}
            
            # 显示每个策略的结果
            for i, strategy_name in enumerate(["多空力量变化策略", "蜘蛛网策略"]):
                with tabs[i]:
                    # 分类整理数据
                    long_signals = []
                    short_signals = []
                    
                    for contract, data in results.items():
                        strategy_data = data['strategies'][strategy_name]
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
                    
                    # 存储策略信号数据
                    all_strategy_signals[strategy_name] = {
                        'long': long_signals,
                        'short': short_signals
                    }
                    
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
                            <div style='background-color: #ffe6e6; padding: 10px; border-radius: 5px; margin: 5px 0;'>
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
                            <div style='background-color: #e6ffe6; padding: 10px; border-radius: 5px; margin: 5px 0;'>
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
                                marker_color='red'
                            ))
                        
                        if short_signals:
                            fig.add_trace(go.Bar(
                                x=[s['contract'] for s in short_signals],
                                y=[-s['strength'] for s in short_signals],
                                name='看空信号',
                                marker_color='green'
                            ))
                        
                        fig.update_layout(
                            title='信号强度分布',
                            xaxis_title='合约',
                            yaxis_title='信号强度',
                            barmode='relative',
                            height=400
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
            
            # 显示期限结构分析页面
            with tabs[2]:
                st.header("期限结构分析")
                
                # 准备期限结构分析数据
                term_structure_data = []
                for contract, data in results.items():
                    if 'raw_data' in data:
                        df = pd.DataFrame(data['raw_data'])
                        if not df.empty:
                            df['variety'] = contract.split('_')[-1][:2].lower()
                            term_structure_data.append(df)
                
                if term_structure_data:
                    # 合并所有数据
                    all_data = pd.concat(term_structure_data, ignore_index=True)
                    
                    # 分析期限结构
                    results_list = []
                    for variety in all_data['variety'].unique():
                        variety_data = all_data[all_data['variety'] == variety].copy()
                        
                        # 检查必要的列是否存在
                        required_columns = ['symbol', 'long_open_interest', 'short_open_interest']
                        if not all(col in variety_data.columns for col in required_columns):
                            continue
                        
                        # 按合约代码排序
                        variety_data = variety_data.sort_values('symbol')
                        
                        # 使用持仓量作为价格指标
                        variety_data['price_indicator'] = variety_data['long_open_interest'] + variety_data['short_open_interest']
                        
                        # 获取合约列表和对应的价格指标
                        contracts = variety_data['symbol'].tolist()
                        prices = variety_data['price_indicator'].tolist()
                        
                        # 检查是否有足够的数据进行分析（至少需要3个合约）
                        if len(contracts) < 3:
                            continue
                            
                        # 计算相邻合约的价格变化率
                        price_changes = []
                        for i in range(len(prices)-1):
                            change_rate = (prices[i+1] - prices[i]) / prices[i]
                            price_changes.append(change_rate)
                        
                        # 判断结构类型
                        # 如果所有变化率都小于-0.05，则为Back结构
                        # 如果所有变化率都大于0.05，则为Contango结构
                        # 其他情况不归类
                        if all(rate < -0.05 for rate in price_changes):
                            structure = "back"
                        elif all(rate > 0.05 for rate in price_changes):
                            structure = "contango"
                        else:
                            continue  # 跳过不符合条件的品种
                            
                        results_list.append((variety, structure, contracts, prices))
                    
                    # 按期限结构类型分类
                    back_results = [r for r in results_list if r[1] == "back"]
                    contango_results = [r for r in results_list if r[1] == "contango"]
                    
                    # 创建两列布局
                    col1, col2 = st.columns(2)
                    
                    # 显示Back结构品种
                    with col1:
                        st.subheader("Back结构（近强远弱）")
                        if back_results:
                            for variety, structure, contracts, prices in back_results:
                                st.markdown(f"**{variety}**")
                                # 计算并显示变化率
                                for i in range(len(contracts)-1):
                                    change_rate = (prices[i+1] - prices[i]) / prices[i] * 100
                                    st.markdown(f"{contracts[i]} → {contracts[i+1]}: {change_rate:.1f}%")
                                st.markdown("---")
                        else:
                            st.info("无")
                    
                    # 显示Contango结构品种
                    with col2:
                        st.subheader("Contango结构（近弱远强）")
                        if contango_results:
                            for variety, structure, contracts, prices in contango_results:
                                st.markdown(f"**{variety}**")
                                # 计算并显示变化率
                                for i in range(len(contracts)-1):
                                    change_rate = (prices[i+1] - prices[i]) / prices[i] * 100
                                    st.markdown(f"{contracts[i]} → {contracts[i+1]}: {change_rate:.1f}%")
                                st.markdown("---")
                        else:
                            st.info("无")
                    
                    # 显示统计信息
                    st.markdown("---")
                    st.markdown(f"""
                    ### 统计信息
                    - Back结构品种数量: {len(back_results)}
                    - Contango结构品种数量: {len(contango_results)}
                    - 总品种数量: {len(results_list)}
                    """)
                else:
                    st.warning("没有可用的期限结构数据")
            
            # 显示策略总结页面
            with tabs[3]:
                st.header("策略总结")
                
                # 获取每个策略的前十名品种
                strategy_top_10 = {}
                for strategy_name, signals in all_strategy_signals.items():
                    # 获取看多和看空的前十名
                    long_signals = signals['long'][:10]
                    short_signals = signals['short'][:10]
                    
                    # 提取品种代码（去掉交易所前缀和数字）
                    long_symbols = set()
                    short_symbols = set()
                    
                    def extract_symbol(contract):
                        """提取品种代码的函数"""
                        try:
                            # 分割合约名称
                            parts = contract.split('_')
                            if len(parts) > 1:
                                # 获取最后一部分（如：cu2505）
                                symbol_part = parts[-1]
                                # 提取字母部分
                                symbol = ''.join(c for c in symbol_part if c.isalpha())
                                return symbol.lower()
                        except:
                            return None
                        return None
                    
                    for signal in long_signals:
                        symbol = extract_symbol(signal['contract'])
                        if symbol:
                            long_symbols.add(symbol)
                    
                    for signal in short_signals:
                        symbol = extract_symbol(signal['contract'])
                        if symbol:
                            short_symbols.add(symbol)
                    
                    strategy_top_10[strategy_name] = {
                        'long_signals': long_signals,
                        'short_signals': short_signals,
                        'long_symbols': long_symbols,
                        'short_symbols': short_symbols
                    }
                
                # 找出共同看多的品种
                common_long = set.intersection(*[data['long_symbols'] for data in strategy_top_10.values()])
                # 找出共同看空的品种
                common_short = set.intersection(*[data['short_symbols'] for data in strategy_top_10.values()])
                
                # 显示共同信号
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("共同看多品种")
                    if common_long:
                        for symbol in sorted(common_long):
                            st.markdown(f"""
                            <div style='background-color: #e6ffe6; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                                <strong>{symbol}</strong>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("没有共同看多的品种")
                
                with col2:
                    st.subheader("共同看空品种")
                    if common_short:
                        for symbol in sorted(common_short):
                            st.markdown(f"""
                            <div style='background-color: #ffe6e6; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                                <strong>{symbol}</strong>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("没有共同看空的品种")
                
                # 显示每个策略的前十名
                st.markdown("---")
                st.subheader("各策略前十名品种")
                
                for strategy_name, data in strategy_top_10.items():
                    st.markdown(f"### {strategy_name}")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**看多品种**")
                        for signal in data['long_signals']:
                            st.markdown(f"""
                            <div style='background-color: #e6ffe6; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                                <strong>{signal['contract']}</strong><br>
                                强度: {signal['strength']:.2f}<br>
                                {signal['reason']}
                            </div>
                            """, unsafe_allow_html=True)
                    
                    with col2:
                        st.markdown("**看空品种**")
                        for signal in data['short_signals']:
                            st.markdown(f"""
                            <div style='background-color: #ffe6e6; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                                <strong>{signal['contract']}</strong><br>
                                强度: {signal['strength']:.2f}<br>
                                {signal['reason']}
                            </div>
                            """, unsafe_allow_html=True)
            
            # 添加下载按钮
            st.markdown("---")
            st.subheader("下载分析结果")
            
            # 准备Excel数据
            excel_data = {}
            
            # 添加策略总结数据
            summary_data = []
            for strategy_name, data in strategy_top_10.items():
                # 添加看多信号
                for signal in data['long_signals']:
                    summary_data.append({
                        '策略': strategy_name,
                        '信号类型': '看多',
                        '合约': signal['contract'],
                        '强度': signal['strength'],
                        '原因': signal['reason']
                    })
                # 添加看空信号
                for signal in data['short_signals']:
                    summary_data.append({
                        '策略': strategy_name,
                        '信号类型': '看空',
                        '合约': signal['contract'],
                        '强度': signal['strength'],
                        '原因': signal['reason']
                    })
            
            # 创建Excel文件
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # 写入策略总结
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='策略总结', index=False)
                
                # 写入共同信号
                common_signals = []
                for symbol in common_long:
                    common_signals.append({
                        '品种': symbol,
                        '信号类型': '共同看多'
                    })
                for symbol in common_short:
                    common_signals.append({
                        '品种': symbol,
                        '信号类型': '共同看空'
                    })
                pd.DataFrame(common_signals).to_excel(writer, sheet_name='共同信号', index=False)
                
                # 写入原始数据
                for contract, data in results.items():
                    if 'raw_data' in data:
                        df = pd.DataFrame(data['raw_data'])
                        sheet_name = contract[:31]  # Excel sheet名称最大31字符
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # 创建下载按钮
            st.download_button(
                label="下载分析结果(Excel)",
                data=output.getvalue(),
                file_name=f"futures_analysis_{trade_date_str}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"download_excel_{trade_date_str}"  # 使用日期作为key的一部分
            )
            
            # 添加文本格式下载
            text_output = io.StringIO()
            text_output.write(f"期货持仓分析报告 - {trade_date_str}\n")
            text_output.write("=" * 50 + "\n\n")
            
            # 写入策略总结
            text_output.write("策略总结\n")
            text_output.write("-" * 20 + "\n")
            for strategy_name, data in strategy_top_10.items():
                text_output.write(f"\n{strategy_name}:\n")
                text_output.write("看多信号:\n")
                for signal in data['long_signals']:
                    text_output.write(f"- {signal['contract']} (强度: {signal['strength']:.2f})\n")
                    text_output.write(f"  原因: {signal['reason']}\n")
                text_output.write("\n看空信号:\n")
                for signal in data['short_signals']:
                    text_output.write(f"- {signal['contract']} (强度: {signal['strength']:.2f})\n")
                    text_output.write(f"  原因: {signal['reason']}\n")
            
            # 写入共同信号
            text_output.write("\n共同信号\n")
            text_output.write("-" * 20 + "\n")
            text_output.write("共同看多品种:\n")
            for symbol in sorted(common_long):
                text_output.write(f"- {symbol}\n")
            text_output.write("\n共同看空品种:\n")
            for symbol in sorted(common_short):
                text_output.write(f"- {symbol}\n")
            
            # 写入期限结构分析结果
            text_output.write("\n期限结构分析\n")
            text_output.write("-" * 20 + "\n")
            
            text_output.write("\nBack结构品种（近强远弱）:\n")
            for variety, structure, contracts, prices in back_results:
                text_output.write(f"\n品种: {variety}\n")
                text_output.write("合约持仓详情:\n")
                for contract, price in zip(contracts, prices):
                    text_output.write(f"  {contract}: {price:.0f}\n")
            
            text_output.write("\nContango结构品种（近弱远强）:\n")
            for variety, structure, contracts, prices in contango_results:
                text_output.write(f"\n品种: {variety}\n")
                text_output.write("合约持仓详情:\n")
                for contract, price in zip(contracts, prices):
                    text_output.write(f"  {contract}: {price:.0f}\n")
            
            # 获取文本内容并创建下载按钮
            text_content = text_output.getvalue()
            st.download_button(
                label="下载分析结果(TXT)",
                data=text_content,
                file_name=f"futures_analysis_{trade_date_str}.txt",
                mime="text/plain",
                key=f"download_txt_{trade_date_str}"
            )

if __name__ == "__main__":
    main() 
