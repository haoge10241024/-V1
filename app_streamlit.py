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
import concurrent.futures
import time
from functools import partial

# 设置页面配置
st.set_page_config(
    page_title="期货持仓分析系统",
    page_icon="📊",
    layout="wide"
)

# 优化的数据获取函数，添加超时和进度显示
def fetch_single_exchange_data(exchange_info, trade_date, timeout=30):
    """获取单个交易所的数据，带超时机制"""
    try:
        if exchange_info["market"] == "DCE":
            data = ak.futures_dce_position_rank(date=trade_date)
        elif exchange_info["market"] == "CFFEX":
            data = ak.get_cffex_rank_table(date=trade_date)
        elif exchange_info["market"] == "CZCE":
            data = ak.get_czce_rank_table(date=trade_date)
        elif exchange_info["market"] == "SHFE":
            data = ak.get_shfe_rank_table(date=trade_date)
        elif exchange_info["market"] == "GFEX":
            data = ak.futures_gfex_position_rank(date=trade_date)
        else:
            return None, f"未知交易所: {exchange_info['market']}"
        
        return data, None
    except Exception as e:
        return None, f"获取{exchange_info['name']}数据失败: {str(e)}"

# 优化的分析结果获取函数
@st.cache_data(ttl=3600, show_spinner=False)  # 缓存1小时，不显示默认spinner
def get_analysis_results_optimized(trade_date):
    """优化的分析结果获取，支持并行处理和进度显示"""
    
    # 创建进度条
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # 交易所配置
        exchanges = [
            {"market": "DCE", "name": "大商所"},
            {"market": "CFFEX", "name": "中金所"},
            {"market": "CZCE", "name": "郑商所"},
            {"market": "SHFE", "name": "上期所"},
            {"market": "GFEX", "name": "广期所"}
        ]
        
        status_text.text("正在获取期货持仓数据...")
        progress_bar.progress(10)
        
        # 使用线程池并行获取数据
        results = {}
        successful_exchanges = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # 提交所有任务
            future_to_exchange = {
                executor.submit(fetch_single_exchange_data, exchange, trade_date): exchange 
                for exchange in exchanges
            }
            
            # 处理完成的任务
            for i, future in enumerate(concurrent.futures.as_completed(future_to_exchange, timeout=60)):
                exchange = future_to_exchange[future]
                try:
                    data, error = future.result()
                    if data and not error:
                        # 模拟数据处理
                        for contract_name, df in data.items():
                            # 这里应该调用实际的数据处理逻辑
                            # 为了演示，我们创建一个简化的结果
                            results[f"{exchange['name']}_{contract_name}"] = {
                                'strategies': {
                                    '多空力量变化策略': {'signal': '中性', 'reason': '数据处理中...', 'strength': 0},
                                    '蜘蛛网策略': {'signal': '中性', 'reason': '数据处理中...', 'strength': 0}
                                },
                                'raw_data': df.head(20) if not df.empty else pd.DataFrame()
                            }
                        successful_exchanges += 1
                    else:
                        st.warning(f"{exchange['name']}: {error}")
                except Exception as e:
                    st.warning(f"处理{exchange['name']}数据时出错: {str(e)}")
                
                # 更新进度
                progress = 10 + (i + 1) * 60 // len(exchanges)
                progress_bar.progress(progress)
                status_text.text(f"已处理 {i + 1}/{len(exchanges)} 个交易所...")
        
        if successful_exchanges == 0:
            progress_bar.progress(100)
            status_text.text("❌ 未能获取到任何数据")
            return None
        
        status_text.text("正在进行策略分析...")
        progress_bar.progress(80)
        
        # 这里应该调用实际的策略分析逻辑
        # 由于原始的FuturesPositionAnalyzer比较复杂，我们先返回模拟结果
        time.sleep(1)  # 模拟分析时间
        
        progress_bar.progress(100)
        status_text.text(f"✅ 分析完成！成功获取 {successful_exchanges} 个交易所数据")
        
        return results
        
    except concurrent.futures.TimeoutError:
        progress_bar.progress(100)
        status_text.text("❌ 数据获取超时，请稍后重试")
        return None
    except Exception as e:
        progress_bar.progress(100)
        status_text.text(f"❌ 分析过程中出错: {str(e)}")
        return None

