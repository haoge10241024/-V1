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
import akshare as ak
import concurrent.futures
import time
from functools import partial

# 设置页面配置
st.set_page_config(
    page_title="期货持仓分析系统",
    page_icon="📊",
    layout="wide"
)

# 优化的数据获取函数
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
@st.cache_data(ttl=3600, show_spinner=False)
def get_analysis_results_optimized(trade_date, max_workers=3, timeout=60):
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
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_exchange = {
                executor.submit(fetch_single_exchange_data, exchange, trade_date): exchange 
                for exchange in exchanges
            }
            
            # 处理完成的任务
            for i, future in enumerate(concurrent.futures.as_completed(future_to_exchange, timeout=timeout)):
                exchange = future_to_exchange[future]
                try:
                    data, error = future.result()
                    if data and not error:
                        # 使用实际的分析器处理数据
                        analyzer = FuturesPositionAnalyzer("data")
                        for contract_name, df in data.items():
                            processed_data = analyzer.process_position_data(df)
                            if processed_data:
                                # 对每个策略进行分析
                                strategy_results = {}
                                for strategy in analyzer.strategies:
                                    signal, reason, strength = strategy.analyze(processed_data)
                                    strategy_results[strategy.name] = {
                                        'signal': signal,
                                        'reason': reason,
                                        'strength': strength
                                    }
                                results[f"{exchange['name']}_{contract_name}"] = {
                                    'strategies': strategy_results,
                                    'raw_data': processed_data['raw_data']
                                }
                        successful_exchanges += 1
                    else:
                        st.warning(f"{exchange['name']}: {error}")
                except Exception as e:
                    st.warning(f"处理{exchange['name']}数据时出错: {str(e)}")
                
                # 更新进度
                progress = 10 + (i + 1) * 80 // len(exchanges)
                progress_bar.progress(progress)
                status_text.text(f"已处理 {i + 1}/{len(exchanges)} 个交易所...")
        
        progress_bar.progress(100)
        if successful_exchanges == 0:
            status_text.text("❌ 未能获取到任何数据")
            return None
        else:
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

# 原有的缓存函数作为备用
@st.cache_data(ttl=3600)
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
def fetch_single_exchange_price_data(exchange, date_str):
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

@st.cache_data(ttl=1800, show_spinner=False)
def get_futures_price_data_optimized(date_str, max_workers=3):
    """获取期货行情数据，支持并行处理"""
    
    # 创建进度指示器
    price_progress = st.progress(0)
    price_status = st.empty()
    
    try:
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
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
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
        required_columns = ['symbol', 'close', 'variety']
        if not all(col in df.columns for col in required_columns):
            return []
            
        results = []
        for variety in df['variety'].unique():
            variety_data = df[df['variety'] == variety].copy()
            variety_data = variety_data.sort_values('symbol')
            variety_data = variety_data[
                (variety_data['close'] > 0) & 
                (variety_data['close'].notna())
            ]
            
            contracts = variety_data['symbol'].tolist()
            closes = variety_data['close'].tolist()
            
            if len(contracts) < 2:
                continue
                
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

def analyze_retail_reverse_strategy(df):
    """分析家人席位反向操作策略"""
    retail_seats = ["东方财富", "平安期货", "徽商期货"]
    
    try:
        seat_stats = {name: {'long_chg': 0, 'short_chg': 0, 'long_pos': 0, 'short_pos': 0} for name in retail_seats}
        
        for _, row in df.iterrows():
            if row['long_party_name'] in retail_seats:
                seat_stats[row['long_party_name']]['long_chg'] += row['long_open_interest_chg'] if pd.notna(row['long_open_interest_chg']) else 0
                seat_stats[row['long_party_name']]['long_pos'] += row['long_open_interest'] if pd.notna(row['long_open_interest']) else 0
            if row['short_party_name'] in retail_seats:
                seat_stats[row['short_party_name']]['short_chg'] += row['short_open_interest_chg'] if pd.notna(row['short_open_interest_chg']) else 0
                seat_stats[row['short_party_name']]['short_pos'] += row['short_open_interest'] if pd.notna(row['short_open_interest']) else 0

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

        total_long_chg = sum([seat['long_chg'] for seat in seat_details])
        total_short_chg = sum([seat['short_chg'] for seat in seat_details])
        total_long_pos = sum([seat['long_pos'] for seat in seat_details])
        total_short_pos = sum([seat['short_pos'] for seat in seat_details])
        
        df_total_long = df['long_open_interest'].sum()
        df_total_short = df['short_open_interest'].sum()

        if total_long_chg > 0 and total_short_chg <= 0:
            retail_ratio = total_long_pos / df_total_long if df_total_long > 0 else 0
            return "看空", f"家人席位多单增加{total_long_chg}手，持仓占比{retail_ratio:.2%}", retail_ratio, seat_details
        elif total_short_chg > 0 and total_long_chg <= 0:
            retail_ratio = total_short_pos / df_total_short if df_total_short > 0 else 0
            return "看多", f"家人席位空单增加{total_short_chg}手，持仓占比{retail_ratio:.2%}", retail_ratio, seat_details
        else:
            return "中性", "家人席位持仓变化不符合策略要求", 0, seat_details
            
    except Exception as e:
        return "错误", f"数据处理错误：{str(e)}", 0, []

