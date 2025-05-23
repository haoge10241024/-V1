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
import akshare as ak  # 新增导入
from retail_reverse_strategy import analyze_all_positions  # 新增导入

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

# 缓存期货行情数据获取
@st.cache_data(ttl=1800)  # 缓存30分钟
def get_futures_price_data(date_str):
    """获取期货行情数据用于期限结构分析"""
    try:
        # 交易所列表
        exchanges = [
            {"market": "DCE", "name": "大商所"},
            {"market": "CFFEX", "name": "中金所"},
            {"market": "INE", "name": "上海国际能源交易中心"},
            {"market": "CZCE", "name": "郑商所"},
            {"market": "SHFE", "name": "上期所"},
            {"market": "GFEX", "name": "广期所"}
        ]
        
        all_data = []
        for exchange in exchanges:
            try:
                df = ak.get_futures_daily(start_date=date_str, end_date=date_str, market=exchange["market"])
                if not df.empty:
                    df['exchange'] = exchange["name"]
                    all_data.append(df)
            except Exception as e:
                st.warning(f"获取{exchange['name']}数据失败: {str(e)}")
                continue
        
        if all_data:
            return pd.concat(all_data, ignore_index=True)
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"获取期货行情数据失败: {str(e)}")
        return pd.DataFrame()

