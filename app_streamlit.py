import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import sys
import io

# 添加当前目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from futures_position_analysis import FuturesPositionAnalyzer
    from analyze_term_structure import analyze_term_structure
except ImportError as e:
    st.error(f"导入错误：{str(e)}")
    st.error("请确保futures_position_analysis.py和analyze_term_structure.py文件在正确的位置")
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
            
            # 为每个策略创建标签页，并添加策略总结标签页
            tabs = st.tabs([strategy.name for strategy in analyzer.strategies] + ["期限结构分析", "策略总结"])
            
            # 存储所有策略的信号数据
            all_strategy_signals = {}
            
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
                    
                    # 存储策略信号数据
                    all_strategy_signals[strategy.name] = {
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
            with tabs[-2]:
                st.header("期限结构分析")
                
                # 准备期限结构分析数据
                term_structure_data = []
                for contract, data in results.items():
                    if 'raw_data' in data:
                        df = pd.DataFrame(data['raw_data'])
                        if not df.empty:
                            # 添加品种信息
                            df['variety'] = contract.split('_')[-1][:2].lower()
                            term_structure_data.append(df)
                
                if term_structure_data:
                    # 合并所有数据
                    all_data = pd.concat(term_structure_data, ignore_index=True)
                    
                    # 分析期限结构
                    term_results = analyze_term_structure(all_data)
                    
                    # 按期限结构类型分类
                    back_results = [r for r in term_results if r[1] == "back"]
                    contango_results = [r for r in term_results if r[1] == "contango"]
                    flat_results = [r for r in term_results if r[1] == "flat"]
                    
                    # 显示Back结构品种
                    st.subheader("Back结构品种（近强远弱）")
                    if back_results:
                        for variety, structure, contracts, closes in back_results:
                            st.markdown(f"""
                            <div style='background-color: #ffe6e6; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                                <strong>品种: {variety}</strong><br>
                                合约价格详情:<br>
                                {''.join(f'  {contract}: {close}<br>' for contract, close in zip(contracts, closes))}
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("无")
                    
                    # 显示Contango结构品种
                    st.subheader("Contango结构品种（近弱远强）")
                    if contango_results:
                        for variety, structure, contracts, closes in contango_results:
                            st.markdown(f"""
                            <div style='background-color: #e6ffe6; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                                <strong>品种: {variety}</strong><br>
                                合约价格详情:<br>
                                {''.join(f'  {contract}: {close}<br>' for contract, close in zip(contracts, closes))}
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("无")
                    
                    # 显示Flat结构品种
                    st.subheader("Flat结构品种（近远月价格相近）")
                    if flat_results:
                        for variety, structure, contracts, closes in flat_results:
                            st.markdown(f"""
                            <div style='background-color: #f0f0f0; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                                <strong>品种: {variety}</strong><br>
                                合约价格详情:<br>
                                {''.join(f'  {contract}: {close}<br>' for contract, close in zip(contracts, closes))}
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("无")
                    
                    # 显示统计信息
                    st.markdown("---")
                    st.markdown(f"""
                    ### 统计信息
                    - Back结构品种数量: {len(back_results)}
                    - Contango结构品种数量: {len(contango_results)}
                    - Flat结构品种数量: {len(flat_results)}
                    - 总品种数量: {len(term_results)}
                    """)
                else:
                    st.warning("没有可用的期限结构数据")

            # 显示策略总结页面
            with tabs[-1]:
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
            for variety, structure, contracts, closes in back_results:
                text_output.write(f"\n品种: {variety}\n")
                text_output.write("合约价格详情:\n")
                for contract, close in zip(contracts, closes):
                    text_output.write(f"  {contract}: {close}\n")
            
            text_output.write("\nContango结构品种（近弱远强）:\n")
            for variety, structure, contracts, closes in contango_results:
                text_output.write(f"\n品种: {variety}\n")
                text_output.write("合约价格详情:\n")
                for contract, close in zip(contracts, closes):
                    text_output.write(f"  {contract}: {close}\n")
            
            text_output.write("\nFlat结构品种（近远月价格相近）:\n")
            for variety, structure, contracts, closes in flat_results:
                text_output.write(f"\n品种: {variety}\n")
                text_output.write("合约价格详情:\n")
                for contract, close in zip(contracts, closes):
                    text_output.write(f"  {contract}: {close}\n")
            
            # 获取文本内容并创建下载按钮
            text_content = text_output.getvalue()
            st.download_button(
                label="下载分析结果(TXT)",
                data=text_content,
                file_name=f"futures_analysis_{trade_date_str}.txt",
                mime="text/plain",
                key=f"download_txt_{trade_date_str}"
            )
            
        except Exception as e:
            st.error(f"分析过程中出现错误：{str(e)}")
            st.error("详细错误信息：")
            st.exception(e)

# 添加使用说明
with st.expander("使用说明"):
    st.markdown("""
    ### 使用步骤
    1. 选择要分析的交易日期
    2. 点击"开始分析"按钮
    3. 等待分析完成
    4. 查看不同策略的分析结果
    
    ### 策略说明
    
    #### 多空力量对比策略
    该策略通过分析期货市场中的多空持仓变化来判断市场趋势。主要原理包括：
    - 分析主力合约的持仓量变化
    - 计算多空双方的力量对比
    - 考虑持仓量的变化趋势
    - 结合成交量进行分析
    当多方力量明显强于空方时，给出看多信号；反之则给出看空信号。
    
    #### 蜘蛛网策略
    该策略基于市场微观结构理论，通过分析价格和成交量的关系来判断市场趋势。主要原理包括：
    - 分析价格与成交量的相关性
    - 计算市场深度指标
    - 识别知情交易者的行为特征
    - 评估市场流动性状况
    当市场微观结构显示强势特征时，给出看多信号；反之则给出看空信号。
    
    #### 期限结构分析
    该策略通过分析期货合约的期限结构来判断市场趋势。主要原理包括：
    - 分析近月合约与远月合约的价格关系
    - 识别Back结构（近强远弱）和Contango结构（近弱远强）
    - 评估市场供需状况
    - 判断市场情绪
    当出现Back结构时，表明市场看多情绪较强；当出现Contango结构时，表明市场看空情绪较强。
    
    ### 注意事项
    - 首次运行需要下载数据，可能较慢
    - 确保网络连接正常
    - 数据文件会自动保存在data目录
    """) 
