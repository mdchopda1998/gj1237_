import streamlit as st
from datetime import date,timedelta
from data_access import get_strategy_results
st.set_page_config(page_title='SMC Trading Dashboard',page_icon='📊',layout='wide')
st.markdown('<style>.block-container{padding-top:1rem}[data-testid="stSidebar"]{min-width:260px;max-width:280px}</style>',unsafe_allow_html=True)
WL={'SAIL.NS':'SAIL','RECLTD.NS':'RECLTD','JIOFIN.NS':'JIOFIN','^NSEI':'NIFTY 50','RELIANCE.NS':'RELIANCE','TCS.NS':'TCS','INFY.NS':'INFY','HDFCBANK.NS':'HDFCBANK'}
def main():
 st.title('📊 SMC Trading Dashboard'); st.caption('Prototype UI based on the supplied multi-base SMC workflow')
 with st.sidebar:
  st.header('Control Panel'); ticker=st.selectbox('Instrument',list(WL),format_func=lambda x:WL[x]); custom=st.text_input('Custom ticker',''); ticker=custom.strip().upper() or ticker
  dr=st.date_input('Backtest range',(date.today()-timedelta(days=365*3),date.today())); start,end=dr if len(dr)==2 else (date.today()-timedelta(days=365*3),date.today())
  risk=st.slider('Risk / trade (%)',.1,5.,1.,.1); capital=st.number_input('Initial capital (₹)',10000.,100000000.,100000.,10000.)
  st.divider(); swing=st.checkbox('Show swing points'); bos=st.checkbox('Show BOS'); st.checkbox('Show order blocks',True); st.checkbox('Show liquidity sweeps',True); st.checkbox('Show HTF zones',True); st.checkbox('Show NIFTY confluence',True)
  run=st.button('▶ Run Analysis',type='primary',use_container_width=True)
 if run or 'results' not in st.session_state:
  with st.spinner('Running prototype analysis...'): st.session_state.results=get_strategy_results(ticker,start,end,risk,capital,swing,bos)
 r=st.session_state.results; m=r.metrics
 a,b,c,d,e=st.columns(5); a.metric('Instrument',r.ticker); b.metric('Zones',int(r.daily.Zone_Created.sum())); c.metric('Win Rate',f'{m["Win Rate"]:.1f}%'); d.metric('Profit Factor',f'{m["Profit Factor"]:.2f}' if m['Profit Factor']!=float('inf') else '∞'); e.metric('Net P/L',f'₹{m["Net PnL"]:,.0f}')
 tabs=st.tabs(['📈 Chart & Zones','🎯 Zone Scanner','🧮 Trade Score','📒 Trade Log','📊 Performance','💰 Risk Management'])
 with tabs[0]:
  st.subheader(f'{r.ticker} — Price Action / SMC'); st.plotly_chart(r.figure,use_container_width=True)
  q1,q2,q3,q4=st.columns(4); last=r.daily.iloc[-1]; q1.metric('Close',f'₹{last.Close:,.2f}'); q2.metric('RSI',f'{last.RSI:.1f}' if last.RSI==last.RSI else '—'); q3.metric('SMA 20',f'₹{last.SMA20:,.2f}' if last.SMA20==last.SMA20 else '—'); q4.metric('SMA 50',f'₹{last.SMA50:,.2f}' if last.SMA50==last.SMA50 else '—')
 with tabs[1]:
  z=r.daily[r.daily.Zone_Created].copy(); z['Zone Type']=z['Is Demand'].map({True:'Demand',False:'Supply'}); z['Date']=z.index
  st.dataframe(z[['Date','Zone Type','Proximal','Distal','Target','Base Count','Is Continuous','High Volume','Trending','BOS_Bull','BOS_Bear','Sweep_High','Sweep_Low','OB']].sort_index(ascending=False),use_container_width=True,hide_index=True) if not z.empty else st.info('No zones detected.')
 with tabs[2]:
  z=r.daily[r.daily.Zone_Created].copy(); rows=[]
  for idx,x in z.iterrows():
   score=(1.5 if x.Is_Explosive else 0)+(.5 if x['Base Count']<=3 else .25)+(.5 if x.OB else 0)+(1 if (x.BOS_Bull if x['Is Demand'] else x.BOS_Bear) else 0)+(.5 if x['High Volume'] else 0)+(.5 if x.Trending else 0); rows.append({'Date':idx,'Type':'Demand' if x['Is Demand'] else 'Supply','Score':round(score,2),'Volume':bool(x['High Volume']),'BOS':bool(x.BOS_Bull if x['Is Demand'] else x.BOS_Bear),'OB':bool(x.OB),'Trending':bool(x.Trending)})
  st.dataframe(rows,use_container_width=True,hide_index=True); st.caption('Prototype scoring only; the supplied calculate_trade_score() will be integrated later.')
 with tabs[3]:
  st.dataframe(r.trades,use_container_width=True,hide_index=True); st.download_button('Download trade log CSV',r.trades.to_csv(index=False),'trade_log.csv','text/csv') if not r.trades.empty else None
 with tabs[4]:
  a,b,c,d=st.columns(4); a.metric('Total Trades',m['Total Trades']); b.metric('Winning',m['Winning Trades']); c.metric('Expectancy',f'₹{m["Expectancy"]:,.2f}'); d.metric('Max Drawdown',f'{m["Max Drawdown"]:.2f}%')
  if not r.risk.empty: st.line_chart(r.risk.set_index('Entry Date')['Capital After Trade'])
 with tabs[5]:
  st.subheader('Sequential Risk Management'); st.caption(f'Initial capital ₹{capital:,.0f} • Risk per trade {risk:.1f}%'); st.dataframe(r.risk,use_container_width=True,hide_index=True); st.metric('Final Capital',f'₹{m["Final Capital"]:,.0f}',f'₹{m["Final Capital"]-capital:,.0f}')
if __name__=='__main__': main()
