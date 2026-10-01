/* Hosted widget contract: https://www.tradingview.com/widget-docs/widgets/charts/advanced-chart/
 * Curated exchange keys verified against TradingView /symbols/EXCHANGE-TICKER/ pages.
 * Unknown US listings require review before adding a mapping; never guess an exchange.
 */
(function(){
  'use strict';
  const US=Object.freeze({AAPL:'NASDAQ:AAPL',MSFT:'NASDAQ:MSFT',NVDA:'NASDAQ:NVDA',SPY:'AMEX:SPY',QQQ:'NASDAQ:QQQ',IWM:'AMEX:IWM',JPM:'NYSE:JPM'});
  const SCRIPT='https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';
  function symbol(row){return row?.market==='US'&&typeof row.ticker==='string'&&Object.hasOwn(US,row.ticker)?US[row.ticker]:null}
  function external(row){const mapped=symbol(row);if(mapped)return 'https://www.tradingview.com/chart/?symbol='+encodeURIComponent(mapped);if(row?.market==='MY'&&typeof row.ticker==='string'&&/^\d{4}(?:EA)?$/.test(row.ticker))return 'https://www.tradingview.com/chart/?symbol='+encodeURIComponent('MYX:'+row.ticker);return 'https://www.tradingview.com/symbols/'}
  function node(tag,text){const el=document.createElement(tag);if(text!==undefined)el.textContent=text;return el}
  function create(root){
    const chips=root.querySelector('#ta-chips'),chart=root.querySelector('#ta-chart'),status=root.querySelector('#ta-status'),caption=root.querySelector('#ta-caption'),fallback=root.querySelector('#ta-external');
    let rows=[],selected=-1,active=false,generation=0,timer=null,observer=null;
    function clear(){++generation;clearTimeout(timer);timer=null;observer?.disconnect();observer=null;chart.replaceChildren()}
    function select(index){
      if(index<0||index>=rows.length)return;selected=index;clear();
      [...chips.children].forEach((button,i)=>button.setAttribute('aria-pressed',String(i===index)));
      const row=rows[index],mapped=symbol(row);fallback.href=external(row);fallback.hidden=false;
      fallback.textContent=mapped?'Open '+row.ticker+' on TradingView':row.market==='MY'?'Open Bursa symbol on TradingView (coverage unverified)':'Find symbol on TradingView (exchange unverified)';
      if(!mapped){status.textContent=row.market==='MY'?'Bursa embed coverage is not verified here; use the external chart link.':'No curated US exchange mapping; embedded chart unavailable.';return}
      if(!active){status.textContent='Chart loads when Technical analysis is opened.';return}
      const token=generation,container=node('div');container.className='tradingview-widget-container';container.style.height='100%';container.style.width='100%';
      const widget=node('div');widget.className='tradingview-widget-container__widget';widget.style.height='calc(100% - 32px)';widget.style.width='100%';container.append(widget);
      const copyright=node('div');copyright.className='tradingview-widget-copyright';const credit=node('a','Track all markets on TradingView');credit.href='https://www.tradingview.com/';credit.target='_blank';credit.rel='noopener noreferrer';copyright.append(credit);container.append(copyright);
      const script=node('script');script.src=SCRIPT;script.type='text/javascript';script.async=true;
      script.textContent=JSON.stringify({autosize:true,symbol:mapped,interval:'D',timezone:'Etc/UTC',theme:'dark',style:'1',locale:'en',allow_symbol_change:false,calendar:false,support_host:'https://www.tradingview.com'});
      status.textContent='Loading hosted chart; the external link remains available.';
      const fail=()=>{if(token!==generation||!active)return;clear();status.textContent='Hosted chart unavailable or blocked. Use the external TradingView link.'};
      script.onerror=fail;
      // Script load alone does not establish chart/data availability. Observe only embed presence.
      observer=new MutationObserver(()=>{if(token!==generation)return;const frame=container.querySelector('iframe');if(frame){frame.title='TradingView current/delayed chart for '+row.ticker;clearTimeout(timer);status.textContent='Hosted chart frame added. Data availability/delay is shown by TradingView.'}});
      observer.observe(container,{childList:true,subtree:true});container.append(script);chart.append(container);timer=setTimeout(()=>{if(!container.querySelector('iframe'))fail()},15000);
    }
    function update(report,message){
      clear();selected=-1;chips.replaceChildren();rows=[];fallback.hidden=true;
      caption.textContent=report?.metadata?.date?'Watchlist from '+report.metadata.date+'. Chart prices are current or delayed, not frozen to the report date. Chip direction is the recorded report scenario, not a live price signal.':'Select a saved report date for its research watchlist.';
      const seen=new Set();
      for(const row of Array.isArray(report?.forecasts)?report.forecasts:[]){if(!row||typeof row.ticker!=='string'||!(/^[A-Z][A-Z0-9.\-]{0,14}$/.test(row.ticker)||/^\d{4}(?:EA)?$/.test(row.ticker))||!['US','MY'].includes(row.market))continue;const key=row.market+':'+row.ticker;if(seen.has(key))continue;seen.add(key);rows.push({ticker:row.ticker,market:row.market,direction:row.direction})}
      for(const [index,row] of rows.entries()){
        const directions={up:['📈','Up','up'],down:['📉','Down','down'],flat:['↔️','Flat','flat']},[emoji,label,color]=(typeof row.direction==='string'&&Object.hasOwn(directions,row.direction)?directions[row.direction]:['❔','Unrated','unrated']);
        const button=node('button',emoji+' '+row.ticker+' · '+label);button.type='button';button.className='ta-chip ta-'+color;button.setAttribute('aria-label',row.market+' '+row.ticker+' · '+label+' report scenario');button.setAttribute('aria-pressed','false');button.onclick=()=>select(index);
        button.onkeydown=event=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();const target=event.key==='Home'?0:event.key==='End'?rows.length-1:(index+(event.key==='ArrowRight'?1:-1)+rows.length)%rows.length;chips.children[target].focus();chips.children[target].scrollIntoView({block:'nearest',inline:'nearest',behavior:window.matchMedia?.('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'})};chips.append(button);
      }
      if(rows.length)select(0);else status.textContent=message||'No supported tickers recorded for this report.';
    }
    function show(value){const changed=active!==value;active=value;if(!active)clear();else if(changed&&selected>=0)select(selected)}
    update(null);return {update,show,destroy:clear};
  }
  window.PraesagusTA=Object.freeze({create,symbol,external});
})();