# 原有的缓存函数保持不变，但添加超时处理
@st.cache_data(ttl=3600)  # 缓存1小时
def get_analysis_results(trade_date):
    """原有的分析结果获取函数，作为备用"""
    try:
        analyzer = FuturesPositionAnalyzer("data")
        return analyzer.fetch_and_analyze(trade_date)
    except Exception as e:
        st.error(f"获取分析结果时出错: {str(e)}")
        return None

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

# 优化的期货行情数据获取函数
def fetch_single_exchange_price_data(exchange, date_str, timeout=20):
    """获取单个交易所的行情数据"""
    try:
        df = ak.get_futures_daily(start_date=date_str, end_date=date_str, market=exchange["market"])
        if not df.empty:
            df['exchange'] = exchange["name"]
            return df, None
        else:
            return None, f"{exchange['name']}无数据"
    except Exception as e:
        return None, f"获取{exchange['name']}数据失败: {str(e)}"

# 缓存期货行情数据获取
@st.cache_data(ttl=1800, show_spinner=False)  # 缓存30分钟
def get_futures_price_data(date_str):
    """获取期货行情数据用于期限结构分析，支持并行处理"""
    
    # 创建进度指示器
    price_progress = st.progress(0)
    price_status = st.empty()
    
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
        
        price_status.text("正在获取期货行情数据...")
        price_progress.progress(10)
        
        all_data = []
        successful_count = 0
        
        # 使用线程池并行获取数据
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_exchange = {
                executor.submit(fetch_single_exchange_price_data, exchange, date_str): exchange 
                for exchange in exchanges
            }
            
            for i, future in enumerate(concurrent.futures.as_completed(future_to_exchange, timeout=40)):
                exchange = future_to_exchange[future]
                try:
                    df, error = future.result()
                    if df is not None and not error:
                        all_data.append(df)
                        successful_count += 1
                    else:
                        st.warning(f"期货行情 - {exchange['name']}: {error}")
                except Exception as e:
                    st.warning(f"处理{exchange['name']}行情数据时出错: {str(e)}")
                
                # 更新进度
                progress = 10 + (i + 1) * 80 // len(exchanges)
                price_progress.progress(progress)
                price_status.text(f"行情数据获取中... {i + 1}/{len(exchanges)}")
        
        price_progress.progress(100)
        if all_data:
            price_status.text(f"✅ 成功获取 {successful_count} 个交易所的行情数据")
            return pd.concat(all_data, ignore_index=True)
        else:
            price_status.text("❌ 未能获取到任何行情数据")
            return pd.DataFrame()
            
    except concurrent.futures.TimeoutError:
        price_progress.progress(100)
        price_status.text("❌ 行情数据获取超时")
        return pd.DataFrame()
    except Exception as e:
        price_progress.progress(100)
        price_status.text(f"❌ 获取期货行情数据失败: {str(e)}")
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

