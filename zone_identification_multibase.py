from dataclasses import dataclass
import numpy as np, pandas as pd, plotly.graph_objects as go, yfinance as yf

@dataclass
class StrategyResults:
    ticker: str; daily: pd.DataFrame; weekly: pd.DataFrame; monthly: pd.DataFrame
    trades: pd.DataFrame; risk: pd.DataFrame; metrics: dict; figure: go.Figure

def _data(ticker,start,end):
    try:
        d=yf.download(ticker,start=start,end=end,interval='1d',auto_adjust=True,progress=False)
        if isinstance(d.columns,pd.MultiIndex): d.columns=d.columns.get_level_values(0)
        if not d.empty: return d.dropna(subset=['Open','High','Low','Close']).copy()
    except Exception: pass
    rng=np.random.default_rng(abs(hash(ticker))%(2**32)); idx=pd.date_range(start,end,freq='B'); n=len(idx)
    c=100*np.exp(np.cumsum(rng.normal(.0003,.018,n))); o=np.r_[c[0],c[:-1]]*(1+rng.normal(0,.004,n))
    h=np.maximum(o,c)*(1+rng.uniform(.001,.015,n)); l=np.minimum(o,c)*(1-rng.uniform(.001,.015,n)); v=rng.integers(3e5,5e6,n)
    return pd.DataFrame({'Open':o,'High':h,'Low':l,'Close':c,'Volume':v},index=idx)

def identify_zones(df,max_base=5):
    df=df.copy(); prev=df.Close.shift(); df['TR']=pd.concat([df.High-df.Low,(df.High-prev).abs(),(df.Low-prev).abs()],axis=1).max(axis=1)
    df['ATR']=df.TR.ewm(span=14,adjust=False).mean(); body=(df.Close-df.Open).abs(); df['TR_ATR']=df.TR/df.ATR; df['Body_TR']=body/df.TR.replace(0,np.nan)
    df['Is_Exciting']=(df.TR_ATR>.7)&(df.Body_TR>.45); df['Is_Base']=(df.TR_ATR<1.05)&(df.Body_TR<.45); df['Is_Explosive']=(df.TR_ATR>1.15)&(df.Body_TR>.6)
    df['SMA20']=df.Close.rolling(20).mean(); df['SMA50']=df.Close.rolling(50).mean(); delta=df.Close.diff(); g=delta.clip(lower=0).rolling(14).mean(); lo=(-delta.clip(upper=0)).rolling(14).mean(); df['RSI']=100-100/(1+g/lo.replace(0,np.nan))
    df['High Volume']=df.Volume>((df.Volume.rolling(22).mean()+1.5*df.Volume.rolling(22).std()))
    df['Trending']=(df.Close.rolling(22).std()/df.Close.rolling(22).mean())<.055
    df['Swing_High']=df.High==df.High.rolling(11,center=True).max(); df['Swing_Low']=df.Low==df.Low.rolling(11,center=True).min()
    ph=df.High.where(df.Swing_High).ffill().shift(6); pl=df.Low.where(df.Swing_Low).ffill().shift(6); df['BOS_Bull']=df.Close>ph; df['BOS_Bear']=df.Close<pl
    rng=(df.High-df.Low).replace(0,np.nan); up=df.High-df[['Open','Close']].max(axis=1); dn=df[['Open','Close']].min(axis=1)-df.Low
    df['Sweep_High']=(df.High>ph)&(df.Close<ph)&(up/rng>.45); df['Sweep_Low']=(df.Low<pl)&(df.Close>pl)&(dn/rng>.45)
    for c in ['Zone_Created','Is Demand','Is Continuous','OB']: df[c]=False
    df['Base Count']=0; df['Proximal']=np.nan; df['Distal']=np.nan; df['Target']=np.nan
    for i in range(2,len(df)):
        if not bool(df.Is_Explosive.iloc[i]): continue
        j=i-1; cnt=0
        while j>=0 and bool(df.Is_Base.iloc[j]) and cnt<max_base: cnt+=1; j-=1
        if cnt<1 or j<0 or not bool(df.Is_Exciting.iloc[j]): continue
        demand=bool(df.Close.iloc[i]>df.Open.iloc[i]); cont=bool((df.Close.iloc[j]>df.Open.iloc[j])==demand); bs=j+1; be=i-1
        top=np.maximum(df.Open.iloc[bs:be+1],df.Close.iloc[bs:be+1]); bot=np.minimum(df.Open.iloc[bs:be+1],df.Close.iloc[bs:be+1])
        prox=float(top.max() if demand else bot.min()); dist=float(df.Low.iloc[bs:i+1].min() if demand else df.High.iloc[bs:i+1].max())
        df.iloc[i,df.columns.get_loc('Zone_Created')]=True; df.iloc[i,df.columns.get_loc('Is Demand')]=demand; df.iloc[i,df.columns.get_loc('Is Continuous')]=cont; df.iloc[i,df.columns.get_loc('OB')]=True
        df.iloc[i,df.columns.get_loc('Base Count')]=cnt; df.iloc[i,df.columns.get_loc('Proximal')]=prox; df.iloc[i,df.columns.get_loc('Distal')]=dist; df.iloc[i,df.columns.get_loc('Target')]=prox+2*(prox-dist)
    return df