def analyze_term_structure_with_prices(df):
    """使用真实价格分析期限结构"""
    try:
        # 确保数据框包含必要的列
        required_columns = ['symbol', 'close', 'variety']
        if not all(col in df.columns for col in required_columns):
            return []
            
        results = []
        # 按品种分组分析
        for variety in df['variety'].unique():
            variety_data = df[df['variety'] == variety].copy()
            
            # 按合约代码排序
            variety_data = variety_data.sort_values('symbol')
            
            # 过滤掉价格为0或空值的数据
            variety_data = variety_data[
                (variety_data['close'] > 0) & 
                (variety_data['close'].notna())
            ]
            
            # 获取合约列表和对应的收盘价
            contracts = variety_data['symbol'].tolist()
            closes = variety_data['close'].tolist()
            
            # 检查是否有足够的数据进行分析
            if len(contracts) < 2:
                continue
                
            # 分析期限结构 - 参考analyze_term_structure.py的逻辑
            is_decreasing = all(closes[i] > closes[i+1] for i in range(len(closes)-1))
            is_increasing = all(closes[i] < closes[i+1] for i in range(len(closes)-1))

            if is_decreasing:
                structure = "back"
            elif is_increasing:
                structure = "contango"
            else:
                structure = "flat"
                
            results.append((variety, structure, contracts, closes))
            
        return results
        
    except Exception as e:
        st.error(f"分析期限结构时出错: {str(e)}")
        return []

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
            # 获取家人席位反向操作策略结果
            retail_results = analyze_all_positions(".")
            # 生成图表
            charts = generate_charts(results)
            # 为每个策略创建标签页，并添加策略总结标签页和家人席位反向操作策略页
            tabs = st.tabs(["多空力量变化策略", "蜘蛛网策略", "期限结构分析", "家人席位反向操作策略", "策略总结"])
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
                st.info("基于真实期货合约收盘价进行期限结构分析")
                
                try:
                    # 获取期货行情数据
                    with st.spinner("正在获取期货行情数据..."):
                        price_data = get_futures_price_data(trade_date_str)
                    
                    if not price_data.empty:
                        # 分析期限结构
                        structure_results = analyze_term_structure_with_prices(price_data)
                        
                        if structure_results:
                            # 按期限结构类型分类
                            back_results = [r for r in structure_results if r[1] == "back"]
                            contango_results = [r for r in structure_results if r[1] == "contango"]
                            flat_results = [r for r in structure_results if r[1] == "flat"]
                            
                            # 创建三列布局
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.subheader("Back结构（近强远弱）")
                                if back_results:
                                    for variety, structure, contracts, closes in back_results:
                                        try:
                                            st.markdown(f"**{variety}**")
                                            # 安全计算价格变化百分比
                                            changes = ['']
                                            for i in range(len(closes)-1):
                                                if closes[i] != 0:
                                                    change_pct = ((closes[i+1]-closes[i])/closes[i]*100)
                                                    changes.append(f'{change_pct:+.2f}%')
                                                else:
                                                    changes.append('N/A')
                                            
                                            price_df = pd.DataFrame({
                                                '合约': contracts,
                                                '收盘价': closes,
                                                '变化': changes
                                            })
                                            st.dataframe(price_df, use_container_width=True)
                                            st.markdown("---")
                                        except Exception as e:
                                            st.warning(f"显示{variety}数据时出错: {str(e)}")
                                            continue
                                else:
                                    st.info("无Back结构品种")
                            
                            with col2:
                                st.subheader("Contango结构（近弱远强）")
                                if contango_results:
                                    for variety, structure, contracts, closes in contango_results:
                                        try:
                                            st.markdown(f"**{variety}**")
                                            # 安全计算价格变化百分比
                                            changes = ['']
                                            for i in range(len(closes)-1):
                                                if closes[i] != 0:
                                                    change_pct = ((closes[i+1]-closes[i])/closes[i]*100)
                                                    changes.append(f'{change_pct:+.2f}%')
                                                else:
                                                    changes.append('N/A')
                                            
                                            price_df = pd.DataFrame({
                                                '合约': contracts,
                                                '收盘价': closes,
                                                '变化': changes
                                            })
                                            st.dataframe(price_df, use_container_width=True)
                                            st.markdown("---")
                                        except Exception as e:
                                            st.warning(f"显示{variety}数据时出错: {str(e)}")
                                            continue
                                else:
                                    st.info("无Contango结构品种")
                            
                            with col3:
                                st.subheader("Flat结构（价格相近）")
                                if flat_results:
                                    for variety, structure, contracts, closes in flat_results:
                                        try:
                                            st.markdown(f"**{variety}**")
                                            # 安全计算价格变化百分比
                                            changes = ['']
                                            for i in range(len(closes)-1):
                                                if closes[i] != 0:
                                                    change_pct = ((closes[i+1]-closes[i])/closes[i]*100)
                                                    changes.append(f'{change_pct:+.2f}%')
                                                else:
                                                    changes.append('N/A')
                                            
                                            price_df = pd.DataFrame({
                                                '合约': contracts,
                                                '收盘价': closes,
                                                '变化': changes
                                            })
                                            st.dataframe(price_df, use_container_width=True)
                                            st.markdown("---")
                                        except Exception as e:
                                            st.warning(f"显示{variety}数据时出错: {str(e)}")
                                            continue
                                else:
                                    st.info("无Flat结构品种")
                            
                            # 统计信息
                            st.markdown("---")
                            st.markdown(f"""
                            ### 统计信息
                            - Back结构品种数量: {len(back_results)}
                            - Contango结构品种数量: {len(contango_results)}
                            - Flat结构品种数量: {len(flat_results)}
                            - 总品种数量: {len(structure_results)}
                            """)
                            
                            # 创建期限结构图表
                            try:
                                if back_results or contango_results:
                                    fig = go.Figure()
                                    
                                    # 添加Back结构品种的图表
                                    for variety, structure, contracts, closes in back_results:
                                        fig.add_trace(go.Scatter(
                                            x=contracts,
                                            y=closes,
                                            mode='lines+markers',
                                            name=f'{variety} (Back)',
                                            line=dict(color='red', width=2),
                                            marker=dict(size=6)
                                        ))
                                    
                                    # 添加Contango结构品种的图表
                                    for variety, structure, contracts, closes in contango_results:
                                        fig.add_trace(go.Scatter(
                                            x=contracts,
                                            y=closes,
                                            mode='lines+markers',
                                            name=f'{variety} (Contango)',
                                            line=dict(color='green', width=2),
                                            marker=dict(size=6)
                                        ))
                                    
                                    fig.update_layout(
                                        title='期限结构分析图',
                                        xaxis_title='合约',
                                        yaxis_title='收盘价',
                                        height=500,
                                        showlegend=True
                                    )
                                    
                                    st.plotly_chart(fig, use_container_width=True)
                            except Exception as e:
                                st.warning(f"生成期限结构图表时出错: {str(e)}")
                        else:
                            st.warning("没有找到可分析的期限结构数据")
                    else:
                        st.warning("无法获取期货行情数据，请检查网络连接或稍后重试")
                        
                except Exception as e:
                    st.error(f"期限结构分析出错: {str(e)}")
                    st.info("请继续查看其他策略分析结果")
            
            # 显示家人席位反向操作策略页面
            with tabs[3]:
                st.header("家人席位反向操作策略")
                retail_long = []
                retail_short = []
                for contract, data in retail_results.items():
                    ratio_value = data.get('retail_ratio', 0)
                    try:
                        ratio_value = float(ratio_value) if ratio_value is not None else 0.0
                    except Exception:
                        ratio_value = 0.0
                    if data['signal'] == '看多':
                        retail_long.append({'contract': contract, 'strength': data['strength'], 'reason': data['reason'], 'seat_details': data['seat_details'], 'raw_df': data['raw_df'], 'retail_ratio': ratio_value})
                    elif data['signal'] == '看空':
                        retail_short.append({'contract': contract, 'strength': data['strength'], 'reason': data['reason'], 'seat_details': data['seat_details'], 'raw_df': data['raw_df'], 'retail_ratio': ratio_value})
                # 调试信息：排序前
                st.write("调试信息 - 排序前看多信号:")
                for item in retail_long[:3]:  # 只显示前3个
                    st.write(f"{item['contract']}: {item['retail_ratio']}")
                # 严格按retail_ratio从大到小排序，确保为float
                retail_long = sorted(retail_long, key=lambda x: float(x.get('retail_ratio', 0)), reverse=True)
                retail_short = sorted(retail_short, key=lambda x: float(x.get('retail_ratio', 0)), reverse=True)
                # 调试信息：排序后
                st.write("调试信息 - 排序后看多信号:")
                for item in retail_long[:3]:  # 只显示前3个
                    st.write(f"{item['contract']}: {item['retail_ratio']}")
                all_strategy_signals['家人席位反向操作策略'] = {
                    'long': retail_long,
                    'short': retail_short
                }
                st.subheader("看多信号")
                if retail_long:
                    for idx, signal in enumerate(retail_long, 1):
                        st.markdown(f"{idx}. **{signal['contract']}**  强度: {signal['strength']:.2f}  占比: {signal['retail_ratio']:.2%}  {signal['reason']}")
                        if signal['seat_details']:
                            st.markdown("家人席位持仓变化：")
                            for seat in signal['seat_details']:
                                st.markdown(f"- {seat['seat_name']}: 多单变化{seat['long_chg']}手, 空单变化{seat['short_chg']}手")
                        st.markdown("席位明细：")
                        st.dataframe(signal['raw_df'])
                else:
                    st.info("无看多信号")
                st.subheader("看空信号")
                if retail_short:
                    for idx, signal in enumerate(retail_short, 1):
                        st.markdown(f"{idx}. **{signal['contract']}**  强度: {signal['strength']:.2f}  占比: {signal['retail_ratio']:.2%}  {signal['reason']}")
                        if signal['seat_details']:
                            st.markdown("家人席位持仓变化：")
                            for seat in signal['seat_details']:
                                st.markdown(f"- {seat['seat_name']}: 多单变化{seat['long_chg']}手, 空单变化{seat['short_chg']}手")
                        st.markdown("席位明细：")
                        st.dataframe(signal['raw_df'])
                else:
                    st.info("无看空信号")
                st.markdown(f"看多信号品种数量：{len(retail_long)}  看空信号品种数量：{len(retail_short)}")
            
            # 显示策略总结页面
            with tabs[4]:
                st.header("策略总结")
                
                # 获取每个策略的前十名品种
                strategy_top_10 = {}
                for strategy_name, signals in all_strategy_signals.items():
                    if strategy_name == '家人席位反向操作策略':
                        long_signals = sorted(signals['long'], key=lambda x: float(x['retail_ratio'] or 0), reverse=True)[:10]
                        short_signals = sorted(signals['short'], key=lambda x: float(x['retail_ratio'] or 0), reverse=True)[:10]
                    else:
                        long_signals = signals['long'][:10]
                        short_signals = signals['short'][:10]
                    long_symbols = set()
                    short_symbols = set()
                    def extract_symbol(contract):
                        try:
                            parts = contract.split('_')
                            if len(parts) > 1:
                                symbol_part = parts[-1]
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
                
                # 找出三策略共同看多/看空品种
                if len(strategy_top_10) >= 3:
                    common_long = set.intersection(*[data['long_symbols'] for data in strategy_top_10.values()])
                    common_short = set.intersection(*[data['short_symbols'] for data in strategy_top_10.values()])
                else:
                    common_long = set()
                    common_short = set()
                
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
            
            if 'structure_results' in locals() and structure_results:
                back_results_txt = [r for r in structure_results if r[1] == "back"]
                contango_results_txt = [r for r in structure_results if r[1] == "contango"]
                flat_results_txt = [r for r in structure_results if r[1] == "flat"]
                
                text_output.write("\nBack结构品种（近强远弱）:\n")
                if back_results_txt:
                    for variety, structure, contracts, closes in back_results_txt:
                        text_output.write(f"\n品种: {variety}\n")
                        text_output.write("合约价格详情:\n")
                        for contract, close in zip(contracts, closes):
                            text_output.write(f"  {contract}: {close:.2f}\n")
                else:
                    text_output.write("无\n")
                
                text_output.write("\nContango结构品种（近弱远强）:\n")
                if contango_results_txt:
                    for variety, structure, contracts, closes in contango_results_txt:
                        text_output.write(f"\n品种: {variety}\n")
                        text_output.write("合约价格详情:\n")
                        for contract, close in zip(contracts, closes):
                            text_output.write(f"  {contract}: {close:.2f}\n")
                else:
                    text_output.write("无\n")
                
                text_output.write("\nFlat结构品种（价格相近）:\n")
                if flat_results_txt:
                    for variety, structure, contracts, closes in flat_results_txt:
                        text_output.write(f"\n品种: {variety}\n")
                        text_output.write("合约价格详情:\n")
                        for contract, close in zip(contracts, closes):
                            text_output.write(f"  {contract}: {close:.2f}\n")
                else:
                    text_output.write("无\n")
                
                text_output.write(f"\n统计信息:\n")
                text_output.write(f"Back结构品种数量: {len(back_results_txt)}\n")
                text_output.write(f"Contango结构品种数量: {len(contango_results_txt)}\n")
                text_output.write(f"Flat结构品种数量: {len(flat_results_txt)}\n")
                text_output.write(f"总品种数量: {len(structure_results)}\n")
            else:
                text_output.write("无期限结构分析数据\n")
            
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