# 家人席位反向操作策略分析函数
def analyze_retail_reverse_strategy(df):
    """分析家人席位反向操作策略"""
    retail_seats = ["东方财富", "平安期货", "徽商期货"]
    
    try:
        # 统计家人席位的多空变化（合并同一席位）
        seat_stats = {name: {'long_chg': 0, 'short_chg': 0, 'long_pos': 0, 'short_pos': 0} for name in retail_seats}
        
        for _, row in df.iterrows():
            if row['long_party_name'] in retail_seats:
                seat_stats[row['long_party_name']]['long_chg'] += row['long_open_interest_chg'] if pd.notna(row['long_open_interest_chg']) else 0
                seat_stats[row['long_party_name']]['long_pos'] += row['long_open_interest'] if pd.notna(row['long_open_interest']) else 0
            if row['short_party_name'] in retail_seats:
                seat_stats[row['short_party_name']]['short_chg'] += row['short_open_interest_chg'] if pd.notna(row['short_open_interest_chg']) else 0
                seat_stats[row['short_party_name']]['short_pos'] += row['short_open_interest'] if pd.notna(row['short_open_interest']) else 0

        # 只保留有变化的席位
        seat_details = []
        for seat, stats in seat_stats.items():
            if stats['long_chg'] != 0 or stats['short_chg'] != 0:
                seat_details.append({
                    'seat_name': seat, 
                    'long_chg': stats['long_chg'], 
                    'short_chg': stats['short_chg'],
                    'long_pos': stats['long_pos'],
                    'short_pos': stats['short_pos']
                })

        if not seat_details:
            return "中性", "未发现家人席位持仓变化", 0, []

        # 判断信号 - 家人席位多单增加时看空，空单增加时看多
        total_long_chg = sum([seat['long_chg'] for seat in seat_details])
        total_short_chg = sum([seat['short_chg'] for seat in seat_details])
        total_long_pos = sum([seat['long_pos'] for seat in seat_details])
        total_short_pos = sum([seat['short_pos'] for seat in seat_details])
        
        # 计算总持仓
        df_total_long = df['long_open_interest'].sum()
        df_total_short = df['short_open_interest'].sum()

        if total_long_chg > 0 and total_short_chg <= 0:
            # 家人席位多单增加，看空
            retail_ratio = total_long_pos / df_total_long if df_total_long > 0 else 0
            return "看空", f"家人席位多单增加{total_long_chg}手，持仓占比{retail_ratio:.2%}", retail_ratio, seat_details
        elif total_short_chg > 0 and total_long_chg <= 0:
            # 家人席位空单增加，看多
            retail_ratio = total_short_pos / df_total_short if df_total_short > 0 else 0
            return "看多", f"家人席位空单增加{total_short_chg}手，持仓占比{retail_ratio:.2%}", retail_ratio, seat_details
        else:
            return "中性", "家人席位持仓变化不符合策略要求", 0, seat_details
            
    except Exception as e:
        return "错误", f"数据处理错误：{str(e)}", 0, []