def trades(df):
    out=[]
    for idx,z in df[df.Zone_Created].iterrows():
        fut=df.loc[idx:].iloc[1:]; demand=bool(z['Is Demand']); prox=float(z.Proximal); dist=float(z.Distal); tar=float(z.Target)
        hits=np.where((fut.Low<=prox) if demand else (fut.High>=prox))[0]
        if not len(hits): continue
        ei=fut.index[hits[0]]; aft=df.loc[ei:]; th=np.where((aft.High>=tar) if demand else (aft.Low<=tar))[0]; sh=np.where((aft.Low<=dist) if demand else (aft.High>=dist))[0]
        if not len(th) and not len(sh): xo=aft.index[-1]; xp=float(aft.Close.iloc[-1]); oc='No Exit (Open)'
        elif not len(sh) or (len(th) and th[0]<sh[0]): xo=aft.index[th[0]]; xp=tar; oc='Profit'
        else: xo=aft.index[sh[0]]; xp=dist; oc='Stop Loss'
        ep=prox; pnl=(xp-ep) if demand else (ep-xp); risk=abs(prox-dist)
        out.append({'Date Created':idx,'Entry Date':ei,'Exit Date':xo,'Zone Type':'Demand' if demand else 'Supply','Entry Price':ep,'Exit Price':xp,'Proximal':prox,'Distal':dist,'Target':tar,'Outcome':oc,'P/L':pnl,'R-Multiple':pnl/risk if risk else 0})
    return pd.DataFrame(out)

def risk_sim(t,capital,risk_pct):
    if t.empty:return pd.DataFrame()
    cur=float(capital); rows=[]
    for _,r in t.iterrows():
        if r.Outcome not in ['Profit','Stop Loss']: continue
        ra=cur*risk_pct/100; rp=abs(r.Proximal-r.Distal); q=int(ra/rp) if rp else 0; pnl=r['P/L']*q; before=cur; cur+=pnl
        rows.append({**r.to_dict(),'Capital At Entry':before,'Risk Amount':ra,'Quantity':q,'Trade PnL':pnl,'Capital After Trade':cur})
    return pd.DataFrame(rows)

def make_metrics(t,r,capital):
    v=t[t.Outcome.isin(['Profit','Stop Loss'])] if not t.empty else t; w=v[v.Outcome=='Profit'] if not v.empty else v; l=v[v.Outcome=='Stop Loss'] if not v.empty else v
    gp=w['P/L'].sum() if len(w) else 0; gl=abs(l['P/L'].sum()) if len(l) else 0; wr=len(w)/len(v)*100 if len(v) else 0; pf=gp/gl if gl else (float('inf') if gp else 0)
    exp=(wr/100)*(w['P/L'].mean() if len(w) else 0)-(1-wr/100)*(abs(l['P/L'].mean()) if len(l) else 0)
    dd=((r['Capital After Trade'].cummax()-r['Capital After Trade'])/r['Capital After Trade'].cummax()).max()*100 if not r.empty else 0
    return {'Total Trades':len(v),'Winning Trades':len(w),'Win Rate':wr,'Profit Factor':pf,'Net PnL':v['P/L'].sum() if len(v) else 0,'Expectancy':exp,'Final Capital':float(r['Capital After Trade'].iloc[-1]) if not r.empty else capital,'Max Drawdown':float(dd)}

def figure(df,show_swing=False,show_bos=False):
    f=go.Figure([go.Candlestick(x=df.index,open=df.Open,high=df.High,low=df.Low,close=df.Close,name='Price'),go.Scatter(x=df.index,y=df.SMA20,name='SMA 20'),go.Scatter(x=df.index,y=df.SMA50,name='SMA 50')])
    for idx,z in df[df.Zone_Created].iterrows():
        col='rgba(0,180,80,.18)' if z['Is Demand'] else 'rgba(220,50,50,.18)'; f.add_shape(type='rect',x0=idx,x1=df.index[-1],y0=z.Proximal,y1=z.Distal,fillcolor=col,line=dict(width=1),layer='below')
    if show_swing:
        for mask,name,y,sym in [(df.Swing_High,'Swing High',df.High,'triangle-up'),(df.Swing_Low,'Swing Low',df.Low,'triangle-down')]:
            x=df[mask]; f.add_trace(go.Scatter(x=x.index,y=y.loc[x.index],mode='markers',name=name,marker_symbol=sym))
    if show_bos:
        for mask,name,y in [(df.BOS_Bull,'BOS Bull',df.High*1.01),(df.BOS_Bear,'BOS Bear',df.Low*.99)]:
            x=df[mask]; f.add_trace(go.Scatter(x=x.index,y=y.loc[x.index],mode='markers',name=name,marker_symbol='star'))
    f.update_layout(height=650,xaxis_rangeslider_visible=False,margin=dict(l=10,r=10,t=20,b=10)); return f

def run_strategy_for_ticker(ticker,start_date,end_date,risk_pct,initial_capital,show_swing=False,show_bos=False):
    d=identify_zones(_data(ticker,start_date,end_date)); w=identify_zones(d.resample('W-FRI').agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'}).dropna()); m=identify_zones(d.resample('ME').agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'}).dropna()); t=trades(d); r=risk_sim(t,initial_capital,risk_pct); met=make_metrics(t,r,initial_capital); return StrategyResults(ticker,d,w,m,t,r,met,figure(d,show_swing,show_bos))