def main():
    st.title("期货持仓分析系统 - 优化版")
    
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
            st.rerun()
        if st.button("上周五"):
            days_back = (today.weekday() + 3) % 7
            if days_back == 0:
                days_back = 7
            trade_date = today - timedelta(days=days_back)
            st.rerun()
    
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
            results = get_analysis_results_optimized(trade_date_str, max_workers, timeout_seconds)
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
                for contract in list(results.keys())[:10]:
                    st.write(f"- {contract}")
                if len(results) > 10:
                    st.write(f"... 还有 {len(results) - 10} 个合约")
        
        # 生成图表
        charts = generate_charts(results)
        
        # 创建策略分析标签页
        tabs = st.tabs(["多空力量变化策略", "蜘蛛网策略", "家人席位反向操作策略", "期限结构分析", "策略总结"])
        all_strategy_signals = {}
        
        # 多空力量变化策略
        with tabs[0]:
            st.header("多空力量变化策略")
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
        
        # 期限结构分析
        with tabs[3]:
            st.header("期限结构分析")
            
            st.info("""
            **策略原理：**
            期限结构分析通过比较同一品种不同交割月份合约的价格关系，判断市场对该品种未来供需的预期。
            Back结构（近强远弱）：近月合约价格高于远月，通常表明当前供应紧张，可能看多现货、看空远期；
            Contango结构（近弱远强）：远月合约价格高于近月，通常表明当前供应充足但预期未来需求增长，可能看空现货、看多远期。
            """)
            
            if not include_term_structure:
                st.warning("⚠️ 期限结构分析已在设置中关闭。如需启用，请在侧边栏中勾选'包含期限结构分析'。")
            else:
                try:
                    price_data = get_futures_price_data_optimized(trade_date_str, max_workers)
                    
                    if not price_data.empty:
                        structure_results = analyze_term_structure_with_prices(price_data)
                        
                        if structure_results:
                            back_results = [r for r in structure_results if r[1] == "back"]
                            contango_results = [r for r in structure_results if r[1] == "contango"]
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.subheader("Back结构（近强远弱）")
                                if back_results:
                                    for variety, structure, contracts, closes in back_results:
                                        st.markdown(f"**{variety}**")
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
                                else:
                                    st.info("无Back结构品种")
                            
                            with col2:
                                st.subheader("Contango结构（近弱远强）")
                                if contango_results:
                                    for variety, structure, contracts, closes in contango_results:
                                        st.markdown(f"**{variety}**")
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
                                else:
                                    st.info("无Contango结构品种")
                            
                            st.markdown("---")
                            st.markdown(f"""
                            ### 统计信息
                            - Back结构品种数量: {len(back_results)}
                            - Contango结构品种数量: {len(contango_results)}
                            - 总品种数量: {len(structure_results)}
                            """)
                        else:
                            st.warning("没有找到可分析的期限结构数据")
                    else:
                        st.warning("无法获取期货行情数据，请检查网络连接或稍后重试")
                        
                except Exception as e:
                    st.error(f"期限结构分析出错: {str(e)}")

if __name__ == "__main__":
    main() 