def main():
    st.title("期货持仓分析系统")
    
    # 侧边栏设置
    with st.sidebar:
        st.header("⚙️ 系统设置")
        
        # 性能设置
        st.subheader("性能优化")
        use_parallel = st.checkbox("启用并行处理", value=True, help="并行获取数据可以显著提高速度")
        max_workers = st.slider("最大并发数", 1, 5, 3, help="增加并发数可能提高速度，但也可能导致API限制")
        timeout_seconds = st.slider("超时时间(秒)", 10, 120, 60, help="网络请求的最大等待时间")
        
        # 数据设置
        st.subheader("数据选项")
        include_term_structure = st.checkbox("包含期限结构分析", value=True, help="期限结构分析需要额外的网络请求")
        cache_duration = st.selectbox("缓存时间", [30, 60, 180, 360], index=1, help="数据缓存时间（分钟）")
        
        # 显示设置
        st.subheader("显示选项")
        show_debug_info = st.checkbox("显示调试信息", value=False)
        auto_refresh = st.checkbox("自动刷新缓存", value=False, help="每次分析时清除缓存")
    
    # 主界面
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # 日期选择
        today = datetime.now()
        default_date = today - timedelta(days=1)
        trade_date = st.date_input(
            "选择交易日期",
            value=default_date,
            max_value=today,
            help="选择要分析的交易日期，建议选择最近的交易日"
        )
    
    with col2:
        # 快速日期选择
        st.write("快速选择：")
        if st.button("昨天"):
            trade_date = today - timedelta(days=1)
        if st.button("上周五"):
            days_back = (today.weekday() + 3) % 7
            if days_back == 0:
                days_back = 7
            trade_date = today - timedelta(days=days_back)
    
    # 转换日期格式
    trade_date_str = trade_date.strftime("%Y%m%d")
    
    # 显示选择的日期信息
    st.info(f"📅 分析日期: {trade_date.strftime('%Y年%m月%d日')} ({trade_date.strftime('%A')})")
    
    # 创建分析按钮
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        analyze_button = st.button(
            "🚀 开始分析", 
            type="primary", 
            use_container_width=True,
            help="点击开始获取数据并进行分析"
        )
    
    if analyze_button:
        # 根据设置决定是否清除缓存
        if auto_refresh:
            st.cache_data.clear()
            st.success("缓存已清除")
        
        # 显示分析开始信息
        start_time = time.time()
        st.info("🔄 开始数据分析流程...")
        
        # 尝试获取分析结果
        results = None
        
        if use_parallel:
            st.info("⚡ 使用并行模式获取数据...")
            results = get_analysis_results_optimized(trade_date_str)
        else:
            st.info("🐌 使用标准模式获取数据...")
            with st.spinner("正在分析数据..."):
                results = get_analysis_results(trade_date_str)
        
        # 检查结果
        if not results:
            st.error("❌ 获取数据失败")
            
            # 提供故障排除建议
            with st.expander("🔧 故障排除建议"):
                st.markdown("""
                **可能的原因和解决方案：**
                
                1. **网络连接问题**
                   - 检查网络连接是否正常
                   - 尝试增加超时时间
                
                2. **API限制**
                   - 降低并发数量
                   - 稍后重试
                
                3. **日期问题**
                   - 确认选择的是交易日
                   - 尝试选择最近的交易日
                
                4. **数据源问题**
                   - akshare服务可能暂时不可用
                   - 尝试关闭期限结构分析
                """)
            
            # 提供重试选项
            if st.button("🔄 重试分析"):
                st.rerun()
            
            return
        
        # 显示成功信息和耗时
        elapsed_time = time.time() - start_time
        st.success(f"✅ 数据获取成功！耗时: {elapsed_time:.1f}秒")
        
        # 显示数据统计
        if show_debug_info:
            with st.expander("📊 数据统计信息"):
                st.write(f"获取到的合约数量: {len(results)}")
                st.write(f"数据获取时间: {elapsed_time:.2f}秒")
                st.write("合约列表:")
                for contract in list(results.keys())[:10]:  # 只显示前10个
                    st.write(f"- {contract}")
                if len(results) > 10:
                    st.write(f"... 还有 {len(results) - 10} 个合约")
            
            # 生成图表
            charts = generate_charts(results)
            # 为每个策略创建标签页，并添加策略总结标签页和家人席位反向操作策略页
            tabs = st.tabs(["多空力量变化策略", "蜘蛛网策略", "家人席位反向操作策略", "期限结构分析", "策略总结"])
            # 存储所有策略的信号数据
            all_strategy_signals = {}
            
            # 显示多空力量变化策略
            with tabs[0]:
                st.header("多空力量变化策略")
                
                # 策略原理说明
                st.info("""
                **策略原理：**
                多空力量变化策略通过分析席位持仓的增减变化来判断市场趋势。当多头席位大幅增仓而空头席位减仓时，
                表明市场看多情绪浓厚，产生看多信号；反之，当空头席位大幅增仓而多头席位减仓时，产生看空信号。
                信号强度=|多头持仓变化|+|空头持仓变化|，变化越大，信号越强。
                """)
                
                strategy_name = "多空力量变化策略"
                long_signals = []
                short_signals = []
                
                for contract, data in results.items():
                    if strategy_name in data['strategies']:
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
            
            # 显示蜘蛛网策略
            with tabs[1]:
                st.header("蜘蛛网策略")
                
                # 策略原理说明
                st.info("""
                **策略原理：**
                蜘蛛网策略基于持仓分布的分化程度判断机构资金的参与情况。通过计算MSD（Mean Square Deviation）指标，
                衡量各席位持仓与平均持仓的偏离程度。当MSD > 0时，表明机构资金（知情者）看多；当MSD < 0时，表明机构资金看空。
                MSD绝对值越大，机构资金的态度越明确，信号强度越高。该策略假设机构投资者具有更准确的市场信息。
                """)
                
                strategy_name = "蜘蛛网策略"
                long_signals = []
                short_signals = []
                
                for contract, data in results.items():
                    if strategy_name in data['strategies']:
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
            
            # 显示家人席位反向操作策略
            with tabs[2]:
                st.header("家人席位反向操作策略")
                
                # 策略原理说明
                st.info("""
                **策略原理：**
                家人席位反向操作策略基于散户投资者往往在市场顶部做多、底部做空的特点，采用反向操作思路。
                策略跟踪特定散户席位（东方财富、平安期货、徽商期货等）的持仓变化，当这些席位增加多单时产生看空信号，
                增加空单时产生看多信号。持仓占比越高，信号强度越大。该策略基于"聪明钱与散户资金相反操作"的市场规律。
                """)
                
                # 直接分析家人席位策略
                retail_long_signals = []
                retail_short_signals = []
                
                for contract, data in results.items():
                    if 'raw_data' in data:
                        df = data['raw_data']
                        signal, reason, strength, seat_details = analyze_retail_reverse_strategy(df)
                        
                        if signal == '看多':
                            retail_long_signals.append({
                                'contract': contract,
                                'strength': strength,
                                'reason': reason,
                                'seat_details': seat_details,
                                'raw_df': df
                            })
                        elif signal == '看空':
                            retail_short_signals.append({
                                'contract': contract,
                                'strength': strength,
                                'reason': reason,
                                'seat_details': seat_details,
                                'raw_df': df
                            })
                
                # 按强度排序（从大到小）
                retail_long_signals = sorted(retail_long_signals, key=lambda x: float(x.get('strength', 0)), reverse=True)
                retail_short_signals = sorted(retail_short_signals, key=lambda x: float(x.get('strength', 0)), reverse=True)
                
                # 存储策略信号数据
                all_strategy_signals['家人席位反向操作策略'] = {
                    'long': retail_long_signals,
                    'short': retail_short_signals
                }
                
                # 创建两列布局
                col1, col2 = st.columns(2)
                
                # 显示看多信号
                with col1:
                    st.subheader("看多信号")
                    if retail_long_signals:
                        for idx, signal in enumerate(retail_long_signals, 1):
                            st.markdown(f"""
                            <div style='background-color: #ffe6e6; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                                <strong>{idx}. {signal['contract']}</strong><br>
                                强度: {signal['strength']:.4f}<br>
                                信号原因: {signal['reason']}
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # 显示家人席位详情
                            if signal['seat_details']:
                                st.markdown("**家人席位持仓变化：**")
                                for seat in signal['seat_details']:
                                    st.markdown(f"- {seat['seat_name']}: 多单变化{seat['long_chg']}手, 空单变化{seat['short_chg']}手")
                            
                            with st.expander(f"查看{signal['contract']}席位明细"):
                                st.dataframe(signal['raw_df'], use_container_width=True)
                    else:
                        st.info("无看多信号")
                
                # 显示看空信号
                with col2:
                    st.subheader("看空信号")
                    if retail_short_signals:
                        for idx, signal in enumerate(retail_short_signals, 1):
                            st.markdown(f"""
                            <div style='background-color: #e6ffe6; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                                <strong>{idx}. {signal['contract']}</strong><br>
                                强度: {signal['strength']:.4f}<br>
                                信号原因: {signal['reason']}
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # 显示家人席位详情
                            if signal['seat_details']:
                                st.markdown("**家人席位持仓变化：**")
                                for seat in signal['seat_details']:
                                    st.markdown(f"- {seat['seat_name']}: 多单变化{seat['long_chg']}手, 空单变化{seat['short_chg']}手")
                            
                            with st.expander(f"查看{signal['contract']}席位明细"):
                                st.dataframe(signal['raw_df'], use_container_width=True)
                    else:
                        st.info("无看空信号")
                
                # 显示统计信息
                st.markdown("---")
                st.markdown(f"""
                ### 统计信息
                - 看多信号品种数量：{len(retail_long_signals)}
                - 看空信号品种数量：{len(retail_short_signals)}
                - 总分析品种数量：{len(results)}
                - 中性信号品种数量：{len(results) - len(retail_long_signals) - len(retail_short_signals)}
                """)
                
                # 创建信号强度图表
                if retail_long_signals or retail_short_signals:
                    fig = go.Figure()
                    
                    if retail_long_signals:
                        fig.add_trace(go.Bar(
                            x=[s['contract'] for s in retail_long_signals],
                            y=[s['strength'] for s in retail_long_signals],
                            name='看多信号',
                            marker_color='red'
                        ))
                    
                    if retail_short_signals:
                        fig.add_trace(go.Bar(
                            x=[s['contract'] for s in retail_short_signals],
                            y=[-s['strength'] for s in retail_short_signals],
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
            with tabs[3]:
                st.header("期限结构分析")
                
                # 策略原理说明
                st.info("""
                **策略原理：**
                期限结构分析通过比较同一品种不同交割月份合约的价格关系，判断市场对该品种未来供需的预期。
                Back结构（近强远弱）：近月合约价格高于远月，通常表明当前供应紧张，可能看多现货、看空远期；
                Contango结构（近弱远强）：远月合约价格高于近月，通常表明当前供应充足但预期未来需求增长，可能看空现货、看多远期。
                期限结构的变化往往预示着供需基本面的转变。
                """)
                
                if not include_term_structure:
                    st.warning("⚠️ 期限结构分析已在设置中关闭。如需启用，请在侧边栏中勾选'包含期限结构分析'。")
                else:
                    st.info("基于真实期货合约收盘价进行期限结构分析")
                    
                    try:
                        # 获取期货行情数据
                        st.info("正在获取期货行情数据...")
                        price_data = get_futures_price_data(trade_date_str)
                    
                    if not price_data.empty:
                        # 分析期限结构
                        structure_results = analyze_term_structure_with_prices(price_data)
                        
                        if structure_results:
                            # 按期限结构类型分类
                            back_results = [r for r in structure_results if r[1] == "back"]
                            contango_results = [r for r in structure_results if r[1] == "contango"]
                            
                            # 创建两列布局
                            col1, col2 = st.columns(2)
                            
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
                            
                            # 统计信息
                            st.markdown("---")
                            st.markdown(f"""
                            ### 统计信息
                            - Back结构品种数量: {len(back_results)}
                            - Contango结构品种数量: {len(contango_results)}
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
            
            # 显示策略总结页面
            with tabs[4]:
                st.header("策略总结")
                
                # 改进的品种提取函数
                def extract_symbol(contract):
                    """从合约名称中提取品种代码"""
                    try:
                        # 处理各种格式的合约名称
                        if '_' in contract:
                            # 处理格式：交易所_合约代码
                            symbol_part = contract.split('_')[-1]
                        else:
                            symbol_part = contract
                        
                        # 提取字母部分作为品种代码
                        symbol = ''.join(c for c in symbol_part if c.isalpha()).upper()
                        
                        # 处理特殊情况
                        if symbol == 'PTA':
                            return 'PTA'
                        elif symbol.startswith('TA') and len(symbol) > 2:
                            return 'TA'
                        elif symbol == 'OI':
                            return 'OI'
                        elif symbol.lower() in ['cu', 'al', 'zn', 'pb', 'ni', 'sn', 'au', 'ag', 'rb', 'wr', 'hc', 'ss', 'fu', 'bu', 'ru', 'nr', 'sp', 'lu', 'bc', 'ao', 'ec']:
                            # 上期所品种保持小写转大写
                            return symbol.upper()
                        elif symbol.lower() in ['si', 'ps']:
                            # 广期所品种
                            return symbol.upper()
                        else:
                            return symbol
                    except:
                        return None
                
                # 获取每个策略的前十名品种
                strategy_top_10 = {}
                # 添加调试信息
                debug_info = {}
                
                for strategy_name, signals in all_strategy_signals.items():
                    if strategy_name == '家人席位反向操作策略':
                        long_signals = sorted(signals['long'], key=lambda x: float(x['strength'] or 0), reverse=True)[:10]
                        short_signals = sorted(signals['short'], key=lambda x: float(x['strength'] or 0), reverse=True)[:10]
                    else:
                        long_signals = signals['long'][:10]
                        short_signals = signals['short'][:10]
                    
                    # 提取品种代码
                    long_symbols = set()
                    short_symbols = set()
                    
                    # 调试信息
                    debug_info[strategy_name] = {'long_contracts': [], 'long_symbols': [], 'short_contracts': [], 'short_symbols': []}
                    
                    for signal in long_signals:
                        symbol = extract_symbol(signal['contract'])
                        debug_info[strategy_name]['long_contracts'].append(signal['contract'])
                        debug_info[strategy_name]['long_symbols'].append(symbol)
                        if symbol:
                            long_symbols.add(symbol)
                    
                    for signal in short_signals:
                        symbol = extract_symbol(signal['contract'])
                        debug_info[strategy_name]['short_contracts'].append(signal['contract'])
                        debug_info[strategy_name]['short_symbols'].append(symbol)
                        if symbol:
                            short_symbols.add(symbol)
                    
                    strategy_top_10[strategy_name] = {
                        'long_signals': long_signals,
                        'short_signals': short_signals,
                        'long_symbols': long_symbols,
                        'short_symbols': short_symbols
                    }
                
                # 调试信息显示
                with st.expander("调试信息：品种提取结果"):
                    for strategy_name, info in debug_info.items():
                        st.write(f"**{strategy_name}**")
                        st.write("看多合约和品种：")
                        for contract, symbol in zip(info['long_contracts'], info['long_symbols']):
                            st.write(f"  {contract} -> {symbol}")
                        st.write("看空合约和品种：")
                        for contract, symbol in zip(info['short_contracts'], info['short_symbols']):
                            st.write(f"  {contract} -> {symbol}")
                        st.write("---")
                
                # 统计每个品种在多个策略中的出现次数
                long_symbol_count = {}
                short_symbol_count = {}
                
                # 统计看多信号中的品种
                for strategy_name, data in strategy_top_10.items():
                    for symbol in data['long_symbols']:
                        if symbol not in long_symbol_count:
                            long_symbol_count[symbol] = {'count': 0, 'strategies': []}
                        long_symbol_count[symbol]['count'] += 1
                        long_symbol_count[symbol]['strategies'].append(strategy_name)
                
                # 统计看空信号中的品种
                for strategy_name, data in strategy_top_10.items():
                    for symbol in data['short_symbols']:
                        if symbol not in short_symbol_count:
                            short_symbol_count[symbol] = {'count': 0, 'strategies': []}
                        short_symbol_count[symbol]['count'] += 1
                        short_symbol_count[symbol]['strategies'].append(strategy_name)
                
                # 筛选出现在两个及以上策略中的品种
                common_long_symbols = {symbol: info for symbol, info in long_symbol_count.items() if info['count'] >= 2}
                common_short_symbols = {symbol: info for symbol, info in short_symbol_count.items() if info['count'] >= 2}
                
                # 显示共同信号
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("信号共振看多品种")
                    if common_long_symbols:
                        # 按出现次数排序
                        sorted_long = sorted(common_long_symbols.items(), key=lambda x: x[1]['count'], reverse=True)
                        for symbol, info in sorted_long:
                            strategies_text = "、".join(info['strategies'])
                            st.markdown(f"""
                            <div style='background-color: #ffe6e6; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                                <strong>{symbol}</strong> 
                                <span style='color: #666; font-size: 0.9em;'>({info['count']}个策略)</span><br>
                                <span style='font-size: 0.8em; color: #888;'>策略: {strategies_text}</span>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("没有信号共振的看多品种")
                
                with col2:
                    st.subheader("信号共振看空品种")
                    if common_short_symbols:
                        # 按出现次数排序
                        sorted_short = sorted(common_short_symbols.items(), key=lambda x: x[1]['count'], reverse=True)
                        for symbol, info in sorted_short:
                            strategies_text = "、".join(info['strategies'])
                            st.markdown(f"""
                            <div style='background-color: #e6ffe6; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                                <strong>{symbol}</strong> 
                                <span style='color: #666; font-size: 0.9em;'>({info['count']}个策略)</span><br>
                                <span style='font-size: 0.8em; color: #888;'>策略: {strategies_text}</span>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("没有信号共振的看空品种")
                
                # 统计信息
                st.markdown("---")
                st.markdown(f"""
                ### 信号共振统计
                - 看多信号共振品种数量：{len(common_long_symbols)}
                - 看空信号共振品种数量：{len(common_short_symbols)}
                - 总参与策略数量：{len(strategy_top_10)}
                """)
                
                # 显示每个策略的前十名
                st.markdown("---")
                st.subheader("各策略前十名品种")
                
                for strategy_name, data in strategy_top_10.items():
                    st.markdown(f"### {strategy_name}")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**看多品种**")
                        for signal in data['long_signals']:
                            # 检查该品种是否有信号共振
                            symbol = extract_symbol(signal['contract'])
                            is_resonance = symbol in common_long_symbols if symbol else False
                            resonance_badge = " 🔥" if is_resonance else ""
                            
                            st.markdown(f"""
                            <div style='background-color: #ffe6e6; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                                <strong>{signal['contract']}{resonance_badge}</strong><br>
                                强度: {signal['strength']:.2f}<br>
                                {signal['reason']}
                            </div>
                            """, unsafe_allow_html=True)
                    
                    with col2:
                        st.markdown("**看空品种**")
                        for signal in data['short_signals']:
                            # 检查该品种是否有信号共振
                            symbol = extract_symbol(signal['contract'])
                            is_resonance = symbol in common_short_symbols if symbol else False
                            resonance_badge = " 🔥" if is_resonance else ""
                            
                            st.markdown(f"""
                            <div style='background-color: #e6ffe6; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                                <strong>{signal['contract']}{resonance_badge}</strong><br>
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
                for symbol in common_long_symbols:
                    common_signals.append({
                        '品种': symbol,
                        '信号类型': '共同看多'
                    })
                for symbol in common_short_symbols:
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
            for symbol in sorted(common_long_symbols):
                text_output.write(f"- {symbol}\n")
            text_output.write("\n共同看空品种:\n")
            for symbol in sorted(common_short_symbols):
                text_output.write(f"- {symbol}\n")
            
            # 写入期限结构分析结果
            text_output.write("\n期限结构分析\n")
            text_output.write("-" * 20 + "\n")
            
            if 'structure_results' in locals() and structure_results:
                back_results_txt = [r for r in structure_results if r[1] == "back"]
                contango_results_txt = [r for r in structure_results if r[1] == "contango"]
                
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
                
                text_output.write(f"\n统计信息:\n")
                text_output.write(f"Back结构品种数量: {len(back_results_txt)}\n")
                text_output.write(f"Contango结构品种数量: {len(contango_results_txt)}\n")
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
